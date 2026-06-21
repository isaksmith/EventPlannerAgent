from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.config import get_settings
from app.integrations.supabase import get_registration_store

router = APIRouter(tags=["sites"])


def _build_root() -> Path:
    return Path(get_settings().build_output_dir)


def _safe_site_path(slug: str, *parts: str) -> Path:
    root = (_build_root() / slug).resolve()
    target = root.joinpath(*parts).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=404, detail="Invalid path")
    return target


def _thank_you_html(event_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Registered — {event_name}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center px-6">
  <div class="max-w-md text-center">
    <p class="text-5xl mb-4">✓</p>
    <h1 class="text-3xl font-bold mb-3">You're registered!</h1>
    <p class="text-slate-400 mb-8">Thanks for signing up for {event_name}. We'll be in touch soon.</p>
    <a href="./" class="inline-block px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold">
      Back to event page
    </a>
  </div>
</body>
</html>"""


@router.get("/sites")
@router.get("/sites/")
async def list_sites() -> dict:
    """List built registration sites (debug / demo)."""
    root = _build_root()
    root.mkdir(parents=True, exist_ok=True)
    sites = sorted(
        d.name for d in root.iterdir() if d.is_dir() and (d / "index.html").is_file()
    )
    return {"sites": sites, "build_root": str(root)}


@router.get("/sites/{slug}")
@router.get("/sites/{slug}/")
async def serve_site(slug: str) -> FileResponse:
    index = _safe_site_path(slug, "index.html")
    if not index.is_file():
        available = [
            d.name for d in _build_root().iterdir() if d.is_dir() and (d / "index.html").is_file()
        ] if _build_root().exists() else []
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Site not found",
                "slug": slug,
                "available_sites": available,
                "hint": "Complete APPROVE to build the site, or check the slug in your SMS URL",
            },
        )
    return FileResponse(index, media_type="text/html")


@router.post("/sites/{slug}/register")
async def register_for_event(slug: str, request: Request) -> HTMLResponse:
    site_dir = _safe_site_path(slug)
    if not (site_dir / "index.html").is_file():
        raise HTTPException(status_code=404, detail="Site not found")

    form = await request.form()
    entry = {k: str(v) for k, v in form.items()}
    entry["registered_at"] = datetime.now(UTC).isoformat()

    reg_file = site_dir / "registrations.jsonl"
    with reg_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    profile_path = site_dir / "event_profile.json"
    event_name = slug.replace("_", " ")
    if profile_path.is_file():
        try:
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            event_name = data.get("event", {}).get("name") or event_name
        except json.JSONDecodeError:
            pass

    store = get_registration_store()
    if store.enabled:
        await store.save_registration(
            site_slug=slug,
            event_name=event_name,
            form_data=entry,
            registered_at=entry["registered_at"],
        )

    return HTMLResponse(content=_thank_you_html(event_name))


@router.get("/sites/{slug}/{asset_path:path}")
async def serve_site_asset(slug: str, asset_path: str) -> FileResponse:
    target = _safe_site_path(slug, asset_path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(target)
