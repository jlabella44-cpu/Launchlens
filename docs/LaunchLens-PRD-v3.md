# LaunchLens PRD v3: The Listing Media OS

> **Version:** v3.0 | **Date:** 2026-03-27 | **Status:** Active
> Previous version: `docs/LaunchLens-PRD-v2.md` (retained for history)

---

## 1. Vision

LaunchLens is the operating system for real estate listing media. It replaces the fragmented 7+ tool workflow (photographer, editor, Dropbox, MLS login, tour builder, social scheduler, email blast tool) with a single AI-powered platform that turns raw listing photos into a complete, market-ready listing package in under 3 minutes.

**The insight:** The costliest gap in real estate isn't taking photos — it's the 2-4 hours of manual labor to go from finished media to a live listing across MLS, social media, email, and print. LaunchLens eliminates this gap entirely.

**Positioning:** "The Listing Media OS — from raw photos to MLS-ready, social-ready, brand-ready in minutes."

**Tagline:** *From raw listing media to a live, complete listing — without the 7-tool stack.*

---

## 2. Problem Statement

### The Current Workflow (7+ Tools, 2-4 Hours)

```
Photographer shoots → Lightroom edit → Dropbox upload → Agent downloads →
MLS login → Manual photo upload (resize, rename, reorder) → Write description →
Create flyer (Canva) → Write social posts → Schedule posts → Send email blast →
Build virtual tour → Update property website
```

**Pain points:**
- **Time:** 2-4 hours per listing, mostly manual data entry and file shuffling
- **Quality:** Inconsistent photo ordering, missed shots, generic descriptions
- **Fragmentation:** No single system knows the full listing state
- **No learning:** Every listing starts from zero — no institutional knowledge of what works

### The LaunchLens Workflow (1 Platform, 3 Minutes)

```
Upload photos → AI curates + scores + orders →
AI writes description → AI generates flyer + social posts →
Review + approve → Export MLS-ready bundle → Done
```

---

## 3. Target Market

### Phase 1: Media Team Operators (MVP)
- **Who:** Photography companies managing 20-100+ listings/month for multiple agents
- **Pain:** Repetitive post-production workflow, inconsistent quality across team members
- **Value prop:** "Your team processes 50 listings/month. LaunchLens saves 2 hours each. That's 100 hours/month back."
- **Distribution:** Existing Juke Media photography clients (warm leads)

### Phase 2: Solo Photographers + Top Agents
- **Who:** Independent photographers (10-30 listings/month), top-producing agents who manage their own media
- **Pain:** Wearing too many hats, want to look professional without hiring a marketing team
- **Value prop:** "One-person marketing department for $99/month"

### Phase 3: Brokerages + Enterprise
- **Who:** Regional brokerages (100-500 agents), franchise operations
- **Pain:** Brand consistency, compliance, agent onboarding friction
- **Value prop:** "Every listing launches on-brand, on-time, every time. White-label with your brokerage identity."

---

## 4. Product Design

### Product Name: **LaunchLens**
**Tagline:** The Listing Media OS — raw photos to market-ready in minutes.

### Core Feature: The Listing Media Pipeline

```
  UPLOAD          ANALYZE           CURATE            CREATE            EXPORT
  ┌─────┐       ┌──────────┐      ┌──────────┐      ┌──────────┐     ┌──────────┐
  │Photos│──────▶│ AI Media  │─────▶│ Auto-    │─────▶│AI Copy-  │────▶│One-Click │
  │      │       │ Engine    │      │ Curation │      │writer +  │     │MLS Export│
  └─────┘       └──────────┘      └──────────┘      │Brand ID  │     └──────────┘
                     │                  │            │System +  │           │
                 Room labels      Hero select        │Social    │     ZIP download
                 Quality score    Coverage check     │Media     │     Social posts
                 Dedup            Gallery order      │Studio    │     MLS metadata
                 Hero candidate   Missing shots      └──────────┘     Deep links
```

### Agent Pipeline Diagram

```
Upload → IngestionAgent → VisionAgent (T1+T2) → CoverageAgent → PackagingAgent
→ [Human Review] → ContentAgent (dual-tone) → [BrandAgent + SocialContentAgent parallel]
→ MLSExportAgent → DistributionAgent
```

