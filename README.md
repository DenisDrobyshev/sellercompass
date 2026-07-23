# SellerHelper

An open-source decision pipeline for marketplace sellers. It takes a seed interest and returns a Go, Pivot, or Kill verdict on a product niche, computed from live Wildberries listing data rather than from a language model's priors.

[![CI](https://github.com/DenisDrobyshev/sellerhelper/actions/workflows/ci.yml/badge.svg)](https://github.com/DenisDrobyshev/sellerhelper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

English | [Русский](README.ru.md)

The repository is mirrored at [GitLab](https://gitlab.com/DenisDrobyshev/sellerhelper).

Status: v0, under development. All five pipeline stages run against live data. Wildberries is the only supported marketplace.

## Motivation

Beginning sellers usually fail at product selection, before anything else is decided. Existing tools fall into two groups. Business plan generators produce narrative documents populated with invented figures. Analytics services such as MPStats, Moneyplace, Jungle Scout and Helium 10 provide accurate data but present it as a dashboard, which assumes the reader already knows which metrics matter and what threshold separates a viable niche from a bad one.

SellerHelper encodes that judgment as a sequence of gates. Each stage computes metrics from collected listings and applies an explicit pass or fail condition. A stage that fails blocks the pipeline and reports the numbers behind the decision.

## Pipeline

| Stage | Computes | Gate condition |
|---|---|---|
| 1. Discover | Candidate sub-niches mined from product titles, with price and review aggregates per candidate | none (divergent stage) |
| 2. Validate demand | Review totals across top listings, price corridor, demand trend across stored snapshots | demand above threshold and not declining |
| 3. Competition | Brand concentration (top-3 share of review volume), price bands, rating soft spots | market not saturated and at least one opening exists |
| 4. Unit economics | Commission, logistics, acquiring, cost of goods, advertising and tax, yielding margin and a first-batch plan | margin positive and at or above 10 percent, batch size viable |
| 5. Decide | Combines the verdicts of stages 2 to 4 | none (terminal stage) |

Full stage definitions and gate criteria are in [METHODOLOGY.md](METHODOLOGY.md).

## Explanation layer

The pipeline produces the verdict; a language model only explains it. `core/llm.py` takes a finished decision and turns the numbers behind it into a short plain-language summary, instructed to reason strictly from the figures the gates computed and not to introduce data of its own. The layer is optional and degrades cleanly: with no key configured it returns a deterministic template, so the tool runs offline and the test suite exercises both paths. Supplying `LLM_API_KEY`, and optionally `LLM_MODEL`, routes the same call to Claude through the Anthropic SDK:

```bash
pip install -e ".[llm]"
export LLM_API_KEY=...     # without a key, explanations use the built-in template
```

## Data acquisition

Collecting Wildberries data is the constraining problem in this project, and the implementation reflects several measured facts about how the platform behaves.

The public JSON endpoints (`search.wb.ru`, `card.wb.ru`, `feedbacks*.wb.ru`) rate-limit by IP address. A first request from a residential address succeeds. Subsequent requests return HTTP 429, and after repeated attempts the search endpoint returns HTTP 200 with an empty product array instead of an error, which is easy to misread as an empty market. The same limit applies to requests issued from inside a page on `wildberries.ru`, so the restriction follows the address rather than the client fingerprint.

The rendered search page is not subject to that limit. It returns product cards while the JSON API is still refusing requests. The Selenium collector therefore drives Chrome, opens the search results page, scrolls to trigger lazy loading, and reads the cards from the DOM. One crawl of a single query yields roughly 100 products with identifier, title, brand, price, rating and review count.

Two collectors are included:

`core/collectors/wildberries.py` is an async httpx client against the JSON API. It applies randomized exponential backoff on 429, paces requests, and accepts a proxy. It is faster when the address is not throttled.

`core/collectors/wb_selenium.py` is the Selenium collector described above. It is slower, but it returns data under throttling.

Card markup uses hashed CSS module class names whose suffixes change between deployments, so selectors match on stable substrings such as `article.product-card` rather than on exact class names.

## Storage

Each crawl writes a batch of `ProductObservation` rows sharing a single `collected_at` timestamp. Reading the newest timestamp yields the current snapshot. Comparing review totals across timestamps yields the demand trend consumed by stage 2.

SQLAlchemy defines the schema, with SQLite as the default so the project runs without external services. Set `DATABASE_URL` to use PostgreSQL instead.

Historical snapshots cannot be reconstructed retroactively, which is why collection is designed to run repeatedly over time rather than once on demand.

## Installation

```bash
git clone https://github.com/DenisDrobyshev/sellerhelper
cd sellerhelper
cp .env.example .env
pip install -e ".[dev]"
```

The Selenium collector requires a local Chrome installation. Selenium Manager resolves the driver automatically.

## Usage

Collect a snapshot, then run the whole pipeline or any single stage against the stored data:

```bash
python -m core.collectors.wb_selenium "термокружка"             # crawl and store a snapshot
python -m core.engine.pipeline       --db "термокружка" 100000   # all five stages at once

python -m core.engine.discover       --db "термокружка"          # stage 1
python -m core.engine.demand         --db "термокружка"          # stage 2
python -m core.engine.competition    --db "термокружка"          # stage 3
python -m core.engine.unit_economics --db "термокружка" 100000   # stage 4, budget in RUB
python -m core.engine.decide         --db "термокружка" 100000   # stage 5
```

The HTTP API exposes the same stages:

```bash
uvicorn core.main:app --reload      # http://localhost:8000/docs
```

| Endpoint | Stage |
|---|---|
| `GET /stages/discover?seed=&budget=` | 1 |
| `GET /stages/demand?query=` | 2 |
| `GET /stages/competition?query=` | 3 |
| `GET /stages/economics?query=&price=&budget=&cogs=` | 4 |
| `GET /stages/decide?query=&budget=` | 5 |
| `GET /stages/pipeline?query=&budget=` | all five |

The `pipeline` and `decide` responses also carry the plain-language `explanation` described above.

## Web interface

The same process serves a single-page web interface at the root path. It takes a niche query and an optional budget, calls the pipeline endpoint, and lays out the verdict, the gate outcomes, the plain-language explanation, the first-batch plan and the adjacent niches to consider. The page is self-contained, with no build step and no external assets, and operates on niches that already have a stored snapshot.

```bash
uvicorn core.main:app --reload      # http://localhost:8000/
```

## Scheduled collection

Register queries and crawl them on a schedule (cron, or Windows Task Scheduler). Each pass stores a timestamped snapshot, which is what gives the Stage 2 trend a real interval to measure over.

```bash
python -m core.scheduler --add "термокружка"   # register a query
python -m core.scheduler --list                 # show the watchlist
python -m core.scheduler                        # crawl every watched query once
```

`docker compose up --build` starts the API with no configuration required. It uses SQLite on a persistent volume by default and includes a health check; PostgreSQL and Redis start alongside for opt-in use.

```bash
docker compose up --build      # http://localhost:8000/health
```

## Example

Output of stage 5 for the query `термокружка` with a budget of 100 000 RUB, computed from a stored snapshot:

```
Stage 5 . Decide - 'термокружка'
   verdict: PIVOT
   stage 2 demand:      PASS (score 1.0)
   stage 3 competition: FAIL (score 0.26)
   stage 4 economics:   PASS (score 0.15)
   demand exists, but the market has no entry window - try an adjacent niche

   'термокружка': demand is real, but a few brands dominate the market. Rather than fighting
   that head-on, pivot to an adjacent niche (see the Discover candidates) and re-check it.

  First-batch plan:
   price 641.0 RUB | margin 97.04 RUB/unit
   445 units for 99835.75 RUB
   projected profit 43182.8 RUB (ROI 43%)
```

The verdict is PIVOT because the three top brands hold 74 percent of review volume in that niche, although demand is high and the unit economics clear the margin floor. The paragraph below the gate lines is the explanation layer running without a key, on the built-in template; with a key it is regenerated by Claude from the same numbers.

## Repository layout

```
core/
  api/          FastAPI routes (health, five stage endpoints)
  collectors/   Wildberries collectors: httpx API client and Selenium spider
  engine/       stage-gate engine: discover, demand, competition, unit_economics, decide
  llm.py        optional explanation layer: template fallback, Claude when a key is set
  models/       normalized, marketplace-agnostic product model
  storage/      SQLAlchemy models and snapshot repository
  web/          self-contained single-page web interface, served at the root path
tests/          45 unit tests, no network access required
```

## Design decisions

The project is open core. Engine, collectors and self-hosted deployment are MIT licensed. A hosted service holding pre-collected historical data is planned separately. The defensible asset is the collection infrastructure and the accumulated time series, not the scoring code, which is short and easy to reproduce.

Stage 3 measures concentration by brand rather than by seller because search cards expose brand and omit seller. Grouping review volume by brand approximates market structure using data that is actually retrievable.

Stage 3 also uses rating soft spots, meaning popular listings with mediocre ratings, as a stand-in for unmet customer needs. The methodology calls for mining competitor reviews directly. `analyze_reviews` in `core/engine/competition.py` implements that extraction and is covered by tests, but it has no data source yet (see limitations).

Gate thresholds are module-level constants rather than learned parameters. They are calibrated by hand and documented next to the code that applies them, so a seller can adjust them for a category without retraining anything.

Fee assumptions in stage 4 are function parameters with defaults, so a seller with real supplier quotes and category commissions can substitute them without editing the model.

## Known limitations

Review text is not collected. The JSON feedback endpoints are rate-limited, and the reviews page uses hashed class names with seller replies interleaved among buyer reviews. Stage 3 therefore relies on rating soft spots rather than complaint mining.

Trend classification requires at least two snapshots separated in time. A single crawl reports the trend as unknown, and stage 2 falls back to demand level alone.

Stage 4 fee defaults are category-independent approximations of Wildberries commission, logistics and advertising costs. They produce a realistic first pass, not an accounting figure.

The Selenium collector requires a local Chrome installation. Chrome intermittently fails to start on repeated launches within one session; rerunning the command resolves it.

The engine, storage and Product model are marketplace-agnostic, and an Ozon collector (`core/collectors/ozon.py`) implements the same interface; the pipeline runs unchanged on Ozon products. Live Ozon collection is blocked by Ozon's anti-bot, which serves a stub page to automated browsers, and would need residential proxies and stealth that are out of scope here. Amazon and Etsy remain on the roadmap.

## Testing

The test suite covers price parsing, snapshot persistence, trend classification, niche mining, and every gate condition. All tests run offline. GitHub Actions runs `ruff` and `pytest` on each push.

```bash
ruff check core tests
pytest -q
```

## Documentation

[METHODOLOGY.md](METHODOLOGY.md) defines each stage and its gate. [ARCHITECTURE.md](ARCHITECTURE.md) covers components and data flow. [ROADMAP.md](ROADMAP.md) lists completed and planned work.

## License

[MIT](LICENSE), Copyright 2026 Denis Drobyshev.
