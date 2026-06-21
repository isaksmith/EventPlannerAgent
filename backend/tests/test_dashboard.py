import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.memory.redis_store import InMemoryStore
from app.memory.schema import EventProfile, SessionStatus


@pytest.mark.asyncio
async def test_dashboard_session_api(monkeypatch):
    store = InMemoryStore()
    profile = EventProfile.new_session("phone:dashboard-demo")
    profile.event.name = "Dashboard Test"
    profile.status = SessionStatus.INTERVIEWING
    await store.save(profile)

    monkeypatch.setattr("app.routes.dashboard.get_session_store", lambda: store)

    client = TestClient(create_app())

    res = client.get("/api/session", params={"phone": "phone:dashboard-demo"})
    assert res.status_code == 200
    assert res.json()["event"]["name"] == "Dashboard Test"

    res = client.delete("/api/session", params={"phone": "phone:dashboard-demo"})
    assert res.status_code == 200
    assert client.get("/api/session", params={"phone": "phone:dashboard-demo"}).status_code == 404
