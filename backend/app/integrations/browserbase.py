from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import Settings, get_settings
from app.integrations.browserbase_automations import verify_registration_site, verify_slack_link
from app.integrations.slack import provision_slack
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)


@dataclass
class PlatformProvisionResult:
    success: bool
    fallback_guide: str = ""


def _devpost_fallback_guide(profile: EventProfile) -> str:
    site = profile.artifacts.site_url or "(your registration site URL)"
    return (
        f"Manual Devpost setup for {profile.event.name}:\n"
        "1. Log in to https://devpost.com as organizer\n"
        "2. Create new hackathon\n"
        f"3. Set dates, location, and registration link: {site}\n"
        "4. Save as draft until assets are ready"
    )


async def _run_browserbase_devpost(profile: EventProfile, settings: Settings) -> str | None:
    if not settings.browserbase_api_key or not profile.ops.needs_devpost:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.browserbase.com/v1/sessions",
            headers={"X-BB-API-Key": settings.browserbase_api_key},
            json={"projectId": settings.browserbase_project_id},
            timeout=120.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Browserbase API error: {response.status_code}")
        data = response.json()
        return data.get("devpost_url") or None


async def provision_platforms(
    profile: EventProfile,
    settings: Settings | None = None,
) -> PlatformProvisionResult:
    """Slack via Web API. Devpost via Browserbase only when explicitly enabled."""
    tracer = get_tracer()
    cfg = settings or get_settings()
    guides: list[str] = []
    ok = True

    async with tracer.span("platforms.provision", session_id=profile.session_id):
        if profile.ops.needs_slack:
            slack_result = await provision_slack(profile, cfg)
            if not slack_result.success:
                ok = False
                guide = (
                    f"Manual Slack setup for {profile.event.name}:\n"
                    "1. Go to https://slack.com/create\n"
                    "2. Create channels: #general, #announcements, #help, #team-formation\n"
                    f"Slack API error: {slack_result.error or 'not configured'}"
                )
                guides.append(guide)
                profile.artifacts.fallback_guides.append(guide)

        if profile.ops.needs_devpost and cfg.devpost_enabled:
            try:
                devpost_url = await _run_browserbase_devpost(profile, cfg)
                if devpost_url:
                    profile.artifacts.devpost_url = devpost_url
                else:
                    ok = False
                    guide = _devpost_fallback_guide(profile)
                    guides.append(guide)
                    profile.artifacts.fallback_guides.append(guide)
            except Exception as exc:
                logger.warning("Devpost provision failed for %s: %s", profile.session_id, exc)
                ok = False
                guide = _devpost_fallback_guide(profile)
                guides.append(guide)
                profile.artifacts.fallback_guides.append(guide)

        return PlatformProvisionResult(
            success=ok,
            fallback_guide="\n\n".join(guides),
        )


def _build_dir(profile: EventProfile, settings: Settings) -> Path | None:
    slug = profile.session_id.replace(":", "_").replace("+", "")
    build_dir = Path(settings.build_output_dir) / slug
    return build_dir if build_dir.is_dir() else None


async def run_post_build_automations(
    profile: EventProfile,
    settings: Settings | None = None,
) -> EventProfile:
    """
    Easiest Browserbase wins (no third-party logins):
    - QA the live registration site + optional test signup
    - Smoke-check Slack workspace URL
    """
    tracer = get_tracer()
    cfg = settings or get_settings()
    if not cfg.browserbase_enabled or not cfg.browserbase_api_key:
        return profile

    site_url = profile.artifacts.site_url or ""
    build_dir = _build_dir(profile, cfg)

    async with tracer.span("browserbase.post_build", session_id=profile.session_id):
        if cfg.browserbase_verify_site and site_url.startswith("http"):
            screenshot = (
                (build_dir / "assets" / "site-qa.png")
                if build_dir
                else Path(cfg.assets_output_dir) / profile.session_id.replace(":", "_") / "site-qa.png"
            )
            qa = await verify_registration_site(
                site_url=site_url,
                screenshot_path=screenshot,
                test_registration=cfg.browserbase_test_registration,
                event_name=profile.event.name,
                settings=cfg,
            )
            if qa:
                if qa.session_url:
                    profile.artifacts.browserbase_session_urls.append(qa.session_url)
                profile.artifacts.site_verified = qa.ok
                if qa.screenshot_path:
                    profile.artifacts.qa_screenshot_path = qa.screenshot_path
                    if build_dir:
                        assets = build_dir / "assets"
                        assets.mkdir(exist_ok=True)
                        dest = assets / "site-qa.png"
                        if Path(qa.screenshot_path) != dest:
                            shutil.copy2(qa.screenshot_path, dest)
                status = "passed" if qa.ok else "needs review"
                profile.artifacts.fallback_guides.append(
                    f"Browserbase site QA {status}: {qa.detail}\nRecording: {qa.session_url or 'n/a'}"
                )

        if (
            cfg.browserbase_verify_slack
            and profile.ops.needs_slack
            and profile.artifacts.slack_url.startswith("http")
        ):
            slack_check = await verify_slack_link(slack_url=profile.artifacts.slack_url, settings=cfg)
            if slack_check:
                ok, detail = slack_check
                if "browserbase.com/sessions/" in detail:
                    session_url = detail.split(" · ")[-1]
                    profile.artifacts.browserbase_session_urls.append(session_url)
                note = f"Browserbase Slack smoke test: {'ok' if ok else 'check manually'} — {detail}"
                profile.artifacts.fallback_guides.append(note)

    return profile
