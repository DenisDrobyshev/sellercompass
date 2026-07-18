# SellerCompass

> The open-source **AI co-founder for marketplace sellers**. Go from _"I want to sell online but don't know what"_ to a **validated first product** — grounded in live marketplace data, not guesswork.

**English** · [Русский](README.ru.md)

![status](https://img.shields.io/badge/status-early--development-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![python](https://img.shields.io/badge/python-3.12-blue)

---

## The problem

Most people who want to start selling on a marketplace fail at step zero: **they pick the wrong product.** They either:

- stare at a blank business-plan template — and give up, or
- click an "AI business plan generator" that hands them a beautiful PDF full of invented numbers.

Both reward **fake progress** (a nice-looking plan) over **real progress** — evidence that someone will actually buy.

The tools that _do_ have real data (MPStats, Moneyplace, Jungle Scout, Helium 10) are **dashboards**: they dump numbers on you and assume you already know what to do with them. None of them take a beginner by the hand.

## What SellerCompass does differently

SellerCompass is **not a dashboard and not a plan generator**. It is a **guided, stage-gated pipeline** that walks a beginner from idea to a validated first product — and **won't let them advance until each step is backed by real data.**

1. **Evidence over opinion.** Every recommendation is grounded in live marketplace data — never the LLM's imagination.
2. **Gates, not a blank canvas.** You can't jump to "order inventory" until the demand and unit-economics gates pass.
3. **A co-founder, not a report.** The AI explains _why_, flags risks, and tells you to **pivot or kill** when the data says so.

## The 5 stages (v0 — Wildberries)

| # | Stage | What happens | Gate to pass |
|---|-------|--------------|--------------|
| 1 | **Discover** | Budget + interests + goals → candidate niches | — |
| 2 | **Validate demand** | Real search volume, sales of top players, trend direction | Demand above threshold & not declining |
| 3 | **Size up competition** | Density, price bands; NLP over competitor reviews surfaces _unmet needs_ | A real entry window exists |
| 4 | **Unit economics** | Purchase cost, logistics, fees, ads, price → margin, break-even, budget | Margin positive & realistic |
| 5 | **Decide** | Combined **Go / Pivot / Kill** verdict + first-batch plan + launch checklist | — |

Full spec of each gate: [METHODOLOGY.md](METHODOLOGY.md).

## Open-core

- **Open (this repo, MIT):** the methodology engine, the marketplace connectors, and a self-hostable local version — bring your own LLM key.
- **Cloud (planned):** pre-collected live **and historical** marketplace data, zero setup. The **data infrastructure is the moat** — not the algorithm.

## Quickstart

```bash
git clone https://github.com/DenisDrobyshev/sellercompass
cd sellercompass
cp .env.example .env          # add your LLM key; set WB_PROXY_URL if needed

# Option A — Docker (API + Postgres + Redis)
docker compose up --build     # -> http://localhost:8000/docs

# Option B — local Python
pip install -e ".[dev]"
uvicorn core.main:app --reload

# Smoke-test the httpx collector (fast, but WB may throttle the IP)
python -m core.collectors.wildberries "чехол для iphone"

# Collect real data with the browser spider (beats IP throttling) + store a snapshot
python -m core.collectors.wb_selenium "чехол для iphone"

# Stage 1 — mine candidate niches from a stored snapshot
python -m core.engine.discover --db "чехол для iphone"

# Validate demand from stored snapshots (trend appears once you have >= 2)
python -m core.engine.demand --db "чехол для iphone"
```

> **Heads-up on data.** Wildberries rate-limits IPs with HTTP 429 — even a browser's direct API calls. The **Selenium spider** sidesteps this: it drives a real Chrome, opens the search page like a person, and reads the product cards the page renders, so data flows even when the raw API is blocked. The httpx collector remains for fast API access with backoff, throttling, and `WB_PROXY_URL` support.

## Project layout

```
core/
  api/          FastAPI routes
  collectors/   Wildberries collectors — httpx API + Selenium browser spider
  engine/       stage-gate engine (Stage 2: demand + trend)
  models/       normalized data models
  storage/      snapshot persistence (SQLAlchemy)
tests/          unit tests (CI: ruff + pytest)
```

## Tech

Python · FastAPI · SQLAlchemy (SQLite / Postgres) · httpx · Selenium · Docker Compose. Planned: LLM orchestration + RAG over market data, and ML — demand forecasting, niche scoring, review NLP. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

🚧 **Early development.** In: the project skeleton, two Wildberries collectors (httpx + a Selenium browser spider that beats IP throttling), snapshot storage, **Stage 1 — Discover** (mines candidate niches from real listings), **Stage 2 — Validate demand** (with a trend gate), **Stage 3 — Competition** (brand concentration, price bands, entry-window gate), and **Stage 4 — Unit economics** (WB fee model, margin, first-batch plan). Next: Stage 5 — the Go / Pivot / Kill verdict. See the [ROADMAP.md](ROADMAP.md).

## Docs

- [METHODOLOGY.md](METHODOLOGY.md) — the stage-gate engine in detail
- [ARCHITECTURE.md](ARCHITECTURE.md) — stack, data pipeline, AI/ML layer
- [ROADMAP.md](ROADMAP.md) — where this is going

## License

[MIT](LICENSE) © 2026 Denis Drobyshev
