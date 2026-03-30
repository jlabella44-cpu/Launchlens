# ListingJet Cost & Revenue Analysis

**Date:** March 29, 2026
**Scenarios:** Skeleton/Test, Full Production, 100 Active Users

---

## Scenario 1: Skeleton / Test Version

> Minimum viable setup for development, demos, and investor presentations.
> Single developer, local Temporal, no HA, free tiers everywhere possible.

| Category | Service | Monthly Cost | Notes |
|----------|---------|-------------|-------|
| **Compute** | Vercel Hobby (frontend) | $0 | Free tier, 1 project |
| | Railway / Render (API + Worker) | $5 | Hobby plan, single container |
| **Database** | Neon Postgres (free tier) | $0 | 0.5 GB storage, 1 compute |
| **Cache** | Upstash Redis (free tier) | $0 | 10k commands/day |
| **Storage** | AWS S3 (free tier) | $0 | 5 GB, 12 months |
| **AI - Vision** | Google Vision API | ~$2 | Free: 1k units/mo, then $1.50/1k |
| **AI - LLM** | Anthropic Claude | ~$5 | ~50 test listings x ~1k tokens each |
| **AI - Vision 2** | OpenAI GPT-4o | ~$3 | ~50 images x $0.05/image |
| **AI - Video** | Kling AI | ~$5 | ~10 test videos |
| **AI - Voice** | ElevenLabs | ~$1 | Free tier: 10k chars/mo |
| **Design** | Canva (free API) | $0 | Free tier or skip for test |
| **Payments** | Stripe (test mode) | $0 | No live charges |
| **Email** | Gmail SMTP / Resend free | $0 | 100 emails/day free |
| **Monitoring** | Sentry free tier | $0 | 5k events/mo |
| **Domain** | .com domain | ~$12/yr ($1/mo) | Namecheap/Cloudflare |
| **Temporal** | Self-hosted (same container) | $0 | Bundled with API server |
| **ClamAV** | Skip or local | $0 | Not needed for test |
| | | | |
| **TOTAL** | | **~$17/mo** | |

### What you get:
- Working demo with all AI features at low volume
- Shareable URL for investor/customer demos
- All core flows functional (upload → process → deliver)
- No redundancy, no auto-scaling

---

## Scenario 2: Full Production Version

> Production-grade infrastructure ready for paying customers.
> HA database, proper monitoring, CI/CD, all services running.
> Assumes ~0-20 users, low but real traffic.

| Category | Service | Monthly Cost | Notes |
|----------|---------|-------------|-------|
| **Compute** | Vercel Pro (frontend) | $20 | Custom domains, analytics |
| | AWS ECS Fargate - API | $30 | 0.5 vCPU, 1 GB RAM |
| | AWS ECS Fargate - Worker | $30 | 0.5 vCPU, 1 GB RAM |
| | AWS ECS Fargate - Temporal | $30 | 0.5 vCPU, 1 GB RAM |
| **Networking** | AWS ALB | $18 | Load balancer |
| | AWS NAT Gateway | $35 | Fixed + data transfer |
| **Database** | AWS RDS Postgres (t4g.micro) | $42 | 20 GB, daily backups |
| **Cache** | AWS ElastiCache Redis (t4g.micro) | $13 | Single node |
| **Storage** | AWS S3 | $5 | ~50 GB photos/videos |
| | AWS ECR | $2 | Docker image registry |
| **AI - Vision** | Google Vision API | $15 | ~10k detections/mo |
| **AI - LLM** | Anthropic Claude Sonnet | $30 | ~500 listings x ~2k tokens |
| **AI - Vision 2** | OpenAI GPT-4o | $25 | ~500 images/mo |
| **AI - Video** | Kling AI | $50 | ~100 videos/mo |
| **AI - Voice** | ElevenLabs (Starter) | $22 | 30k chars/mo |
| **Design** | Canva Connect API | $0-30 | Depends on plan |
| **Payments** | Stripe | ~$15 | 2.9% + $0.30 on ~$500 MRR |
| **Email** | AWS SES | $5 | ~5k emails/mo |
| **Monitoring** | Sentry (Team) | $29 | 50k events/mo |
| | CloudWatch | $10 | Logs, metrics, alarms |
| **Security** | ClamAV (ECS sidecar) | $0 | Open source, same cluster |
| **Domain + SSL** | Route53 + ACM | $2 | Hosted zone + free SSL |
| **CI/CD** | GitHub Actions | $0 | Free for public / 2k min/mo |
| | | | |
| **TOTAL** | | **~$428/mo** | |

### What you get:
- Production-grade reliability
- Auto-healing containers, health checks
- Real monitoring and alerting
- Stripe live billing
- All AI features active
- Professional email notifications

### Revenue needed to break even:
- At $49/mo Starter plan: **9 paying users**
- At $99/mo Pro plan: **5 paying users**
- At $199/mo Enterprise plan: **3 paying users**

