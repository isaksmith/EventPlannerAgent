#!/usr/bin/env python3
"""Rebuild + redeploy the registration site for an existing session, reusing the
brand images already generated in this session's asset_dir.

Runs build_and_deploy_site directly (skips the creative pipeline) so it consumes
the existing brand assets and the configured OPENROUTER_MODEL (DeepSeek) for the
site coder. Surfaces the resulting site_url with full logging and no swallowing.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from app.config import get_settings
from app.integrations.claude_code import build_and_deploy_site
from app.memory.redis_store import get_session_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = logging.getLogger("rebuild_site")

SESSION_ID = "phone:dashboard-demo"


async def main() -> int:
    cfg = get_settings()
    log.info("Site coder model = %s", cfg.openrouter_model)

    store = get_session_store()
    profile = await store.get(SESSION_ID)
    if profile is None:
        log.error("No stored session %s — run the interview + APPROVE first.", SESSION_ID)
        return 1

    a = profile.artifacts
    log.info(
        "Reusing brand assets: dir=%s asset_urls=%d",
        a.asset_dir or "(none)",
        len(a.asset_urls),
    )
    if not a.asset_dir:
        log.warning("artifacts.asset_dir is empty — site coder will have no brand images to use.")

    log.info("=== build_and_deploy_site START (DeepSeek) ===")
    profile = await build_and_deploy_site(profile, cfg)
    log.info("=== build_and_deploy_site DONE ===")

    await store.save(profile)

    log.info("RESULT site_url = %s", profile.artifacts.site_url or "(none)")
    log.info("RESULT site_verified = %s", profile.artifacts.site_verified)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
