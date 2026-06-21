#!/usr/bin/env python3
"""Deploy the ALREADY-BUILT site for the current session to Vercel, bypassing the
site coder. Validates the fixed Vercel deployment payload and uses the brand
images already copied into the build dir.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.config import get_settings
from app.integrations.vercel_deploy import deploy_site_to_vercel
from app.memory.redis_store import get_session_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s")
logging.getLogger("httpx").setLevel(logging.INFO)
log = logging.getLogger("deploy_only")

SESSION_ID = "phone:dashboard-demo"


async def main() -> int:
    cfg = get_settings()
    slug = SESSION_ID.replace(":", "_").replace("+", "")
    build_dir = Path(cfg.build_output_dir) / slug
    index = build_dir / "index.html"
    if not index.is_file():
        log.error("No built site at %s — run rebuild first.", index)
        return 1
    log.info("Deploying built site: %s (%d bytes) assets=%s",
             index, index.stat().st_size,
             [p.name for p in (build_dir / "assets").glob("*")] if (build_dir / "assets").is_dir() else [])

    url = await deploy_site_to_vercel(
        build_dir, slug=slug, event_name="Berkeley AI Hackathon", settings=cfg
    )
    log.info("RESULT deploy_url = %s", url or "(none)")

    if url:
        store = get_session_store()
        profile = await store.get(SESSION_ID)
        if profile is not None:
            profile.artifacts.site_url = url
            await store.save(profile)
            log.info("Saved site_url to session.")
    return 0 if url else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
