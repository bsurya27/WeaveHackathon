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
    SPECIALIST_SYSTEM_PROMPTS,
    SPECIALIST_USER_TEMPLATE,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER_TEMPLATE,
)
from schemas import (
    DeciderPerspective,
    DeciderReaction,
    FinalBrief,
    PitchDeck,
    SpecialistReport,
)


def _format_deck(deck: PitchDeck) -> str:
    return json.dumps(deck.model_dump(), indent=2)


def _format_reports(reports: list[SpecialistReport]) -> str:
    return json.dumps([r.model_dump() for r in reports], indent=2)


def _format_perspectives(perspectives: list[DeciderPerspective]) -> str:
    return json.dumps([p.model_dump() for p in perspectives], indent=2)


def _format_reactions(reactions: list[DeciderReaction]) -> str:
    return json.dumps([r.model_dump() for r in reactions], indent=2)


@weave.op
async def intake(source: PitchDeck | None = None) -> PitchDeck:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.INTAKE_MODEL, system, user, PitchDeck)
    return source if source is not None else DUMMY_PITCH_DECK.model_copy()


@weave.op
async def specialist(role: str, deck: PitchDeck) -> SpecialistReport:
    system = SPECIALIST_SYSTEM_PROMPTS[role]
    user = SPECIALIST_USER_TEMPLATE.format(deck_json=_format_deck(deck))
    report = await llm.structured(
        config.SPECIALIST_MODEL,
        system,
        user,
        SpecialistReport,
        tools=None,
        max_tokens=4096,
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