Each agent extends `BaseAgent`, opens its own DB session, uses injected providers, transitions `Listing.state`, and emits domain events via the Outbox Pattern.

### Feature Set

#### AI Media Engine (Upload → Analyze → Curate)
- **AI Photo Classification:** Room type, quality score, commercial appeal score (Google Vision bulk + GPT-4V for top candidates)
- **Near-Duplicate Detection:** Hash-based dedup (MVP), embedding-based similarity (Phase 2)
- **Coverage Analysis:** Visual "Shot Coverage Card" — shows which required shots are present/missing by property type
- **Auto-Curation:** AI selects top 25 photos, ordered for buyer journey. Hero photo prominently featured.
- **Transparency Tooltips:** Hover any photo to see "Why selected: quality 92, hero candidate, exterior shot"
- **Human Review:** Drag-reorder, swap photos, override AI selections. Every override becomes training data.

#### AI Copywriter (Curate → Create)
- **AI Listing Description:** Claude-generated prose from property metadata + photo analysis. Dual-tone output (professional + conversational). JSON-validated, FHA-compliant.
- **Branded Flyer:** Auto-generated PDF using brokerage brand kit (logo, colors, fonts). Template-based with photo placement.
- **Email Blast Copy:** Property announcement email with hero image, key features, CTA to listing page.

#### Brand Identity System
- **Brand Kit Management:** Logo, colors, fonts stored per tenant. Set once, applied everywhere.
- **Flyer Templates:** Branded PDF generation with dynamic photo and copy placement.
- **White-Label Support (Enterprise):** Full platform re-skin with brokerage identity.

#### Social Media Studio (Pro+)
- **Platform-Specific Posts:** AI-generated captions for Instagram, Facebook, LinkedIn, Twitter/X. Hashtags, emojis, CTAs optimized per platform.
- **Social Export Package:** Download social-optimized images + captions as a ready-to-post package.
- **Scheduling (Phase 2):** Direct publish to platforms from within LaunchLens.

#### One-Click MLS Export
- **MLS-Ready Bundle:** ZIP download with photos renamed/resized to MLS spec, ordered correctly, plus metadata CSV.
- **Unbranded Export Mode:** Photos stripped of overlays and branding for MLS compliance — agent uploads manually.
- **Metadata CSV:** All listing fields formatted per MLS standards, ready for copy-paste or import.
- **Export API Endpoint:** `GET /listings/{id}/export` returns a signed S3 download URL.

#### Adaptive Intelligence
- **Override Learning:** Every human correction (photo swap, reorder, description edit) trains the system per-tenant.
- **Weight Evolution:** Room-type weights adjust over time. A luxury brokerage that always promotes pool shots gets pool photos ranked higher.
- **Performance Intelligence (Phase 2):** Connect listing outcomes (days-on-market, views, saves) to LaunchLens photo selections. Prove which photos sell faster.

---

## 5. User Stories

### Media Team Operator (Primary Persona)
1. As a media team lead, I upload 50 photos from a shoot and get a curated 25-photo MLS package in under 2 minutes.
2. As a media team lead, I review the AI's photo selections, swap 2 photos, and approve the package — knowing my overrides make the AI smarter next time.
3. As a media team lead, I click "Export to MLS" and get a ZIP with correctly named, resized, ordered photos + a metadata CSV ready for upload to my MLS portal.
4. As a media team lead, I generate social media posts for Instagram and Facebook in one click, with platform-specific formatting.
5. As a media team lead, I see a Coverage Card showing I'm missing a bathroom shot, so I notify the photographer before delivery.

### MLS Export
6. As an agent, I receive an unbranded MLS export ZIP that contains photos in the correct MLS order, renamed to spec, with a metadata CSV — so I can upload directly to my MLS portal without any manual reformatting.
7. As an agent, I can download a separate branded marketing package (with logo overlays and social posts) distinct from the MLS-compliant bundle, so I have the right asset for every channel.

