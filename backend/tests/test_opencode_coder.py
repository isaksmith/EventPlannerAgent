import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.integrations.opencode_coder import generate_site_with_opencode, opencode_available
from app.integrations.site_generation import generate_site_html
from app.integrations.site_workspace import prepare_site_workspace, validate_generated_site
from app.memory.schema import EventProfile, EventType, SessionStatus


@pytest.fixture
def hackathon_profile() -> EventProfile:
    return EventProfile(
        session_id="phone:15551234567",
        status=SessionStatus.EXECUTING,
        event={
            "name": "Berkeley AI Hackathon",
            "type": EventType.HACKATHON,
            "dates": "March 15–16, 2026",
            "location": "UC Berkeley",
            "format": "in_person",
            "expected_attendees": 200,
        },
        aesthetic={"vibe": "futuristic neon", "colors": ["#2563eb", "#22d3ee"]},
        ops={"registration_fields": ["name", "email", "team"]},
    )


def test_opencode_available_respects_path(monkeypatch):
    monkeypatch.setenv("OPENCODE_ENABLED", "true")
    get_settings.cache_clear()
    cfg = get_settings()
    with patch("app.integrations.opencode_coder.shutil.which", return_value="/usr/bin/opencode"):
        assert opencode_available(cfg)
    with patch("app.integrations.opencode_coder.shutil.which", return_value=None), patch(
        "app.integrations.opencode_coder.Path.home",
        return_value=Path("/nonexistent"),
    ):
        assert not opencode_available(cfg)


@pytest.mark.asyncio
async def test_generate_site_with_opencode_mock(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCODE_ENABLED", "true")
    monkeypatch.setenv("OPENCODE_BIN", "opencode")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"
    prepare_site_workspace(build_dir, hackathon_profile)

    html = """<!DOCTYPE html><html><body>
    <h1>Berkeley AI Hackathon</h1>
    <form><button>Register</button></form>
    <script>fetch('./register', {method:'POST'})</script>
    </body></html>"""

    async def fake_communicate():
        (build_dir / "index.html").write_text(html, encoding="utf-8")
        return b"done", b""

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=fake_communicate)
    mock_proc.returncode = 0
    mock_proc.kill = MagicMock()

    with patch(
        "app.integrations.opencode_coder.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=mock_proc),
    ):
        ok, msg = await generate_site_with_opencode(build_dir, hackathon_profile)

    assert ok, msg
    assert "OpenCode" in msg


@pytest.mark.asyncio
async def test_generate_site_html_prefers_ui_ux_openrouter(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_CODER_ENABLED", "true")
    monkeypatch.setenv("OPENCODE_ENABLED", "false")
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"

    with patch(
        "app.integrations.site_generation.generate_design_system",
        return_value="## Design System\n",
    ), patch(
        "app.integrations.site_generation.generate_site_with_openrouter",
        new=AsyncMock(return_value=(True, "OpenRouter agent completed")),
    ) as mock_or:
        ok, msg = await generate_site_html(build_dir, hackathon_profile)

    assert ok
    mock_or.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_site_html_falls_back_to_opencode(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCODE_ENABLED", "true")
    monkeypatch.setenv("SITE_CODER_ENABLED", "true")
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"

    with patch(
        "app.integrations.site_generation.generate_site_with_openrouter",
        new=AsyncMock(return_value=(False, "OpenRouter failed")),
    ), patch(
        "app.integrations.site_generation.generate_site_with_opencode",
        new=AsyncMock(return_value=(True, "OpenCode site-builder completed")),
    ) as mock_opencode:
        ok, msg = await generate_site_html(build_dir, hackathon_profile)

    assert ok
    mock_opencode.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_site_html_falls_back_to_openrouter_when_enabled(
    hackathon_profile, tmp_path, monkeypatch,
):
    monkeypatch.setenv("OPENCODE_ENABLED", "false")
    monkeypatch.setenv("SITE_CODER_ENABLED", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"

    with patch(
        "app.integrations.site_generation.generate_design_system",
        return_value="",
    ), patch(
        "app.integrations.site_generation.generate_site_with_openrouter",
        new=AsyncMock(return_value=(True, "OpenRouter agent completed")),
    ) as mock_or:
        ok, msg = await generate_site_html(build_dir, hackathon_profile)

    assert ok
    mock_or.assert_awaited_once()
