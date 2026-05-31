import json
import uuid
from pathlib import Path
from typing import Any

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
    session_id: str | None = None,
    followups: list[dict[str, Any]] | None = None,
) -> str:
    sid = session_id or uuid.uuid4().hex[:12]
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{sid}.json"
    payload = {
        "session_id": sid,
        "pitch_deck": pitch_deck.model_dump(),
        "specialist_reports": [r.model_dump() for r in specialist_reports],
        "decider_stage1": [p.model_dump() for p in stage1],
        "decider_stage2": [r.model_dump() for r in stage2],
        "final_brief": final_brief.model_dump(),
        "followups": followups or [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sid


def load_session(session_id: str) -> dict[str, Any]:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def append_followup(
    session_id: str,
    question: str,
    answer: str,
    target_role: str,
) -> None:
    data = load_session(session_id)
    data.setdefault("followups", []).append(
        {
            "question": question,
            "answer": answer,
            "target_role": target_role,
        }
    )
    path = SESSIONS_DIR / f"{session_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
