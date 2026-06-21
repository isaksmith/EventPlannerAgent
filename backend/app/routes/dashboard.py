from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.memory.redis_store import get_session_store
from app.memory.schema import EventProfile

router = APIRouter(prefix="/api", tags=["dashboard"])

_ASSET_LABELS = {
    "logo.png": "Logo",
    "logo.svg": "Logo",
    "logo.jpg": "Logo",
    "hero.png": "Hero banner",
    "hero.svg": "Hero banner",
    "logo.webp": "Logo",
    "invite_cover.webp": "Invite cover",
    "invite_cover.png": "Invite cover",
    "invite_cover.jpg": "Invite cover",
    "invite_hero.webp": "Event atmosphere",
    "invite_hero.png": "Event atmosphere",
    "invite_hero.jpg": "Event atmosphere",
    "invite_motif.webp": "Decorative motif",
    "invite_motif.png": "Decorative motif",
    "invite_social.webp": "Social share card",
    "invite_social.png": "Social share card",
    "promo.mp4": "Promo clip",
    "site-qa.png": "Site QA screenshot",
}


def _session_slug(session_id: str) -> str:
    return session_id.replace(":", "_").replace("+", "")


def _resolve_asset_dir(profile: EventProfile) -> Path | None:
    if profile.artifacts.asset_dir:
        path = Path(profile.artifacts.asset_dir)
        if path.is_dir():
            return path

    slug = _session_slug(profile.session_id)
    fallback = Path(get_settings().assets_output_dir) / slug
    if fallback.is_dir() and any(fallback.iterdir()):
        return fallback
    return None


def _brand_files_for_profile(profile: EventProfile) -> list[dict[str, str]]:
    asset_dir = _resolve_asset_dir(profile)
    if not asset_dir:
        return []

    files: list[dict[str, str]] = []
    for path in sorted(asset_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp4"}:
            continue
        files.append(
            {
                "name": path.name,
                "label": _ASSET_LABELS.get(path.name, path.stem.replace("_", " ").title()),
                "url": f"/api/assets/{_session_slug(profile.session_id)}/{path.name}",
            }
        )
    return files


def profile_for_dashboard(profile: EventProfile) -> dict:
    data = profile.model_dump()
    artifacts = dict(data.get("artifacts") or {})
    artifacts["brand_files"] = _brand_files_for_profile(profile)
    data["artifacts"] = artifacts
    return data


@router.get("/session")
async def get_session(phone: str = Query(..., description="Session phone key, e.g. phone:dashboard-demo")) -> dict:
    """Return EventProfile JSON for the desktop dashboard Redis panel."""
    store = get_session_store()
    profile = await store.get(phone)
    if profile is None:
        raise HTTPException(status_code=404, detail="No session for this phone")
    return profile_for_dashboard(profile)


def _clear_session_artifacts(session_id: str) -> None:
    """Remove on-disk brand assets + built site so a new event starts clean."""
    import shutil

    slug = _session_slug(session_id)
    cfg = get_settings()
    for root in (cfg.assets_output_dir, cfg.build_output_dir):
        target = Path(root) / slug
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)


@router.delete("/session")
async def delete_session(phone: str = Query(...)) -> dict[str, bool]:
    store = get_session_store()
    profile = await store.get(phone)
    archived: str | None = None
    if profile is not None:
        from app.memory.event_archive import archive_event

        archived = archive_event(profile)
    await store.delete(phone)
    _clear_session_artifacts(phone)
    return {"ok": True, "archived": bool(archived)}