---

## Scenario 3: 100 Active Users

> 100 paying users, mix of plans, moderate to heavy feature usage.
> Assumes: 40 Starter ($49), 45 Pro ($99), 15 Enterprise ($199).
> Each user processes avg 10 listings/month.

### Revenue Projection

| Plan | Users | Price/mo | Monthly Revenue |
|------|-------|----------|-----------------|
| Starter | 40 | $49 | $1,960 |
| Pro | 45 | $99 | $4,455 |
| Enterprise | 15 | $199 | $2,985 |
| Credit bundles (upsell) | ~20% | avg $25 | $500 |
| **TOTAL MRR** | **100** | | **$9,900** |
| **ARR** | | | **$118,800** |

### Cost Projection (100 Users)

| Category | Service | Monthly Cost | Notes |
|----------|---------|-------------|-------|
| **Compute** | Vercel Pro (frontend) | $20 | Handles traffic fine |
| | ECS Fargate - API (2 tasks) | $60 | Scaled for concurrency |
| | ECS Fargate - Worker (2 tasks) | $60 | Parallel pipeline processing |
| | ECS Fargate - Temporal | $30 | Single instance sufficient |
| **Networking** | ALB | $25 | More LCU usage |
| | NAT Gateway | $50 | Higher data transfer |
| **Database** | RDS Postgres (t4g.small) | $85 | Upgraded, 50 GB, Multi-AZ |
| **Cache** | ElastiCache Redis (t4g.small) | $26 | More rate-limiting, sessions |
| **Storage** | S3 | $30 | ~500 GB (1k listings x 50 photos avg) |
| | ECR | $3 | Image storage |
| | S3 data transfer | $20 | Photo downloads/previews |
| **AI - Vision** | Google Vision | $75 | ~50k detections/mo |
| **AI - LLM** | Anthropic Claude | $200 | ~1k listings x 3 agents x ~2k tokens |
| **AI - Vision 2** | OpenAI GPT-4o | $150 | ~1k listings x 3 re-ranks |
| **AI - Video** | Kling AI | $300 | ~600 videos/mo (Pro+Enterprise) |
| **AI - Voice** | ElevenLabs (Scale) | $99 | 500k chars/mo |
| **Design** | Canva Connect | $50 | ~500 flyer renders/mo |
| **Payments** | Stripe | ~$315 | 2.9% + $0.30 on $9,900 |
| **Email** | AWS SES | $15 | ~30k emails/mo |
| **Monitoring** | Sentry (Business) | $80 | 100k events/mo |
| | CloudWatch | $25 | Higher log volume |
| | Jaeger/OTEL | $0 | Self-hosted |
| **Domain** | Route53 | $2 | |
| **CI/CD** | GitHub Actions | $0 | |
| **RESO MLS** | API fees | $50 | Varies by provider |
| **ClamAV** | Self-hosted | $0 | |
| | | | |
| **TOTAL COSTS** | | **~$1,770/mo** | |

---

## Summary Comparison

| Metric | Skeleton | Full Production | 100 Users |
|--------|----------|----------------|-----------|
| **Monthly Cost** | $17 | $428 | $1,770 |
| **Annual Cost** | $204 | $5,136 | $21,240 |
| **MRR** | $0 | $0-500 | $9,900 |
| **Gross Margin** | N/A | N/A | **82%** |
| **Break-even Users** | N/A | 5-9 | Profitable |
| **Net Monthly Profit** | -$17 | -$428 | **+$8,130** |
| **Biggest Cost Driver** | AI APIs | Infrastructure | AI APIs (41%) |

---

## Cost Distribution at 100 Users

```
AI/ML Services:      $824  (47%)  ← Largest, scales with usage
Infrastructure:      $359  (20%)  ← Compute, networking, DB
Storage:              $53   (3%)
Payments (Stripe):   $315  (18%)  ← Unavoidable revenue %
Monitoring:          $105   (6%)
Other:               $117   (6%)  ← Email, domain, design, MLS
```

---

## Key Insights

1. **AI costs are the #1 variable** — they scale directly with listings processed. Consider:
   - Caching vision results to avoid re-processing
   - Using Claude Haiku for simpler content tasks (~10x cheaper)
   - Negotiating volume discounts with providers at scale

2. **NAT Gateway is surprisingly expensive** — $35-50/mo for basic traffic. Consider VPC endpoints for S3/ECR to reduce this.

3. **82% gross margin at 100 users** is healthy for SaaS. Industry benchmark is 70-80%.

4. **Break-even at ~5-9 users** makes this a very achievable business.

5. **Stripe's 2.9% cut** becomes significant at scale ($315/mo at 100 users). At 1000+ users, consider negotiating custom rates.

6. **Skeleton version at $17/mo** is ideal for:
   - Demo purposes
   - Investor presentations
   - Early beta testing
   - Validating product-market fit before investing in infrastructure
