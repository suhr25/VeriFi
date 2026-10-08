"""SQLAlchemy ORM models.

Design choice: each table stores its corresponding Pydantic model as a JSON
blob (`payload`) plus a handful of indexed columns needed for querying and
joins. This keeps the storage layer simple (single source of truth is the
Pydantic schema in app/schemas/, not a parallel hand-maintained ORM schema)
while still preserving the PRD's required conceptual separation between
sources / claims / evidence / verification_results / conflicts /
research_runs / reports as distinct tables.
"""
from __future__ import annotations

from datetime import datetime

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class ResearchRunORM(Base):
    __tablename__ = "research_runs"

    research_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    query: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    payload: Mapped[dict] = mapped_column(JSON)


class SourceORM(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    source_tier: Mapped[str] = mapped_column(String)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)
    payload: Mapped[dict] = mapped_column(JSON)


class ClaimORM(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[str] = mapped_column(String, index=True)
    entity: Mapped[str] = mapped_column(String, index=True)
    metric: Mapped[str] = mapped_column(String, index=True)
    verification_status: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)


class EvidenceORM(Base):
    """Evidence is embedded inside Claim.evidence_span in the Pydantic model
    and inside VerificationResult, but is also persisted standalone here so
    it can be queried/audited independent of a claim (PRD section 8)."""

    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[str] = mapped_column(String, index=True)
    claim_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)


class VerificationResultORM(Base):
    __tablename__ = "verification_results"

    verification_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True)
    claim_id: Mapped[str] = mapped_column(String, index=True)
    final_verdict: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ConflictORM(Base):
    __tablename__ = "conflicts"

    conflict_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True)
    entity: Mapped[str] = mapped_column(String, index=True)
    metric: Mapped[str] = mapped_column(String, index=True)
    is_genuine_conflict: Mapped[bool] = mapped_column()
    payload: Mapped[dict] = mapped_column(JSON)


class ReportORM(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    payload: Mapped[dict] = mapped_column(JSON)


# ---- Authentication ---------------------------------------------------------


class UserORM(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    # Null for an account that only ever signed in via Google or a magic
    # link - there is no password to check, and a password-login attempt
    # against such an account is rejected with a clear message rather than
    # crashing on a None hash (see app/auth/service.authenticate).
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # "viewer" can read and ask; "admin" can also upload and edit data.
    role: Mapped[str] = mapped_column(String, default="viewer", server_default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class EmailLoginTokenORM(Base):
    """A one-time magic-link sign-in token. Only its SHA-256 is stored, same
    principle as SessionORM - a leaked database can't be used to sign in as
    anyone. Short-lived (see app/auth/service.MAGIC_LINK_MINUTES) and single
    use (`used`), so a link only works once and only shortly after it was
    requested."""

    __tablename__ = "email_login_tokens"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SessionORM(Base):
    """A login session. Only the SHA-256 of the session token is stored, so a
    leaked database can't be replayed as live cookies."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # "user" | "demo"
    user_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


# ---- Financial data store ------------------------------------------------------
#
# The database is the primary source of truth for financial data: everything
# fetched from an API or uploaded by an admin is stored here, and questions are
# answered from here first. Unlike the research tables above, these use real
# typed columns (not JSON blobs) so they can be queried directly.


class CompanyORM(Base):
    __tablename__ = "companies"

    company_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    short_name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    isin: Mapped[str | None] = mapped_column(String, nullable=True)
    industry_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    tier: Mapped[str | None] = mapped_column(String, nullable=True)
    # When this company's filings were last checked against the source API.
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class DocumentORM(Base):
    """A source document: a quarterly result or annual report pulled from the
    exchange, or a file (e.g. an IPO prospectus) uploaded by an admin. Every
    financial fact points back to the document it came from."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_company_type_period", "company_id", "doc_type", "period_end"),
    )

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.company_id"), index=True)
    doc_type: Mapped[str] = mapped_column(String, index=True)  # quarterly_result | annual_report | drhp | rhp | prospectus | other
    title: Mapped[str] = mapped_column(String)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    consolidated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String)  # exchange_api | upload | seed
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # sha256 of the source URL (API documents) or file bytes (uploads) -
    # makes ingestion idempotent: the same document is never stored twice.
    checksum: Mapped[str] = mapped_column(String, unique=True)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audited: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="verified")  # verified | pending_review | rejected
    notes: Mapped[list] = mapped_column(JSON, default=list)
    uploaded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime)


class FinancialFactORM(Base):
    """One number: a metric of one company for one period, taken from one
    document. "Every number has a story" - the story is document_id, origin
    and verification_status."""

    __tablename__ = "financial_facts"
    __table_args__ = (
        UniqueConstraint("document_id", "metric", "period_type", "period_end", name="uq_fact_per_document"),
        Index("ix_facts_lookup", "company_id", "metric", "period_type", "period_end"),
    )

    fact_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.company_id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String)
    period_type: Mapped[str] = mapped_column(String)  # quarter | annual
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date] = mapped_column(Date)
    consolidated: Mapped[bool] = mapped_column(Boolean, default=True)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    unit: Mapped[str] = mapped_column(String)  # INR | INR_per_share
    origin: Mapped[str] = mapped_column(String)  # xbrl | manual | pdf_extracted
    verification_status: Mapped[str] = mapped_column(String, default="verified")  # verified | corrected | unverified
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class IngestionRunORM(Base):
    """Audit log: every sync from an API or upload, with what it changed."""

    __tablename__ = "ingestion_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)  # company_sync | seed | upload
    target: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)  # running | success | failed
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IpoORM(Base):
    """One IPO: the fixed listing details plus the full text of its official
    report (DRHP/RHP/prospectus), stored verbatim so the per-IPO search bar
    can ground every answer in that exact text - never a guess. Structured
    sections (financial summary, objects of issue, risk factors, promoters,
    ...) live in `payload` as flexible JSON, matching the payload pattern
    used by the research tables above, since an IPO document's sections
    vary too much company to company to force into fixed columns."""

    __tablename__ = "ipos"

    ipo_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    board: Mapped[str] = mapped_column(String, index=True)  # mainboard | sme
    status: Mapped[str] = mapped_column(String, index=True)  # upcoming | open | closed | listed
    exchange: Mapped[str] = mapped_column(String)  # NSE | BSE | NSE+BSE
    open_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    price_band_low: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    price_band_high: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    lot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    issue_size_cr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fresh_issue_cr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ofs_cr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    registrar: Mapped[str | None] = mapped_column(String, nullable=True)
    lead_managers: Mapped[list] = mapped_column(JSON, default=list)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full report text (verbatim) - the only thing the Ask box is allowed to
    # answer from. Never summarized or rewritten on the way in.
    report_text: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class SearchLogORM(Base):
    """Every question asked, and where its answer came from - the database
    (instant), a reused earlier research run, or a new research run."""

    __tablename__ = "search_log"

    search_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text)
    normalized_query: Mapped[str] = mapped_column(String, index=True)
    answered_from: Mapped[str] = mapped_column(String, index=True)  # database | cache | research | none
    companies: Mapped[list] = mapped_column(JSON, default=list)
    research_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
