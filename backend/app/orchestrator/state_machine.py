from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.memory.schema import EventProfile, EventType, SessionStatus


class InterviewStep(StrEnum):
    EVENT_NAME = "event_name"
    EVENT_TYPE = "event_type"
    DATES = "dates"
    LOCATION = "location"
    ATTENDEES = "attendees"
    BUDGET = "budget"
    AUDIENCE = "audience"
    AESTHETIC = "aesthetic"
    THEME = "theme"
    NEEDS_SLACK = "needs_slack"
    NEEDS_DEVPOST = "needs_devpost"
    SPONSORS = "sponsors"
    DONE = "done"


@dataclass(frozen=True)
class Question:
    step: InterviewStep
    prompt: str


QUESTIONS: dict[InterviewStep, Question] = {
    InterviewStep.EVENT_NAME: Question(
        InterviewStep.EVENT_NAME,
        "What's the name of your event?",
    ),
    InterviewStep.EVENT_TYPE: Question(
        InterviewStep.EVENT_TYPE,
        "What type of event is it? (e.g. hackathon, conference, party, meetup, workshop — or describe your own)",
    ),
    InterviewStep.DATES: Question(
        InterviewStep.DATES,
        "When is it? Share date(s) or a rough timeframe.",
    ),
    InterviewStep.LOCATION: Question(
        InterviewStep.LOCATION,
        "Where will it happen? (city/venue, or say virtual/hybrid)",
    ),
    InterviewStep.ATTENDEES: Question(
        InterviewStep.ATTENDEES,
        "How many attendees do you expect?",
    ),
    InterviewStep.BUDGET: Question(
        InterviewStep.BUDGET,
        "What's your total budget band in USD? (e.g. 500, 2000, 10000)",
    ),
    InterviewStep.AUDIENCE: Question(
        InterviewStep.AUDIENCE,
        "Who is this for? Describe your audience.",
    ),
    InterviewStep.AESTHETIC: Question(
        InterviewStep.AESTHETIC,
        "What's the vibe? Any colors or reference brands?",
    ),
    InterviewStep.THEME: Question(
        InterviewStep.THEME,
        "What's the theme for your invites and visuals? (e.g. tropical sunset, black-tie glam, garden party, retro 90s)",
    ),
    InterviewStep.NEEDS_SLACK: Question(
        InterviewStep.NEEDS_SLACK,
        "Do you need a Slack workspace set up? (yes/no)",
    ),
    InterviewStep.NEEDS_DEVPOST: Question(
        InterviewStep.NEEDS_DEVPOST,
        "Do you need a Devpost page? (yes/no)",
    ),
    InterviewStep.SPONSORS: Question(
        InterviewStep.SPONSORS,
        "Any sponsor targets or outreach channels? (comma-separated, or 'none')",
    ),
}


def _audience_prompt(profile: EventProfile) -> str:
    if profile.event.type == EventType.HACKATHON:
        return "Who is this for? Describe your audience and how technical they are."
    return QUESTIONS[InterviewStep.AUDIENCE].prompt


def _parse_yes_no(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"yes", "y", "true", "1", "yeah", "yep"}


def _parse_event_type(text: str) -> tuple[EventType, str]:
    normalized = text.strip().lower()
    raw = text.strip()
    if "hack" in normalized:
        return EventType.HACKATHON, ""
    if "confer" in normalized:
        return EventType.CONFERENCE, ""
    if "summit" in normalized:
        return EventType.SUMMIT, ""
    if "party" in normalized or "celebration" in normalized or "birthday" in normalized:
        return EventType.PARTY, ""
    if "meetup" in normalized or "mixer" in normalized or "networking" in normalized:
        return EventType.MEETUP, ""
    if "workshop" in normalized or "seminar" in normalized or "bootcamp" in normalized:
        return EventType.WORKSHOP, ""
    if "festival" in normalized or "fair" in normalized:
        return EventType.FESTIVAL, ""
    if "gala" in normalized or "banquet" in normalized or "dinner" in normalized:
        return EventType.GALA, ""
    if "retreat" in normalized or "offsite" in normalized:
        return EventType.RETREAT, ""
    return EventType.OTHER, raw


def _event_type_display(profile: EventProfile) -> str:
    if profile.event.type_label:
        return profile.event.type_label
    return profile.event.type.value.replace("_", " ")


def _parse_format(text: str) -> tuple[str, str]:
    normalized = text.strip().lower()
    if "virtual" in normalized and "hybrid" not in normalized:
        return normalized, "virtual"
    if "hybrid" in normalized:
        return text.strip(), "hybrid"
    return text.strip(), "in_person"


def next_step(current: InterviewStep, profile: EventProfile) -> InterviewStep:
    """Branching: skip Devpost when disabled or event is not a hackathon."""
    from app.config import get_settings

    devpost_enabled = get_settings().devpost_enabled
    order = [
        InterviewStep.EVENT_NAME,
        InterviewStep.EVENT_TYPE,
        InterviewStep.DATES,
        InterviewStep.LOCATION,
        InterviewStep.ATTENDEES,
        InterviewStep.BUDGET,
        InterviewStep.AUDIENCE,
        InterviewStep.AESTHETIC,
        InterviewStep.THEME,
        InterviewStep.NEEDS_SLACK,
    ]
    if profile.event.type == EventType.HACKATHON and devpost_enabled:
        order.append(InterviewStep.NEEDS_DEVPOST)
    else:
        profile.ops.needs_devpost = False
    order.append(InterviewStep.SPONSORS)
    order.append(InterviewStep.DONE)

    try:
        idx = order.index(current)
    except ValueError:
        return InterviewStep.DONE
    return order[idx + 1] if idx + 1 < len(order) else InterviewStep.DONE


