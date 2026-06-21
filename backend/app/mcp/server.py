from __future__ import annotations

from fastmcp import FastMCP

from app.memory.redis_store import get_session_store
from app.memory.schema import SessionStatus
from app.orchestrator.sai import PLAN_KEYWORD, get_dispatcher

mcp = FastMCP(
    name="Marquee",
    instructions=(
        "Event planning agent for hackathons and conferences. "
        "Use start_event_planning to begin, then send_planning_message for each user reply. "
        "Guide the user through the interview, plan approval (APPROVE), and handoff (ALL-SKIP)."
    ),
)


def _session_key(user_id: str) -> str:
    if user_id.startswith("phone:"):
        return user_id
    return f"phone:poke-{user_id}"


def _format_replies(replies: list[str], status: SessionStatus | None) -> str:
    body = "\n\n".join(replies)
    if status:
        body = f"[status: {status.value}]\n\n{body}"
    return body


@mcp.tool
async def start_event_planning(user_id: str = "default") -> str:
    """
    Start a new Marquee event planning session (equivalent to texting PLAN).
    Returns the welcome message and first interview question.
    """
    dispatcher = get_dispatcher()
    result = await dispatcher.dispatch(_session_key(user_id), PLAN_KEYWORD, deliver_sms=False)
    status = result.profile.status if result.profile else None
    return _format_replies(result.replies, status)


@mcp.tool
async def send_planning_message(message: str, user_id: str = "default") -> str:
    """
    Send the user's message to the active planning session.
    Use for interview answers, APPROVE, amendments, ALL-SKIP, etc.
    """
    dispatcher = get_dispatcher()
    result = await dispatcher.dispatch(_session_key(user_id), message, deliver_sms=False)
    status = result.profile.status if result.profile else None
    return _format_replies(result.replies, status)


@mcp.tool
async def get_planning_status(user_id: str = "default") -> str:
    """Return the current session phase and event name, if a session exists."""
    store = get_session_store()
    profile = await store.get(_session_key(user_id))
    if profile is None:
        return "No active session. Call start_event_planning first."
    e = profile.event
    return (
        f"status={profile.status.value}\n"
        f"step={profile.interview_step}\n"
        f"event={e.name or 'TBD'}\n"
        f"type={e.type.value}"
    )


# ASGI app mounted at /mcp in main.py (Streamable HTTP)
mcp_app = mcp.http_app(path="/")