### Social Content
8. As a photographer, I generate platform-optimized social posts for a listing in one click — Instagram caption with hashtags, Facebook post with CTA, LinkedIn professional blurb — all from the same AI session.
9. As a media team lead, I download the Social Media Studio package and hand it directly to the agent, eliminating a manual copywriting step from my workflow.

### Solo Photographer
10. As a solo photographer, I upload photos and get a complete listing package (description, flyer, social posts, MLS bundle) without switching between 5 different tools.
11. As a solo photographer, I set up my brand kit once and every flyer uses my logo, colors, and contact info automatically.

### Brokerage Admin
12. As a brokerage admin, I see platform stats: how many listings are in-progress, average processing time, and which agents have pending reviews.
13. As a brokerage admin, I manage team members — invite agents, set roles, and enforce brand compliance.

---

## 6. Scope

### MVP (Built — v0.1.0 through v0.9.0)
- Full AI pipeline: Ingestion → Vision (2-tier) → Coverage → Packaging → Content (dual-tone) → Brand → SocialContent → MLSExport → Distribution
- JWT auth with register/login, role-based access
- Stripe subscriptions with checkout, portal, webhooks
- 9 REST API endpoints for listing CRUD + review + approve
- **Export API endpoint** — `GET /listings/{id}/export` returns signed download URL
- **MLS Export Agent** — ZIP packaging with MLS-spec photos + metadata CSV (unbranded mode)
- **Social Content Agent** — Platform-specific social media post generation
- **Demo Pipeline** — Upload without auth → see AI results → register → claim listing
- Temporal workflow orchestration with signal-based human review gate
- Plan enforcement (listing + asset quotas per tier)
- Admin dashboard (tenant/user CRUD, platform stats)
- Docker Compose dev environment
- CI/CD (GitHub Actions: lint, test, docker build)

### Phase 2 (Deferred)
- Photo compliance scanner (automated MLS photo rule checking)
- Two export modes UI: MLS mode vs. Marketing mode (currently manual)
- Image embedding-based near-duplicate detection
- Property website auto-generation
- Performance Intelligence (outcome linking)
- Real-time collaborative review (Figma-style multi-cursor)
- Canva API integration (replace template stub)
- LiDAR room measurement extraction
- Social platform direct publish + scheduling

### Phase 3 (Vision)
- RESO Web API vendor certification (official MLS integration)
- Official listing input API ("Stripe for Real Estate Listings")
- White-label brokerage deployment
- ML scoring model (replace rule-based Learning Agent)

> **Note:** Browser automation for MLS upload is explicitly out of scope at all phases. The integration path is RESO Web API vendor certification (Phase 3), not Playwright-based automation.

---

## 7. Pricing

### Hybrid: Base Fee + Per-Listing Usage

| | Starter ($49/mo) | Pro ($99/mo) | Enterprise (Custom) |
|---|---|---|---|
| **Headline** | "Launch listings faster" | "Your AI marketing team" | "Listing ops at scale" |
| **Hero feature** | AI Photo Curation + MLS Export | Full Media OS | White-label Media OS + API |
| **CTA** | "Start free trial" | "Start free trial" | "Talk to sales" |
| **Per listing** | $9 | $7 (10 included) | $5 (volume) |
| **Users** | 2 | 5 | Unlimited |
| **Listings/month** | 5 | 50 | 500+ |
| **Photos/listing** | 25 | 50 | 100 |
| **AI Copywriter** | Basic | Full + FHA | Full + FHA + custom prompt |
| **Social Media Studio** | - | Instagram + Facebook | All platforms + scheduling |
| **One-Click MLS Export** | ZIP download | ZIP + metadata CSV | ZIP + RESO API (Phase 3) |
| **Brand Identity System** | 1 kit | 3 kits | Unlimited |
| **Adaptive Intelligence** | - | Per-tenant weights | Per-agent weights |
| **Support** | Email | Priority | Dedicated CSM |

**Unit economics (Pro, 30 listings/month):**
- Revenue: $99 + (20 x $7) = $239/month
- COGS: ~$40 (Vision API + Claude + S3)
- Gross margin: ~83%

