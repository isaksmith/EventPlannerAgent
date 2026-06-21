from __future__ import annotations

import json

from app.config import get_settings
from app.integrations import vercel_deploy as vd


def test_project_name_sanitizes():
    assert vd._project_name("phone:dashboard-demo") == "orchestrate-phone-dashboard-demo"
    assert vd._project_name("Phone+1 555") == "orchestrate-phone-1-555"


def test_iter_upload_files_applies_denylist(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hero.jpg").write_bytes(b"jpg")
    (tmp_path / "event_profile.json").write_text("{}", encoding="utf-8")
    (tmp_path / "SITE_BRIEF.md").write_text("brief", encoding="utf-8")
    (tmp_path / "registrations.jsonl").write_text("{}\n", encoding="utf-8")

    names = {p.name for p in vd._iter_upload_files(tmp_path)}
    assert "index.html" in names
    assert "hero.jpg" in names
    assert "event_profile.json" not in names
    assert "SITE_BRIEF.md" not in names
    assert "registrations.jsonl" not in names


def test_inject_serverless_registration(tmp_path):
    get_settings.cache_clear()
    cfg = get_settings()
    vd._inject_serverless_registration(tmp_path, cfg, event_name="AI Hackathon", site_slug="phone_x")

    func = (tmp_path / "api" / "register.js").read_text(encoding="utf-8")
    assert "module.exports" in func
    assert "rest/v1/registrations" in func
    assert "AI Hackathon" in func

    rewrite = json.loads((tmp_path / "vercel.json").read_text(encoding="utf-8"))
    assert rewrite["rewrites"][0]["destination"] == "/api/register"
