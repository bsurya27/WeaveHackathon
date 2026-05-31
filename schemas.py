from pydantic import BaseModel


class PitchDeck(BaseModel):
    problem: str
    customer: str
    solution: str
    wedge: str
    current_stage: str
    founder_background: str
    traction: str
    key_assumptions: list[str]
    current_ask: str


class FocusItem(BaseModel):
    title: str
    why_now: str
    action: str
    success_criteria: str
    evidence_citations: list[str]


class WatchItem(BaseModel):
    trigger: str
    why_it_matters: str


class SpecialistReport(BaseModel):
    role: str
    focus_items: list[FocusItem]
    watch_items: list[WatchItem]
    assumptions_made: list[str]
    founder_questions: list[str]
    strategic_questions: list[str]


class DeciderPerspective(BaseModel):
    role: str
    key_findings: list["KeyFinding"]
    priority_actions: list[str]


class KeyFinding(BaseModel):
    finding: str
    citation: str
    confidence: int


class DeciderReaction(BaseModel):
    role: str
    reacting_to: list[str]
    agreements: list["Agreement"]
    pushbacks: list["Pushback"]
    missed_by_them: list["Missed"]


class Agreement(BaseModel):
    point: str
    why: str


class Pushback(BaseModel):
    point: str
    counter: str


class Missed(BaseModel):
    point: str
    why_it_matters: str


class FinalBrief(BaseModel):
    recommendation: str
    summary: str