**Monetization hooks:**
- Annual contracts: 2-month discount (17% off)
- Per-photo overage: $0.05/photo beyond tier limit
- Tier-2 Vision bypass: "Lite" mode for rentals/land (Google Vision only, ~$0.12/listing)

---

## 8. Go-to-Market Strategy

### Results-First Onboarding Flow
New users experience value before friction:
1. **Upload without auth** — visitor uploads listing photos, no account required
2. **See AI results** — full AI pipeline runs: curated gallery, coverage card, sample description
3. **Register to claim** — "Create your account to save this listing and export your package"
4. **Claim listing** — listing transfers to new account; user is already a paying prospect

This eliminates the "sign up to see if it's worth it" conversion killer. The product earns the account.

### Phase 1: Design Partner (Weeks 1-8)
- **Juke Media** as exclusive launch partner
- Shadow review dashboard — internal QA for first 100 listings
- Goal: validate pipeline accuracy, collect override data for Adaptive Intelligence

### Phase 2: Soft Launch (Weeks 8-12)
- 5-10 invited photographers (from Juke network)
- Free access in exchange for case studies and feedback
- Self-serve onboarding wizard: brand scraping → coverage profiles → first listing test

### Phase 3: Public Launch (Week 12+)
- Paid tiers live on Stripe
- Content marketing: "We cut listing prep from 3 hours to 3 minutes" case study
- Distribution: Facebook photographer groups, ActiveRain, industry newsletters
- Partnership: regional MLS associations for co-marketing

### Month 6+ Hook
"Revenue Accelerator" data claim — publish days-on-market impact linked to LaunchLens-processed listings. This becomes the enterprise sales pitch.

---

## 9. Technical Architecture

### Stack
```
Frontend:  Next.js 15 + React 19 + TypeScript + Tailwind CSS 4 + React Three Fiber
Backend:   Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Alembic
Workflow:  Temporal (durable workflow orchestration)
Database:  PostgreSQL 16 (multi-tenant RLS)
Cache:     Redis 7 (rate limiting, pub/sub)
Storage:   S3 (raw + processed assets, export bundles)
Payments:  Stripe (checkout, portal, webhooks)
CI/CD:     GitHub Actions (lint, test, docker build)
Dev Env:   Docker Compose (Postgres, Redis, Temporal, API, Worker)
```

### Agent Pipeline Architecture
```
Upload → IngestionAgent → VisionAgent (Tier 1 + Tier 2)
                                  ↓
                           CoverageAgent
                                  ↓
                           PackagingAgent
                                  ↓
                      [Human Review Signal]
                                  ↓
                    ContentAgent (dual-tone)
                                  ↓
                  ┌───────────────┴──────────────┐
             BrandAgent                  SocialContentAgent
                  └───────────────┬──────────────┘
                                  ↓
                           MLSExportAgent
                                  ↓
                          DistributionAgent
```

Each agent extends `BaseAgent`, opens its own DB session, uses injected providers, transitions `Listing.state`, and emits domain events via the Outbox Pattern.

### Listing State Machine
```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED
    → EXPORTING → DELIVERED

DEMO: NEW → UPLOADING → ANALYZING → DEMO_READY (unauthenticated, ephemeral)
```

**States added in v0.9.0:**
- `EXPORTING` — MLSExportAgent is packaging the ZIP bundle + metadata CSV
- `DEMO` — Anonymous pipeline run; claimed on registration, transitions to standard flow

### Multi-Tenant Isolation
- All tables have `tenant_id` column with RLS policies
- `TenantMiddleware` decodes JWT, sets `SET LOCAL app.current_tenant`
- Admin endpoints use `get_db_admin` (bypasses RLS for cross-tenant queries)

### Data as Training Set
The event store is append-only. Every agent action, human override, and listing outcome is captured as a labeled event. This data powers the Adaptive Intelligence layer and eventual ML model.

---

## 10. MLS Compliance Strategy

LaunchLens operates as a **listing preparation tool**, not a listing submission system. This is a deliberate architectural and legal decision.

### Phase 1 — NOW (v0.9.0): Manual Upload with Compliant Export

