from pathlib import Path
from unittest.mock import patch

import pytest

from app.integrations.ui_ux_pro_max import design_query_for_profile, generate_design_system
from app.memory.schema import EventProfile, EventType, SessionStatus


@pytest.fixture
def party_profile() -> EventProfile:
    return EventProfile(
        session_id="phone:15551234567",
        status=SessionStatus.EXECUTING,
        event={
            "name": "Kristy Birthday",
            "type": EventType.PARTY,
            "dates": "July 7",
            "location": "Wichita",
            "format": "in_person",
        },
        aesthetic={"vibe": "gala ballroom feminine", "theme": "victorian", "colors": ["#DB2777"]},
        audience={"description": "friends and family"},
    )


def test_design_query_for_profile(party_profile):
    q = design_query_for_profile(party_profile)
    assert "event landing page" in q.lower()
    assert "party" in q.lower()
    assert "Kristy" in q


def test_generate_design_system_writes_files(party_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()

    fake_md = "## Design System\n\nPattern: Event Landing\n"
    with patch(
        "app.integrations.ui_ux_pro_max.subprocess.run",
        return_value=type("R", (), {"returncode": 0, "stdout": fake_md, "stderr": ""})(),
    ):
        out = generate_design_system(party_profile, tmp_path)

    assert "Design System" in out
    assert (tmp_path / "UI_UX_DESIGN_SYSTEM.md").is_file()
    assert "Pattern: Event Landing" in (tmp_path / "design-system" / "MASTER.md").read_text(encoding="utf-8")


def test_generate_design_system_disabled(party_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("UI_UX_PRO_MAX_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    assert generate_design_system(party_profile, tmp_path) == ""
