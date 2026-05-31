import json
import uuid
from pathlib import Path

from schemas import (
    DeciderPerspective,
    DeciderReaction,
    FinalBrief,
    PitchDeck,
    SpecialistReport,
)

SESSIONS_DIR = Path("sessions")


def save_session(
    pitch_deck: PitchDeck,
    specialist_reports: list[SpecialistReport],
    stage1: list[DeciderPerspective],
    stage2: list[DeciderReaction],
    final_brief: FinalBrief,
) -> str:
    session_id = uuid.uuid4().hex[:12]
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{session_id}.json"
    payload = {
        "session_id": session_id,
        "pitch_deck": pitch_deck.model_dump(),
        "specialist_reports": [r.model_dump() for r in specialist_reports],
        "decider_stage1": [p.model_dump() for p in stage1],
        "decider_stage2": [r.model_dump() for r in stage2],
        "final_brief": final_brief.model_dump(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return session_id
