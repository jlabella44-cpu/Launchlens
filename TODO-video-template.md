# Video Template — Kling 2.5 Turbo Integration TODO

## Jeff
- [ ] Buy Kling API credits (dashboard: https://klingai.com)
- [ ] Verify API key works with `kling-v2-5-turbo` model name
- [ ] Pick a test listing ID for E2E pipeline run

## Claude
- [ ] Run single-clip smoke test against Kling API once Jeff has credits
- [ ] Trigger full E2E pipeline on test listing (`POST /listings/{id}/retry`)
- [ ] Verify output MP4: 60s duration, 12 clips, no audio, hard cuts, exterior bookends
- [ ] Verify endcard appends correctly
- [ ] Create feature branch + PR for merge
- [ ] Run full test suite in CI before merge
