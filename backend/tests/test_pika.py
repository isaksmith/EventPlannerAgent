import pytest
from unittest.mock import AsyncMock, patch

from app.integrations.pika import _extract_video_url, build_promo_prompt
from app.memory.schema import EventProfile, EventType, SessionStatus


@pytest.fixture
def hackathon_profile() -> EventProfile:
    profile = EventProfile.new_session("+15551234567")
    profile.event.name = "Berkeley AI Hackathon"
    profile.event.type = EventType.HACKATHON
    profile.approvals.plan_approved = True
    profile.status = SessionStatus.EXECUTING
    return profile


def test_build_promo_prompt_includes_event_name():
    profile = EventProfile.new_session("+1")
    profile.event.name = "Berkeley AI Hackathon"
    profile.event.type = EventType.HACKATHON
    profile.aesthetic.vibe = "retro-futuristic"
    prompt = build_promo_prompt(profile)
    assert "Berkeley AI Hackathon" in prompt
    assert "hackathon" in prompt


def test_extract_video_url_from_fal_response():
    assert _extract_video_url({"video": {"url": "https://cdn.example.com/out.mp4"}}) == (
        "https://cdn.example.com/out.mp4"
    )
    assert _extract_video_url({"video_url": "https://cdn.example.com/x.mp4"}) == (
        "https://cdn.example.com/x.mp4"
    )
    assert _extract_video_url({}) is None


@pytest.mark.asyncio
async def test_generate_promo_stub_without_api_key(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("PIKA_ENABLED", "false")
    monkeypatch.setenv("PIKA_API_KEY", "")
    from app.config import get_settings
    from app.integrations.pika import generate_promo_clip

    get_settings.cache_clear()
    hackathon_profile.artifacts.asset_dir = str(tmp_path / "assets" / "phone_15551234567")
    profile = await generate_promo_clip(hackathon_profile)
    assert profile.artifacts.promo_video_url.endswith("promo.txt")


@pytest.mark.asyncio
async def test_generate_promo_downloads_video(hackathon_profile, tmp_path, monkeypatch):
    monkeypatch.setenv("ASSETS_OUTPUT_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("PIKA_ENABLED", "true")
    monkeypatch.setenv("PIKA_API_KEY", "test-key")
    from app.config import get_settings
    from app.integrations.pika import generate_promo_clip

    get_settings.cache_clear()
    asset_dir = tmp_path / "assets" / "phone_15551234567"
    asset_dir.mkdir(parents=True)
    hackathon_profile.artifacts.asset_dir = str(asset_dir)

    async def fake_download(url: str, dest):
        dest.write_bytes(b"fake-mp4")
        return dest

    with patch(
        "app.integrations.pika._call_pika_api",
        new=AsyncMock(return_value="https://cdn.example.com/promo.mp4"),
    ), patch("app.integrations.pika._download_video", new=fake_download):
        profile = await generate_promo_clip(hackathon_profile)

    assert profile.artifacts.promo_video_url.endswith("promo.mp4")
    assert (asset_dir / "promo.mp4").is_file()
