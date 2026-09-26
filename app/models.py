from pydantic import BaseModel, Field


class FactCheckReport(BaseModel):
    verified_claims: list[str] = Field(default_factory=list)
    disputed_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    verification_score: float = Field(ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class SupervisorDecision(BaseModel):
    approved: bool
    confidence: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=2000)


class HumanDecision(BaseModel):
    approved: bool
    feedback: str = Field(default="", max_length=5000)
