from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings
from app.integrations.image_prompt_smith import craft_invite_prompts
from app.integrations.midjourney_mcp import generate_invite_assets_via_mcp, mcp_configured
from app.integrations.openrouter_auth import openrouter_images_ready
from app.integrations.openrouter_images import generate_invite_assets_via_openrouter
from app.integrations.token_compression import compress_profile_context
from app.memory.schema import EventProfile, EventType
from app.observability.arize import get_tracer

logger = logging.getLogger(__name__)

STYLE_SUFFIX = "--style raw --v 6"

INVITE_ASSET_NAMES = (
    "invite_cover",
    "invite_hero",
    "invite_motif",
    "invite_social",
)


@dataclass(frozen=True)
class InviteAssetBrief:
    """One Midjourney generation = one full-resolution invite asset (not a 4-up grid)."""

    filename: str
    label: str
    aspect: str
    scene: str


def _event_label(profile: EventProfile) -> str:
    if profile.event.type_label:
        return profile.event.type_label
    return profile.event.type.value.replace("_", " ")


def _is_social_event(profile: EventProfile) -> bool:
    return profile.event.type in {
        EventType.PARTY,
        EventType.GALA,
        EventType.FESTIVAL,
        EventType.MEETUP,
        EventType.RETREAT,
    }


def build_design_seed(profile: EventProfile) -> str:
    """Single internal design-system seed for visual consistency across assets."""
    ctx = compress_profile_context(profile, max_chars=400)
    colors = ", ".join(profile.aesthetic.colors) or "brand-primary"
    theme = profile.aesthetic.theme or profile.aesthetic.vibe or "celebratory"
    return (
        f"Marquee event brand | {ctx} | theme={theme[:80]} | "
        f"vibe={profile.aesthetic.vibe[:60]} | palette={colors} | {STYLE_SUFFIX}"
    )


def build_invite_context(profile: EventProfile) -> str:
    name = profile.event.name or "Your Event"
    event_type = _event_label(profile)
    theme = profile.aesthetic.theme or profile.aesthetic.vibe or "elegant and festive"
    vibe = profile.aesthetic.vibe or theme
    colors = ", ".join(profile.aesthetic.colors) or "rich warm tones"
    audience = profile.audience.description or "guests"
    location = profile.event.location or "a beautiful venue"
    dates = profile.event.dates or "soon"
    seed = build_design_seed(profile)
    return (
        f"Event: {name} ({event_type}). Theme: {theme}. Mood: {vibe}. "
        f"Palette: {colors}. For: {audience}. Where: {location}. When: {dates}. "
        f"Design seed: {seed}"
    )


def build_invite_asset_briefs(profile: EventProfile) -> list[InviteAssetBrief]:
    """Structured invite-image briefs derived from the full interview context."""
    ctx = build_invite_context(profile)
    name = profile.event.name or "Your Event"
    theme = profile.aesthetic.theme or profile.aesthetic.vibe or "celebratory"
    social = _is_social_event(profile)

    if social:
        cover_scene = (
            f"Premium printed event invitation cover for '{name}', {theme} theme, "
            f"single hero illustration with elegant negative space for typography, "
            f"luxury stationery aesthetic, one cohesive scene, no collage"
        )
        hero_scene = (
            f"Cinematic venue atmosphere photo for '{name}' {theme} party, "
            f"wide establishing shot, warm inviting lighting, editorial quality"
        )
        motif_scene = (
            f"Decorative border motif and icon set for '{name}' invites, {theme}, "
            f"single centered emblem, flat lay ornamental design, print-ready"
        )
        social_scene = (
            f"Instagram story invitation graphic for '{name}', {theme}, "
            f"bold focal point, mobile-first vertical-friendly composition"
        )
    else:
        cover_scene = (
            f"Professional event poster key art for '{name}', {theme}, "
            f"single striking illustration, poster-ready, space for title overlay"
        )
        hero_scene = (
            f"Wide hero banner for '{name}' registration site, {theme}, "
            f"one panoramic scene, modern event marketing photography"
        )
        motif_scene = (
            f"Minimal brand mark and pattern tile for '{name}', {theme}, "
            f"single icon on clean background, vector-friendly"
        )
        social_scene = (
            f"Social media announcement card for '{name}', {theme}, "
            f"single graphic with strong focal point"
        )

    shared = (
        f"{ctx}. High-end print quality, cohesive art direction, "
        "single full-bleed image, NOT a grid, NOT four quadrants, NOT a contact sheet."
    )

    return [
        InviteAssetBrief("invite_cover", "Invite cover", "3:4", f"{cover_scene}. {shared}"),
        InviteAssetBrief("invite_hero", "Event atmosphere", "16:9", f"{hero_scene}. {shared}"),
        InviteAssetBrief("invite_motif", "Decorative motif", "1:1", f"{motif_scene}. {shared}"),
        InviteAssetBrief("invite_social", "Social share card", "1:1", f"{social_scene}. {shared}"),
    ]


