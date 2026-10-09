from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    content: str
    claim_ids: list[str] = Field(default_factory=list)


class ComparisonTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[dict]


class Report(BaseModel):
    report_id: str = Field(default_factory=lambda: f"rpt_{uuid4().hex[:12]}")
    research_run_id: str
    company_summary: str
    executive_overview: ReportSection
    financial_performance: ReportSection
    key_metrics: ReportSection
    risks: ReportSection
    important_findings: ReportSection
    conflicting_information: ReportSection
    claim_verification_summary: ReportSection
    sources_section: ReportSection
    comparison_tables: list[ComparisonTable] = Field(default_factory=list)

    total_claims: int = 0
    supported_claims: int = 0
    contradicted_claims: int = 0
    insufficient_claims: int = 0
    average_confidence: float | None = None
