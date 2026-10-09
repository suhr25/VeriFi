from __future__ import annotations

import re

from app.analysis.normalizer import SCALE_FACTORS
from app.schemas import Basis, Claim, ClaimType, NumericMatchResult

_NUMBER_RE = re.compile(
    r"(?P<currency>[$₹])?\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<scale>billion|million|thousand|trillion|crore|lakh)?",
    re.IGNORECASE,
)

EXACT_MATCH_TOLERANCE_PCT = 0.5
CONTRADICTION_THRESHOLD_PCT = 2.0


def _find_candidate_magnitudes(text: str) -> list[tuple[float, str]]:
    candidates: list[tuple[float, str]] = []
    for m in _NUMBER_RE.finditer(text):
        end = m.end()
        num = float(m.group("num").replace(",", ""))
        if text[end : end + 1] == "%":
            candidates.append((num, "%"))
            continue
        scale = (m.group("scale") or "").lower()
        currency_symbol = m.group("currency")
        if not scale and not currency_symbol:
            continue
        magnitude = num * SCALE_FACTORS[scale] if scale else num
        base_unit = "INR" if (currency_symbol == "₹" or scale in ("crore", "lakh")) else "USD"
        candidates.append((magnitude, base_unit))
    return candidates


def _exact_match(value: str, unit: str | None, evidence_text: str) -> bool:
    value_str = value.strip()
    if not value_str or value_str not in evidence_text:
        return False
    unit_l = (unit or "").strip().lower()
    if unit_l in SCALE_FACTORS:
        idx = evidence_text.find(value_str)
        window = evidence_text[idx : idx + len(value_str) + 20].lower()
        return unit_l in window
    return True


def _period_match(claim_period: str | None, evidence_text: str) -> bool | None:
    if not claim_period:
        return None
    evidence_lower = evidence_text.lower()
    quarter = re.search(r"\bQ[1-4]\b", claim_period, re.IGNORECASE)
    year = re.search(r"\b20\d{2}\b", claim_period)
    checks = []
    if quarter:
        checks.append(re.search(rf"\b{quarter.group(0)}\b", evidence_text, re.IGNORECASE) is not None)
    if year:
        checks.append(year.group(0) in evidence_lower)
    if not checks:
        return claim_period.lower() in evidence_lower
    return all(checks)


def _infer_basis_in_text(text: str) -> Basis:
    t = text.lower()
    if "non-gaap" in t:
        return Basis.NON_GAAP
    if "adjusted" in t:
        return Basis.ADJUSTED
    if "gaap" in t:
        return Basis.GAAP
    return Basis.UNKNOWN


class NumericMatcher:
    def match(self, claim: Claim) -> NumericMatchResult:
        if claim.claim_type != ClaimType.NUMERIC or not claim.normalized or claim.normalized.magnitude is None:
            return NumericMatchResult(applicable=False, notes="Not a numeric claim with a parseable magnitude")

        evidence_text = claim.evidence_span.evidence_text
        claim_magnitude = claim.normalized.magnitude
        claim_unit = claim.normalized.base_unit

        exact_match = _exact_match(claim.value, claim.unit, evidence_text)

        candidates = _find_candidate_magnitudes(evidence_text)
        same_unit = [(mag, unit) for mag, unit in candidates if unit == claim_unit]

        best_diff: float | None = None
        for mag, _unit in same_unit:
            if mag == 0 and claim_magnitude == 0:
                diff = 0.0
            elif mag == 0:
                continue
            else:
                diff = abs(claim_magnitude - mag) / abs(mag) * 100
            if best_diff is None or diff < best_diff:
                best_diff = diff

        normalized_match = best_diff is not None and best_diff <= EXACT_MATCH_TOLERANCE_PCT
        percent_difference = round(best_diff, 4) if best_diff is not None else None

        period_match = _period_match(claim.period, evidence_text)

        basis_match: bool | None = None
        if claim.basis != Basis.UNKNOWN:
            inferred = _infer_basis_in_text(evidence_text)
            basis_match = (inferred == claim.basis) if inferred != Basis.UNKNOWN else None

        unit_currency_converted = bool(candidates) and not same_unit

        if exact_match:
            notes = "exact textual value match found in evidence"
        elif normalized_match:
            notes = f"normalized numeric match within {EXACT_MATCH_TOLERANCE_PCT}% tolerance (diff={percent_difference}%)"
        elif best_diff is not None:
            notes = f"closest comparable figure in evidence differs by {percent_difference}%"
        elif unit_currency_converted:
            notes = "evidence contains numeric figures but none share the claim's unit/currency"
        else:
            notes = "no comparable numeric value found in evidence text"

        return NumericMatchResult(
            applicable=True,
            exact_match=exact_match,
            normalized_match=normalized_match or exact_match,
            percent_difference=percent_difference,
            period_match=period_match,
            basis_match=basis_match,
            unit_currency_converted=unit_currency_converted,
            notes=notes,
        )
