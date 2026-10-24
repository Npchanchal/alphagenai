"""Outbound email. SMTP when SMTP_HOST is set; Amazon SES when INTELLENS_MAIL_TRANSPORT=ses."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

log = logging.getLogger("intellens.mail")


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def ses_configured() -> bool:
    transport = os.environ.get("INTELLENS_MAIL_TRANSPORT", "").strip().lower()
    return transport == "ses" and bool(os.environ.get("SMTP_FROM"))


def transport() -> str:
    """smtp wins so a staging SMTP host still overrides SES."""
    if smtp_configured():
        return "smtp"
    if ses_configured():
        return "ses"
    return "stub"


def auth_dev_tokens_enabled() -> bool:
    """Expose one-time tokens in API responses for local/test (never in prod)."""
    return os.environ.get("INTELLENS_AUTH_DEV_TOKENS", "").lower() in ("1", "true", "yes")


def _safe_reply_to(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    addr = value.strip()
    if not addr or any(c in addr for c in "\r\n, ") or addr.count("@") != 1:
        return None
    return addr


def send_mail(
    *,
    to: str,
    subject: str,
    body: str,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Send or stub. SMTP: SMTP_HOST, SMTP_PORT, SMTP_FROM, SMTP_USER, SMTP_PASS.

    SES: INTELLENS_MAIL_TRANSPORT=ses, SMTP_FROM, and the task role's ses:SendEmail.
    """
    reply = _safe_reply_to(reply_to)
    kind = transport()
    if kind == "smtp":
        return _send_smtp(to=to, subject=subject, body=body, reply_to=reply)
    if kind == "ses":
        return _send_ses(to=to, subject=subject, body=body, reply_to=reply)
    log.info("mail_stub to=%s subject=%s body=%s", to, subject, body[:200])
    return {"status": "stubbed", "to": to, "smtp": False}


def _send_smtp(*, to: str, subject: str, body: str, reply_to: Optional[str]) -> Dict[str, Any]:
    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.environ["SMTP_FROM"]
        msg["To"] = to
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)
        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASS")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"status": "sent", "to": to, "smtp": True}
    except Exception as exc:  # noqa: BLE001 — surface as stub failure detail
        log.exception("smtp_send_failed")
        return {"status": "error", "to": to, "smtp": True, "detail": str(exc)}


def _ses_region() -> str:
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "ap-south-1"
    )


def _ses_client():
    import boto3

    return boto3.client("sesv2", region_name=_ses_region())


def _send_ses(*, to: str, subject: str, body: str, reply_to: Optional[str]) -> Dict[str, Any]:
    try:
        kwargs: Dict[str, Any] = {
            "FromEmailAddress": os.environ["SMTP_FROM"],
            "Destination": {"ToAddresses": [to]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        }
        if reply_to:
            kwargs["ReplyToAddresses"] = [reply_to]
        _ses_client().send_email(**kwargs)
        return {"status": "sent", "to": to, "ses": True}
    except Exception as exc:  # noqa: BLE001 — caller keeps the stored request
        log.exception("ses_send_failed")
        return {"status": "error", "to": to, "ses": True, "detail": str(exc)}


def public_base_url() -> str:
    return (os.environ.get("INTELLENS_PUBLIC_URL") or "http://localhost:8080").rstrip("/")
