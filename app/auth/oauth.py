"""Google OAuth client registration (Authlib).

One `OAuth` registry for the whole process, matching how every other
external client in this app is constructed once and reused (see
app/llm/factory.py). Registered unconditionally - Authlib only ever talks
to Google when a route calls `oauth.google.authorize_redirect(...)`, so an
unset client id/secret just means that route is never exercised (and the
frontend hides the Google button via settings.google_oauth_available), not
that this import fails.
"""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth

from app.config import get_settings

settings = get_settings()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
