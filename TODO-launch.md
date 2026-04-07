# ListingJet Launch — Tomorrow's Todo List

**Date:** April 8, 2026
**Context:** Day 1 of Week 1, 3-week launch plan ($1K budget)

---

## Founder Todos

- [ ] **Write LinkedIn origin story post** — "I built an AI that turns property photos into complete listing packages in minutes. Here's the story." Schedule for morning.
- [ ] **Record 60-second screen demo** — Upload 25 photos → show MLS bundle, flyer, description, social posts. Use Loom or screen recorder. This becomes the hero asset for everything.
- [ ] **Draft warm outreach DM list** — Pull every agent/broker from your network into a spreadsheet (name, email, Instagram, phone). Aim for 30+ contacts.
- [ ] **Send first batch of DMs** — "Built something for you — want to try it free?" Offer 30-day free Active Agent tier to first 30 users.
- [ ] **Set up Resend account** — Sign up at resend.com (free tier), verify sending domain, get SMTP credentials. Needed for drip emails.
- [ ] **Set up Meta Pixel** — Create pixel in Meta Business Suite, grab the pixel ID. Needed for Week 3 retargeting.
- [ ] **Collect 1–2 beta testimonials** — Even informal quotes from anyone who's seen the product. Landing page has placeholders that need real ones.
- [ ] **Pick analytics provider** — PostHog (free/self-hosted) or Mixpanel (free tier)?

## Claude Todos

- [ ] Embed Meta Pixel script in app layout (needs pixel ID from founder)
- [ ] Wire referral code field through to backend so referred signups get credited
- [ ] Add Founding 200 live counter to pricing page (currently only on billing page)
- [ ] Add "Powered by ListingJet" watermark to backend export pipeline (`src/listingjet/agents/watermark.py`)
- [ ] Wire drip scheduler as cron job / Temporal schedule (Day 1, 3, 5, 10 emails)
- [ ] Integrate PostHog or Mixpanel (pending founder's choice)
- [ ] Create `/product-hunt` public directory with gallery images and OG meta tags

## Blockers

| Blocker | Who Provides | Needed For |
|---------|-------------|------------|
| Resend SMTP credentials | Founder | Drip emails working |
| Meta Pixel ID | Founder | Retargeting pixel embed |
| Analytics provider choice | Founder | PostHog vs Mixpanel integration |
| 2 real testimonial quotes | Founder | Replace landing page placeholders |
