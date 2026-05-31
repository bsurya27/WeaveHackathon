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
async def run(pitch_deck: PitchDeck | None = None) -> RunOutput:
    deck = await agents.intake(pitch_deck)

    specialist_reports: list[SpecialistReport] = list(
        await asyncio.gather(
            *[agents.specialist(role, deck) for role in config.SPECIALIST_ROLES]
        )
    )

    stage1: list[DeciderPerspective] = list(
        await asyncio.gather(
            *[
                agents.decider_stage1(role, deck, specialist_reports)
                for role in config.DECIDER_ROLES
            ]
        )
    )

    stage1_by_role = {p.role: p for p in stage1}

    stage2 = list(
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

    final_brief = await agents.synthesis(deck, specialist_reports, stage1, stage2)

    return RunOutput(
        pitch_deck=deck,
        specialist_reports=specialist_reports,
        stage1=stage1,
        stage2=stage2,
        final_brief=final_brief,
    )
