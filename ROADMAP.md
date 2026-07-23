# Roadmap

The sequence is deliberate: one marketplace, one complete pipeline, real users, before any widening of scope.

## v0. Wildberries, self-hosted (current)

- [x] Wildberries collectors: httpx JSON client and Selenium DOM spider
- [x] Snapshot storage with timestamps, which makes trend analysis possible
- [x] Stage 1, Discover: `GET /stages/discover`
- [x] Stage 2, Validate demand: `GET /stages/demand`
- [x] Stage 3, Competition: `GET /stages/competition`
- [x] Stage 4, Unit economics: `GET /stages/economics`
- [x] Stage 5, Decide: `GET /stages/decide`
- [x] Full-pipeline runner: one command runs all five stages (`core.engine.pipeline`, `GET /stages/pipeline`)
- [x] Scheduled collection via a watchlist (`core.scheduler`), so trend classification has real separation in time
- [x] Onboarding flow: a profile (budget, interests, goal) ranked into a recommendation (`core.engine.onboarding`, `GET /stages/recommend`)
- [x] Review digest (WB's aggregated summary and aspect facets) wired into Stage 3 as customer voice; raw per-review complaint mining still awaits a source
- [x] Docker Compose that runs with no configuration (SQLite volume, healthcheck, no `.env` required); compose config validated
- [x] Explanation layer: a language model renders the verdict in plain language, grounded strictly on the gate figures, with a deterministic template fallback when no key is set (`core/llm.py`)
- [x] Web interface: a self-contained single page served at the root path that runs the pipeline and presents the verdict, explanation, first-batch plan and adjacent niches

Completion criterion: ten beginning sellers run the pipeline end to end.

## v1. Hosted service and Ozon

- [x] Ozon collector implementing the shared Product interface; the engine runs unchanged on Ozon products. Live Ozon collection is blocked by Ozon's anti-bot (headless Chrome receives a stub) and needs residential proxies or stealth
- [ ] Hosted deployment serving pre-collected current and historical data
- [ ] Accounts and a paid tier

Completion criterion: first paying users.

## v2. Non-Russian marketplaces

- [ ] Amazon and Etsy connectors
- [ ] Community-contributed connectors
- [ ] Coverage beyond the first product, toward ongoing seller operations

## Out of scope

The following are excluded deliberately rather than overlooked.

Managing an already operating business, such as repricing and stock control, is covered by sellerboard and comparable tools.

Supplier sourcing and purchasing.

A mobile application.

Billing infrastructure, until the self-hosted version demonstrates value.
