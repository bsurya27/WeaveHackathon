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


def empty_pitch_deck() -> PitchDeck:
    return PitchDeck(
        problem="",
        customer="",
        solution="",
        wedge="",
        current_stage="",
        founder_background="",
        traction="",
        key_assumptions=[],
        current_ask="",
    )


class IntakeUpdates(BaseModel):
    problem: str | None = None
    customer: str | None = None
    solution: str | None = None
    wedge: str | None = None
    current_stage: str | None = None
    founder_background: str | None = None
    traction: str | None = None
    key_assumptions: list[str] | None = None
    current_ask: str | None = None


class IntakeTurn(BaseModel):
    updates: IntakeUpdates
    next_question: str | None = None
    done: bool = False


class FollowupReply(BaseModel):
    reply: str


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


class FocusListItem(BaseModel):
    title: str
    action: str
    success_criteria: str
    rationale: str


class WatchlistItem(BaseModel):
    trigger: str
    why_it_matters: str


class TerrainMap(BaseModel):
    marketer: str
    legal: str
    tech: str
    finance: str


class Disagreement(BaseModel):
    topic: str
    investor_view: str
    devils_advocate_view: str
    innovator_view: str
    resolution_question: str


class FinalBrief(BaseModel):
    focus_list: list[FocusListItem]
    watchlist: list[WatchlistItem]
    deprioritize_list: list[str]
    terrain_map_by_domain: TerrainMap
    advisor_disagreements: list[Disagreement]
    open_questions_for_founder: list[str]
    how_constructed: str
