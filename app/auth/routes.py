"""Auth endpoints, the session dependency that protects the app's APIs, and
the small public API the login page uses.

Public:     /api/health, /api/public/overview, /api/auth/*
Protected:  everything else under /api (research + industry data)
"""
from __future__ import annotations

import logging
from datetime import datetime

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.email import EmailError, send_login_link_email
from app.auth.oauth import oauth
from app.config import get_settings
from app.storage.database import get_session

logger = logging.getLogger("financial_research_agent.auth")

auth_router = APIRouter(prefix="/auth", tags=["auth"])
public_router = APIRouter(tags=["public"])


def db_session():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def require_session(request: Request, db: Session = Depends(db_session)) -> service.Principal:
    principal = service.resolve_session(db, request.cookies.get(service.SESSION_COOKIE))
    if principal is None:
        raise HTTPException(status_code=401, detail="Please sign in or start a demo session.")
    return principal


# ---- Auth ----------------------------------------------------------------------------


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class Me(BaseModel):
    kind: str
    name: str
    email: str | None
    expires_at: datetime


def _set_cookie(response: Response, token: str, expires: datetime) -> None:
    response.set_cookie(
        service.SESSION_COOKIE, token,
        max_age=int((expires - service._now()).total_seconds()),
        httponly=True, samesite="lax", secure=get_settings().session_cookie_secure, path="/",
    )


def _me(p: service.Principal) -> Me:
    return Me(kind=p.kind, name=p.name, email=p.email, expires_at=p.expires_at)


def _open_session(response: Response, db: Session, kind: str, user=None) -> Me:
    token, expires = service.start_session(db, kind, user.user_id if user else None)
    _set_cookie(response, token, expires)
    if user:
        return Me(kind="user", name=user.name, email=user.email, expires_at=expires)
    return Me(kind="demo", name="Guest", email=None, expires_at=expires)


@auth_router.post("/signup", response_model=Me, status_code=201)
def signup(req: SignupRequest, response: Response, db: Session = Depends(db_session)):
    try:
        user = service.create_user(db, req.name, req.email, req.password)
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    return _open_session(response, db, "user", user)


@auth_router.post("/login", response_model=Me)
def login(req: LoginRequest, response: Response, db: Session = Depends(db_session)):
    try:
        user = service.authenticate(db, req.email, req.password)
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    return _open_session(response, db, "user", user)


@auth_router.post("/demo", response_model=Me)
def demo(response: Response, db: Session = Depends(db_session)):
    return _open_session(response, db, "demo")


@auth_router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(db_session)):
    service.end_session(db, request.cookies.get(service.SESSION_COOKIE))
    response.delete_cookie(service.SESSION_COOKIE, path="/")


@auth_router.get("/me", response_model=Me)
def me(principal: service.Principal = Depends(require_session)):
    return _me(principal)


# ---- Sign in with Google --------------------------------------------------------
#
# A browser-navigation flow, not a JSON fetch: /google/login redirects the
# whole page to Google, Google redirects the whole page back to
# /google/callback, which sets the session cookie and redirects the whole
# page to "/". The SPA's existing GET /api/auth/me check on load then picks
# up the new session - see frontend/src/main.tsx.


@auth_router.get("/google/login")
async def google_login(request: Request):
    settings = get_settings()
    if not settings.google_oauth_available:
        raise HTTPException(status_code=404, detail="Google sign-in isn't configured.")
    redirect_uri = f"{settings.app_base_url}/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(db_session)):
    settings = get_settings()
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        logger.warning("Google OAuth callback failed")
        return RedirectResponse(f"{settings.app_base_url}/?auth_error=google")
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not email or not userinfo.get("email_verified"):
        return RedirectResponse(f"{settings.app_base_url}/?auth_error=google_unverified")
    user = service.get_or_create_user_by_email(db, email, userinfo.get("name"))
    response = RedirectResponse(f"{settings.app_base_url}/")
    _open_session(response, db, "user", user)
    return response


# ---- Magic-link email sign-in ----------------------------------------------------


class MagicLinkRequest(BaseModel):
    email: str


@auth_router.post("/magic-link", status_code=202)
def request_magic_link(req: MagicLinkRequest, db: Session = Depends(db_session)):
    settings = get_settings()
    if not settings.resend_available:
        raise HTTPException(status_code=503, detail="Email sign-in isn't configured on this server.")
    try:
        token = service.create_login_link_token(db, req.email)
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    link = f"{settings.app_base_url}/api/auth/magic-link/callback?token={token}"
    try:
        send_login_link_email(req.email, link)
    except EmailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"sent": True}


@auth_router.get("/magic-link/callback")
def magic_link_callback(token: str, db: Session = Depends(db_session)):
    settings = get_settings()
    try:
        email = service.consume_login_link_token(db, token)
    except service.AuthError:
        return RedirectResponse(f"{settings.app_base_url}/?auth_error=link")
    user = service.get_or_create_user_by_email(db, email)
    response = RedirectResponse(f"{settings.app_base_url}/")
    _open_session(response, db, "user", user)
    return response


# ---- Public --------------------------------------------------------------------------


@public_router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "demo_mode": settings.effective_demo_mode,
        "llm_provider": settings.llm_provider,
        "llm_available": settings.llm_available,
        "search_provider": settings.search_provider,
        "search_available": settings.search_available,
    }


@public_router.get("/public/overview")
def public_overview():
    """A small, real slice of the industry snapshot for the login page: one
    fully traced figure per company (revenue over the last twelve months
    and the report checks behind it). Deliberately no market data - VeriFi
    is about verified reports. Served from the snapshot cache."""
    from app.industry.service import IndustryService
    from app.industry.universe import list_industries

    settings = get_settings()
    signin_methods = {
        "google_signin_available": settings.google_oauth_available,
        "email_signin_available": settings.resend_available,
    }
    industries = list_industries()
    if not industries:
        return {"companies": [], **signin_methods}
    try:
        snap = IndustryService().get_snapshot(industries[0].id)
    except Exception:  # noqa: BLE001
        logger.exception("Public overview unavailable")
        return {"companies": [], **signin_methods}
    if snap is None:
        return {"companies": [], **signin_methods}
    companies = []
    for c in snap.companies:
        if not c.available:
            continue
        companies.append({
            "name": c.name, "short_name": c.short_name, "nse": c.nse,
            "revenue_ttm": c.revenue_ttm, "latest_quarter": c.latest_quarter,
            "quarters_filed": sum(1 for q in c.quarters if q.filing_url),
            "verification_status": c.verification_status,
            "checks": [
                {"label": k.label, "status": k.status, "difference_pct": k.difference_pct}
                # Report checks only - the price cross-check is market data.
                for k in c.checks if not k.informational and k.metric != "price"
            ],
        })
    return {
        "industry": snap.industry.name,
        "universe": snap.industry.universe,
        "mode": snap.mode,
        "verified": sum(1 for c in snap.companies if c.verification_status == "verified"),
        "companies": companies,
        **signin_methods,
    }
