import pytest

from app.memory.redis_store import InMemoryStore
from app.memory.schema import SessionStatus
from app.orchestrator.sai import SaiDispatcher


@pytest.fixture(autouse=True)
async def mock_send_sms(monkeypatch):
    async def _noop(*args, **kwargs):
        return {"status": "stub"}

    monkeypatch.setattr("app.orchestrator.sai.send_sms", _noop)


@pytest.mark.asyncio
async def test_handoff_all_skip_completes_session():
    store = InMemoryStore()
    dispatcher = SaiDispatcher(store)
    phone = "+15559998888"

    await dispatcher.dispatch(phone, "PLAN")
    answers = [
        "Test Event",
        "hackathon",
        "Jan 2026",
        "virtual",
        "100",
        "1000",
        "students",
        "minimal",
        "clean campus launch",
        "yes",
        "none",
    ]
    for answer in answers:
        await dispatcher.dispatch(phone, answer)

    await dispatcher.dispatch(phone, "APPROVE")
    await dispatcher.wait_for_execution(phone)

    profile = await store.get(phone)
    assert profile is not None
    assert profile.status == SessionStatus.AWAITING_HANDOFF

    result = await dispatcher.dispatch(phone, "ALL-SKIP")
    assert profile.status == SessionStatus.DONE
    assert any("ready" in r.lower() or "site:" in r.lower() for r in result.replies)
