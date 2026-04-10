"""Email notification templates with inline CSS for email client compatibility."""

_WRAPPER = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#F1F5F9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F1F5F9;padding:32px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;">
  <tr><td style="background-color:{header_color};padding:24px 32px;">
    <span style="color:#ffffff;font-size:22px;font-weight:bold;">{brand_name}</span>
  </td></tr>
  <tr><td style="padding:32px;">
    {content}
  </td></tr>
  <tr><td style="background-color:#F1F5F9;padding:16px 32px;text-align:center;font-size:12px;color:#64748b;">
    {footer_text}
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


def _render(
    content: str,
    brand_name: str = "ListingJet",
    header_color: str = "#0F1B2D",
    footer_text: str = "&copy; ListingJet &mdash; Automated real-estate marketing",
) -> str:
    return _WRAPPER.format(
        content=content,
        brand_name=brand_name,
        header_color=header_color,
        footer_text=footer_text,
    )


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


# ── Launch drip sequence templates ──


def welcome_drip_1(*, name: str, upload_url: str) -> tuple[str, str]:
    """WELCOME_DRIP_1 — Welcome + first upload CTA (sent immediately)."""
    subject = "Welcome to ListingJet — upload your first listing in 60 seconds"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Welcome to ListingJet! You're now part of the Founding 200.</p>"
        f"<p style=\"font-size:16px;color:#334155;\">Here's how to get started: upload your property photos and let our AI create your complete listing package — MLS descriptions, branded flyers, social content, and more.</p>"
        f"<p style=\"font-size:16px;color:#334155;\"><strong>It takes about 60 seconds.</strong></p>"
        f"<p style=\"margin:24px 0;\">{_CTA_BUTTON.format(url=upload_url, label='Upload Your First Listing')}</p>"
        f"<p style=\"font-size:14px;color:#64748b;\">Questions? Just reply to this email — we read every message.</p>"
    )
    return subject, body


def welcome_drip_2(*, name: str, listing_url: str) -> tuple[str, str]:
    """WELCOME_DRIP_2 — Results showcase (Day 1)."""
    subject = "Here's what ListingJet just did with your photos"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">If you've uploaded your first listing, here's what our AI generated for you:</p>"
        f"<ul style=\"font-size:15px;color:#334155;line-height:1.8;\">"
        f"<li><strong>MLS-ready description</strong> — formal, compliant, ready to paste</li>"
        f"<li><strong>Marketing description</strong> — engaging copy that sells</li>"
        f"<li><strong>Photo curation</strong> — ranked, scored, hero shots selected</li>"
        f"<li><strong>Social captions</strong> — ready for Instagram, Facebook, TikTok</li>"
        f"</ul>"
        f"<p style=\"margin:24px 0;\">{_CTA_BUTTON.format(url=listing_url, label='View Your Results')}</p>"
        f"<p style=\"font-size:14px;color:#64748b;\">Haven't uploaded yet? No worries — you can start anytime.</p>"
    )
    return subject, body


def welcome_drip_3(*, name: str) -> tuple[str, str]:
    """WELCOME_DRIP_3 — Use cases (Day 3)."""
    subject = "5 ways agents are using ListingJet to win more listings"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Here's how top agents use ListingJet:</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin:16px 0;\">"
        f"<tr><td style=\"padding:8px 0;font-size:15px;color:#334155;\"><strong>1.</strong> Upload photos from their phone right after a showing</td></tr>"
        f"<tr><td style=\"padding:8px 0;font-size:15px;color:#334155;\"><strong>2.</strong> Send AI-generated descriptions to clients for approval in minutes</td></tr>"
        f"<tr><td style=\"padding:8px 0;font-size:15px;color:#334155;\"><strong>3.</strong> Use the social content pack for Instagram/TikTok launch posts</td></tr>"
        f"<tr><td style=\"padding:8px 0;font-size:15px;color:#334155;\"><strong>4.</strong> Create branded flyers for open houses without a designer</td></tr>"
        f"<tr><td style=\"padding:8px 0;font-size:15px;color:#334155;\"><strong>5.</strong> Export MLS-compliant packages and list faster than the competition</td></tr>"
        f"</table>"
        f"<p style=\"font-size:14px;color:#64748b;\">What takes most agents 3 hours takes ListingJet 3 minutes.</p>"
    )
    return subject, body


