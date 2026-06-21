import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.integrations.site_coder import (
    generate_site_with_openrouter,
    _execute_tool,
    _resolve_workspace_path,
)
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


def test_validate_generated_site_ok(hackathon_profile, tmp_path):
    html = """<!DOCTYPE html><html><body>
    <h1>Berkeley AI Hackathon</h1>
    <form id="reg"><script>fetch('./register')</script></form>
    </body></html>"""
    path = tmp_path / "index.html"
    path.write_text(html, encoding="utf-8")
    ok, msg = validate_generated_site(path, hackathon_profile)
    assert ok, msg


def test_tool_write_and_read(tmp_path):
    html = "<html><body>Hello</body></html>"
    result = _execute_tool(tmp_path, "write_file", {"path": "index.html", "content": html})
    assert "Wrote" in result
    read_back = _execute_tool(tmp_path, "read_file", {"path": "index.html"})
    assert read_back == html


def test_tool_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        _resolve_workspace_path(tmp_path, "../../etc/passwd")


@pytest.mark.asyncio
async def test_generate_site_with_agent_mock(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"
    build_dir.mkdir()

    write_call = {
        "path": "index.html",
        "content": """<!DOCTYPE html><html><body>
        <h1>Berkeley AI Hackathon</h1>
        <form><button>Register</button></form>
        <script>fetch('./register', {method:'POST'})</script>
        </body></html>""",
    }

    tool_call_id = "call_1"
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": json.dumps(write_call),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "SITE_COMPLETE",
                    },
                    "finish_reason": "stop",
                }
            ]
        },
    ]

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: responses.pop(0)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    prepare_site_workspace(build_dir, hackathon_profile)

    with patch("app.integrations.site_coder.httpx.AsyncClient", return_value=mock_client):
        ok, msg = await generate_site_with_openrouter(build_dir, hackathon_profile)

    assert ok, msg
    assert (build_dir / "index.html").is_file()
    assert "Berkeley AI Hackathon" in (build_dir / "index.html").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generate_site_without_api_key(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    get_settings.cache_clear()
    build_dir = tmp_path / "phone_test"
    with patch("app.integrations.site_coder.resolve_openrouter_api_key", return_value=""):
        ok, msg = await generate_site_with_openrouter(build_dir, hackathon_profile)
    assert not ok
    assert "OPENROUTER_API_KEY" in msg
