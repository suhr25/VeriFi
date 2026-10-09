from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class IndustryCompanyRef(BaseModel):
    name: str
    short_name: str
    symbol: str
    nse: str
    tier: str
    aliases: list[str] = Field(default_factory=list)


class IndustryDefinition(BaseModel):
    id: str
    name: str
    short_name: str
    universe: str
    description: str
    currency: str
    benchmark_symbol: str | None = None
    companies: list[IndustryCompanyRef]


class IndustrySummary(BaseModel):
    id: str
    name: str
    short_name: str
    universe: str
    description: str
    company_count: int


CheckStatus = Literal["verified", "mismatch", "unavailable"]


class CrossCheck(BaseModel):
    metric: str
    label: str
    reported: float | None = None
    recomputed: float | None = None
    difference_pct: float | None = None
    tolerance_pct: float
    status: CheckStatus
    detail: str
    informational: bool = False


class QuarterPoint(BaseModel):
    period_end: str
    revenue: float | None = None
    net_income: float | None = None
    operating_profit: float | None = None
    eps_diluted: float | None = None
    filed_at: str | None = None
    audited: str | None = None
    filing_url: str | None = None
    notes: list[str] = Field(default_factory=list)


class CompanyMetrics(BaseModel):
    name: str
    short_name: str
    symbol: str
    nse: str
    tier: str
    available: bool = True
    error: str | None = None

    shares_outstanding: float | None = None
    revenue_ttm: float | None = None
    net_income_ttm: float | None = None
    eps_ttm: float | None = None
    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    operating_margin: float | None = None
    profit_margin: float | None = None
    revenue_share: float | None = None

    latest_quarter: str | None = None
    quarters: list[QuarterPoint] = Field(default_factory=list)
    checks: list[CrossCheck] = Field(default_factory=list)
    verification_status: CheckStatus = "unavailable"


class MetricAggregate(BaseModel):
    metric: str
    median: float | None = None
    mean: float | None = None
    weighted_mean: float | None = None
    min: float | None = None
    max: float | None = None
    leader: str | None = None
    laggard: str | None = None
    count: int = 0


class Concentration(BaseModel):
    total_revenue: float | None = None
    hhi: float | None = None
    effective_companies: float | None = None
    top3_share: float | None = None
    largest: str | None = None
    largest_share: float | None = None


class Insight(BaseModel):
    kind: Literal["concentration", "growth", "profitability", "earnings", "data"]
    title: str
    detail: str


class IndustrySnapshot(BaseModel):
    industry: IndustrySummary
    mode: Literal["live", "demo"]
    currency: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fetch_seconds: float | None = None
    stale: bool = False
    refreshing: bool = False
    synced_at: datetime | None = None
    source: str = "Companies' reported quarterly results (consolidated), stored in the VeriFi database"
    companies: list[CompanyMetrics]
    aggregates: dict[str, MetricAggregate] = Field(default_factory=dict)
    concentration: Concentration = Field(default_factory=Concentration)
    insights: list[Insight] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
