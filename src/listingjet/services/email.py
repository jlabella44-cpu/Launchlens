"""Email service — SES, SMTP, or NoOp depending on config."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from listingjet.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


def _load_template(name: str, **kwargs: str) -> str:
    """Load an HTML template and substitute {placeholders}."""
    path = TEMPLATE_DIR / name
    html = path.read_text()
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", value)
    return html


class EmailService:
    """Send emails via SMTP."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        sender: str | None = None,
    ) -> None:
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.user = user or settings.smtp_user
        self.password = password or settings.smtp_password
        self.sender = sender or settings.email_from

    def send(self, to: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.sendmail(self.sender, [to], msg.as_string())
        logger.info("email_sent", extra={"to": to, "subject": subject})

    def send_pipeline_complete(self, to: str, listing_address: str, listing_id: str) -> None:
        html = _load_template("pipeline_complete.html", address=listing_address, listing_id=listing_id)
        self.send(to, f"Your listing is ready: {listing_address}", html)

    def send_pipeline_failed(self, to: str, listing_address: str, error: str) -> None:
        html = _load_template("pipeline_failed.html", address=listing_address, error=error)
        self.send(to, f"Pipeline issue: {listing_address}", html)

    def send_review_ready(self, to: str, listing_address: str, listing_id: str) -> None:
        html = _load_template("review_ready.html", address=listing_address, listing_id=listing_id)
        self.send(to, f"Ready for review: {listing_address}", html)

    def send_welcome(self, to: str, name: str) -> None:
        html = _load_template("welcome.html", name=name)
        self.send(to, "Welcome to ListingJet", html)

    async def send_template(self, to: str, template_name: str, context: dict) -> None:
        """Send a named template with context variables. Async for fire-and-forget."""
        template_file = f"{template_name}.html"
        try:
            html = _load_template(template_file, **{k: str(v) for k, v in context.items()})
            self.send(to, f"ListingJet — {template_name.replace('_', ' ').title()}", html)
        except FileNotFoundError:
            logger.warning("email_template_missing template=%s", template_name)

    def send_notification(self, to: str, template_name: str, **kwargs: str) -> None:
        """Look up a template function by name, render it, and send."""
        from listingjet.services.email_templates import TEMPLATES

        template_fn = TEMPLATES.get(template_name)
        if not template_fn:
            logger.warning("email_template_unknown template=%s", template_name)
            return
        subject, html_body = template_fn(**kwargs)
        self.send(to, subject, html_body)


class SESEmailService(EmailService):
    """Send emails via AWS SES."""

    def __init__(self, sender: str | None = None) -> None:
        self.sender = sender or settings.email_from
        self._client = boto3.client("ses", region_name=settings.aws_region)

    def send(self, to: str, subject: str, html_body: str) -> None:
        try:
            self._client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            logger.info("ses_email_sent", extra={"to": to, "subject": subject})
        except ClientError as e:
            logger.error("ses_email_failed", extra={"to": to, "error": str(e)})
            raise

    # Share-specific notification helpers

    def send_listing_shared(self, to: str, sharer_name: str, listing_address: str, permission: str, listing_id: str) -> None:
        html = _load_template(
            "listing_shared.html",
            sharer_name=sharer_name,
            listing_address=listing_address,
            permission=permission,
            listing_id=listing_id,
        )
        self.send(to, f"{sharer_name} shared a listing with you on ListingJet", html)

    def send_listing_unshared(self, to: str, listing_address: str) -> None:
        html = _load_template("listing_unshared.html", listing_address=listing_address)
        self.send(to, f"Your access was revoked: {listing_address}", html)

    def send_permission_expiring(self, to: str, listing_address: str, days_left: str) -> None:
        html = _load_template("permission_expiring.html", listing_address=listing_address, days_left=days_left)
        self.send(to, f"Access expiring soon: {listing_address}", html)

    def send_edit_digest(self, to: str, listing_address: str, change_count: str, editor_names: str) -> None:
        html = _load_template(
            "edit_digest.html",
            listing_address=listing_address,
            change_count=change_count,
            editor_names=editor_names,
        )
        self.send(to, f"{change_count} changes on {listing_address}", html)


class NoOpEmailService(EmailService):
    """Does nothing — used in dev/test."""

    def send(self, to: str, subject: str, html_body: str) -> None:
        logger.debug("noop_email", extra={"to": to, "subject": subject})

    async def send_template(self, to: str, template_name: str, context: dict) -> None:
        logger.debug("noop_email_template", extra={"to": to, "template": template_name})

    def send_notification(self, to: str, template_name: str, **kwargs: str) -> None:
        logger.debug("noop_email_notification", extra={"to": to, "template": template_name})


def get_email_service() -> EmailService:
    """Return the appropriate email service based on config."""
    if not settings.email_enabled:
        return NoOpEmailService()
    if getattr(settings, "ses_enabled", False):
        return SESEmailService()
    return EmailService()
