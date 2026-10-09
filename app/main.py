from __future__ import annotations

import logging
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from fastapi import Depends

from app.api.routes import router
from app.auth.routes import auth_router, public_router, require_session
from app.config import BASE_DIR, get_settings
from app.storage.database import engine, init_db

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("financial_research_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Fill/refresh the financial data store in the background, so the first
    # dashboard visit is answered straight from the database.
    from app.industry.service import IndustryService
    from app.industry.universe import list_industries

    for industry in list_industries():
        IndustryService().refresh_in_background(industry.id)

    # Loading the RAG embedding model is CPU-bound and can take well over a
    # minute on a modest machine - doing it now means the first real Ask-box
    # question never pays that cost on the request path.
    if settings.rag_enabled:
        from app.rag import warm_up as warm_up_rag

        threading.Thread(target=warm_up_rag, name="rag-warmup", daemon=True).start()

    logger.info(
        "Startup complete. demo_mode=%s llm_provider=%s llm_available=%s",
        settings.effective_demo_mode,
        settings.llm_provider,
        settings.llm_available,
    )
    yield
    # Return pooled database connections cleanly when the platform stops us.
    engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(title="Financial Research Agent", version="0.1.0", lifespan=lifespan)

# Authlib's Google OAuth flow stores short-lived state/nonce in a signed
# cookie via Starlette's session - unrelated to VeriFi's own session cookie
# (app/auth/service.py), which stays a custom HttpOnly token either way.
app.add_middleware(SessionMiddleware, secret_key=settings.oauth_state_secret or secrets.token_hex(32),
                   https_only=settings.session_cookie_secure)

# Only for a frontend on a different origin (CORS_ORIGINS); the default
# deployment serves the built frontend from this same server.
if settings.cors_origin_list:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"],
    )

app.include_router(public_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
# Research and industry data need a signed-in or demo session.
app.include_router(router, prefix="/api", dependencies=[Depends(require_session)])

FRONTEND_DIR = BASE_DIR / "frontend" / "dist"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
