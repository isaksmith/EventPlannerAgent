from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.memory.event_archive import (
    archived_event_dir,
    delete_archived_event,
    list_archived_events,
)

router = APIRouter(prefix="/api", tags=["archive"])


@router.get("/events")
async def get_events() -> dict:
    """List previously generated events (snapshots) for the dashboard history menu."""
    return {"events": list_archived_events()}


@router.delete("/events/{archive_id}")
async def remove_event(archive_id: str) -> dict[str, bool]:
    ok = delete_archived_event(archive_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Archived event not found")
    return {"ok": True}


def _safe_child(base: Path, *parts: str) -> Path:
    target = base.joinpath(*parts).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=404, detail="Invalid path")
    return target


@router.get("/archive/{archive_id}/asset/{filename}")
async def serve_archived_asset(archive_id: str, filename: str) -> FileResponse:
    base = archived_event_dir(archive_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Archived event not found")
    target = _safe_child(base / "assets", filename)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(target)


@router.get("/archive/{archive_id}/site")
@router.get("/archive/{archive_id}/site/")
async def serve_archived_site(archive_id: str) -> FileResponse:
    base = archived_event_dir(archive_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Archived event not found")
    index = base / "site" / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Site not found")
    return FileResponse(index, media_type="text/html")


@router.get("/archive/{archive_id}/site/{asset_path:path}")
async def serve_archived_site_asset(archive_id: str, asset_path: str) -> FileResponse:
    base = archived_event_dir(archive_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Archived event not found")
    target = _safe_child(base / "site", asset_path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(target)
