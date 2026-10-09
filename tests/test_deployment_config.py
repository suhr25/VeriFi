"""Production configuration: database URLs, Render URL fallback, cookies,
CORS and the RAG memory switch."""
import importlib

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.mark.parametrize("url, expected", [
    ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
    ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("sqlite:///./data/x.db", "sqlite:///./data/x.db"),
])
def test_hosted_database_urls_use_the_installed_psycopg_driver(url, expected):
    assert Settings(_env_file=None, database_url=url).database_url == expected


def test_render_external_url_is_the_default_public_base_url(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://verifi.onrender.com/")
    s = Settings(_env_file=None)
    assert s.app_base_url == "https://verifi.onrender.com"
    assert s.post_login_url == "https://verifi.onrender.com"


def test_explicit_app_base_url_wins_over_render_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://verifi.onrender.com")
    monkeypatch.setenv("APP_BASE_URL", "https://verifi.example.com")
    assert Settings(_env_file=None).app_base_url == "https://verifi.example.com"


def test_frontend_url_controls_where_sign_in_redirects():
    s = Settings(_env_file=None, app_base_url="https://api.example.com", frontend_url="https://app.example.com/")
    assert s.post_login_url == "https://app.example.com"


def test_cors_origins_are_parsed_and_trimmed():
    s = Settings(_env_file=None, cors_origins=" https://a.onrender.com/ ,https://b.example.com,, ")
    assert s.cors_origin_list == ["https://a.onrender.com", "https://b.example.com"]


def test_samesite_none_cookie_is_always_secure(monkeypatch):
    from app.auth import routes

    monkeypatch.setattr(routes, "get_settings", lambda: Settings(
        _env_file=None, session_cookie_samesite="none", session_cookie_secure=False))
    policy = routes._cookie_policy()
    assert policy["samesite"] == "none" and policy["secure"] is True and policy["httponly"] is True


def test_default_cookie_policy_is_same_site_lax():
    from app.auth import routes

    assert routes._cookie_policy()["samesite"] == "lax"


def test_rag_disabled_falls_back_to_prefix_truncation_without_loading_a_model(monkeypatch):
    from app.rag import indexer

    monkeypatch.setattr("app.config.get_settings", lambda: Settings(_env_file=None, rag_enabled=False))
    monkeypatch.setattr(indexer, "_rag_select", lambda *a, **k: pytest.fail("embedding path must not run"))
    text = "x" * 10_000
    assert indexer.retrieve_relevant_text(text, "anything", 500) == text[:500]


def test_cors_headers_only_when_origins_are_configured(monkeypatch):
    # Same-origin default: no CORS headers at all.
    from app import main

    plain = TestClient(main.app).get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in plain.headers

    monkeypatch.setenv("CORS_ORIGINS", "https://verifi-web.onrender.com")
    from app import config

    config.get_settings.cache_clear()
    try:
        reloaded = importlib.reload(main)
        client = TestClient(reloaded.app)
        ok = client.get("/api/health", headers={"Origin": "https://verifi-web.onrender.com"})
        assert ok.headers["access-control-allow-origin"] == "https://verifi-web.onrender.com"
        assert ok.headers["access-control-allow-credentials"] == "true"
        denied = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
        assert "access-control-allow-origin" not in denied.headers
    finally:
        monkeypatch.delenv("CORS_ORIGINS")
        config.get_settings.cache_clear()
        importlib.reload(main)


def test_health_endpoint_is_public_and_cheap():
    from app.main import app

    resp = TestClient(app).get("/api/health")
    assert resp.status_code == 200 and resp.json()["status"] == "ok"
