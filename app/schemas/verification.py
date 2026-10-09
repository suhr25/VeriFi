from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import VerificationVerdict


class NumericMatchResult(BaseModel):
    applicable: bool
    exact_match: bool = False
    normalized_match: bool = False
    percent_difference: float | None = None
    period_match: bool | None = None
    basis_match: bool | None = None
    unit_currency_converted: bool = False
    notes: str = ""


class EntailmentResult(BaseModel):
    verdict: VerificationVerdict
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class VerificationResult(BaseModel):
    claim_id: str
    numeric_result: NumericMatchResult | None = None
    entailment_result: EntailmentResult
    final_verdict: VerificationVerdict
    combined_reason: str
