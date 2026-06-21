#!/usr/bin/env python3
"""Reproduce the exact Phase-3 execution run with full logging and NO error swallowing.

Loads the live 'phone:dashboard-demo' session (Berkeley AI Hackathon) — or rebuilds
an equivalent profile — flips it to approved, and runs the executor pipeline directly
so any exception in image generation / site build surfaces with a full traceback.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from app.memory.redis_store import get_session_store
from app.memory.schema import EventProfile, SessionStatus
from app.orchestrator.executor import run_execution

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
# Quiet noisy libraries but keep our app + http at INFO+
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = logging.getLogger("simulate_run")

SESSION_ID = "phone:dashboard-demo"


def _fallback_profile() -> EventProfile:
    """Recreate the exact Berkeley AI Hackathon profile if no session is stored."""
    p = EventProfile.new_session("dashboard-demo")
    p.event.name = "Berkeley AI Hackathon"
    p.event.type = "hackathon"
    p.event.dates = "July, 2027"
    p.event.location = "Berkeley, CA"
    p.event.expected_attendees = 1300
    p.event.format = "in_person"
    p.budget.total_usd = 10000
    p.budget.paid_tools_allowed = True
    p.audience.description = "CS, CE majors"
    p.aesthetic.vibe = "Yellow, blue, hackathon, tech, academic"
    p.aesthetic.theme = "Academic, college, hackathon"
    p.aesthetic.colors = ["blue"]
    p.ops.needs_slack = True
    p.ops.needs_devpost = False
    p.outreach.sponsor_targets = ["Midjourney", "Anthropic"]
    p.outreach.channels = ["email"]
    return p


async def main() -> int:
    store = get_session_store()
    profile = await store.get(SESSION_ID)
    if profile is None:
        log.warning("No stored session %s — using fallback profile", SESSION_ID)
        profile = _fallback_profile()
    else:
        log.info("Loaded stored session %s (status=%s)", SESSION_ID, profile.status)

    # Reset to a clean pre-execution state so we replay the exact build.
    profile.status = SessionStatus.EXECUTING
    profile.approvals.plan_approved = True

    async def on_progress(msg: str) -> None:
        log.info("PROGRESS → %s", msg)

    async def on_checkpoint(p: EventProfile) -> None:
        log.info("CHECKPOINT (status=%s, assets=%d, site=%r)",
                 p.status, len(p.artifacts.asset_urls), p.artifacts.site_url)

    log.info("=== STARTING run_execution ===")
    profile = await run_execution(profile, on_progress=on_progress, on_checkpoint=on_checkpoint)
    log.info("=== run_execution COMPLETE ===")

    a = profile.artifacts
    log.info("RESULT status=%s", profile.status)
    log.info("  asset_urls       = %s", a.asset_urls)
    log.info("  asset_dir        = %r", a.asset_dir)
    log.info("  promo_video_url  = %r", a.promo_video_url)
    log.info("  site_url         = %r", a.site_url)
    log.info("  slack_url        = %r", a.slack_url)
    log.info("  outreach_drafts  = %d", len(a.outreach_drafts))
    log.info("  fallback_guides  = %d", len(a.fallback_guides))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
