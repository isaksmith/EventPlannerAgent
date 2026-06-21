from app.memory.schema import EventProfile, EventType, SessionStatus
from app.orchestrator.approval_gate import handle_approval_gate, is_approve_message
from app.orchestrator.state_machine import (
    InterviewStep,
    advance_interview,
    compile_summary,
    get_question,
    next_step,
    start_interview,
)
import pytest


@pytest.fixture(autouse=True)
def devpost_disabled(monkeypatch):
    monkeypatch.setenv("DEVPOST_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_start_interview_sets_first_question():
    profile = EventProfile.new_session("+15551234567")
    profile, prompt = start_interview(profile)
    assert profile.status == SessionStatus.INTERVIEWING
    assert profile.interview_step == InterviewStep.EVENT_NAME.value
    assert "name" in prompt.lower()


def test_hackathon_includes_devpost_step_when_enabled(monkeypatch):
    monkeypatch.setenv("DEVPOST_ENABLED", "true")
    from app.config import get_settings

    get_settings.cache_clear()

    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.HACKATHON
    step = next_step(InterviewStep.NEEDS_SLACK, profile)
    assert step == InterviewStep.NEEDS_DEVPOST


def test_hackathon_skips_devpost_when_disabled():
    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.HACKATHON
    step = next_step(InterviewStep.NEEDS_SLACK, profile)
    assert step == InterviewStep.SPONSORS
    assert profile.ops.needs_devpost is False


def test_conference_skips_devpost():
    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.CONFERENCE
    step = next_step(InterviewStep.NEEDS_SLACK, profile)
    assert step == InterviewStep.SPONSORS
    assert profile.ops.needs_devpost is False


def test_party_event_type():
    profile = EventProfile.new_session("+15551234567")
    profile, _ = start_interview(profile)
    answers = [
        "Summer Kickoff",
        "birthday party",
        "July 4, 2026",
        "San Francisco",
        "50",
        "2000",
        "friends and coworkers",
        "fun and colorful",
        "tropical garden party",
        "no",
        "none",
    ]
    for answer in answers:
        profile, _, complete = advance_interview(profile, answer)
    assert complete is True
    assert profile.event.type == EventType.PARTY
    assert profile.ops.needs_devpost is False


def test_custom_event_type():
    profile = EventProfile.new_session("+15551234567")
    profile, _ = start_interview(profile)
    profile, _, _ = advance_interview(profile, "Product Launch")
    profile, _, _ = advance_interview(profile, "product launch")
    assert profile.event.type == EventType.OTHER
    assert profile.event.type_label == "product launch"


def test_audience_question_hackathon():
    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.HACKATHON
    prompt = get_question(InterviewStep.AUDIENCE, profile)
    assert "technical" in prompt.lower()


def test_audience_question_non_hackathon():
    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.PARTY
    prompt = get_question(InterviewStep.AUDIENCE, profile)
    assert "technical" not in prompt.lower()
    assert "audience" in prompt.lower()


def test_theme_question_in_interview():
    profile = EventProfile.new_session("+15551234567")
    profile, _ = start_interview(profile)
    profile.event.type = EventType.PARTY
    for answer in [
        "Garden Party",
        "party",
        "June 1",
        "Backyard",
        "40",
        "1500",
        "neighbors and friends",
        "casual and bright",
    ]:
        profile, prompt, complete = advance_interview(profile, answer)
        assert not complete
    assert profile.interview_step == InterviewStep.THEME.value
    assert "theme" in (prompt or "").lower()
    profile, _, complete = advance_interview(profile, "English garden, florals, pastel")
    assert profile.aesthetic.theme == "English garden, florals, pastel"


def test_audience_answer_skips_technical_level_for_party():
    profile = EventProfile.new_session("+15551234567")
    profile.event.type = EventType.PARTY
    profile, _ = start_interview(profile)
    for answer in [
        "Summer Kickoff",
        "party",
        "July 4",
        "SF",
        "50",
        "2000",
        "friends and coworkers",
    ]:
        profile, _, complete = advance_interview(profile, answer)
    assert profile.audience.description == "friends and coworkers"
    assert profile.audience.technical_level == ""


def test_full_interview_flow():
    profile = EventProfile.new_session("+15551234567")
    profile, _ = start_interview(profile)

    answers = [
        "Berkeley AI Hackathon",
        "hackathon",
        "March 15-16, 2026",
        "Berkeley, CA",
        "200",
        "5000",
        "undergrad CS students, very technical",
        "futuristic blue cyberpunk",
        "neon cyberpunk night",
        "yes",
        "Anthropic, OpenAI",
    ]

    for answer in answers:
        profile, prompt, complete = advance_interview(profile, answer)
        if not complete:
            assert prompt is not None

    assert profile.status == SessionStatus.AWAITING_APPROVAL
    assert profile.event.name == "Berkeley AI Hackathon"
    assert profile.event.expected_attendees == 200
    assert profile.ops.needs_devpost is False


def test_conference_interview_skips_devpost_question():
    profile = EventProfile.new_session("+15551234567")
    profile, _ = start_interview(profile)

    answers = [
        "AI Summit",
        "conference",
        "June 2026",
        "virtual",
        "500",
        "10000",
        "industry leaders",
        "professional minimal",
        "sleek modern keynote",
        "yes",
        "none",
    ]

    for answer in answers:
        profile, _, complete = advance_interview(profile, answer)

    assert complete is True
    assert profile.ops.needs_devpost is False


def test_compile_summary_contains_key_fields():
    profile = EventProfile.new_session("+15551234567")
    profile.event.name = "Test Event"
    profile.event.type = EventType.HACKATHON
    summary = compile_summary(profile)
    assert "Test Event" in summary
    assert "APPROVE" in summary


def test_approval_gate_approve():
    profile = EventProfile.new_session("+15551234567")
    profile.status = SessionStatus.AWAITING_APPROVAL
    profile, reply, approved = handle_approval_gate(profile, "APPROVE")
    assert approved is True
    assert profile.approvals.plan_approved is True
    assert profile.status == SessionStatus.EXECUTING
    assert "Approved" in reply


def test_approval_gate_amendment():
    profile = EventProfile.new_session("+15551234567")
    profile.status = SessionStatus.AWAITING_APPROVAL
    profile.event.name = "Old Name"
    profile, reply, approved = handle_approval_gate(profile, "change the name to New Name")
    assert approved is False
    assert profile.event.name == "New Name"
    assert "New Name" in reply


def test_is_approve_message():
    assert is_approve_message("APPROVE") is True
    assert is_approve_message("yes") is True
    assert is_approve_message("change colors") is False
