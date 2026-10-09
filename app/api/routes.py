from __future__ import annotations

import logging

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.answer import intent as answer_intent
from app.answer import service as answer_service
from app.auth.routes import require_session
from app.auth.service import Principal
from app.config import get_settings

from app.industry.service import IndustryService
from app.industry.universe import list_industries
from app.schemas import Claim, Conflict, ResearchRun, Source
from app.schemas.answer import DatabaseAnswer, NotAnswered
from app.schemas.industry import IndustrySnapshot, IndustrySummary
from app.schemas.ipo import IpoAskRequest, IpoAskResponse, IpoDetail, IpoSummary
from app.storage import repositories as repo
from app.storage.database import get_session
from app.storage.models import ResearchRunORM, SearchLogORM

logger = logging.getLogger("financial_research_agent.api")

router = APIRouter()


def db_session():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


class ResearchRequest(BaseModel):
    query: str
    # True = run fresh research even if the same question was answered recently.
    fresh: bool = False


def normalize_query(query: str) -> str:
    return " ".join(query.lower().split()).strip(" ?.!")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def log_search(db: Session, query: str, answered_from: str, principal: Principal | None, *,
               companies: list[str] | None = None, run_id: str | None = None, elapsed_ms: int | None = None) -> None:
    db.add(SearchLogORM(query=query, normalized_query=normalize_query(query), answered_from=answered_from,
                        companies=companies or [], research_run_id=run_id, elapsed_ms=elapsed_ms,
                        user_kind=principal.kind if principal else None, created_at=_now()))
    db.commit()


@router.post("/answer", response_model=DatabaseAnswer | NotAnswered)
def answer_question(req: ResearchRequest, db: Session = Depends(db_session), principal: Principal = Depends(require_session)):
    """Database first: answers questions about companies VeriFi holds
    straight from stored, verified filings (milliseconds). Returns
    answered=false when the database can't answer - the client then starts
    full research (POST /research)."""
    started = time.perf_counter()
    intent = answer_intent.parse(req.query)
    result = answer_service.answer(db, intent)
    elapsed = round((time.perf_counter() - started) * 1000)
    log_search(db, req.query, "database" if result.answered else "none", principal,
               companies=[c.nse for c in intent.companies], elapsed_ms=elapsed)
    return result


@router.get("/industries", response_model=list[IndustrySummary])
def get_industries():
    return list_industries()


@router.get("/industries/{industry_id}", response_model=IndustrySnapshot)
def get_industry_snapshot(industry_id: str, refresh: bool = False):
    """Peer metrics, consistency checks and revenue share for one industry,
    computed from the database. Companies with nothing stored are fetched
    from the source first; pass refresh=true to re-check every company's
    filings against the source now."""
    try:
        snapshot = IndustryService().get_snapshot(industry_id, force_refresh=refresh)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Industry snapshot failed for %s", industry_id)
        raise HTTPException(status_code=502, detail=f"Could not load industry data: {exc}") from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail="industry not found")
    return snapshot