**What we do:**
- Export unbranded MLS bundles: photos stripped of overlays, renamed per MLS spec, ordered correctly
- Branded content (flyers, social posts, email copy) is delivered as a separate, clearly labeled package
- Agent manually logs into their MLS portal and uploads the bundle

**What we do NOT do:**
- No browser automation (Playwright, Selenium, or any headless browser)
- No credential storage for MLS systems
- No programmatic submission of any kind

**Key principle:** LaunchLens delivers the right file in the right format. The agent presses upload. We prepare; they submit.

### Phase 2 — Compliance Tooling (v1.x)

- **Photo compliance scanner:** Automated pre-export check against common MLS photo rules (minimum dimensions, no text overlays, no borders, no watermarks in MLS mode)
- **Two explicit export modes:**
  - **MLS Mode** — unbranded, spec-compliant, ready for portal upload
  - **Marketing Mode** — branded, social-optimized, agent-facing assets
- Both modes generated from the same approved photo package; user selects at export time

### Phase 3 — RESO Web API Certification (v2.x)

- Apply for RESO (Real Estate Standards Organization) Web API vendor certification
- Implement RESO-compliant data submission against certified MLS boards
- Deliver a true one-click MLS publish for participating boards
- **The path is certification, not automation.** We become a recognized vendor, not a scraper.

### What We Will Never Do
- Browser automation against MLS portals (legal risk, ToS violation, fragile, unscalable)
- Store MLS credentials on behalf of agents
- Submit listings without explicit per-listing agent authorization

---

## 11. Key Metrics

### North Star: Time-to-Market
Median time from photo upload to approved listing package. Target: <3 minutes for a 50-photo listing.

### Pipeline Metrics
| Metric | Target |
|---|---|
| Vision accuracy (room classification) | >90% |
| Coverage gap detection rate | >95% |
| Hero photo agreement (AI vs. human) | >80% |
| FHA compliance (zero violations shipped) | 100% |
| Description approval rate (no edits) | >70% |
| Social post click-through improvement | >15% vs. manual |
| MLS export bundle acceptance rate | >98% (no MLS rejection due to format) |

### Business Metrics
| Metric | Target (Month 6) |
|---|---|
| Monthly active tenants | 50+ |
| Listings processed/month | 1,000+ |
| MRR | $15K+ |
| Gross margin | >80% |
| Net promoter score | >50 |
| Demo-to-registration conversion | >30% |

---

## 12. Competitive Moat

The moat is NOT the AI (anyone can call GPT-4V). The moat is:

1. **The Learning Loop:** Every override is labeled training data. After 500 listings, LaunchLens knows that luxury brokerages want pool shots first and modern kitchens need wide-angle emphasis. Competitors start from zero.

2. **The Workflow Lock-in:** Once a team's brand kit, coverage profiles, and weight preferences are in LaunchLens, switching costs are high. It's their institutional knowledge.

3. **The Data Asset:** Performance Intelligence (Phase 2) links photo selections to listing outcomes. "LaunchLens-optimized listings sell 12% faster" is an un-copyable claim backed by proprietary data.

4. **Distribution:** Existing photography client base provides day-1 users. Most AI SaaS founders have a product but no distribution. You have both.

5. **Compliance-First Positioning:** By refusing browser automation and pursuing RESO certification, LaunchLens becomes the trusted vendor choice for brokerages with compliance requirements — a market that self-selects against scraper-based competitors.

---

## 13. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Vision API cost at scale | High | Medium | Tier-2 bypass for simple listings, cache results, batch pricing |
| MLS format mismatch (export rejected) | Medium | Medium | Phase 2 compliance scanner; Phase 1 manual review by agent before upload |
| Photo quality too low for AI | Medium | Medium | Coverage Agent flags issues, photographer notification flow |
| Agent resistance to AI descriptions | Medium | Low | Always allow human editing, show "AI draft" not "final copy" |
| Competitor copies features | High | Low | Learning loop + data asset = 6-month head start compounds |
| FHA violation in AI-generated copy | Low | Critical | Hardcoded baseline regex + DB-additive terms, retry-on-violation |
| RESO certification timeline (Phase 3) | High | Low | Phase 1/2 manual export is a complete, sellable product without it |