def apply_answer(profile: EventProfile, step: InterviewStep, answer: str) -> EventProfile:
    text = answer.strip()
    if step == InterviewStep.EVENT_NAME:
        profile.event.name = text
    elif step == InterviewStep.EVENT_TYPE:
        event_type, type_label = _parse_event_type(text)
        profile.event.type = event_type
        profile.event.type_label = type_label
        if profile.event.type != EventType.HACKATHON:
            profile.ops.needs_devpost = False
    elif step == InterviewStep.DATES:
        profile.event.dates = text
    elif step == InterviewStep.LOCATION:
        location, fmt = _parse_format(text)
        profile.event.location = location
        profile.event.format = fmt  # type: ignore[assignment]
    elif step == InterviewStep.ATTENDEES:
        digits = "".join(ch for ch in text if ch.isdigit())
        profile.event.expected_attendees = int(digits) if digits else 0
    elif step == InterviewStep.BUDGET:
        digits = "".join(ch for ch in text if ch.isdigit())
        profile.budget.total_usd = int(digits) if digits else 0
        profile.budget.paid_tools_allowed = profile.budget.total_usd >= 1000
    elif step == InterviewStep.AUDIENCE:
        profile.audience.description = text
        if profile.event.type == EventType.HACKATHON:
            profile.audience.technical_level = "technical" if "tech" in text.lower() else "general"
        else:
            profile.audience.technical_level = ""
    elif step == InterviewStep.AESTHETIC:
        profile.aesthetic.vibe = text
        if "blue" in text.lower():
            profile.aesthetic.colors.append("blue")
        if "navy" in text.lower():
            profile.aesthetic.colors.append("navy")
    elif step == InterviewStep.THEME:
        profile.aesthetic.theme = text
        lowered = text.lower()
        for color, token in (
            ("gold", "gold"),
            ("pink", "pink"),
            ("green", "green"),
            ("red", "red"),
            ("purple", "purple"),
            ("orange", "orange"),
        ):
            if token in lowered and color not in profile.aesthetic.colors:
                profile.aesthetic.colors.append(color)
    elif step == InterviewStep.NEEDS_SLACK:
        profile.ops.needs_slack = _parse_yes_no(text)
    elif step == InterviewStep.NEEDS_DEVPOST:
        profile.ops.needs_devpost = _parse_yes_no(text)
    elif step == InterviewStep.SPONSORS:
        if text.lower() not in {"none", "no", "n/a", ""}:
            profile.outreach.sponsor_targets = [s.strip() for s in text.split(",") if s.strip()]
            profile.outreach.channels = ["email"]
    return profile


def get_question(step: InterviewStep, profile: EventProfile) -> str | None:
    if step == InterviewStep.DONE:
        return None
    if step == InterviewStep.AUDIENCE:
        return _audience_prompt(profile)
    return QUESTIONS[step].prompt


def start_interview(profile: EventProfile) -> tuple[EventProfile, str]:
    profile.status = SessionStatus.INTERVIEWING
    profile.interview_step = InterviewStep.EVENT_NAME.value
    profile.pending_question = QUESTIONS[InterviewStep.EVENT_NAME].prompt
    return profile, profile.pending_question


def advance_interview(profile: EventProfile, answer: str) -> tuple[EventProfile, str | None, bool]:
    """
    Process an interview answer.
    Returns (updated_profile, next_prompt_or_summary, interview_complete).
    """
    current = InterviewStep(profile.interview_step)
    profile = apply_answer(profile, current, answer)
    nxt = next_step(current, profile)

    if nxt == InterviewStep.DONE:
        profile.interview_step = InterviewStep.DONE.value
        profile.pending_question = None
        profile.status = SessionStatus.AWAITING_APPROVAL
        return profile, None, True

    profile.interview_step = nxt.value
    prompt = get_question(nxt, profile)
    profile.pending_question = prompt
    return profile, prompt, False


def compile_summary(profile: EventProfile) -> str:
    e = profile.event
    lines = [
        "*Your Event Plan*",
        f"• Name: {e.name or 'TBD'}",
        f"• Type: {_event_type_display(profile)}",
        f"• Dates: {e.dates or 'TBD'}",
        f"• Location: {e.location or 'TBD'} ({e.format})",
        f"• Attendees: ~{e.expected_attendees}",
        f"• Budget: ${profile.budget.total_usd}",
        f"• Audience: {profile.audience.description or 'TBD'}",
        f"• Vibe: {profile.aesthetic.vibe or 'TBD'}",
        f"• Theme: {profile.aesthetic.theme or 'TBD'}",
        f"• Slack: {'yes' if profile.ops.needs_slack else 'no'}",
        f"• Devpost: {'yes' if profile.ops.needs_devpost else 'no'}",
    ]
    if profile.outreach.sponsor_targets:
        lines.append(f"• Sponsors: {', '.join(profile.outreach.sponsor_targets)}")
    lines.append("")
    lines.append("Reply APPROVE to proceed, or send amendments.")
    return "\n".join(lines)
