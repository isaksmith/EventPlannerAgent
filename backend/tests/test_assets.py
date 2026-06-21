import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.routes.dashboard import profile_for_dashboard
from app.memory.schema import EventProfile, SessionStatus


def test_serve_session_asset(tmp_path, monkeypatch):
    slug = "phone_dashboard-demo"
    asset_dir = tmp_path / slug
    asset_dir.mkdir()
    (asset_dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()

    client = TestClient(create_app())
    res = client.get(f"/api/assets/{slug}/logo.png")
    assert res.status_code == 200
    assert res.content.startswith(b"\x89PNG")


def test_brand_files_enrichment(tmp_path):
    profile = EventProfile.new_session("phone:dashboard-demo")
    profile.status = SessionStatus.EXECUTING
    asset_dir = tmp_path / "phone_dashboard-demo"
    asset_dir.mkdir()
    (asset_dir / "logo.png").write_bytes(b"png")
    (asset_dir / "hero.png").write_bytes(b"png")
    profile.artifacts.asset_dir = str(asset_dir)

    data = profile_for_dashboard(profile)
    names = {f["name"] for f in data["artifacts"]["brand_files"]}
    assert names == {"hero.png", "logo.png"}
    assert all(f["url"].startswith("/api/assets/phone_dashboard-demo/") for f in data["artifacts"]["brand_files"])


def test_delete_session_clears_assets(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    get_settings.cache_clear()

    slug = "phone_dashboard-demo"
    asset_dir = tmp_path / "assets" / slug
    asset_dir.mkdir(parents=True)
    (asset_dir / "invite_cover.png").write_bytes(b"png")
    build_dir = tmp_path / "builds" / slug
    build_dir.mkdir(parents=True)
    (build_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    client = TestClient(create_app())
    res = client.delete("/api/session?phone=phone%3Adashboard-demo")
    assert res.status_code == 200
    assert not asset_dir.exists()
    assert not build_dir.exists()


def test_brand_files_fallback_without_asset_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()

    profile = EventProfile.new_session("phone:dashboard-demo")
    profile.status = SessionStatus.EXECUTING
    asset_dir = tmp_path / "phone_dashboard-demo"
    asset_dir.mkdir()
    (asset_dir / "invite_cover.png").write_bytes(b"png")

    data = profile_for_dashboard(profile)
    names = {f["name"] for f in data["artifacts"]["brand_files"]}
    assert names == {"invite_cover.png"}
