"""Central application configuration.

All external credentials and tunables are read from environment variables
(see .env.example). Nothing is hardcoded. Providers check `settings.demo_mode`
(or the absence of their own API key) to decide whether to fall back to a
mock implementation - see app/retrieval/base.py and app/llm/base.py.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Mode
    demo_mode: bool = True

    # LLM
    llm_provider: Literal["openai", "groq"] = "groq"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    groq_api_key: str | None = None
    groq_model: str = "groq/compound-mini"
    # Optional tokens-per-minute pacing budget for whichever provider is
    # active (see app/llm/rate_limiter.py). None = no pacing, fire calls as
    # ready (fine for a paid/high-limit account). Set this below your
    # provider's actual TPM cap to trade latency for every call succeeding
    # instead of racing the limit and falling back to mock under load.
    llm_tpm_limit: int | None = None

    # Search
    search_provider: Literal["tavily", "serpapi"] = "tavily"
    tavily_api_key: str | None = None
    serpapi_api_key: str | None = None

    # Financial data
    sec_edgar_user_agent: str = "Financial Research Agent OJT Project contact@example.com"
    alphavantage_api_key: str | None = None

    # Storage. Hosted providers (Render, Heroku, Neon...) hand out
    # postgres:// or postgresql:// URLs; see _normalise_database_url.
    database_url: str = "sqlite:///./data/financial_research_agent.db"

    # Agent loop limits (see PRD 5.1: unbounded iterations is a named risk)
    max_followup_iterations: int = 2
    max_research_queries: int = 12
    max_subqueries_per_plan: int = 6

    # Financial data store: a company's stored filings older than this are
    # still served straight from the database, while a background sync checks
    # the source API for newer filings (database first, API as fallback).
    filings_sync_hours: int = 12
    # A completed research run is reused for the same question asked again
    # within this window, instead of re-running the whole pipeline.
    research_reuse_hours: int = 72

    # Auth (app/auth): session cookie lifetimes. Set SESSION_COOKIE_SECURE=true
    # when serving over HTTPS so the cookie is never sent in clear text.
    user_session_days: int = 7
    demo_session_hours: int = 2
    session_cookie_secure: bool = False

    # Sign in with Google (app/auth/oauth.py). Both unset = the button is
    # hidden rather than shown broken. Get these from the Google Cloud
    # Console's OAuth client (type "Web application"), with
    # {APP_BASE_URL}/api/auth/google/callback added as an authorized
    # redirect URI.
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # Magic-link email sign-in, sent via Resend (app/auth/email.py). Unset =
    # the "email me a link" option is hidden. RESEND_FROM_EMAIL must be a
    # sender Resend will let you use - its shared onboarding@resend.dev
    # address needs no domain verification and works out of the box.
    resend_api_key: str | None = None
    resend_from_email: str = "VeriFi <onboarding@resend.dev>"

    # Base URL this server is reachable at - used to build the Google OAuth
    # redirect URI and the link sent in magic-link emails. Must match what
    # is registered in the Google Cloud Console exactly (scheme+host+port).
    app_base_url: str = "http://localhost:8000"

    # Signs the short-lived cookie Authlib uses to hold OAuth state/nonce
    # during the Google redirect round-trip (not the session cookie itself).
    # A random value generated at process start is fine - the whole
    # round-trip completes in seconds, well within one process's lifetime.
    oauth_state_secret: str | None = None

    # Only needed when the frontend is served from a different origin than
    # this API (e.g. a separate Render Static Site). Comma-separated list of
    # exact origins allowed to call the API with credentials. Empty = same
    # origin only (the default deployment, where this server serves the
    # built frontend itself).
    cors_origins: str = ""
    # Where to send the browser after Google / magic-link sign-in. Defaults
    # to APP_BASE_URL; set it when the frontend lives on another origin.
    frontend_url: str | None = None
    # "lax" for same-origin deployments. A frontend on a different site
    # needs "none" (which also forces Secure) - see DEPLOYMENT.md for the
    # third-party-cookie caveat.
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Local sentence-transformers embeddings for RAG (app/rag/indexer.py).
    # Loading the model needs roughly 600-700 MB of RAM; on small instances
    # (e.g. Render free/starter, 512 MB) set this to false and long documents
    # fall back to prefix truncation instead of crashing the server.
    rag_enabled: bool = True

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, url: str) -> str:
        """SQLAlchemy reads a bare postgres:// URL as the psycopg2 driver,
        which isn't installed; this app uses psycopg 3."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @model_validator(mode="after")
    def _render_base_url(self) -> "Settings":
        """On Render, fall back to the service's own public URL so OAuth
        redirects and magic links work without setting APP_BASE_URL."""
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_url and "APP_BASE_URL" not in os.environ and self.app_base_url == "http://localhost:8000":
            self.app_base_url = render_url.rstrip("/")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def post_login_url(self) -> str:
        return (self.frontend_url or self.app_base_url).rstrip("/")

    @property
    def llm_available(self) -> bool:
        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        return bool(self.openai_api_key)

    @property
    def search_available(self) -> bool:
        if self.search_provider == "tavily":
            return bool(self.tavily_api_key)
        return bool(self.serpapi_api_key)

    @property
    def alphavantage_available(self) -> bool:
        return bool(self.alphavantage_api_key)

    @property
    def google_oauth_available(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def resend_available(self) -> bool:
        return bool(self.resend_api_key)

    @property
    def effective_demo_mode(self) -> bool:
        """DEMO_MODE=true forces mocks. Otherwise, missing keys force mocks
        per-provider (handled in each provider's `is_available`), but if the
        LLM itself has no key we cannot run the real pipeline at all."""
        return self.demo_mode or not self.llm_available


@lru_cache
def get_settings() -> Settings:
    return Settings()
