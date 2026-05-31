import asyncio
from dataclasses import dataclass

import weave

import agents
import config
from schemas import DeciderPerspective, DeciderReaction, FinalBrief, PitchDeck, SpecialistReport


@dataclass
class RunOutput:
    pitch_deck: PitchDeck
    specialist_reports: list[SpecialistReport]
    stage1: list[DeciderPerspective]
    stage2: list[DeciderReaction]
    final_brief: FinalBrief


@weave.op
async def run_specialists(deck: PitchDeck) -> list[SpecialistReport]:
    return list(
        await asyncio.gather(
            *[agents.specialist(role, deck) for role in config.SPECIALIST_ROLES]
        )
    )


@weave.op
async def run_decider_stage1(
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
) -> list[DeciderPerspective]:
    return list(
        await asyncio.gather(
            *[
                agents.decider_stage1(role, deck, specialist_reports)
                for role in config.DECIDER_ROLES
            ]
        )
    )


@weave.op
async def run_decider_stage2(
    deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    stage1: list[DeciderPerspective],
) -> list[DeciderReaction]:
    stage1_by_role = {p.role: p for p in stage1}
    return list(
        await asyncio.gather(
            *[
                agents.decider_stage2(
                    role,
                    deck,
                    specialist_reports,
                    stage1_by_role[role],
                    [stage1_by_role[r] for r in config.DECIDER_ROLES if r != role],
                )
                for role in config.DECIDER_ROLES
            ]
        )
    )


@weave.op
async def run(pitch_deck: PitchDeck | None = None) -> RunOutput:
    deck = await agents.intake(pitch_deck)
    specialist_reports = await run_specialists(deck)
    stage1 = await run_decider_stage1(deck, specialist_reports)
    stage2 = await run_decider_stage2(deck, specialist_reports, stage1)
    final_brief = await agents.synthesis(deck, specialist_reports, stage1, stage2)

    return RunOutput(
        pitch_deck=deck,
        specialist_reports=specialist_reports,
        stage1=stage1,
        stage2=stage2,
        final_brief=final_brief,
    )
