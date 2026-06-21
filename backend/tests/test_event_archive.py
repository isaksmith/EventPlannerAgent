from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.memory.event_archive import archive_event, list_archived_events
from app.memory.schema import EventDetails, EventProfile


def _seed_event(tmp_path):
    cfg = get_settings()
    slug = "phone_dashboard-demo"
    asset_dir = tmp_path / "assets" / slug
    asset_dir.mkdir(parents=True)
    (asset_dir / "invite_cover.png").write_bytes(b"png")
    (asset_dir / "invite_hero.jpg").write_bytes(b"jpg")
    build_dir = tmp_path / "builds" / slug
    build_dir.mkdir(parents=True)
    (build_dir / "index.html").write_text("<html>site</html>", encoding="utf-8")
    profile = EventProfile(
        session_id="phone:dashboard-demo",
        event=EventDetails(name="AI Hackathon Berkeley", location="Berkeley, CA"),
    )
    return cfg, profile


def test_archive_event_snapshots_site_and_assets(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("ARCHIVE_OUTPUT_DIR", str(tmp_path / "archive"))
    get_settings.cache_clear()

    cfg, profile = _seed_event(tmp_path)
    archive_id = archive_event(profile, cfg)
    assert archive_id

    events = list_archived_events(cfg)
    assert len(events) == 1
    ev = events[0]
    assert ev["name"] == "AI Hackathon Berkeley"
    assert ev["has_site"] is True
    assert ev["cover_url"].endswith("invite_cover.png")
    assert ev["site_url"].endswith("/site/")
    assert any(f["name"] == "invite_cover.png" for f in ev["brand_files"])


def test_archive_skips_unnamed_event(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("ARCHIVE_OUTPUT_DIR", str(tmp_path / "archive"))
    get_settings.cache_clear()

    cfg = get_settings()
    profile = EventProfile(session_id="phone:dashboard-demo")  # no event name
    assert archive_event(profile, cfg) is None


def test_events_endpoint_and_serving(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("ARCHIVE_OUTPUT_DIR", str(tmp_path / "archive"))
    get_settings.cache_clear()

    cfg, profile = _seed_event(tmp_path)
    archive_id = archive_event(profile, cfg)

    client = TestClient(create_app())
    res = client.get("/api/events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert events and events[0]["id"] == archive_id

    asset = client.get(f"/api/archive/{archive_id}/asset/invite_cover.png")
    assert asset.status_code == 200

    site = client.get(f"/api/archive/{archive_id}/site/")
    assert site.status_code == 200
    assert "site" in site.text

    deleted = client.delete(f"/api/events/{archive_id}")
    assert deleted.status_code == 200
    assert client.get("/api/events").json()["events"] == []
