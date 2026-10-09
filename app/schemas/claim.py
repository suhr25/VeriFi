from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.enums import Basis, ClaimType, PeriodType, VerificationVerdict
from app.schemas.source import Evidence


class NormalizedValue(BaseModel):
    raw_value: str
    magnitude: float | None = None
    base_unit: str | None = None
    scale_applied: str | None = None
    period_type: PeriodType = PeriodType.UNKNOWN
    period_label: str | None = None
    basis: Basis = Basis.UNKNOWN
    normalization_notes: str | None = None


class Claim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm_{uuid4().hex[:12]}")
    research_run_id: str

    claim_type: ClaimType

    entity: str
    metric: str
    value: str
    unit: str | None = None
    period: str | None = None
    basis: Basis = Basis.UNKNOWN

    normalized: NormalizedValue | None = None

    source_id: str
    evidence_span: Evidence

    verification_status: VerificationVerdict | None = None
    verification_reason: str | None = None
    confidence: float | None = None
    confidence_breakdown: dict[str, float] | None = None

    statement: str
