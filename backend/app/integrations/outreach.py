from __future__ import annotations

from app.memory.schema import EventProfile
from app.observability.arize import get_tracer


def compile_outreach_drafts(profile: EventProfile) -> list[str]:
    """
    Tier-3 draft-only outreach — never auto-send (spec §3.4, PRD §7).
    """
    e = profile.event
    drafts: list[str] = []

    for target in profile.outreach.sponsor_targets:
        drafts.append(
            f"Subject: Partnership — {e.name}\n\n"
            f"Hi {target} team,\n\n"
            f"We're organizing {e.name} ({e.dates or 'dates TBD'}) "
            f"for ~{e.expected_attendees} {profile.audience.description or 'attendees'}. "
            f"We'd love to discuss sponsorship.\n\n"
            f"Registration: {profile.artifacts.site_url or 'TBD'}\n\n"
            f"Best,\nOrganizing Team\n\n"
            f"[DRAFT — reply SEND to approve sending, EDIT to revise, SKIP to discard]"
        )

    if not drafts:
        drafts.append(
            f"Marketing sequence draft for {e.name}:\n"
            f"1. Launch announcement — {e.dates}\n"
            f"2. Early-bird registration push\n"
            f"3. Sponsor spotlight (if applicable)\n\n"
            f"[DRAFT — Tier 3: requires per-action SMS approval before send]"
        )

    return drafts


async def generate_outreach_drafts(profile: EventProfile) -> EventProfile:
    tracer = get_tracer()
    async with tracer.span("outreach.compile", session_id=profile.session_id):
        profile.artifacts.outreach_drafts = compile_outreach_drafts(profile)
    return profile
