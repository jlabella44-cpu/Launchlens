# LaunchLens PRD v2: The Listing Media OS

## 1. Vision

LaunchLens is the operating system for real estate listing media. It replaces the fragmented 7+ tool workflow (photographer, editor, Dropbox, MLS login, tour builder, social scheduler, email blast tool) with a single AI-powered platform that turns raw listing photos into a complete, market-ready listing package in under 3 minutes.

**The insight:** The costliest gap in real estate isn't taking photos — it's the 2-4 hours of manual labor to go from finished media to a live listing across MLS, social media, email, and print. LaunchLens eliminates this gap entirely.

**Positioning:** "The AI-powered listing creation platform that turns raw photos into market-ready listings in 3 minutes. From photo curation to MLS export to social media — all in one app."

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
**Tagline:** From raw listing media to launch-ready marketing in minutes.

### Core Feature: The Listing Media Pipeline

```
  UPLOAD          ANALYZE           CURATE            CREATE            EXPORT
  ┌─────┐       ┌──────────┐      ┌──────────┐      ┌──────────┐     ┌──────────┐
  │Photos│──────▶│ AI Vision │─────▶│ Smart    │─────▶│ Content  │────▶│ MLS-Ready│
  │      │       │ + Score   │      │ Package  │      │ + Brand  │     │ Bundle   │
  └─────┘       └──────────┘      └──────────┘      └──────────┘     └──────────┘
                     │                  │                  │                │
                 Room labels      Hero select         Description      ZIP download
                 Quality score    Coverage check      Flyer PDF        Social posts
                 Dedup            Gallery order       Social captions  MLS metadata
                 Hero candidate   Missing shots       Email blast      Deep links
```

### Feature Set

#### Tier 1: Photo Intelligence (Upload → Analyze → Curate)
- **AI Photo Classification:** Room type, quality score, commercial appeal score (Google Vision bulk + GPT-4V for top candidates)
- **Near-Duplicate Detection:** Hash-based dedup (MVP), embedding-based similarity (Phase 2)
- **Coverage Analysis:** Visual "Shot Coverage Card" — shows which required shots are present/missing by property type
- **Smart Package Selection:** AI selects top 25 photos, ordered for buyer journey. Hero photo prominently featured.
- **Transparency Tooltips:** Hover any photo to see "Why selected: quality 92, hero candidate, exterior shot"
- **Human Review:** Drag-reorder, swap photos, override AI selections. Every override becomes training data.

#### Tier 2: Content Creation (Curate → Create)
- **AI Listing Description:** Claude-generated prose from property metadata + photo analysis. JSON-validated, FHA-compliant.
- **Branded Flyer:** Auto-generated PDF using brokerage brand kit (logo, colors, fonts). Template-based with photo placement.
- **Social Media Posts:** Platform-specific captions for Instagram, Facebook, LinkedIn, Twitter/X. Hashtags, emojis, CTAs optimized per platform.
- **Email Blast Copy:** Property announcement email with hero image, key features, CTA to listing page.

#### Tier 3: Export + Distribution (Create → Export)
- **MLS-Ready Bundle:** ZIP download with photos renamed/resized to MLS spec, ordered correctly, plus metadata CSV.
- **MLS Deep Link Export:** "Export to MLS" button opens the agent's MLS system with files pre-staged for upload.
- **Social Media Export:** Download social-optimized images + captions as a ready-to-post package.
- **Webhook Delivery:** POST to any URL when a listing package is approved (CRM integration, team notifications).
- **Property Website (Phase 2):** Auto-generated single-page property site with photos, description, map, contact form.

#### Platform Layer: The Learning Engine
- **Override Learning:** Every human correction (photo swap, reorder, description edit) trains the system per-tenant.
- **Weight Evolution:** Room-type weights adjust over time. A luxury brokerage that always promotes pool shots gets pool photos ranked higher.
- **Performance Intelligence (Phase 2):** Connect listing outcomes (days-on-market, views, saves) to LaunchLens photo selections. Prove which photos sell faster.

---

## 5. User Stories

### Media Team Operator (Primary Persona)
1. As a media team lead, I upload 50 photos from a shoot and get a curated 25-photo MLS package in under 2 minutes.
2. As a media team lead, I review the AI's photo selections, swap 2 photos, and approve the package — knowing my overrides make the AI smarter next time.
3. As a media team lead, I click "Export to MLS" and get a ZIP with correctly named, resized, ordered photos + a metadata file ready for upload.
4. As a media team lead, I generate social media posts for Instagram and Facebook in one click, with platform-specific formatting.
5. As a media team lead, I see a Coverage Card showing I'm missing a bathroom shot, so I notify the photographer before delivery.

### Solo Photographer
6. As a solo photographer, I upload photos and get a complete listing package (description, flyer, social posts, MLS bundle) without switching between 5 different tools.
7. As a solo photographer, I set up my brand kit once and every flyer uses my logo, colors, and contact info automatically.

### Brokerage Admin
8. As a brokerage admin, I see platform stats: how many listings are in-progress, average processing time, and which agents have pending reviews.
9. As a brokerage admin, I manage team members — invite agents, set roles, and enforce brand compliance.

---

## 6. Scope