def _session_asset_dir(profile: EventProfile, settings: Settings) -> Path:
    safe_id = profile.session_id.replace(":", "_").replace("+", "")
    path = Path(settings.assets_output_dir) / safe_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_stub_assets(
    asset_dir: Path,
    profile: EventProfile,
    only: set[str] | None = None,
) -> list[str]:
    """Local placeholder assets when image generation is unavailable.

    When ``only`` is given, write stubs solely for those stems (used to fill
    gaps from a partial generation without clobbering successful images).
    """
    primary = profile.aesthetic.colors[0] if profile.aesthetic.colors else "#2563eb"
    name = profile.event.name or "Your Event"
    theme = profile.aesthetic.theme or profile.aesthetic.vibe or "Your theme"
    paths: list[str] = []

    stubs = {
        "invite_cover": ("900", "1200", "Invite cover"),
        "invite_hero": ("1600", "900", "Event atmosphere"),
        "invite_motif": ("800", "800", "Motif"),
        "invite_social": ("800", "800", "Social card"),
    }
    for stem, (w, h, label) in stubs.items():
        if only is not None and stem not in only:
            continue
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{primary}"/><stop offset="100%" stop-color="#0f172a"/>
  </linearGradient></defs>
  <rect width="{w}" height="{h}" fill="url(#g)"/>
  <text x="{int(w)//2}" y="{int(h)//2 - 20}" font-family="sans-serif" font-size="48" fill="white" text-anchor="middle">{label}</text>
  <text x="{int(w)//2}" y="{int(h)//2 + 40}" font-family="sans-serif" font-size="28" fill="white" text-anchor="middle" opacity="0.85">{name[:24]}</text>
  <text x="{int(w)//2}" y="{int(h)//2 + 90}" font-family="sans-serif" font-size="22" fill="white" text-anchor="middle" opacity="0.7">{theme[:32]}</text>
</svg>"""
        path = asset_dir / f"{stem}.svg"
        path.write_text(svg, encoding="utf-8")
        paths.append(str(path))

    _mirror_site_assets(asset_dir, paths)
    return paths


def _mirror_site_assets(asset_dir: Path, generated: list[str]) -> None:
    """Copy primary invite assets to legacy logo/hero filenames for the registration site."""
    by_stem = {Path(p).stem.split(".")[0]: Path(p) for p in generated}
    cover = by_stem.get("invite_cover") or by_stem.get("invite_motif")
    hero = by_stem.get("invite_hero") or by_stem.get("invite_cover")
    if cover and cover.is_file():
        shutil.copy2(cover, asset_dir / f"logo{cover.suffix}")
    if hero and hero.is_file():
        shutil.copy2(hero, asset_dir / f"hero{hero.suffix}")


def _clear_previous_brand_assets(asset_dir: Path) -> None:
    """Remove stale logo/hero/invite files so old grid previews cannot resurface."""
    for path in asset_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            continue
        if path.stem.startswith("invite_") or path.stem in {"logo", "hero"}:
            path.unlink(missing_ok=True)


async def generate_brand_assets(
    profile: EventProfile,
    settings: Settings | None = None,
) -> EventProfile:
    tracer = get_tracer()
    cfg = settings or get_settings()
    asset_dir = _session_asset_dir(profile, cfg)
    _clear_previous_brand_assets(asset_dir)
    briefs = build_invite_asset_briefs(profile)
    briefs = await craft_invite_prompts(profile, briefs, cfg)

    async with tracer.span("midjourney.generate", session_id=profile.session_id):
        paths: list[str] | None = None
        or_ready = openrouter_images_ready(cfg)

        if or_ready and cfg.openrouter_image_primary:
            logger.info("OpenRouter primary — generating brand assets for %s", profile.session_id)
            paths = await generate_invite_assets_via_openrouter(
                briefs=[(b.filename, b.scene, b.aspect) for b in briefs],
                asset_dir=asset_dir,
                settings=cfg,
            )
            if paths is None:
                logger.warning("OpenRouter primary failed; trying Midjourney MCP")

        if paths is None and mcp_configured(cfg):
            logger.info("Trying Midjourney MCP for brand assets")
            paths = await generate_invite_assets_via_mcp(
                briefs=[(b.filename, b.scene, b.aspect) for b in briefs],
                asset_dir=asset_dir,
                settings=cfg,
            )

        if paths is None and or_ready and not cfg.openrouter_image_primary:
            logger.info("Midjourney MCP unavailable or failed; trying OpenRouter images")
            paths = await generate_invite_assets_via_openrouter(
                briefs=[(b.filename, b.scene, b.aspect) for b in briefs],
                asset_dir=asset_dir,
                settings=cfg,
            )
        if paths is None and not or_ready and not mcp_configured(cfg):
            logger.warning(
                "No brand image providers — set OPENROUTER_API_KEY or enable Midjourney MCP"
            )
        if paths is None:
            logger.info("Brand image generation failed; writing SVG stubs for %s", profile.session_id)
            paths = _write_stub_assets(asset_dir, profile)
        elif len(paths) < len(briefs):
            logger.info("OpenRouter partial (%d/%d); stubbing missing invite assets", len(paths), len(briefs))
            have = {Path(p).stem.split(".")[0] for p in paths}
            missing = {b.filename for b in briefs} - have
            stubs = _write_stub_assets(asset_dir, profile, only=missing)
            paths = paths + stubs
            _mirror_site_assets(asset_dir, paths)
        else:
            _mirror_site_assets(asset_dir, paths)

        profile.artifacts.asset_dir = str(asset_dir)
        profile.artifacts.asset_urls = paths
    return profile
