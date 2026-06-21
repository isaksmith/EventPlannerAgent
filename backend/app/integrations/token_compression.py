from __future__ import annotations

from app.memory.schema import EventProfile


def compress_profile_context(profile: EventProfile, max_chars: int = 1200) -> str:
    """
    Compress Event Profile into a concise context string for LLM calls.
    Milestone 3 wrapper — deterministic summarization (no external API).
    """
    e = profile.event
    colors = ", ".join(profile.aesthetic.colors) or "default"
    sponsors = ", ".join(profile.outreach.sponsor_targets) or "none"
    parts = [
        f"event={e.name or 'TBD'} type={e.type.value}",
        f"dates={e.dates or 'TBD'} loc={e.location or 'TBD'} fmt={e.format}",
        f"attendees={e.expected_attendees} budget=${profile.budget.total_usd}",
        f"audience={profile.audience.description[:120]}",
        f"vibe={profile.aesthetic.vibe[:80]} theme={profile.aesthetic.theme[:80]} colors={colors}",
        f"slack={profile.ops.needs_slack} devpost={profile.ops.needs_devpost}",
        f"sponsors={sponsors}",
    ]
    text = " | ".join(parts)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
