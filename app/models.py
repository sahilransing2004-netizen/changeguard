from enum import Enum
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AnalyzeRequest(BaseModel):
    diff: str = Field(..., min_length=1)
    title: str = ""

class ChangeSummary(BaseModel):
    files: list[str]
    added: int
    removed: int
    categories: list[str]   # e.g. "kubernetes", "terraform", "ci", "app"

class Verdict(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    level: RiskLevel
    reasons: list[str]
    summary: ChangeSummary
    source: str = "heuristic"
