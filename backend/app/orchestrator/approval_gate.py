from __future__ import annotations

import re

from app.memory.schema import EventProfile, SessionStatus
from app.orchestrator.state_machine import compile_summary


AMEND_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"change (?:the )?color(?:s)? to (.+)", re.I), "aesthetic.colors"),
    (re.compile(r"audience is (.+)", re.I), "audience.description"),
    (re.compile(r"change (?:the )?name to (.+)", re.I), "event.name"),
    (re.compile(r"budget (?:is )?\$?(\d+)", re.I), "budget.total_usd"),
    (re.compile(r"dates?(?: are)? (.+)", re.I), "event.dates"),
]


def _set_nested(profile: EventProfile, path: str, value: str) -> EventProfile:
    if path == "event.name":
        profile.event.name = value.strip()
    elif path == "event.dates":
        profile.event.dates = value.strip()
    elif path == "audience.description":
        profile.audience.description = value.strip()
    elif path == "aesthetic.colors":
        profile.aesthetic.colors = [c.strip() for c in value.split(",") if c.strip()]
    elif path == "budget.total_usd":
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            profile.budget.total_usd = int(digits)
    return profile


def is_approve_message(text: str) -> bool:
    return text.strip().upper() in {"APPROVE", "YES", "OK", "CONFIRM"}


def handle_approval_gate(profile: EventProfile, message: str) -> tuple[EventProfile, str, bool]:
    """
    Phase 2 consensus gate.
    Returns (profile, reply_text, approved).
    """
    if is_approve_message(message):
        profile.approvals.plan_approved = True
        profile.status = SessionStatus.EXECUTING
        return profile, "Approved! Starting build — I'll text progress updates.", True

    for pattern, path in AMEND_PATTERNS:
        match = pattern.search(message)
        if match:
            profile = _set_nested(profile, path, match.group(1))
            summary = compile_summary(profile)
            return profile, f"Updated.\n\n{summary}", False

    # Unrecognized amendment — store in audience description as fallback note
    profile.audience.description = f"{profile.audience.description} [note: {message.strip()}]".strip()
    summary = compile_summary(profile)
    return profile, f"Got it — noted your change.\n\n{summary}", False
