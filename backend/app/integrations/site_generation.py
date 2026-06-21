from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings, get_settings
from app.integrations.openrouter_auth import resolve_openrouter_api_key
from app.integrations.opencode_coder import generate_site_with_opencode, opencode_available
from app.integrations.site_coder import generate_site_with_openrouter
from app.integrations.site_workspace import prepare_site_workspace, validate_generated_site
from app.integrations.ui_ux_pro_max import generate_design_system
from app.memory.schema import EventProfile

logger = logging.getLogger(__name__)


async def generate_site_html(
    build_dir: Path,
    profile: EventProfile,
    settings: Settings | None = None,
) -> tuple[bool, str]:
    """
    Event site generation pipeline (every APPROVE):
    1. Seed Marquee template + assets
    2. UI/UX Pro Max design system for this event
    3. OpenRouter site coder (primary) — customizes index.html
    4. OpenCode CLI (optional fallback)
    5. Pre-seeded template if both agents fail
    """
    cfg = settings or get_settings()
    prepare_site_workspace(build_dir, profile, reseed=True)

    design_system = ""
    if cfg.ui_ux_pro_max_enabled:
        design_system = generate_design_system(profile, build_dir, cfg)
        if design_system:
            logger.info("UI/UX Pro Max design system ready (%d chars)", len(design_system))
        else:
            logger.warning("UI/UX Pro Max design system empty; coder uses template defaults")

    if cfg.site_coder_enabled and resolve_openrouter_api_key(cfg):
        ok, msg = await generate_site_with_openrouter(
            build_dir, profile, cfg, design_system=design_system
        )
        if ok:
            return True, msg
        logger.warning("OpenRouter UI/UX site coder failed (%s)", msg)
    elif cfg.site_coder_enabled:
        logger.warning("Site coder enabled but OPENROUTER_API_KEY missing")

    if cfg.opencode_enabled and opencode_available(cfg):
        ok, msg = await generate_site_with_opencode(build_dir, profile, cfg)
        if ok:
            return True, msg
        logger.warning("OpenCode site generation failed (%s)", msg)
    elif cfg.opencode_enabled:
        logger.warning(
            "OpenCode not available — install CLI or set OPENCODE_BIN (looked for %s)",
            cfg.opencode_bin,
        )

    ok, reason = validate_generated_site(build_dir / "index.html", profile)
    if ok:
        return True, "Marquee template (agents unavailable or failed validation retry)"
    return False, f"Site generation failed; template invalid: {reason}"
