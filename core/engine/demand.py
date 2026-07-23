"""Stage 2 — Validate demand.

Turns a snapshot of the top marketplace products for a query into a demand
verdict. The gate passes when there is proven buying activity (reviews across
the top sellers) in a market that is not trivially thin, and demand is not
declining across snapshots.

Trend needs at least two historized snapshots; with a single snapshot the gate
uses the demand *level* only and reports the trend as unknown.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import log10

from core.engine.stages import GateResult, Stage
from core.models.product import Product

# Tunable gate thresholds — conservative defaults for a first pass.
DEFAULT_MIN_PRODUCTS = 10
DEFAULT_MIN_TOTAL_REVIEWS = 2000
TREND_BAND = 0.05  # +/-5% between first and last snapshot counts as "flat"


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 2)


@dataclass
class DemandMetrics:
    query: str
    products_analyzed: int
    total_reviews: int
    median_reviews: float | None
    reviewed_share: float           # fraction of products carrying any reviews
    price_median: float | None
    price_p25: float | None
    price_p75: float | None
    avg_rating: float | None


def analyze_demand(query: str, products: list[Product]) -> DemandMetrics:
    reviews = [p.reviews or 0 for p in products]
    prices = [p.price for p in products if p.price]
    ratings = [p.rating for p in products if p.rating]
    reviewed = [r for r in reviews if r > 0]
    return DemandMetrics(
        query=query,
        products_analyzed=len(products),
        total_reviews=sum(reviews),
        median_reviews=_percentile([float(r) for r in reviews], 0.5),
        reviewed_share=round(len(reviewed) / len(products), 2) if products else 0.0,
        price_median=_percentile(prices, 0.5),
        price_p25=_percentile(prices, 0.25),
        price_p75=_percentile(prices, 0.75),
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
    )


def demand_score(m: DemandMetrics) -> float:
    """0..1 — a log-scaled read of buying activity (~100k+ reviews approaches 1.0)."""
    if m.total_reviews <= 0:
        return 0.0
    return round(min(1.0, log10(m.total_reviews + 1) / 5), 2)


def compute_trend(totals: list[tuple[datetime, int]]) -> str:
    """Classify demand trend from (timestamp, total_reviews) snapshots, oldest first."""
    if len(totals) < 2:
        return "unknown"
    first, last = totals[0][1], totals[-1][1]
    if first <= 0:
        return "unknown"
    change = (last - first) / first
    if change > TREND_BAND:
        return "growing"
    if change < -TREND_BAND:
        return "declining"
    return "flat"


def trend_from_db(query: str) -> str:
    """Demand trend for a query, computed over products common to first/last snapshot."""
    from core.storage.repo import overlap_review_totals

    return compute_trend(overlap_review_totals(query))


def validate_demand(
    query: str,
    products: list[Product],
    *,
    min_products: int = DEFAULT_MIN_PRODUCTS,
    min_total_reviews: int = DEFAULT_MIN_TOTAL_REVIEWS,
    trend: str | None = None,
) -> GateResult:
    """Run the Stage 2 gate over a product snapshot and return a GateResult."""
    m = analyze_demand(query, products)
    reasons: list[str] = []
    passed = True

    if m.products_analyzed < min_products:
        passed = False
        reasons.append(
            f"only {m.products_analyzed} products found (need >= {min_products}) "
            "- market too thin, or the data source was blocked"
        )
    if m.total_reviews < min_total_reviews:
        passed = False
        reasons.append(
            f"{m.total_reviews} reviews across the top {m.products_analyzed} products "
            f"- weak buying signal (need >= {min_total_reviews})"
        )
    else:
        reasons.append(
            f"{m.total_reviews} reviews across the top {m.products_analyzed} products "
            "- real, active demand"
        )
    if m.price_median:
        reasons.append(
            f"price corridor ~ {m.price_p25}-{m.price_p75} RUB (median {m.price_median} RUB)"
        )

    level_ok = passed  # demand level cleared the thresholds, before the trend check

    if trend == "declining":
        passed = False
        reasons.append("demand is declining across snapshots - fails the 'not declining' gate")
    elif trend in ("growing", "flat"):
        reasons.append(f"trend across snapshots: {trend}")
    else:
        reasons.append(
            "trend not evaluated - needs >= 2 historized snapshots (run the spider over time)"
        )

    return GateResult(
        stage=Stage.VALIDATE_DEMAND,
        passed=passed,
        score=demand_score(m),
        reasons=reasons,
        evidence={**asdict(m), "trend": trend or "unknown", "level_ok": level_ok},
    )


async def _demo(query: str) -> None:
    import httpx

    from core.collectors.wildberries import WildberriesCollector

    try:
        async with WildberriesCollector() as wb:
            products = await wb.search(query, limit=100)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        print(f"\nData source error for {query!r}: HTTP {code}.")
        if code == 429:
            print("Wildberries throttled the request - retry from a residential/RU IP, "
                  "set WB_PROXY_URL, or use the Selenium spider (core.collectors.wb_selenium).")
        return
    result = validate_demand(query, products)
    _print_result(query, result, snapshots=1)


def _demo_db(query: str) -> None:
    from core.storage.repo import latest_snapshot, snapshot_totals_over_time

    products = latest_snapshot(query)
    if not products:
        print(f"No stored snapshot for {query!r}. Collect one first:")
        print(f'  python -m core.collectors.wb_selenium "{query}"')
        return
    snapshots = len(snapshot_totals_over_time(query))
    result = validate_demand(query, products, trend=trend_from_db(query))
    _print_result(query, result, snapshots=snapshots)


def _print_result(query: str, result: GateResult, *, snapshots: int) -> None:
    print(f"\nStage 2 . Validate demand - {query!r}")
    print(f"  verdict: {'PASS' if result.passed else 'FAIL'}   demand score: {result.score}")
    print(f"  based on {result.evidence.get('products_analyzed', 0)} products "
          f"across {snapshots} snapshot(s)")
    for r in result.reasons:
        print(f"   - {r}")


if __name__ == "__main__":
    import asyncio
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "--db":
        _demo_db(" ".join(argv[1:]) or "чехол для iphone")
    else:
        asyncio.run(_demo(" ".join(argv) or "чехол для iphone"))
