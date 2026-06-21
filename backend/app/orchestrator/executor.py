from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.integrations.browserbase import provision_platforms, run_post_build_automations
from app.integrations.claude_code import build_and_deploy_site
from app.integrations.midjourney import generate_brand_assets
from app.integrations.outreach import generate_outreach_drafts
from app.integrations.pika import generate_promo_clip
from app.memory.schema import EventProfile, SessionStatus
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], Awaitable[None]]


async def _notify(on_progress: ProgressCallback | None, message: str) -> None:
    if on_progress:
        await on_progress(message)


async def run_creative_pipeline(
    profile: EventProfile,
    on_checkpoint: Callable[[EventProfile], Awaitable[None]] | None = None,
) -> EventProfile:
    profile = await generate_brand_assets(profile)
    if on_checkpoint:
        await on_checkpoint(profile)
    profile = await generate_promo_clip(profile)
    return profile


async def run_execution(
    profile: EventProfile,
    on_progress: ProgressCallback | None = None,
    on_checkpoint: Callable[[EventProfile], Awaitable[None]] | None = None,
) -> EventProfile:
    """
    Phase 3 calibrated execution — Tier-1 fan-out with graceful Browserbase fallback.
    Creative + Browserbase run in parallel; site build consumes generated assets.
    Outreach is Tier-3 draft-only.
    """
    tracer = get_tracer()
    async with tracer.span("executor.run", session_id=profile.session_id):
        profile.status = SessionStatus.EXECUTING
        logger.info("executor: starting build for %s", profile.session_id)

        await _notify(on_progress, "Generating brand assets (~45s)…")

        creative_task = asyncio.create_task(run_creative_pipeline(profile, on_checkpoint=on_checkpoint))
        browser_task = asyncio.create_task(provision_platforms(profile))

        profile = await creative_task
        if on_checkpoint:
            await on_checkpoint(profile)
        browser_result = await browser_task

        if not browser_result.success:
            await _notify(
                on_progress,
                "Some platform setup needs manual steps — continuing build.",
            )
        elif profile.ops.needs_slack and profile.artifacts.slack_url:
            await _notify(on_progress, "Slack ready. OpenCode is building your registration site (~1–3 min)…")
        else:
            await _notify(on_progress, "OpenCode is building your registration site (~1–3 min)…")

        profile = await build_and_deploy_site(profile)
        if on_checkpoint:
            await on_checkpoint(profile)

        await _notify(on_progress, "Running Browserbase QA on your live site…")
        profile = await run_post_build_automations(profile)

        await _notify(on_progress, "Drafting sponsor outreach (for your approval)…")
        profile = await generate_outreach_drafts(profile)

        profile.status = SessionStatus.AWAITING_HANDOFF
        logger.info("executor: complete for %s site=%s", profile.session_id, profile.artifacts.site_url)

    return profile


def _platform_line(label: str, url: str, needs: bool) -> str | None:
    if not needs:
        return None
    if url:
        return f"• {label}: {url}"
    return f"• {label}: manual setup (see setup-guides.txt on your site)"


def format_handoff_message(profile: EventProfile) -> str:
    """Phase 4 — present Tier-3 drafts and deliverables for human gate."""
    a = profile.artifacts
    lines = [
        "*Build complete — review before send/spend*",
        f"• Site: {a.site_url or 'pending'}",
    ]
    if slack := _platform_line("Slack", a.slack_url, profile.ops.needs_slack):
        lines.append(slack)
    if devpost := _platform_line("Devpost", a.devpost_url, profile.ops.needs_devpost):
        lines.append(devpost)
    if a.site_verified:
        lines.append("• Site QA: passed (Browserbase)")
    if a.browserbase_session_urls:
        lines.append(f"• Browserbase recordings: {len(a.browserbase_session_urls)}")
    if a.asset_urls:
        lines.append(f"• Assets: {len(a.asset_urls)} file(s)")
    if a.promo_video_url:
        lines.append(f"• Promo: {a.promo_video_url}")
    if a.fallback_guides:
        lines.append(f"• Manual guides: {len(a.fallback_guides)} (on site + in session)")
    lines.append(f"• Outreach drafts: {len(a.outreach_drafts)}")
    lines.append("")
    lines.append("Reply SEND / EDIT / SKIP per draft, or ALL-SKIP to finish.")
    return "\n".join(lines)


def format_final_delivery(profile: EventProfile) -> str:
    """Phase 5 — wrap-up SMS."""
    a = profile.artifacts
    lines = [
        f"🎉 {profile.event.name or 'Your event'} is ready!",
        f"Site: {a.site_url}",
    ]
    if profile.ops.needs_slack:
        lines.append(f"Slack: {a.slack_url or 'manual setup guide on your site'}")
    if profile.ops.needs_devpost:
        lines.append(f"Devpost: {a.devpost_url or 'manual setup guide on your site'}")
    if a.outreach_drafts:
        lines.append(f"Outreach drafts saved ({len(a.outreach_drafts)}) — not sent.")
    if a.fallback_guides:
        lines.append("Manual setup guides saved on your registration site.")
    return "\n".join(lines)
