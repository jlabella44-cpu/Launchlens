# White-Label Brokerage Deployment — Design Spec

> **Date:** 2026-04-08 | **Status:** Active
> **Plan gate:** Team/Enterprise only

---

## 1. Overview

White-label lets brokerages run ListingJet under their own brand: custom domain, their logo, their colors, their name everywhere. Users see "Acme Realty Media OS" instead of "ListingJet".

Extends the existing BrandKit (logo, colors, fonts) with domain mapping, login page customization, email template overrides, and a branding API that the frontend consumes at runtime.

---

## 2. Data Model

### Extend `brand_kits` table

| Column | Type | Description |
|--------|------|-------------|
| `custom_domain` | String(255) | e.g., "media.acmerealty.com" |
| `domain_verified` | Boolean | DNS verification passed |
| `white_label_enabled` | Boolean | Hide ListingJet branding |
| `app_name` | String(100) | Custom app name (e.g., "Acme Media OS") |
| `tagline` | String(255) | Custom tagline |
| `favicon_url` | String(500) | Custom favicon |
| `login_bg_url` | String(500) | Custom login background image |
| `email_header_color` | String(7) | Email header background color |
| `email_footer_text` | String(500) | Custom email footer |
| `powered_by_visible` | Boolean | Show "Powered by ListingJet" footer |

---

## 3. Domain Resolution

Middleware checks `Host` header → looks up `brand_kits.custom_domain` → sets `request.state.white_label_tenant_id`. Frontend fetches `/branding` endpoint to get theme config.

For MVP: no actual DNS verification — just store the domain and let ops configure the reverse proxy. Future: automated DNS TXT record verification.

---

## 4. API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/branding` | Public | Get branding config for current domain/tenant |
| PATCH | `/settings/white-label` | User (Team+) | Update white-label settings |
| GET | `/settings/white-label` | User (Team+) | Get current white-label config |

### `GET /branding` Response
```json
{
  "app_name": "Acme Media OS",
  "tagline": "From photos to market-ready",
  "logo_url": "https://s3.../acme-logo.png",
  "favicon_url": "https://s3.../acme-favicon.ico",
  "primary_color": "#1E40AF",
  "secondary_color": "#F59E0B",
  "font_primary": "Inter",
  "powered_by_visible": true,
  "white_label_enabled": true
}
```

---

## 5. Implementation Order

1. Extend BrandKit model + migration
2. WhiteLabelService + branding API endpoint
3. Email template dynamic branding
4. Frontend BrandingProvider context
5. Tests
