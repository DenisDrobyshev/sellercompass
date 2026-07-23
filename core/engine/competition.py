"""Stage 3 — Size up competition.

Reads a niche's product snapshot and measures whether there is room to enter:
how concentrated the brands are, the price corridor, and where incumbents are
weak. "Weak incumbents" — popular products that buyers rate only so-so — are the
v0, data-grounded proxy for the unmet needs that become your angle.

`analyze_reviews` is the deeper review-NLP engine, ready to plug in once review
text is available (WB throttles the review API and hashes the review DOM — the
same data frontier the collectors already fight).

Gate: an entry window exists — the market is not saturated AND there is at least
one credible opening.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass

from core.engine.stages import GateResult, Stage
from core.models.product import Product

SATURATION_SHARE = 0.60     # top-3 brands owning > 60% of reviews = saturated
SOFT_SPOT_RATING = 4.4      # a popular product rated <= this is an opening
MIN_OPENING_REVIEWS = 200


def _pct(values: list[float], p: float) -> float | None:
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
class Opening:
    name: str
    rating: float | None
    reviews: int
    brand: str | None


@dataclass
class CompetitionMetrics:
    query: str
    products: int
    brands: int
    top3_brand_share: float     # share of total reviews held by the top 3 brands
    price_p25: float | None
    price_median: float | None
    price_p75: float | None
    avg_rating: float | None


def analyze_competition(query: str, products: list[Product]) -> CompetitionMetrics:
    reviews_by_brand: dict[str, int] = defaultdict(int)
    for p in products:
        reviews_by_brand[p.brand or p.seller or "?"] += p.reviews or 0
    total_reviews = sum(reviews_by_brand.values())
    top3 = sum(sorted(reviews_by_brand.values(), reverse=True)[:3])
    prices = [p.price for p in products if p.price]
    ratings = [p.rating for p in products if p.rating]
    return CompetitionMetrics(
        query=query,
        products=len(products),
        brands=len({p.brand for p in products if p.brand}),
        top3_brand_share=round(top3 / total_reviews, 2) if total_reviews else 0.0,
        price_p25=_pct(prices, 0.25),
        price_median=_pct(prices, 0.5),
        price_p75=_pct(prices, 0.75),
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
    )


def find_openings(products: list[Product], *, limit: int = 5) -> list[Opening]:
    """Popular-but-mediocre incumbents — buyers are lukewarm, so there is room."""
    soft = [
        p
        for p in products
        if p.rating is not None
        and p.rating <= SOFT_SPOT_RATING
        and (p.reviews or 0) >= MIN_OPENING_REVIEWS
    ]
    soft.sort(key=lambda p: p.reviews or 0, reverse=True)
    return [
        Opening(name=p.name[:60], rating=p.rating, reviews=p.reviews or 0, brand=p.brand)
        for p in soft[:limit]
    ]


def evaluate_competition(
    query: str, products: list[Product], *, voice: dict | None = None
) -> GateResult:
    m = analyze_competition(query, products)
    openings = find_openings(products)
    reasons: list[str] = []

    saturated = m.top3_brand_share > SATURATION_SHARE
    reasons.append(
        f"{m.brands} brands; top-3 brands hold {int(m.top3_brand_share * 100)}% of reviews"
        + (" - saturated" if saturated else " - not saturated")
    )
    if m.price_median:
        reasons.append(f"price corridor ~ {m.price_p25}-{m.price_p75} RUB (median {m.price_median})")
    if openings:
        reasons.append(
            f"{len(openings)} popular products rated <= {SOFT_SPOT_RATING} - room to do better:"
        )
        reasons.extend(
            f"    * {o.rating} stars, {o.reviews} reviews - {o.name}" for o in openings
        )
    else:
        reasons.append(
            f"no popular product rated <= {SOFT_SPOT_RATING} - leaders look strong; "
            "dig into reviews for a sharper angle"
        )

    if voice:
        aspects = voice.get("aspects") or []
        if aspects:
            reasons.append("buyers focus on: " + ", ".join(aspects))
        summary = voice.get("summary")
        if summary:
            reasons.append(f"WB review summary: {summary[:160]}")

    passed = (not saturated) and bool(openings)
    return GateResult(
        stage=Stage.COMPETITION,
        passed=passed,
        score=round(1 - m.top3_brand_share, 2),  # more fragmented = more entry room
        reasons=reasons,
        evidence={**asdict(m), "openings": [asdict(o) for o in openings], "voice": voice or {}},
    )


# --- Review NLP: the deeper unmet-needs engine (plug in a review feed later) ---

_STOP = {
    "и", "в", "на", "с", "не", "что", "но", "а", "по", "за", "к", "у", "из", "то",
    "это", "как", "для", "очень", "всё", "все", "так", "же", "бы", "мне", "меня",
}
_WORD = re.compile(r"[а-яёa-z]+", re.IGNORECASE)


def analyze_reviews(reviews: list[tuple[str, int]], *, top: int = 6) -> list[str]:
    """From (text, rating) pairs, surface recurring complaint themes in negatives.

    Pure and network-free. Consumes review text once a review feed is wired up.
    """
    counter: Counter[str] = Counter()
    for text, rating in reviews:
        if rating > 3 or not text:
            continue
        tokens = [w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 3]
        for i in range(len(tokens) - 1):
            counter[f"{tokens[i]} {tokens[i + 1]}"] += 1
    return [phrase for phrase, n in counter.most_common(top) if n >= 2]


def _print(query: str, result: GateResult, products: int) -> None:
    print(f"\nStage 3 . Competition - {query!r}  ({products} products)")
    print(f"  verdict: {'PASS' if result.passed else 'FAIL'}   entry-room score: {result.score}")
    for reason in result.reasons:
        print(f"   - {reason}")


def _demo(query: str) -> None:
    from core.collectors.wb_selenium import crawl

    products = crawl(query)
    if not products:
        print(f"No products for {query!r}.")
        return
    _print(query, evaluate_competition(query, products), len(products))


def _demo_db(query: str) -> None:
    from core.storage.repo import latest_snapshot

    products = latest_snapshot(query)
    if not products:
        print(f"No stored snapshot for {query!r}. Crawl first:")
        print(f'  python -m core.collectors.wb_selenium "{query}"')
        return
    _print(query, evaluate_competition(query, products), len(products))


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "--db":
        _demo_db(" ".join(argv[1:]) or "термокружка")
    else:
        _demo(" ".join(argv) or "термокружка")
