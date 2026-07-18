# Roadmap

The strategy is **start narrow, prove the engine, then widen**. One marketplace, one killer outcome, real users — before anything else.

## v0 — MVP (open-source, Wildberries)

The whole 5-stage pipeline for **Wildberries only**, self-hostable locally.

- [ ] Onboarding: budget, interests, goal
- [x] Wildberries data connector — httpx API + Selenium browser spider (beats IP throttling)
- [x] Historization: timestamped snapshots in SQLite/Postgres (enables demand trend)
- [x] Stage 1 — Discover (candidate niches) — `GET /stages/discover`
- [x] Stage 2 — Validate demand (+ gate) — `GET /stages/demand`
- [x] Stage 3 — Competition: brand concentration + price bands + rating soft-spots (+ gate); review-NLP engine built, awaiting a review feed
- [x] Stage 4 — Unit economics (+ gate) — `GET /stages/economics`
- [ ] Stage 5 — Decide: Go/Pivot/Kill verdict + first-batch plan + launch checklist
- [ ] One-command Docker Compose self-host

**Success = 10 real beginner sellers run it end-to-end + first GitHub stars.**

## v1 — Hosted + Ozon

- [ ] Ozon connector (proves the architecture is marketplace-agnostic)
- [ ] Hosted version with pre-collected live + historical data (zero setup)
- [ ] Accounts + a basic paid tier (the cloud half of open-core)

**Success = first paying users.**

## v2 — Go global

- [ ] Amazon / Etsy connectors (English-speaking market)
- [ ] Community-contributed connectors
- [ ] Expand beyond "first product" toward ongoing seller growth

---

## Explicitly NOT in scope (for now)

Keeping these out is a feature, not an omission:

- Managing an already-running business (repricing, stock management) — that's sellerboard's territory, not ours.
- Supplier sourcing / auto-purchasing (1688, etc.).
- A mobile app.
- Real billing infrastructure before the local version has proven its value.
