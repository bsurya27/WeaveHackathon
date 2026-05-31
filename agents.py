import json

import weave

import config
import llm
from fixtures import DUMMY_PITCH_DECK
from prompts import (
    DECIDER_STAGE1_SYSTEM_PROMPTS,
    DECIDER_STAGE1_USER_TEMPLATE,
    DECIDER_STAGE2_SYSTEM_PROMPTS,
    DECIDER_STAGE2_USER_TEMPLATE,
    FOLLOWUP_SYSTEM,
    FOLLOWUP_USER_TEMPLATE,
    FOLLOWUP_VOICE,
    INTAKE_SYSTEM,
    INTAKE_USER_TEMPLATE,
    SPECIALIST_SYSTEM_PROMPTS,
    SPECIALIST_USER_TEMPLATE,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER_TEMPLATE,
)
from schemas import (
    DeciderPerspective,
    DeciderReaction,
    FinalBrief,
    FollowupReply,
    IntakeTurn,
    IntakeUpdates,
    PitchDeck,
    SpecialistReport,
    empty_pitch_deck,
)
from specialist_tools import get_specialist_tools
from yc_retrieval import format_precedents_block, retrieve_yc_precedents


def _format_deck(deck: PitchDeck) -> str:
    return json.dumps(deck.model_dump(), indent=2)


def _format_reports(reports: list[SpecialistReport]) -> str:
    return json.dumps([r.model_dump() for r in reports], indent=2)


def _format_perspectives(perspectives: list[DeciderPerspective]) -> str:
    return json.dumps([p.model_dump() for p in perspectives], indent=2)


def _format_reactions(reactions: list[DeciderReaction]) -> str:
    return json.dumps([r.model_dump() for r in reactions], indent=2)


def merge_intake_updates(deck: PitchDeck, updates: IntakeUpdates) -> PitchDeck:
    data = deck.model_dump()
    for key, val in updates.model_dump(exclude_none=True).items():
        if isinstance(val, str) and not val.strip():
            continue
        if isinstance(val, list) and not val:
            continue
        data[key] = val
    return PitchDeck(**data)


def _format_transcript(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "(no messages yet)"
    return "\n".join(f"{m['role']}: {m['text']}" for m in messages)


@weave.op
async def intake_turn(
    deck: PitchDeck,
    user_message: str | None,
    transcript: list[dict[str, str]],
) -> IntakeTurn:
    user = INTAKE_USER_TEMPLATE.format(
        deck_json=_format_deck(deck),
        transcript=_format_transcript(transcript),
        user_message=user_message or "(starting intake — greet briefly, then ask your first question)",
    )
    return await llm.structured(
        config.INTAKE_MODEL,
        INTAKE_SYSTEM,
        user,
        IntakeTurn,
        tools=None,
        max_tokens=2048,
    )


@weave.op
async def intake(source: PitchDeck | None = None) -> PitchDeck:
    if source is not None:
        return source.model_copy()
    return DUMMY_PITCH_DECK.model_copy()


@weave.op
async def specialist(role: str, deck: PitchDeck) -> SpecialistReport:
    system = SPECIALIST_SYSTEM_PROMPTS[role]
    precedents_block = ""
    if role == "marketer":
        matches = await retrieve_yc_precedents(deck)
        precedents_block = format_precedents_block(matches)
    user = SPECIALIST_USER_TEMPLATE.format(
        deck_json=_format_deck(deck),
        precedents_block=precedents_block,
    )
    tools = get_specialist_tools(role)
    max_tokens = 6000 if tools else 4096
    report = await llm.structured(
        config.SPECIALIST_MODEL,
        system,
        user,
        SpecialistReport,
        tools=tools,
        max_tokens=max_tokens,
    )
    return report.model_copy(update={"role": role})


@weave.op
async def decider_stage1(
    role: str,
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
) -> DeciderPerspective:
    system = DECIDER_STAGE1_SYSTEM_PROMPTS[role]
    user = DECIDER_STAGE1_USER_TEMPLATE.format(
        deck_json=_format_deck(deck),
        reports_json=_format_reports(specialist_reports),
    )
    perspective = await llm.structured(
        config.DECIDER_MODEL,
        system,
        user,
        DeciderPerspective,
        tools=None,
        max_tokens=4096,
    )
    return perspective.model_copy(update={"role": role})


@weave.op
async def decider_stage2(
    role: str,
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    own_stage1: DeciderPerspective,
    peer_stage1: list[DeciderPerspective],
) -> DeciderReaction:
    system = DECIDER_STAGE2_SYSTEM_PROMPTS[role]
    user = DECIDER_STAGE2_USER_TEMPLATE.format(
        own_json=json.dumps(own_stage1.model_dump(), indent=2),
        peers_json=_format_perspectives(peer_stage1),
    )
    reaction = await llm.structured(
        config.DECIDER_MODEL,
        system,
        user,
        DeciderReaction,
        tools=None,
        max_tokens=4096,
    )
    return reaction.model_copy(
        update={"role": role, "reacting_to": [p.role for p in peer_stage1]}
    )


@weave.op
async def synthesis(
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    stage1: list[DeciderPerspective],
    stage2: list[DeciderReaction],
) -> FinalBrief:
    user = SYNTHESIS_USER_TEMPLATE.format(
        deck_json=_format_deck(deck),
        reports_json=_format_reports(specialist_reports),
        stage1_json=_format_perspectives(stage1),
        stage2_json=_format_reactions(stage2),
    )
    return await llm.structured(
        config.SYNTHESIS_MODEL,
        SYNTHESIS_SYSTEM,
        user,
        FinalBrief,
        tools=None,
        max_tokens=6000,
    )


@weave.op
async def followup(
    session_data: dict,
    question: str,
    target_role: str = "supervisor",
) -> FollowupReply:
    voice = FOLLOWUP_VOICE.get(target_role, FOLLOWUP_VOICE["supervisor"])
    system = FOLLOWUP_SYSTEM.format(voice_instruction=voice)
    user = FOLLOWUP_USER_TEMPLATE.format(
        session_json=json.dumps(session_data, indent=2),
        question=question,
    )
    return await llm.structured(
        config.INTAKE_MODEL,
        system,
        user,
        FollowupReply,
        tools=None,
        max_tokens=2048,
    )
