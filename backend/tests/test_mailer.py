"""Mail transport: SES via the task role, SMTP when a host is set, stub otherwise."""

from app.services import mailer


def test_unset_mail_is_stubbed(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.delenv("INTELLENS_MAIL_TRANSPORT", raising=False)
    out = mailer.send_mail(to="sales@citealpha.com", subject="s", body="b")
    assert out["status"] == "stubbed"
    assert mailer.transport() == "stub"


def test_smtp_wins_over_ses(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example")
    monkeypatch.setenv("SMTP_FROM", "CiteAlpha <no-reply@citealpha.com>")
    monkeypatch.setenv("INTELLENS_MAIL_TRANSPORT", "ses")
    assert mailer.transport() == "smtp"


def test_ses_send(monkeypatch):
    captured = {}

    class _Fake:
        def send_email(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "m1"}

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("INTELLENS_MAIL_TRANSPORT", "ses")
    monkeypatch.setenv("SMTP_FROM", "CiteAlpha <no-reply@citealpha.com>")
    monkeypatch.setattr(mailer, "_ses_client", lambda: _Fake())
    out = mailer.send_mail(
        to="sales@citealpha.com",
        subject="Pilot",
        body="Firm: Example",
        reply_to="analyst@desk.test",
    )
    assert out == {"status": "sent", "to": "sales@citealpha.com", "ses": True}
    assert captured["FromEmailAddress"] == "CiteAlpha <no-reply@citealpha.com>"
    assert captured["Destination"]["ToAddresses"] == ["sales@citealpha.com"]
    assert captured["ReplyToAddresses"] == ["analyst@desk.test"]
    assert captured["Content"]["Simple"]["Subject"]["Data"] == "Pilot"


def test_ses_error_is_returned(monkeypatch):
    class _Fake:
        def send_email(self, **_kwargs):
            raise RuntimeError("Message rejected")

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("INTELLENS_MAIL_TRANSPORT", "ses")
    monkeypatch.setenv("SMTP_FROM", "CiteAlpha <no-reply@citealpha.com>")
    monkeypatch.setattr(mailer, "_ses_client", lambda: _Fake())
    out = mailer.send_mail(to="sales@citealpha.com", subject="s", body="b")
    assert out["status"] == "error"
    assert out["ses"] is True
    assert "rejected" in out["detail"]


def test_reply_to_with_newline_is_dropped(monkeypatch):
    captured = {}

    class _Fake:
        def send_email(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "m1"}

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("INTELLENS_MAIL_TRANSPORT", "ses")
    monkeypatch.setenv("SMTP_FROM", "CiteAlpha <no-reply@citealpha.com>")
    monkeypatch.setattr(mailer, "_ses_client", lambda: _Fake())
    mailer.send_mail(to="sales@citealpha.com", subject="s", body="b", reply_to="a@b.c\nBcc: x@y.z")
    assert "ReplyToAddresses" not in captured
