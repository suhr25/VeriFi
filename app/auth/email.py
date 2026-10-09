"""Sends the magic-link sign-in email through Brevo or Resend.

Both are plain HTTP APIs, called directly with httpx. Brevo is preferred when
configured: it can deliver to any address from a single verified sender
(e.g. your own Gmail) without owning a domain. Resend needs a verified domain
before it will send to anyone other than the account owner. If neither is
configured, sending fails loudly (EmailError) rather than pretending the
email went out - consistent with this project's rule that a disabled
integration never silently fakes success (see app/retrieval/base.py).

HTTP APIs are used rather than SMTP on purpose: many hosts (including
Render's free plan) block outbound SMTP ports.
"""
from __future__ import annotations

import html
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("financial_research_agent.auth.email")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
RESEND_API_URL = "https://api.resend.com/emails"
SUBJECT = "Sign in to VeriFi"


class EmailError(Exception):
    pass


def _body(link: str) -> str:
    safe = html.escape(link, quote=True)
    return (
        '<div style="font-family:Arial,sans-serif;font-size:15px;color:#10222b">'
        "<p>Click the button below to sign in to VeriFi. The link works once and expires in 15 minutes.</p>"
        f'<p><a href="{safe}" style="display:inline-block;padding:10px 18px;border-radius:6px;'
        'background:#3fd6c4;color:#052723;font-weight:bold;text-decoration:none">Sign in to VeriFi</a></p>'
        f'<p style="color:#6b7f85;font-size:13px">Or paste this address into your browser:<br>{safe}</p>'
        '<p style="color:#6b7f85;font-size:13px">If you didn\'t request this, you can ignore this email.</p>'
        "</div>"
    )


def _send_brevo(to_email: str, link: str) -> None:
    settings = get_settings()
    response = httpx.post(
        BREVO_API_URL,
        headers={"api-key": settings.brevo_api_key or "", "accept": "application/json"},
        json={
            "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
            "to": [{"email": to_email}],
            "subject": SUBJECT,
            "htmlContent": _body(link),
        },
        timeout=10.0,
    )
    response.raise_for_status()


def _send_resend(to_email: str, link: str) -> None:
    settings = get_settings()
    response = httpx.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.resend_from_email, "to": [to_email], "subject": SUBJECT, "html": _body(link)},
        timeout=10.0,
    )
    response.raise_for_status()


def send_login_link_email(to_email: str, link: str) -> None:
    settings = get_settings()
    if settings.brevo_available:
        provider, send = "brevo", _send_brevo
    elif settings.resend_available:
        provider, send = "resend", _send_resend
    else:
        raise EmailError("Email sign-in isn't configured on this server.")
    try:
        send(to_email, link)
    except httpx.HTTPStatusError as exc:
        # The provider's own message (e.g. "sender not verified") is logged
        # for the operator; the user only sees a generic failure.
        logger.warning("%s rejected the sign-in email (HTTP %s): %s", provider, exc.response.status_code, exc.response.text[:300])
        raise EmailError("Could not send the sign-in email. Please try again.") from exc
    except httpx.HTTPError as exc:
        logger.warning("%s send failed: %s", provider, exc)
        raise EmailError("Could not send the sign-in email. Please try again.") from exc
