import pytest

from app.config import get_settings
from app.integrations.slack import provision_slack
from app.memory.schema import EventProfile


@pytest.fixture
def event_profile() -> EventProfile:
    profile = EventProfile.new_session("+15551234567")
    profile.event.name = "Berkeley AI Hackathon"
    profile.ops.needs_slack = True
    return profile


@pytest.mark.asyncio
async def test_provision_slack_not_configured(event_profile, monkeypatch):
    monkeypatch.setenv("SLACK_ACCESS_TOKEN", "")
    get_settings.cache_clear()

    result = await provision_slack(event_profile)
    assert result.success is False
    assert result.error == "not_configured"


@pytest.mark.asyncio
async def test_provision_slack_creates_channels(event_profile, monkeypatch):
    monkeypatch.setenv("SLACK_ACCESS_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_INVITE_URL", "https://join.slack.com/t/demo/shared_invite/abc")
    get_settings.cache_clear()

    calls: list[tuple[str, dict]] = []

    async def fake_slack_call(token: str, method: str, payload: dict | None = None) -> dict:
        calls.append((method, payload or {}))
        if method == "auth.test":
            return {"ok": True, "url": "https://demo-workspace.slack.com/"}
        if method == "conversations.create":
            name = payload["name"]
            return {"ok": True, "channel": {"id": f"C_{name}"}}
        if method == "chat.postMessage":
            return {"ok": True}
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("app.integrations.slack._slack_call", fake_slack_call)

    result = await provision_slack(event_profile)
    assert result.success is True
    assert event_profile.artifacts.slack_url == "https://join.slack.com/t/demo/shared_invite/abc"
    assert len(result.channel_ids) == 4
    assert calls[0][0] == "auth.test"
    assert any(c[0] == "chat.postMessage" for c in calls)
