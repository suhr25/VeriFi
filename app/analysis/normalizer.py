from __future__ import annotations

import re

from app.schemas import Claim, ClaimType, NormalizedValue, PeriodType

SCALE_FACTORS = {
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
    "trillion": 1e12,
    "lakh": 1e5,
    "crore": 1e7,
}


def _detect_currency(evidence_text: str, unit: str) -> str | None:
    t = f"{evidence_text} {unit}".lower()
    if "₹" in evidence_text or "inr" in t or "rs." in t or "rupee" in t or "crore" in t or "lakh" in t:
        return "INR"
    if "$" in evidence_text or "usd" in t or "dollar" in t:
        return "USD"
    return None


def normalize_value(value: str, unit: str | None, evidence_text: str) -> tuple[float | None, str | None, str | None]:
    cleaned = re.sub(r"[,\s]", "", value or "")
    cleaned = cleaned.lstrip("$₹")
    try:
        num = float(cleaned)
    except ValueError:
        return None, None, None

    unit_l = (unit or "").strip().lower()
    currency = _detect_currency(evidence_text, unit_l)

    scale_key = next(
        (key for key in SCALE_FACTORS if re.search(rf"\b{key}s?\b", unit_l)), None
    )
    if scale_key:
        magnitude = num * SCALE_FACTORS[scale_key]
        base_unit = currency or "USD"
        return magnitude, base_unit, f"{scale_key}->{base_unit}"

    if "%" in unit_l or re.search(r"\bpercent(age)?\b", unit_l):
        return num, "%", None

    base_unit = currency or (unit_l.upper() if unit_l else None) or "USD"
    return num, base_unit, None


PERIOD_QUARTER_RE = re.compile(r"\bQ[1-4]\b", re.IGNORECASE)


def infer_period_type(period: str | None) -> PeriodType:
    if not period:
        return PeriodType.UNKNOWN
    p = period.upper()
    if PERIOD_QUARTER_RE.search(p) or "QUARTER" in p:
        return PeriodType.QUARTERLY
    if "TTM" in p or "TRAILING" in p:
        return PeriodType.TTM
    if p.startswith("FY") or "ANNUAL" in p or "FULL YEAR" in p or "FISCAL YEAR" in p:
        return PeriodType.ANNUAL
    if re.fullmatch(r"20\d{2}", p):
        return PeriodType.ANNUAL
    return PeriodType.UNKNOWN


class ClaimNormalizer:
    def normalize(self, claims: list[Claim]) -> list[Claim]:
        for claim in claims:
            claim.normalized = self._normalize_one(claim)
        return claims

    def _normalize_one(self, claim: Claim) -> NormalizedValue:
        period_type = infer_period_type(claim.period)
        if claim.claim_type != ClaimType.NUMERIC:
            return NormalizedValue(
                raw_value=claim.value,
                period_type=period_type,
                period_label=claim.period,
                basis=claim.basis,
            )

        magnitude, base_unit, scale_note = normalize_value(
            claim.value, claim.unit, claim.evidence_span.evidence_text
        )
        notes = None if magnitude is not None else f"Could not parse a numeric magnitude from '{claim.value}'"
        return NormalizedValue(
            raw_value=claim.value,
            magnitude=magnitude,
            base_unit=base_unit,
            scale_applied=scale_note,
            period_type=period_type,
            period_label=claim.period,
            basis=claim.basis,
            normalization_notes=notes,
        )
