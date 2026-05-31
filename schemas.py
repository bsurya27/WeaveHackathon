from pydantic import BaseModel


class PitchDeck(BaseModel):
    company: str
    tagline: str
    problem: str
    solution: str
    market: str
    team: str
    ask: str


class SpecialistReport(BaseModel):
    role: str
    findings: str


class DeciderPerspective(BaseModel):
    role: str
    perspective: str


class DeciderReaction(BaseModel):
    role: str
    reaction: str


class FinalBrief(BaseModel):
    recommendation: str
    summary: str
