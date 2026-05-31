import weave

import config
import llm
from fixtures import DUMMY_PITCH_DECK
from schemas import (
    DeciderPerspective,
    DeciderReaction,
    FinalBrief,
    PitchDeck,
    SpecialistReport,
)


@weave.op
async def intake(source: PitchDeck | None = None) -> PitchDeck:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.INTAKE_MODEL, system, user, PitchDeck)
    return source if source is not None else DUMMY_PITCH_DECK.model_copy()


@weave.op
async def specialist(role: str, deck: PitchDeck) -> SpecialistReport:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.SPECIALIST_MODEL, system, user, SpecialistReport)
    return SpecialistReport(
        role=role,
        findings=f"[stub] {role} review of {deck.company}: {deck.solution}",
    )


@weave.op
async def decider_stage1(
    role: str,
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
) -> DeciderPerspective:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.DECIDER_MODEL, system, user, DeciderPerspective)
    roles = ", ".join(r.role for r in specialist_reports)
    return DeciderPerspective(
        role=role,
        perspective=f"[stub] {role} initial take on {deck.company} after {roles} input",
    )


@weave.op
async def decider_stage2(
    role: str,
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    own_stage1: DeciderPerspective,
    peer_stage1: list[DeciderPerspective],
) -> DeciderReaction:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.DECIDER_MODEL, system, user, DeciderReaction)
    peers = ", ".join(p.role for p in peer_stage1)
    return DeciderReaction(
        role=role,
        reaction=(
            f"[stub] {role} reacts to peers ({peers}) "
            f"after own view: {own_stage1.perspective[:60]}"
        ),
    )


@weave.op
async def synthesis(
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    stage1: list[DeciderPerspective],
    stage2: list[DeciderReaction],
) -> FinalBrief:
    # TODO: real prompt + llm.structured() call
    # return await llm.structured(config.SYNTHESIS_MODEL, system, user, FinalBrief)
    return FinalBrief(
        recommendation=f"[stub] proceed with diligence on {deck.company}",
        summary=(
            f"[stub] {len(specialist_reports)} specialist reports, "
            f"{len(stage1)} stage-1 and {len(stage2)} stage-2 decider views synthesized"
        ),
    )
