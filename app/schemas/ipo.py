"""IPO Centre schemas.

An IPO's fixed listing details are plain fields; everything else that
varies document to document (financial summary table, objects of issue,
risk factors, promoters, anchor investors...) lives in `payload` as
freeform JSON - mirrored by IpoDetail.payload below. The Ask endpoint
never touches payload - it answers only from the stored report_text (see
IpoAskResponse.grounded), so a structured field and a free-text answer can
never silently drift apart.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class IpoSummary(BaseModel):
    ipo_id: str
    company_name: str
    symbol: str
    board: str
    status: str
    exchange: str
    open_date: date | None = None
    close_date: date | None = None
    listing_date: date | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None


class IpoDetail(IpoSummary):
    face_value: float | None = None
    fresh_issue_cr: float | None = None
    ofs_cr: float | None = None
    registrar: str | None = None
    lead_managers: list[str] = []
    about: str | None = None
    payload: dict = {}
    has_report: bool  # whether report_text is non-empty - the Ask box depends on this
    updated_at: datetime


class IpoAskRequest(BaseModel):
    question: str


class IpoAskResponse(BaseModel):
    answer: str
    # True = the LLM answered strictly from a retrieved excerpt of the
    # stored report. False = no LLM was available and the excerpt itself is
    # shown instead - still grounded, just not phrased as a sentence.
    grounded: bool
    excerpt: str | None = None
