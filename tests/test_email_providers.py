import httpx
import pytest

from app.auth import email
from app.config import Settings


class _Resp:
    def __init__(self, status=201, text="{}"):
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=httpx.Request("POST", "https://x"), response=self)


def _use(monkeypatch, **settings):
    monkeypatch.setattr(email, "get_settings", lambda: Settings(_env_file=None, **settings))


def _capture(monkeypatch, resp=None):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return resp or _Resp()

    monkeypatch.setattr(email.httpx, "post", fake_post)
    return calls


def test_brevo_sends_to_any_recipient_from_the_verified_sender(monkeypatch):
    _use(monkeypatch, brevo_api_key="key-123", brevo_sender_email="me@gmail.com")
    calls = _capture(monkeypatch)
    email.send_login_link_email("someone@outlook.com", "https://verifi.onrender.com/api/auth/magic-link/callback?token=abc")
    url, kw = calls[0]
    assert url == email.BREVO_API_URL
    assert kw["headers"]["api-key"] == "key-123"
    assert kw["json"]["sender"] == {"name": "VeriFi", "email": "me@gmail.com"}
    assert kw["json"]["to"] == [{"email": "someone@outlook.com"}]
    assert "token=abc" in kw["json"]["htmlContent"]


def test_brevo_is_preferred_when_both_providers_are_configured(monkeypatch):
    _use(monkeypatch, brevo_api_key="b", brevo_sender_email="me@gmail.com", resend_api_key="r")
    calls = _capture(monkeypatch)
    email.send_login_link_email("x@example.com", "https://v/link")
    assert calls[0][0] == email.BREVO_API_URL


def test_resend_is_used_when_brevo_is_not_configured(monkeypatch):
    _use(monkeypatch, resend_api_key="r")
    calls = _capture(monkeypatch)
    email.send_login_link_email("x@example.com", "https://v/link")
    assert calls[0][0] == email.RESEND_API_URL
    assert calls[0][1]["headers"]["Authorization"] == "Bearer r"


def test_brevo_needs_both_key_and_sender(monkeypatch):
    assert not Settings(_env_file=None, brevo_api_key="b").brevo_available
    assert Settings(_env_file=None, brevo_api_key="b", brevo_sender_email="me@gmail.com").email_signin_available


def test_unconfigured_email_raises(monkeypatch):
    _use(monkeypatch)
    with pytest.raises(email.EmailError, match="isn't configured"):
        email.send_login_link_email("x@example.com", "https://v/link")


def test_provider_rejection_becomes_a_generic_error(monkeypatch):
    _use(monkeypatch, brevo_api_key="b", brevo_sender_email="me@gmail.com")
    _capture(monkeypatch, _Resp(400, '{"message":"sender not valid"}'))
    with pytest.raises(email.EmailError, match="Could not send"):
        email.send_login_link_email("x@example.com", "https://v/link")


def test_link_is_html_escaped_in_the_email_body():
    body = email._body('https://v/cb?token=a&x="><script>')
    assert "<script>" not in body and "&amp;x=" in body