### MVP (Built — v0.1.0 through v0.8.3)
- Full AI pipeline: Ingestion → Vision (2-tier) → Coverage → Packaging → Content → Brand → Distribution
- JWT auth with register/login, role-based access
- Stripe subscriptions with checkout, portal, webhooks
- 9 REST API endpoints for listing CRUD + review + approve
- Temporal workflow orchestration with signal-based human review gate
- Plan enforcement (listing + asset quotas per tier)
- Admin dashboard (tenant/user CRUD, platform stats)
- Docker Compose dev environment
- CI/CD (GitHub Actions: lint, test, docker build)

### Next Milestone (v0.9.x — This Plan)
- **MLS Export Agent** — ZIP packaging with MLS-spec photos + metadata CSV
- **Social Content Agent** — Platform-specific social media post generation
- **Export API endpoint** — `GET /listings/{id}/export` returns download URL
- **Frontend** — Next.js with 3D interactive design (plan written, awaiting execution)

### Phase 2 (Deferred)
- Browser automation for MLS upload (Playwright + credential vault)
- Image embedding-based near-duplicate detection
- Property website auto-generation
- Performance Intelligence (outcome linking)
- Real-time collaborative review (Figma-style multi-cursor)
- Canva API integration (replace template stub)
- LiDAR room measurement extraction

### Phase 3 (Vision)
- RESO/MLS vendor certification
- Official listing input API ("Stripe for Real Estate Listings")
- White-label brokerage deployment
- ML scoring model (replace rule-based Learning Agent)

---

## 7. Pricing

### Hybrid: Base Fee + Per-Listing Usage

| | Starter | Pro | Enterprise |
|---|---|---|---|
| **Monthly base** | $49 | $99 | Custom |
| **Per listing** | $9 | $7 (10 included) | $5 (volume) |
| **Users** | 2 | 5 | Unlimited |
| **Listings/month** | 5 | 50 | 500+ |
| **Photos/listing** | 25 | 50 | 100 |
| **AI Description** | Basic | Full + FHA | Full + FHA + custom prompt |
| **Social Posts** | - | Instagram + Facebook | All platforms + scheduling |
| **MLS Export** | ZIP download | ZIP + deep link | ZIP + automated upload (Phase 2) |
| **Brand Kits** | 1 | 3 | Unlimited |
| **Learning Engine** | - | Per-tenant weights | Per-agent weights |
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

### Phase 1: Design Partner (Weeks 1-8)
- **Juke Media** as exclusive launch partner
- Shadow review dashboard — internal QA for first 100 listings
- Goal: validate pipeline accuracy, collect override data for Learning Engine

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
                             ContentAgent → BrandAgent → SocialContentAgent
                                                              ↓
                                                      MLSExportAgent
                                                              ↓
                                                     DistributionAgent
```

Each agent extends `BaseAgent`, opens its own DB session, uses injected providers, transitions `Listing.state`, and emits domain events via the Outbox Pattern.

### Listing State Machine
```
NEW → UPLOADING → ANALYZING → AWAITING_REVIEW → IN_REVIEW → APPROVED → EXPORTING → DELIVERED
```

### Multi-Tenant Isolation
- All tables have `tenant_id` column with RLS policies
- `TenantMiddleware` decodes JWT, sets `SET LOCAL app.current_tenant`
- Admin endpoints use `get_db_admin` (bypasses RLS for cross-tenant queries)

### Data as Training Set
The Event store is append-only. Every agent action, human override, and listing outcome is captured as a labeled event. This data powers the Learning Engine and eventual ML model.

---

## 10. Key Metrics

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

### Business Metrics
| Metric | Target (Month 6) |
|---|---|
| Monthly active tenants | 50+ |
| Listings processed/month | 1,000+ |
| MRR | $15K+ |
| Gross margin | >80% |
| Net promoter score | >50 |

---

## 11. Competitive Moat

The moat is NOT the AI (anyone can call GPT-4V). The moat is:

1. **The Learning Loop:** Every override is labeled training data. After 500 listings, LaunchLens knows that luxury brokerages want pool shots first and modern kitchens need wide-angle emphasis. Competitors start from zero.

2. **The Workflow Lock-in:** Once a team's brand kit, coverage profiles, and weight preferences are in LaunchLens, switching costs are high. It's their institutional knowledge.

3. **The Data Asset:** Performance Intelligence (Phase 2) links photo selections to listing outcomes. "LaunchLens-optimized listings sell 12% faster" is an un-copyable claim backed by proprietary data.

4. **Distribution:** Existing photography client base provides day-1 users. Most AI SaaS founders have a product but no distribution. You have both.

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Vision API cost at scale | High | Medium | Tier-2 bypass for simple listings, cache results, batch pricing |
| MLS compliance (Phase 2 automation) | Medium | High | Start with export-only (no automation), get legal review before Phase 2 |
| Photo quality too low for AI | Medium | Medium | Coverage Agent flags issues, photographer notification flow |
| Agent resistance to AI descriptions | Medium | Low | Always allow human editing, show "AI draft" not "final copy" |
| Competitor copies features | High | Low | Learning loop + data asset = 6-month head start compounds |
| FHA violation in AI-generated copy | Low | Critical | Hardcoded baseline regex + DB-additive terms, retry-on-violation |
