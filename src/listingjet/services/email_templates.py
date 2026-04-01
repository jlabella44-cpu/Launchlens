"""Email notification templates with inline CSS for email client compatibility."""

_WRAPPER = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#F1F5F9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F1F5F9;padding:32px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;">
  <tr><td style="background-color:#0F1B2D;padding:24px 32px;">
    <span style="color:#ffffff;font-size:22px;font-weight:bold;">ListingJet</span>
  </td></tr>
  <tr><td style="padding:32px;">
    {content}
  </td></tr>
  <tr><td style="background-color:#F1F5F9;padding:16px 32px;text-align:center;font-size:12px;color:#64748b;">
    &copy; ListingJet &mdash; Automated real-estate marketing
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

_CTA_BUTTON = (
    '<a href="{url}" style="display:inline-block;padding:12px 28px;'
    "background-color:#FF6B2C;color:#ffffff;text-decoration:none;"
    'font-weight:bold;border-radius:6px;font-size:16px;">{label}</a>'
)


def _render(content: str) -> str:
    return _WRAPPER.format(content=content)


def listing_delivered(*, name: str, address: str, download_url: str, listing_url: str) -> tuple[str, str]:
    """LISTING_DELIVERED — Your listing is ready!"""
    subject = "Your listing is ready!"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Your marketing package for "
        f"<strong>{address}</strong> is ready.</p>"
        f"<p style=\"font-size:16px;color:#334155;\">Download your assets or view the full listing below.</p>"
        f"<table cellpadding=\"0\" cellspacing=\"0\" style=\"margin:24px 0;\"><tr>"
        f"<td style=\"padding-right:12px;\">{_CTA_BUTTON.format(url=download_url, label='Download Package')}</td>"
        f"<td>{_CTA_BUTTON.format(url=listing_url, label='View Listing')}</td>"
        f"</tr></table>"
    )
    return subject, body


def review_approved(*, name: str, address: str) -> tuple[str, str]:
    """REVIEW_APPROVED — Listing approved."""
    subject = "Listing approved"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Your listing at "
        f"<strong>{address}</strong> has been approved and is now processing.</p>"
        f"<p style=\"font-size:14px;color:#64748b;\">You'll receive another email once your marketing package is ready.</p>"
    )
    return subject, body


def review_rejected(*, name: str, address: str, reason: str, detail: str) -> tuple[str, str]:
    """REVIEW_REJECTED — Listing needs changes."""
    subject = "Listing needs changes"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Your listing at "
        f"<strong>{address}</strong> was returned for changes.</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin:16px 0;background-color:#FEF2F2;border-radius:6px;padding:16px;\">"
        f"<tr><td>"
        f"<p style=\"margin:0 0 4px;font-weight:bold;color:#991B1B;\">Reason: {reason}</p>"
        f"<p style=\"margin:0;color:#7F1D1D;\">{detail}</p>"
        f"</td></tr></table>"
        f"<p style=\"font-size:14px;color:#64748b;\">Please update your listing and resubmit.</p>"
    )
    return subject, body


def credits_low(*, name: str, balance: str, buy_url: str) -> tuple[str, str]:
    """CREDITS_LOW — Low credit balance."""
    subject = "Low credit balance"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">You have <strong>{balance} credits</strong> remaining.</p>"
        f"<p style=\"font-size:16px;color:#334155;\">Purchase more credits to keep creating listings without interruption.</p>"
        f"<p style=\"margin:24px 0;\">{_CTA_BUTTON.format(url=buy_url, label='Buy Credits')}</p>"
    )
    return subject, body


def weekly_summary(*, name: str, listings_processed: str, credits_used: str, credits_remaining: str, period: str) -> tuple[str, str]:
    """WEEKLY_SUMMARY — Your weekly ListingJet summary."""
    subject = "Your weekly ListingJet summary"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Here's your summary for <strong>{period}</strong>:</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin:16px 0;border:1px solid #E2E8F0;border-radius:6px;overflow:hidden;\">"
        f"<tr style=\"background-color:#0F1B2D;\">"
        f"<th style=\"padding:10px 16px;text-align:left;color:#ffffff;font-size:14px;\">Metric</th>"
        f"<th style=\"padding:10px 16px;text-align:right;color:#ffffff;font-size:14px;\">Value</th>"
        f"</tr>"
        f"<tr><td style=\"padding:10px 16px;border-bottom:1px solid #E2E8F0;font-size:14px;color:#334155;\">Listings Processed</td>"
        f"<td style=\"padding:10px 16px;border-bottom:1px solid #E2E8F0;text-align:right;font-weight:bold;font-size:14px;color:#0F1B2D;\">{listings_processed}</td></tr>"
        f"<tr><td style=\"padding:10px 16px;border-bottom:1px solid #E2E8F0;font-size:14px;color:#334155;\">Credits Used</td>"
        f"<td style=\"padding:10px 16px;border-bottom:1px solid #E2E8F0;text-align:right;font-weight:bold;font-size:14px;color:#0F1B2D;\">{credits_used}</td></tr>"
        f"<tr><td style=\"padding:10px 16px;font-size:14px;color:#334155;\">Credits Remaining</td>"
        f"<td style=\"padding:10px 16px;text-align:right;font-weight:bold;font-size:14px;color:#FF6B2C;\">{credits_remaining}</td></tr>"
        f"</table>"
    )
    return subject, body


# Registry mapping template names to functions
TEMPLATES: dict[str, callable] = {
    "listing_delivered": listing_delivered,
    "review_approved": review_approved,
    "review_rejected": review_rejected,
    "credits_low": credits_low,
    "weekly_summary": weekly_summary,
}
