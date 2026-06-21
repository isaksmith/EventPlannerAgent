import pytest

from app.integrations.site_template import render_event_site, seed_event_site, template_path
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


def test_template_path_exists():
    assert template_path().is_file()


def test_render_event_site(hackathon_profile):
    html = render_event_site(hackathon_profile)
    assert "Berkeley AI Hackathon" in html
    assert "Bebas Neue" in html
    assert "./register" in html
    assert 'for="reg-email"' in html
    assert 'id="reg-email"' in html
    assert "Register your team" in html
    assert "You're invited" in html
    assert "bento-grid" in html
    assert "{{" not in html


def test_seed_event_site(hackathon_profile, tmp_path):
    build_dir = tmp_path / "phone_test"
    index = seed_event_site(build_dir, hackathon_profile)
    assert index.is_file()
    assert (build_dir / "site_template.html").is_file()
    assert "Berkeley AI Hackathon" in index.read_text(encoding="utf-8")
