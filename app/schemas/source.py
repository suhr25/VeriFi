from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import SourceTier, SourceType


class Source(BaseModel):
    source_id: str = Field(default_factory=lambda: f"src_{uuid4().hex[:12]}")
    title: str
    url: str | None = None
    source_type: SourceType
    source_tier: SourceTier
    publisher: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    document_text: str
    metadata: dict = Field(default_factory=dict)

    def slice(self, start_char: int, end_char: int) -> str:
        return self.document_text[start_char:end_char]


class Evidence(BaseModel):
    source_id: str
    start_char: int
    end_char: int
    evidence_text: str

    @model_validator(mode="after")
    def _validate_span(self) -> "Evidence":
        if self.start_char < 0 or self.end_char < self.start_char:
            raise ValueError(f"Invalid span [{self.start_char}, {self.end_char}]")
        return self
