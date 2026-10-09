from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalCase:
    case_id: str
    entity: str
    metric: str
    claim_type: str
    claim_value: str
    claim_unit: str | None
    claim_period: str | None
    claim_basis: str
    evidence_text: str
    expected_verdict: str
    scenario: str


ENTITIES = ["Apple Inc.", "Microsoft Corporation"]

METRIC_TEMPLATES = [
    ("revenue", "85.8", "billion", "88.5", "million", ("85800", "million")),
    ("net_income", "21.4", "billion", "19.0", "million", ("21400", "million")),
    ("operating_margin", "29.6", "%", "24.0", None, None),
    ("ebitda", "30.1", "billion", "25.0", "million", ("30100", "million")),
    ("eps_diluted", "1.40", "USD", "1.10", None, None),
    ("cash_and_equivalents", "28.4", "billion", "20.0", "million", None),
]

QUALITATIVE_STATEMENTS = [
    "The company faces substantial competition in all of the markets in which it operates.",
    "Ongoing supply chain constraints could materially affect future results.",
    "Foreign currency fluctuations pose a continuing risk to reported revenue.",
]

UNRELATED_TEXT = (
    "The company announced a new sustainability initiative focused on renewable energy sourcing "
    "for its data centers, alongside a refreshed corporate design system for its retail locations."
)


def build_eval_set() -> list[EvalCase]:
    cases: list[EvalCase] = []
    n = 0

    for entity in ENTITIES:
        for metric, base_val, unit, wrong_val, wrong_unit, scale_alt in METRIC_TEMPLATES:
            n += 1
            period = "Q3 2024"

            evidence = f"{metric.replace('_', ' ').title()} was {_fmt(base_val, unit)} for {period}."

            cases.append(EvalCase(f"case_{n:03d}_exact", entity, metric, "numeric", base_val, unit, period, "unknown", evidence, "supported", "exact_match"))
            n += 1

            cases.append(EvalCase(f"case_{n:03d}_wrongnum", entity, metric, "numeric", wrong_val, unit, period, "unknown", evidence, "contradicted", "wrong_number"))
            n += 1

            other_period = "Q2 2024"
            evidence_other_period = f"{metric.replace('_', ' ').title()} was {_fmt(base_val, unit)} for {other_period}."
            cases.append(EvalCase(f"case_{n:03d}_wrongperiod", entity, metric, "numeric", base_val, unit, period, "unknown", evidence_other_period, "insufficient", "wrong_period"))
            n += 1

            cases.append(EvalCase(f"case_{n:03d}_nomention", entity, metric, "numeric", base_val, unit, period, "unknown", UNRELATED_TEXT, "insufficient", "no_mention"))
            n += 1

            if wrong_unit:
                cases.append(EvalCase(f"case_{n:03d}_wrongunit", entity, metric, "numeric", base_val, wrong_unit, period, "unknown", evidence, "contradicted", "wrong_unit"))
                n += 1

            if scale_alt:
                alt_val, alt_unit = scale_alt
                alt_evidence = f"{metric.replace('_', ' ').title()} was {_fmt(alt_val, alt_unit)} for {period}."
                cases.append(EvalCase(f"case_{n:03d}_scaleequiv", entity, metric, "numeric", base_val, unit, period, "unknown", alt_evidence, "supported", "scale_equivalent"))
                n += 1

        for statement in QUALITATIVE_STATEMENTS:
            n += 1
            cases.append(EvalCase(f"case_{n:03d}_qualsupported", entity, "risk_factor", "qualitative", statement, None, None, "unknown", statement, "supported", "qualitative_direct_support"))
            n += 1
            cases.append(EvalCase(f"case_{n:03d}_qualinsufficient", entity, "risk_factor", "qualitative", statement, None, None, "unknown", UNRELATED_TEXT, "insufficient", "qualitative_no_mention"))

    return cases


def _fmt(value: str, unit: str) -> str:
    if unit == "%":
        return f"approximately {value}%"
    if unit == "USD":
        return f"${value}"
    return f"${value} {unit}"
