from unittest.mock import MagicMock, patch

from listingjet.services.email import EmailService, NoOpEmailService


@patch("listingjet.services.email.settings")
def test_send_calls_smtp(mock_settings):
    mock_settings.smtp_host = "mail.test"
    mock_settings.smtp_port = 587
    mock_settings.smtp_user = "user"
    mock_settings.smtp_password = "pass"
    mock_settings.email_from = "noreply@test.com"

    svc = EmailService(host="mail.test", port=587, user="user", password="pass", sender="noreply@test.com")

    with patch("listingjet.services.email.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        svc.send("agent@test.com", "Test Subject", "<p>Hello</p>")

        mock_smtp.assert_called_once_with("mail.test", 587, timeout=15)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.sendmail.assert_called_once()


@patch("listingjet.services.email.settings")
def test_noop_service_does_not_send(mock_settings):
    mock_settings.smtp_host = "mail.test"
    mock_settings.smtp_port = 587
    mock_settings.smtp_user = None
    mock_settings.smtp_password = None
    mock_settings.email_from = "noreply@test.com"

    svc = NoOpEmailService()

    with patch("listingjet.services.email.smtplib.SMTP") as mock_smtp:
        svc.send("agent@test.com", "Test", "<p>Hi</p>")
        mock_smtp.assert_not_called()


@patch("listingjet.services.email.settings")
def test_get_email_service_returns_noop_when_disabled(mock_settings):
    mock_settings.email_enabled = False
    from listingjet.services.email import get_email_service
    svc = get_email_service()
    assert isinstance(svc, NoOpEmailService)


@patch("listingjet.services.email.settings")
def test_get_email_service_returns_real_when_enabled(mock_settings):
    mock_settings.email_enabled = True
    mock_settings.ses_enabled = False
    mock_settings.resend_api_key = ""
    mock_settings.smtp_host = "mail.test"
    mock_settings.smtp_port = 587
    mock_settings.smtp_user = "user"
    mock_settings.smtp_password = "pass"
    mock_settings.email_from = "noreply@test.com"
    from listingjet.services.email import get_email_service
    svc = get_email_service()
    assert type(svc) is EmailService
