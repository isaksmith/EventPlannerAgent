"""Snapshot completed events so the dashboard can browse previously generated events.

The desktop dashboard reuses a single session slug and wipes assets/builds on
"Plan new event". To keep a history, we copy the built site + brand assets into
``archive_output_dir/<archive_id>/`` with a ``meta.json`` describing the event
right before the live session is cleared.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.memory.schema import EventProfile

logger = logging.getLogger(__name__)

_ASSET_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp4"}


def _slug(session_id: str) -> str:
    return session_id.replace(":", "_").replace("+", "")


def _archive_root(cfg: Settings) -> Path:
    return Path(cfg.archive_output_dir)


def _event_type_label(profile: EventProfile) -> str | None:
    label = (profile.event.type_label or "").strip()
    if label:
        return label
    raw = getattr(profile.event.type, "value", profile.event.type)
    return str(raw) if raw else None


def archive_event(profile: EventProfile, cfg: Settings | None = None) -> str | None:
    """Copy the current event's site + assets into the archive. Returns archive id or None."""
    cfg = cfg or get_settings()
    name = (profile.event.name or "").strip()
    if not name:
        return None

    slug = _slug(profile.session_id)
    build_dir = Path(cfg.build_output_dir) / slug
    asset_dir = Path(cfg.assets_output_dir) / slug
    has_site = (build_dir / "index.html").is_file()
    has_assets = asset_dir.is_dir() and any(asset_dir.iterdir())
    if not has_site and not has_assets:
        return None

    ts = datetime.now(UTC)
    archive_id = f"{slug}__{ts.strftime('%Y%m%d-%H%M%S')}"
    dest = _archive_root(cfg) / archive_id
    dest.mkdir(parents=True, exist_ok=True)

    if has_site:
        shutil.copytree(build_dir, dest / "site", dirs_exist_ok=True)
    if has_assets:
        shutil.copytree(asset_dir, dest / "assets", dirs_exist_ok=True)

    brand_files: list[str] = []
    archived_assets = dest / "assets"
    if archived_assets.is_dir():
        for path in sorted(archived_assets.iterdir()):
            if path.is_file() and path.suffix.lower() in _ASSET_EXTS:
                brand_files.append(path.name)

    meta = {
        "id": archive_id,
        "session_id": profile.session_id,
        "name": name,
        "type": _event_type_label(profile),
        "location": profile.event.location or None,
        "dates": profile.event.dates or None,
        "attendees": profile.event.expected_attendees or None,
        "vibe": profile.aesthetic.vibe or None,
        "theme": profile.aesthetic.theme or None,
        "colors": list(profile.aesthetic.colors or []),
        "created_at": ts.isoformat(),
        "has_site": has_site,
        "brand_files": brand_files,
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Archived event '%s' -> %s", name, archive_id)
    return archive_id


def _public_meta(meta: dict, archive_id: str) -> dict:
    """Augment stored meta with dashboard-ready URLs."""
    brand_files = [
        {
            "name": fname,
            "url": f"/api/archive/{archive_id}/asset/{fname}",
        }
        for fname in meta.get("brand_files", [])
        if not fname.endswith(".mp4")
    ]
    cover = None
    for stem in ("invite_cover", "invite_hero", "hero", "invite_motif", "logo"):
        match = next((bf for bf in brand_files if bf["name"].startswith(stem + ".")), None)
        if match:
            cover = match["url"]
            break

    out = dict(meta)
    out["brand_files"] = brand_files
    out["cover_url"] = cover
    out["site_url"] = f"/api/archive/{archive_id}/site/" if meta.get("has_site") else None
    return out


def list_archived_events(cfg: Settings | None = None) -> list[dict]:
    """Return archived events (most recent first) with dashboard-ready URLs."""
    cfg = cfg or get_settings()
    root = _archive_root(cfg)
    if not root.is_dir():
        return []

    events: list[dict] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        events.append(_public_meta(meta, entry.name))

    events.sort(key=lambda e: e.get("created_at") or "", reverse=True)
    return events


def archived_event_dir(archive_id: str, cfg: Settings | None = None) -> Path | None:
    """Resolve an archive id to its directory, guarding against path traversal."""
    cfg = cfg or get_settings()
    root = _archive_root(cfg).resolve()
    target = (root / archive_id).resolve()
    if not str(target).startswith(str(root)) or not target.is_dir():
        return None
    return target


def delete_archived_event(archive_id: str, cfg: Settings | None = None) -> bool:
    target = archived_event_dir(archive_id, cfg)
    if target is None:
        return False
    shutil.rmtree(target, ignore_errors=True)
    return True
