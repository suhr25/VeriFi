from __future__ import annotations

from pydantic import BaseModel, Field


class CompanyEntity(BaseModel):
    name: str
    ticker: str | None = None
    cik: str | None = Field(default=None, description="SEC Central Index Key, zero-padded to 10 digits")
    exchange: str | None = None
    aliases: list[str] = Field(default_factory=list)
    resolved: bool = True
    resolution_notes: str | None = None
