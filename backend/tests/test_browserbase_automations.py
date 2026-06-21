import pytest
from unittest.mock import AsyncMock, patch
from app.integrations.browserbase import run_post_build_automations
from app.integrations.browserbase_automations import SiteQAResult
from app.memory.schema import EventProfile, EventType, SessionStatus


@pytest.fixture
def hackathon_profile() -> EventProfile:
    profile = EventProfile.new_session("+15551234567")
    profile.event.name = "Berkeley AI Hackathon"
    profile.event.type = EventType.HACKATHON
    profile.approvals.plan_approved = True
    profile.status = SessionStatus.EXECUTING
    return profile


@pytest.mark.asyncio
async def test_post_build_records_site_qa(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_OUTPUT_DIR", str(tmp_path / "builds"))
    monkeypatch.setenv("BROWSERBASE_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()

    slug = hackathon_profile.session_id.replace(":", "_")
    build_dir = tmp_path / "builds" / slug
    build_dir.mkdir(parents=True)
    (build_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    hackathon_profile.artifacts.site_url = "https://demo.ngrok-free.dev/sites/test/"
    hackathon_profile.artifacts.slack_url = "https://example.slack.com"

    qa = SiteQAResult(
        ok=True,
        session_url="https://browserbase.com/sessions/abc",
        screenshot_path=str(build_dir / "assets" / "site-qa.png"),
        registration_tested=True,
        detail="ok",
    )

    with patch(
        "app.integrations.browserbase.verify_registration_site",
        new=AsyncMock(return_value=qa),
    ), patch(
        "app.integrations.browserbase.verify_slack_link",
        new=AsyncMock(return_value=(True, "ok · https://browserbase.com/sessions/def")),
    ):
        result = await run_post_build_automations(hackathon_profile)

    assert result.artifacts.site_verified is True
    assert len(result.artifacts.browserbase_session_urls) == 2


@pytest.mark.asyncio
async def test_post_build_skipped_without_public_url(hackathon_profile, monkeypatch):
    monkeypatch.setenv("BROWSERBASE_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    hackathon_profile.artifacts.site_url = "file:///tmp/site/index.html"

    with patch(
        "app.integrations.browserbase.verify_registration_site",
        new=AsyncMock(),
    ) as mock_qa:
        result = await run_post_build_automations(hackathon_profile)

    mock_qa.assert_not_called()
    assert result.artifacts.site_verified is False
