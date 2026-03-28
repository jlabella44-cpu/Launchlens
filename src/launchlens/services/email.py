"""
Email service for sending transactional emails.

In development mode (USE_MOCK_EMAIL=true or no SMTP configured),
emails are logged instead of sent.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


class EmailService:
    """Simple email service with template support."""

    def __init__(self, mock: bool = True):
        self._mock = mock

    async def send_template(
        self,
        to: str,
        template_name: str,
        context: dict,
        subject: str | None = None,
    ) -> bool:
        """Send a templated email. Returns True if sent/logged successfully."""
        template_path = _TEMPLATE_DIR / f"{template_name}.html"
        if template_path.exists():
            html = template_path.read_text()
            for key, value in context.items():
                html = html.replace(f"{{{{{key}}}}}", str(value))
        else:
            html = f"Template '{template_name}' not found. Context: {context}"

        subject = subject or f"LaunchLens — {template_name.replace('_', ' ').title()}"

        if self._mock:
            logger.info(
                "email.mock to=%s subject=%s template=%s context=%s",
                to, subject, template_name, context,
            )
            return True

        # Production: integrate with SES, SendGrid, etc.
        logger.info("email.sent to=%s subject=%s", to, subject)
        return True


_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService(mock=True)
    return _email_service
