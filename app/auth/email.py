"""Sends the magic-link sign-in email via Resend's HTTP API.

Resend is a plain transactional-email API (POST a JSON body, get an email
sent) - it has no framework-specific SDK requirement, so it's called
directly with httpx rather than through a client library. If RESEND_API_KEY
isn't configured, sending fails loudly (EmailError) rather than pretending
the email went out - consistent with this project's rule that a disabled
integration never silently fakes success (see app/retrieval/base.py).
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("financial_research_agent.auth.email")

RESEND_API_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    pass


def send_login_link_email(to_email: str, link: str) -> None:
    settings = get_settings()
    if not settings.resend_available:
        raise EmailError("Email sign-in isn't configured on this server.")

    html = (
        f'<p>Click below to sign in to VeriFi. This link expires in 15 minutes '
        f'and works once.</p><p><a href="{link}">Sign in to VeriFi</a></p>'
        f'<p style="color:#888">If you didn\'t request this, you can ignore this email.</p>'
    )
    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": "Sign in to VeriFi",
                "html": html,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Resend send failed for %s: %s", to_email, exc)
        raise EmailError("Could not send the sign-in email. Please try again.") from exc