@router.post("/research", response_model=ResearchRun, status_code=202)
def start_research(req: ResearchRequest, db: Session = Depends(db_session), principal: Principal = Depends(require_session)):
    """Returns immediately with status=PENDING and a research_run_id - the
    actual pipeline runs in a background thread (see
    ResearchOrchestrator.start_async). A fully real run with paced LLM
    calls can take minutes; blocking the HTTP response on that would hang
    the browser with no feedback and risk a silent timeout. Poll
    GET /research/{id} for live status until it reaches complete/failed."""
    from app.agents.research_orchestrator import PIPELINE_VERSION, ResearchOrchestrator

    if not req.fresh:
        since = _now() - timedelta(hours=get_settings().research_reuse_hours)
        wanted = normalize_query(req.query)
        for row in db.scalars(select(ResearchRunORM).where(ResearchRunORM.status == "complete", ResearchRunORM.updated_at >= since)
                              .order_by(ResearchRunORM.updated_at.desc())):
            if normalize_query(row.query) != wanted:
                continue
            run = repo.get_research_run(db, row.research_run_id)
            if run is None or run.pipeline_version != PIPELINE_VERSION:
                continue
            log_search(db, req.query, "cache", principal, run_id=row.research_run_id, elapsed_ms=0)
            return run

    orchestrator = ResearchOrchestrator(db)
    try:
        run = orchestrator.start_async(req.query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to queue research run for query=%r", req.query)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    log_search(db, req.query, "research", principal, run_id=run.research_run_id)
    return run


@router.get("/research/{research_id}", response_model=ResearchRun)
def get_research(research_id: str, db: Session = Depends(db_session)):
    run = repo.get_research_run(db, research_id)
    if not run:
        raise HTTPException(status_code=404, detail="research run not found")
    return run


@router.get("/research/{research_id}/claims", response_model=list[Claim])
def get_research_claims(research_id: str, db: Session = Depends(db_session)):
    return repo.get_claims_for_run(db, research_id)


@router.get("/research/{research_id}/sources", response_model=list[Source])
def get_research_sources(research_id: str, db: Session = Depends(db_session)):
    return repo.get_sources_for_run(db, research_id)


@router.get("/research/{research_id}/conflicts", response_model=list[Conflict])
def get_research_conflicts(research_id: str, db: Session = Depends(db_session)):
    return repo.get_conflicts_for_run(db, research_id)


@router.get("/research/{research_id}/report")
def get_research_report(research_id: str, db: Session = Depends(db_session)):
    report = repo.get_report_for_run(db, research_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report


def _ipo_summary(row) -> IpoSummary:
    return IpoSummary(
        ipo_id=row.ipo_id, company_name=row.company_name, symbol=row.symbol, board=row.board,
        status=row.status, exchange=row.exchange, open_date=row.open_date, close_date=row.close_date,
        listing_date=row.listing_date,
        price_band_low=float(row.price_band_low) if row.price_band_low is not None else None,
        price_band_high=float(row.price_band_high) if row.price_band_high is not None else None,
        lot_size=row.lot_size, issue_size_cr=float(row.issue_size_cr) if row.issue_size_cr is not None else None,
    )


@router.get("/ipos", response_model=list[IpoSummary])
def list_ipos(board: str = "mainboard", db: Session = Depends(db_session)):
    """Upcoming/open/closed/listed IPOs, soonest-closing first. board="" returns every board."""
    return [_ipo_summary(row) for row in repo.list_ipos(db, board=board or None)]


@router.get("/ipos/{ipo_id}", response_model=IpoDetail)
def get_ipo(ipo_id: str, db: Session = Depends(db_session)):
    row = repo.get_ipo(db, ipo_id)
    if not row:
        raise HTTPException(status_code=404, detail="IPO not found")
    summary = _ipo_summary(row)
    return IpoDetail(
        **summary.model_dump(), face_value=float(row.face_value) if row.face_value is not None else None,
        fresh_issue_cr=float(row.fresh_issue_cr) if row.fresh_issue_cr is not None else None,
        ofs_cr=float(row.ofs_cr) if row.ofs_cr is not None else None, registrar=row.registrar,
        lead_managers=row.lead_managers or [], about=row.about, payload=row.payload or {},
        has_report=bool(row.report_text), updated_at=row.updated_at,
    )


IPO_ASK_SYSTEM_PROMPT = (
    "You answer questions about an IPO using ONLY the excerpt of its official report given below. "
    "Never use outside knowledge, never guess, and never state a number that is not in the excerpt. "
    "If the excerpt does not contain the answer, say plainly that the report does not mention it - "
    "do not speculate about what it might say."
)


@router.post("/ipos/{ipo_id}/ask", response_model=IpoAskResponse)
def ask_ipo(ipo_id: str, req: IpoAskRequest, db: Session = Depends(db_session)):
    """Answers a free-text question strictly from this IPO's stored report
    text - never from payload, never from the LLM's own knowledge. The same
    RAG chunk-retrieval used by the research pipeline's Claim Extractor
    (app/rag/indexer.py) picks the most relevant excerpt first, so the
    question is answered from the right section of a long report rather
    than whatever happened to be first."""
    from app.llm import get_llm_provider
    from app.rag import retrieve_relevant_text

    row = repo.get_ipo(db, ipo_id)
    if not row:
        raise HTTPException(status_code=404, detail="IPO not found")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    if not row.report_text:
        return IpoAskResponse(answer="No report has been added for this IPO yet, so there is nothing to search.", grounded=False)

    excerpt = retrieve_relevant_text(row.report_text, question, max_chars=6000)
    llm = get_llm_provider()
    if llm is None:
        return IpoAskResponse(
            answer="The AI answerer isn't configured right now - showing the most relevant excerpt from the report instead.",
            grounded=False, excerpt=excerpt,
        )
    user_prompt = f"Report excerpt:\n\"\"\"\n{excerpt}\n\"\"\"\n\nQuestion: {question}"
    answer = llm.complete(IPO_ASK_SYSTEM_PROMPT, user_prompt, max_tokens=500)
    return IpoAskResponse(answer=answer.strip(), grounded=True, excerpt=excerpt)
