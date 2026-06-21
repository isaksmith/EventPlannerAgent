from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.integrations.slack import provision_slack
from app.memory.schema import EventProfile, SessionStatus
from app.observability.arize import get_tracer

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/traces")
async def recent_traces() -> dict:
    """Recent execution spans for demo / Arize debugging."""
    tracer = get_tracer()
    spans = [
        {
            "name": s.name,
            "latency_ms": round(s.latency_ms or 0, 1),
            "attributes": s.attributes,
        }
        for s in tracer.recent_spans()[-50:]
    ]
    return {"arize_enabled": tracer.enabled, "spans": spans}


@router.get("/slack/test")
async def test_slack(provision: bool = Query(default=False, description="Create demo channels")) -> dict:
    """Verify Slack token; optionally run a one-off channel provision."""
    from app.integrations.slack import SlackError, _slack_call

    settings = get_settings()
    if not settings.slack_access_token:
        raise HTTPException(status_code=400, detail="SLACK_ACCESS_TOKEN not set in .env")

    try:
        auth = await _slack_call(settings.slack_access_token, "auth.test")
    except SlackError as exc:
        raise HTTPException(status_code=502, detail=f"Slack auth.test failed: {exc.error}") from exc

    result: dict = {
        "ok": True,
        "team": auth.get("team"),
        "user": auth.get("user"),
        "workspace_url": auth.get("url"),
        "invite_url_configured": bool(settings.slack_invite_url),
    }

    if provision:
        profile = EventProfile.new_session("phone:admin-test")
        profile.event.name = "OrchestrateAI Demo Test"
        profile.ops.needs_slack = True
        profile.status = SessionStatus.EXECUTING
        slack = await provision_slack(profile)
        result["provision"] = {
            "success": slack.success,
            "slack_url": profile.artifacts.slack_url,
            "channels_created": len(slack.channel_ids or []),
            "error": slack.error or None,
        }

    return result
