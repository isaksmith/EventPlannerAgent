#!/usr/bin/env python3
"""Regenerate an event registration site with the OpenRouter coding subagent."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.integrations.claude_code import build_and_deploy_site
from app.integrations.site_workspace import run_site_generation_for_slug
from app.memory.schema import EventProfile


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()

    if args.from_profile_json:
        profile = EventProfile.model_validate_json(
            args.from_profile_json.read_text(encoding="utf-8")
        )
        profile = await build_and_deploy_site(profile, settings)
        print(f"Built site: {profile.artifacts.site_url}")
        return 0

    if args.reseed_template:
        from pathlib import Path

        from app.integrations.claude_code import _copy_assets_into_build
        from app.integrations.site_template import seed_event_site

        build_dir = Path(settings.build_output_dir) / args.slug
        profile_path = build_dir / "event_profile.json"
        if not profile_path.is_file():
            print(f"No event_profile.json in {build_dir}", file=sys.stderr)
            return 1
        profile = EventProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
        _copy_assets_into_build(profile, build_dir)
        seed_event_site(build_dir, profile)
        print(f"Reseeded template: {build_dir / 'index.html'}")
        if settings.public_base_url:
            print(f"Preview: {settings.public_base_url.rstrip('/')}/sites/{args.slug}/")
        else:
            print(f"Preview: http://127.0.0.1:8000/sites/{args.slug}/")
        return 0

    ok, msg, build_dir = await run_site_generation_for_slug(args.slug, settings)
    if ok:
        print(f"OK — {msg}")
        print(f"Site files: {build_dir / 'index.html'}")
        if settings.public_base_url:
            print(f"Public URL: {settings.public_base_url.rstrip('/')}/sites/{args.slug}/")
        return 0

    print(f"FAILED — {msg}", file=sys.stderr)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate event site HTML via OpenCode CLI (OpenRouter fallback).",
    )
    parser.add_argument(
        "--slug",
        default="phone_dashboard-demo",
        help="Build directory slug (default: phone_dashboard-demo)",
    )
    parser.add_argument(
        "--from-profile-json",
        type=argparse.FileType("r", encoding="utf-8"),
        help="Full rebuild: load EventProfile JSON and run build_and_deploy_site",
    )
    parser.add_argument(
        "--reseed-template",
        action="store_true",
        help="Re-render index.html from the Marquee template (skip OpenCode)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
