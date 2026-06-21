from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.config import Settings, get_settings
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"
DEFAULT_CHANNELS = ("general", "announcements", "help", "team-formation")

SCOPE_HINT = (
    " — add Bot scopes channels:manage, channels:read, chat:write at "
    "https://api.slack.com/apps → EventPlannerAgent → OAuth & Permissions, "
    "reinstall app, then set SLACK_ACCESS_TOKEN to the Bot User OAuth Token (xoxb-...)"
)


def _scope_hint(error: str) -> str:
    return SCOPE_HINT if error == "missing_scope" else ""


class SlackError(Exception):
    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__(error)


@dataclass
class SlackProvisionResult:
    success: bool
    workspace_url: str = ""
    channel_ids: list[str] | None = None
    error: str = ""


def _event_channel_prefix(event_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (event_name or "event").lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)[:18] or "event"
    return f"ep-{slug}"


async def _slack_call(token: str, method: str, payload: dict | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SLACK_API}/{method}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=payload or {},
            timeout=30.0,
        )
        data = response.json()
        if not data.get("ok"):
            raise SlackError(str(data.get("error", "unknown_error")))
        return data


async def _create_or_get_channel(token: str, name: str) -> str:
    try:
        created = await _slack_call(token, "conversations.create", {"name": name, "is_private": False})
        return str(created["channel"]["id"])
    except SlackError as exc:
        if exc.error != "name_taken":
            raise
        listed = await _slack_call(
            token,
            "conversations.list",
            {"types": "public_channel", "exclude_archived": True, "limit": 1000},
        )
        for channel in listed.get("channels", []):
            if channel.get("name") == name:
                return str(channel["id"])
        raise


async def provision_slack(
    profile: EventProfile,
    settings: Settings | None = None,
) -> SlackProvisionResult:
    """
    Provision event channels in a pre-existing Slack workspace via Web API.
    Requires SLACK_ACCESS_TOKEN (xoxb bot or xoxp user token with channels:manage).
    """
    tracer = get_tracer()
    cfg = settings or get_settings()

    async with tracer.span("slack.provision", session_id=profile.session_id):
        token = cfg.slack_access_token
        if not token:
            logger.info("Slack token not configured for %s", profile.session_id)
            return SlackProvisionResult(success=False, error="not_configured")

        try:
            auth = await _slack_call(token, "auth.test")
            workspace_url = str(auth.get("url") or "").rstrip("/")
            prefix = _event_channel_prefix(profile.event.name)
            channel_ids: list[str] = []

            for suffix in DEFAULT_CHANNELS:
                channel_name = f"{prefix}-{suffix}"[:80]
                channel_id = await _create_or_get_channel(token, channel_name)
                channel_ids.append(channel_id)

            welcome = (
                f"Welcome to *{profile.event.name or 'your event'}* — "
                f"channels for this event are prefixed `{prefix}-`."
            )
            await _slack_call(
                token,
                "chat.postMessage",
                {"channel": channel_ids[0], "text": welcome},
            )

            invite = cfg.slack_invite_url.strip() or workspace_url
            profile.artifacts.slack_url = invite
            logger.info("Slack provisioned for %s: %s (%d channels)", profile.session_id, invite, len(channel_ids))
            return SlackProvisionResult(
                success=True,
                workspace_url=invite,
                channel_ids=channel_ids,
            )

        except SlackError as exc:
            logger.warning("Slack provision failed for %s: %s", profile.session_id, exc.error)
            hint = _scope_hint(exc.error)
            return SlackProvisionResult(success=False, error=f"{exc.error}{hint}")
        except Exception as exc:
            logger.warning("Slack provision failed for %s: %s", profile.session_id, exc)
            return SlackProvisionResult(success=False, error=str(exc))