def welcome_drip_4(*, name: str, upgrade_url: str) -> tuple[str, str]:
    """WELCOME_DRIP_4 — FOMO + upgrade CTA (Day 5)."""
    subject = "Your free trial is halfway done — here's what you'd lose"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Your trial is halfway through. Here's what paid members keep:</p>"
        f"<ul style=\"font-size:15px;color:#334155;line-height:1.8;\">"
        f"<li>Unlimited AI listing descriptions (dual-tone)</li>"
        f"<li>Full white-label branding (no ListingJet watermarks)</li>"
        f"<li>Priority cloud rendering</li>"
        f"<li>Advanced market analytics HUD</li>"
        f"<li>30% off for life as a Founding 200 member</li>"
        f"</ul>"
        f"<p style=\"margin:24px 0;\">{_CTA_BUTTON.format(url=upgrade_url, label='Lock In Founding Pricing')}</p>"
        f"<p style=\"font-size:14px;color:#64748b;\">Only a limited number of founding spots remain.</p>"
    )
    return subject, body


def welcome_drip_5(*, name: str, upgrade_url: str) -> tuple[str, str]:
    """WELCOME_DRIP_5 — Hard upgrade CTA (Day 10)."""
    subject = "Last chance: Lock in 30% off ListingJet for life"
    body = _render(
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">Hi {name},</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">Your trial is ending soon. As a Founding 200 member, you can lock in <strong>30% off for life</strong> — but only while spots last.</p>"
        f"<p style=\"font-size:16px;color:#334155;\">After the Founding 200 fills up, pricing goes to full rate.</p>"
        f"<p style=\"margin:24px 0;\">{_CTA_BUTTON.format(url=upgrade_url, label='Upgrade Now — 30% Off For Life')}</p>"
        f"<p style=\"font-size:14px;color:#64748b;\">Questions? Reply to this email — we're here to help.</p>"
    )
    return subject, body


# ── Social reminder templates ──


def _social_reminder(**kwargs) -> tuple[str, str]:
    address = kwargs.get("address", "your listing")
    social_url = kwargs.get("social_url", "#")
    subject = f"Time to share: {address} on social media"
    html_body = f"""
    <h2>Your listing is ready to share!</h2>
    <p>Your listing at <strong>{address}</strong> has content ready for Instagram, Facebook, and TikTok.</p>
    <p>Now is a great time to post — your captions, hashtags, and video cuts are all prepared.</p>
    <p><a href="{social_url}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:8px;">View & Post Now</a></p>
    <p style="color:#6B7280;font-size:14px;">Tip: Post during peak engagement hours for maximum visibility.</p>
    """
    return subject, html_body


def _social_reminder_followup(**kwargs) -> tuple[str, str]:
    address = kwargs.get("address", "your listing")
    social_url = kwargs.get("social_url", "#")
    subject = f"Reminder: Share {address} — engagement window closing"
    html_body = f"""
    <h2>Don't miss the engagement window</h2>
    <p>Your listing at <strong>{address}</strong> still hasn't been shared on social media.</p>
    <p>Listings shared within 48 hours of going live get significantly more engagement.</p>
    <p><a href="{social_url}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:8px;">Share Now</a></p>
    """
    return subject, html_body


def team_member_invite(
    *,
    inviter_name: str,
    tenant_name: str,
    accept_url: str,
    expires_hours: int = 72,
) -> tuple[str, str]:
    """TEAM_MEMBER_INVITE — invitation to join a tenant's team."""
    subject = f"{inviter_name} invited you to {tenant_name} on ListingJet"
    content = (
        f"<h2 style=\"color:#0F1B2D;margin:0 0 16px;\">You've been invited</h2>"
        f"<p style=\"font-size:16px;color:#334155;\">"
        f"<strong>{inviter_name}</strong> invited you to join "
        f"<strong>{tenant_name}</strong> on ListingJet. "
        f"Click the button below to set your password and get started."
        f"</p>"
        f"<p style=\"margin:32px 0;\">{_CTA_BUTTON.format(url=accept_url, label='Accept Invitation')}</p>"
        f"<p style=\"font-size:14px;color:#64748B;\">"
        f"This invitation expires in {expires_hours} hours. "
        f"If the button doesn't work, copy and paste this link into your browser:"
        f"</p>"
        f"<p style=\"font-size:13px;color:#64748B;word-break:break-all;\">{accept_url}</p>"
        f"<p style=\"font-size:13px;color:#94A3B8;margin-top:24px;\">"
        f"If you weren't expecting this invitation, you can safely ignore this email."
        f"</p>"
    )
    return subject, _render(content)


# Registry mapping template names to functions
TEMPLATES: dict[str, callable] = {
    "listing_delivered": listing_delivered,
    "review_approved": review_approved,
    "review_rejected": review_rejected,
    "credits_low": credits_low,
    "weekly_summary": weekly_summary,
    "welcome_drip_1": welcome_drip_1,
    "welcome_drip_2": welcome_drip_2,
    "welcome_drip_3": welcome_drip_3,
    "welcome_drip_4": welcome_drip_4,
    "welcome_drip_5": welcome_drip_5,
    "social_reminder": _social_reminder,
    "social_reminder_followup": _social_reminder_followup,
    "team_member_invite": team_member_invite,
}
