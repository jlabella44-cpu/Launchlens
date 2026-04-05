# ListingJet — Qwen/Gemma Integration: Todo Lists

> Saved 2026-04-05 from Claude Code session.

---

## Your Todo List (things only you can do)

### Before going live
- [ ] **Get API keys**
  - [ ] Sign up for Alibaba Cloud Model Studio → get `QWEN_API_KEY`
  - [ ] Sign up for Google AI Studio → get `GEMINI_API_KEY`
- [ ] **Add GitHub Actions secrets** — `QWEN_API_KEY` and `GEMINI_API_KEY` (enables weekly smoke tests)
- [ ] **Decide routing strategy** — which agents go to Qwen vs Gemma vs Claude?
- [ ] **Decide tier model** — which plans get premium AI vs economy AI?
- [ ] **Set pricing** — re-price your plans now that costs dropped ~70% on bulk jobs
- [ ] **Add env vars to prod** (Vercel/Render/AWS/wherever you deploy)
- [ ] **Stakeholder review** — share `docs/AI-Models-Overview.md` with co-founders/investors
- [ ] **Legal/compliance** — confirm sending client photos to Alibaba (China) is OK for your customers; if not, default enterprise tenants to Claude+Google
- [ ] **Merge the PR** — review `claude/qwen-integration-research-X6fS5` and merge to main

### After go-live
- [ ] **Monitor costs for 1 week** using the new `/admin/providers/rate-card` endpoint
- [ ] **A/B test quality** — compare Gemma-generated captions vs Claude on a small sample
- [ ] **Update marketing** — add "multi-model AI" as a feature on your site
- [ ] **Customer comms** — tell enterprise tenants they can opt into premium-only routing

---

## Claude Can Do (things to delegate next session)

### Quality & reliability
- [ ] **Quality evaluation harness** — automated side-by-side comparison of Claude vs Qwen vs Gemma outputs on real listings, with a scoring rubric
- [ ] **Circuit breaker** — if Qwen/Gemma fail 5x in a row, auto-disable them for 10 min and use Claude
- [ ] **Latency tracking** — add response-time metrics per provider so you can spot slowdowns

### Cost & billing
- [ ] **Per-tenant cost dashboard** — show each customer their monthly AI spend
- [ ] **Budget alerts** — email admins when a tenant exceeds a $ threshold
- [ ] **Cost-aware routing** — auto-downgrade to Gemma when a tenant is near their plan's AI budget cap
- [ ] **Monthly cost report** — cron job that emails a PDF cost breakdown to you

### Feature expansion
- [ ] **Audio transcription** — use Gemma E4B's native audio support for voice-dictated listings
- [ ] **Design-to-code** — new feature using Qwen's screenshot-to-HTML to turn agent design mocks into microsites
- [ ] **Frontend UI for routing config** — React page in your admin dashboard to edit routing without editing env vars

### DevOps & testing
- [ ] **Self-hosted Gemma deployment guide** — write docker-compose + vLLM setup instructions
- [ ] **Load test** — benchmark how many parallel photos each provider can handle
- [ ] **Add Sentry breadcrumbs** — tag errors with which provider was active when they fired

### Documentation
- [ ] **Technical README** — developer-facing doc for the providers module
- [ ] **Runbook** — "what to do when Qwen is down" for on-call
- [ ] **Example `.env.providers`** file showing all the new settings

---

## Already Completed (this session)

- [x] Qwen 3.6-Plus provider scaffold (`providers/qwen.py`)
- [x] Gemma 4 provider scaffold (`providers/gemma.py`)
- [x] Per-agent routing via `AGENT_MODEL_ROUTING`
- [x] Per-tenant routing via `TENANT_MODEL_ROUTING`
- [x] Retry with exponential backoff (`providers/_retry.py`)
- [x] Token cost tracking (`record_token_usage` + `TOKEN_COSTS`)
- [x] Fallback chain (`LLM_FALLBACK_ENABLED`)
- [x] Shadow mode (`LLM_SHADOW_MODE`)
- [x] Self-hosted Gemma support (`GEMMA_BASE_URL`)
- [x] Qwen context caching (`QWEN_ENABLE_CACHE`)
- [x] Admin endpoints (`/admin/providers/{config,rate-card,estimate}`)
- [x] Wired all 7 agents through factory with routing
- [x] Golden-response fixture tests (4 JSON fixtures)
- [x] Weekly live smoke test CI workflow
- [x] Non-technical overview doc (`docs/AI-Models-Overview.md`)
- [x] 82 tests passing, 0 failures
