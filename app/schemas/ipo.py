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
    has_report: bool
    updated_at: datetime


class IpoAskRequest(BaseModel):
    question: str


class IpoAskResponse(BaseModel):
    answer: str
    grounded: bool
    excerpt: str | None = None
