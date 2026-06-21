import pytest

from app.mcp.server import _session_key, start_event_planning, send_planning_message, get_planning_status
from app.memory.redis_store import InMemoryStore
from app.memory.schema import SessionStatus
from app.orchestrator.sai import SaiDispatcher


@pytest.fixture
def mcp_store():
    store = InMemoryStore()
    SaiDispatcher(store)
    from app.orchestrator import sai as sai_module

    sai_module._dispatcher = SaiDispatcher(store)
    return store


@pytest.mark.asyncio
async def test_mcp_start_session(mcp_store):
    text = await start_event_planning(user_id="test-user")
    assert "Welcome to Marquee" in text
    assert "name of your event" in text.lower()
    profile = await mcp_store.get(_session_key("test-user"))
    assert profile is not None
    assert profile.status == SessionStatus.INTERVIEWING


@pytest.mark.asyncio
async def test_mcp_interview_message(mcp_store):
    await start_event_planning(user_id="alice")
    text = await send_planning_message(message="My Hackathon", user_id="alice")
    assert "type of event" in text.lower() or "hackathon" in text.lower()


@pytest.mark.asyncio
async def test_mcp_get_status_no_session():
    text = await get_planning_status(user_id="nobody")
    assert "No active session" in text
