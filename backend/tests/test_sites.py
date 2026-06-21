from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_list_and_serve_site(tmp_path, monkeypatch):
    build_dir = tmp_path / "builds"
    slug_dir = build_dir / "phone_15551234567"
    slug_dir.mkdir(parents=True)
    (slug_dir / "index.html").write_text("<html><body>Demo</body></html>", encoding="utf-8")

    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(build_dir))
    get_settings.cache_clear()

    client = TestClient(create_app())
    listed = client.get("/sites")
    assert listed.status_code == 200
    assert listed.json()["sites"] == ["phone_15551234567"]

    served = client.get("/sites/phone_15551234567/")
    assert served.status_code == 200
    assert "Demo" in served.text

    missing = client.get("/sites/unknown_slug/")
    assert missing.status_code == 404
    detail = missing.json()["detail"]
    assert detail["slug"] == "unknown_slug"
    assert "phone_15551234567" in detail["available_sites"]

    reg = client.post(
        "/sites/phone_15551234567/register",
        data={"name": "Ada", "email": "ada@example.com"},
    )
    assert reg.status_code == 200
    assert "You're registered" in reg.text
    assert (build_dir / "phone_15551234567" / "registrations.jsonl").is_file()
