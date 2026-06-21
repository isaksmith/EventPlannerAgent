from unittest.mock import patch

from app.config import Settings
from app.integrations.openrouter_auth import openrouter_images_ready, resolve_openrouter_api_key


def test_resolve_from_settings():
    cfg = Settings(openrouter_api_key="sk-or-test", openrouter_image_enabled=True)
    assert resolve_openrouter_api_key(cfg) == "sk-or-test"
    assert openrouter_images_ready(cfg)


def test_resolve_from_opencode_auth_file(tmp_path, monkeypatch):
    auth = tmp_path / "auth.json"
    auth.write_text('{"openrouter": {"type": "api", "key": "sk-or-from-opencode"}}', encoding="utf-8")
    monkeypatch.setattr("app.integrations.openrouter_auth._OPENCODE_AUTH", auth)
    cfg = Settings(openrouter_api_key="", openrouter_image_enabled=True)
    assert resolve_openrouter_api_key(cfg) == "sk-or-from-opencode"
    assert openrouter_images_ready(cfg)


def test_not_ready_without_key(tmp_path, monkeypatch):
    cfg = Settings(openrouter_api_key="", openrouter_image_enabled=True)
    missing = tmp_path / "missing.json"
    monkeypatch.setattr("app.integrations.openrouter_auth._OPENCODE_AUTH", missing)
    assert resolve_openrouter_api_key(cfg) == ""
    assert not openrouter_images_ready(cfg)
