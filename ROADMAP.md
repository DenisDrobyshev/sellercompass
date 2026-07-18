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
- [ ] Onboarding flow that collects budget, interests and goal
- [ ] Scheduled collection, so trend classification has real separation in time
- [ ] Review feed for the complaint extraction in stage 3
- [ ] Verified single-command Docker Compose deployment

Completion criterion: ten beginning sellers run the pipeline end to end.

## v1. Hosted service and Ozon

- [ ] Ozon connector, which tests whether the collector interface is genuinely marketplace-agnostic
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
