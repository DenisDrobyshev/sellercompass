"""Stage endpoints — run a pipeline stage over marketplace data."""

import httpx
from fastapi import APIRouter, Query

from core.collectors.wildberries import WildberriesCollector
from core.engine.competition import evaluate_competition
from core.engine.demand import validate_demand
from core.engine.discover import discover_from_products
from core.engine.unit_economics import evaluate_unit_economics
from core.storage.repo import latest_snapshot

router = APIRouter(prefix="/stages", tags=["stages"])


@router.get("/competition")
def competition(query: str = Query(..., min_length=2)) -> dict:
    """Stage 3 — size up competition from the latest stored snapshot."""
    products = latest_snapshot(query)
    if not products:
        return {
            "stage": "competition",
            "query": query,
            "passed": False,
            "note": f'no stored snapshot - crawl first: python -m core.collectors.wb_selenium "{query}"',
        }
    result = evaluate_competition(query, products)
    return {
        "stage": result.stage.value,
        "query": query,
        "passed": result.passed,
        "score": result.score,
        "reasons": result.reasons,
        "evidence": result.evidence,
    }


@router.get("/discover")
def discover(seed: str = Query(..., min_length=2), budget: float | None = None) -> dict:
    """Stage 1 — mine candidate niches from the latest stored snapshot of the seed."""
    products = latest_snapshot(seed)
    if not products:
        return {
            "stage": "discover",
            "seed": seed,
            "candidates": [],
            "note": f'no stored snapshot - crawl first: '
                    f'python -m core.collectors.wb_selenium "{seed}"',
        }
    niches = discover_from_products(seed, products, budget=budget)
    return {
        "stage": "discover",
        "seed": seed,
        "candidates": [
            {
                "query": n.query,
                "products": n.products,
                "price_median": n.price_median,
                "total_reviews": n.total_reviews,
            }
            for n in niches
        ],
    }


@router.get("/demand")
async def demand(query: str = Query(..., min_length=2), limit: int = 100) -> dict:
    """Stage 2 — validate demand for a query on live Wildberries data."""
    try:
        async with WildberriesCollector() as wb:
            products = await wb.search(query, limit=limit)
    except httpx.HTTPStatusError as exc:
        return {
            "stage": "validate_demand",
            "query": query,
            "passed": False,
            "score": 0.0,
            "reasons": [
                f"data source returned HTTP {exc.response.status_code} (Wildberries "
                "throttling) - retry from a residential/RU IP or set WB_PROXY_URL"
            ],
            "evidence": {},
        }
    result = validate_demand(query, products)
    return {
        "stage": result.stage.value,
        "query": query,
        "passed": result.passed,
        "score": result.score,
        "reasons": result.reasons,
        "evidence": result.evidence,
    }


@router.get("/economics")
def economics(
    query: str = Query(..., min_length=2),
    price: float | None = None,
    budget: float | None = None,
    cogs: float | None = None,
) -> dict:
    """Stage 4 — unit economics (price falls back to the stored snapshot median)."""
    if price is None:
        products = latest_snapshot(query)
        prices = sorted(p.price for p in products if p.price)
        if not prices:
            return {
                "stage": "unit_economics",
                "query": query,
                "passed": False,
                "note": f'no price - pass ?price= or crawl first: '
                        f'python -m core.collectors.wb_selenium "{query}"',
            }
        price = prices[len(prices) // 2]
    extra = {} if cogs is None else {"cogs": cogs}
    result = evaluate_unit_economics(query, price, budget=budget, **extra)
    return {
        "stage": result.stage.value,
        "query": query,
        "price": price,
        "passed": result.passed,
        "score": result.score,
        "reasons": result.reasons,
        "evidence": result.evidence,
    }
