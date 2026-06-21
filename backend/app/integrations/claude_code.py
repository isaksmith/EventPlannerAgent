from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import Settings, get_settings
from app.integrations.site_generation import generate_site_html
from app.integrations.site_template import render_event_site, seed_event_site
from app.integrations.token_compression import compress_profile_context
from app.integrations.vercel_deploy import deploy_site_to_vercel
from app.memory.schema import EventProfile
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)


def _build_site_html(profile: EventProfile, *, slug: str) -> str:
    """Render the shared Marquee event site template (backwards-compatible alias)."""
    del slug
    return render_event_site(profile)


def _session_build_dir(profile: EventProfile, settings: Settings) -> Path:
    path = Path(settings.build_output_dir) / _session_slug(profile)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_assets_into_build(profile: EventProfile, build_dir: Path) -> None:
    assets_dir = build_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    if not profile.artifacts.asset_dir:
        return
    src = Path(profile.artifacts.asset_dir)
    if not src.exists():
        return
    for item in src.iterdir():
        if item.is_file() and item.suffix in {".svg", ".png", ".jpg", ".webp", ".mp4"}:
            shutil.copy2(item, assets_dir / item.name)


def _session_slug(profile: EventProfile) -> str:
    return profile.session_id.replace(":", "_").replace("+", "")


def _public_site_url(profile: EventProfile, settings: Settings, slug: str) -> str | None:
    """Optional fallback to a self-hosted public base (e.g. tunnel) when Vercel is unavailable."""
    if settings.public_base_url:
        return f"{settings.public_base_url.rstrip('/')}/sites/{slug}/"
    return None


async def build_and_deploy_site(
    profile: EventProfile,
    settings: Settings | None = None,
) -> EventProfile:
    tracer = get_tracer()
    cfg = settings or get_settings()
    context = compress_profile_context(profile)

    async with tracer.span("claude_code.build", session_id=profile.session_id, context_len=len(context)):
        build_dir = _session_build_dir(profile, cfg)
        _copy_assets_into_build(profile, build_dir)

        index_path = build_dir / "index.html"
        # generate_site_html runs the full pipeline (UI/UX Pro Max design system +
        # OpenRouter site coder primary, OpenCode optional, Marquee template fallback)
        # and seeds the workspace itself, so always invoke it.
        agent_ok, agent_msg = await generate_site_html(build_dir, profile, cfg)
        if agent_ok:
            logger.info("Site build: %s", agent_msg)
        else:
            logger.warning("Site generation failed (%s); using Marquee template", agent_msg)

        if not index_path.is_file():
            seed_event_site(build_dir, profile)
            logger.warning("index.html missing after build; re-seeded from template")

        if profile.artifacts.fallback_guides:
            guides_path = build_dir / "setup-guides.txt"
            guides_path.write_text("\n\n---\n\n".join(profile.artifacts.fallback_guides), encoding="utf-8")

        schema_path = build_dir / "event_profile.json"
        schema_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

        slug = _session_slug(profile)
        deploy_url = await deploy_site_to_vercel(
            build_dir,
            slug=slug,
            event_name=profile.event.name or "Your Event",
            settings=cfg,
        )
        public_url = _public_site_url(profile, cfg, slug)

        if deploy_url:
            profile.artifacts.site_url = deploy_url
            logger.info("Site deployed to Vercel: %s", deploy_url)
        elif public_url:
            profile.artifacts.site_url = public_url
            logger.info("Vercel unavailable; using self-hosted public URL: %s", public_url)
        else:
            profile.artifacts.site_url = f"file://{index_path.resolve()}"
            logger.info("Site written to %s", index_path)

    return profile
