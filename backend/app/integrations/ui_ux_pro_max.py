from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from app.config import Settings, get_settings
from app.memory.schema import EventProfile

logger = logging.getLogger(__name__)

_SKILL_ROOT = Path(__file__).resolve().parent.parent.parent / "skills" / "ui-ux-pro-max"
_SEARCH_SCRIPT = _SKILL_ROOT / "scripts" / "search.py"


def _enum_label(value: object) -> str:
    raw = value.value if hasattr(value, "value") else str(value)
    return raw.replace("_", " ").title()


def design_query_for_profile(profile: EventProfile) -> str:
    """Build a UI/UX Pro Max search query from event profile fields."""
    e = profile.event
    parts = [
        "event landing page registration",
        _enum_label(e.type),
        _enum_label(e.format),
        profile.aesthetic.vibe,
        getattr(profile.aesthetic, "theme", "") or "",
        profile.aesthetic.colors and " ".join(profile.aesthetic.colors) or "",
        e.name,
        profile.audience.description,
    ]
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def _project_name(profile: EventProfile) -> str:
    return (profile.event.name or profile.session_id).strip()[:80] or "Marquee Event"


def generate_design_system(
    profile: EventProfile,
    build_dir: Path | None = None,
    settings: Settings | None = None,
) -> str:
    """
    Run UI/UX Pro Max --design-system search for this event.
    Persists MASTER.md under build_dir when provided; returns markdown text.
    """
    cfg = settings or get_settings()
    if not cfg.ui_ux_pro_max_enabled:
        return ""

    if not _SEARCH_SCRIPT.is_file():
        logger.warning("UI/UX Pro Max skill missing at %s", _SEARCH_SCRIPT)
        return ""

    query = design_query_for_profile(profile)
    project = _project_name(profile)
    cmd = [
        sys.executable,
        str(_SEARCH_SCRIPT),
        query,
        "--design-system",
        "-p",
        project,
        "-f",
        "markdown",
    ]

    logger.info("UI/UX Pro Max design system query=%r project=%r", query[:120], project)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_SKILL_ROOT),
            timeout=cfg.ui_ux_pro_max_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("UI/UX Pro Max design system timed out")
        return ""
    except OSError as exc:
        logger.warning("UI/UX Pro Max subprocess failed: %s", exc)
        return ""

    if result.returncode != 0:
        logger.warning(
            "UI/UX Pro Max search failed (exit %s): %s",
            result.returncode,
            (result.stderr or result.stdout)[:500],
        )
        return ""

    markdown = result.stdout.strip()
    if build_dir is not None and markdown:
        ds_dir = build_dir / "design-system"
        ds_dir.mkdir(parents=True, exist_ok=True)
        (ds_dir / "MASTER.md").write_text(markdown, encoding="utf-8")
        (build_dir / "UI_UX_DESIGN_SYSTEM.md").write_text(markdown, encoding="utf-8")

    return markdown
