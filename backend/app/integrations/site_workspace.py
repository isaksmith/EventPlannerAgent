from __future__ import annotations

import shutil
from pathlib import Path

from app.config import Settings, get_settings
from app.integrations.site_template import seed_event_site
from app.integrations.token_compression import compress_profile_context
from app.memory.schema import EventProfile

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_OPENCODE_TEMPLATE_DIR = _BACKEND_ROOT / ".opencode"


def site_brief(profile: EventProfile, slug: str) -> str:
    e = profile.event
    fields = profile.ops.registration_fields or ["name", "email", "team"]
    colors = ", ".join(profile.aesthetic.colors) or "(use tasteful defaults)"
    theme = getattr(profile.aesthetic, "theme", "") or profile.aesthetic.vibe or ""
    lines = [
        f"# Site brief — {e.name or slug}",
        "",
        compress_profile_context(profile),
        "",
        "## Registration",
        f"- Fields: {', '.join(fields)}",
        "- Submit: POST ./register (FormData, fetch with ngrok-skip-browser-warning header)",
        "",
        "## Template",
        "- `index.html` — pre-rendered from the shared Marquee event site template",
        "- `UI_UX_DESIGN_SYSTEM.md` — UI/UX Pro Max design system for this event",
        "- `site_template.html` — raw template with placeholders (reference only)",
        "- Customize colors, copy, and imagery to match the event; keep registration wiring intact",
        "",
        "## Brand",
        f"- Colors: {colors}",
        f"- Vibe/theme: {theme or 'match event type'}",
        "- Logo/images: ./assets/ (inspect directory before referencing)",
        "",
        "## Links",
        f"- Slack: {profile.artifacts.slack_url or 'none'}",
        f"- Devpost: {profile.artifacts.devpost_url or 'none'}",
    ]
    return "\n".join(lines)


def validate_generated_site(index_path: Path, profile: EventProfile) -> tuple[bool, str]:
    if not index_path.is_file():
        return False, "index.html missing"
    html = index_path.read_text(encoding="utf-8")
    if len(html) < 100:
        return False, "index.html too short"
    lower = html.lower()
    if "register" not in lower:
        return False, "registration section missing"
    if "./register" not in html and "/register" not in lower:
        return False, "register endpoint not referenced"
    name = (profile.event.name or "").strip()
    if name and name.lower() not in lower:
        return False, f"event name '{name}' not found in page"
    return True, "ok"


def _copy_opencode_config(build_dir: Path) -> None:
    """Copy bundled OpenCode agent + config into the site workspace."""
    if not _OPENCODE_TEMPLATE_DIR.is_dir():
        return
    target = build_dir / ".opencode"
    agents_src = _OPENCODE_TEMPLATE_DIR / "agents"
    if agents_src.is_dir():
        shutil.copytree(agents_src, target / "agents", dirs_exist_ok=True)
    config_src = _OPENCODE_TEMPLATE_DIR / "opencode.json"
    if config_src.is_file():
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_src, target / "opencode.json")


def prepare_site_workspace(build_dir: Path, profile: EventProfile, *, reseed: bool = True) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    build_dir.joinpath("event_profile.json").write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )
    build_dir.joinpath("SITE_BRIEF.md").write_text(
        site_brief(profile, build_dir.name),
        encoding="utf-8",
    )
    if reseed or not (build_dir / "index.html").is_file():
        seed_event_site(build_dir, profile)
    _copy_opencode_config(build_dir)


def opencode_run_prompt(slug: str) -> str:
    return (
        f"Customize index.html for event site slug '{slug}'. "
        "A pre-rendered Marquee template is already in index.html — read SITE_BRIEF.md, "
        "event_profile.json, and assets/, then tailor the design (colors, hero, copy) to this event. "
        "Keep registration POST to ./register via fetch + FormData with "
        "header ngrok-skip-browser-warning: true. "
        "Do not remove the registration form or break ./register wiring."
    )


async def run_site_generation_for_slug(
    slug: str,
    settings: Settings | None = None,
) -> tuple[bool, str, Path]:
    """Regenerate site HTML for an existing build directory."""
    from app.integrations.site_generation import generate_site_html

    cfg = settings or get_settings()
    build_dir = Path(cfg.build_output_dir) / slug
    profile_path = build_dir / "event_profile.json"
    if not profile_path.is_file():
        return False, f"No event_profile.json in {build_dir}", build_dir
    profile = EventProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
    ok, msg = await generate_site_html(build_dir, profile, cfg)
    return ok, msg, build_dir
