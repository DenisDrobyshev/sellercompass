"""Tests for Stage 3 (Competition) — pure logic, no network."""

from core.engine.competition import (
    analyze_reviews,
    evaluate_competition,
    find_openings,
)
from core.engine.stages import Stage
from core.models.product import Product


def _p(reviews, rating, *, price=500, brand="B", name="товар"):
    return Product(
        marketplace="wildberries", external_id=1, name=name,
        reviews=reviews, rating=rating, price=price, brand=brand,
    )


def test_saturated_market_fails_gate():
    products = [_p(10000, 4.9, brand="Giant")] + [_p(10, 4.9, brand=f"B{i}") for i in range(10)]
    result = evaluate_competition("q", products)
    assert result.stage == Stage.COMPETITION
    assert result.passed is False  # one brand owns the reviews


def test_open_market_with_soft_spot_passes():
    products = [_p(1000, 4.2, brand=f"B{i}") for i in range(8)] + [_p(1500, 4.1, brand="B9")]
    result = evaluate_competition("q", products)
    assert result.passed is True
    assert result.evidence["openings"]


def test_find_openings_flags_popular_mediocre():
    products = [
        _p(2000, 4.1, name="lukewarm leader"),
        _p(2000, 4.9, name="loved leader"),
        _p(5, 3.0, name="unpopular"),
    ]
    names = [o.name for o in find_openings(products)]
    assert "lukewarm leader" in names
    assert "loved leader" not in names   # rating too high
    assert "unpopular" not in names       # too few reviews


def test_voice_enriches_reasons():
    products = [_p(1000, 4.2, brand=f"B{i}") for i in range(10)]
    result = evaluate_competition(
        "q", products, voice={"aspects": ["Качество", "Удобство"], "summary": "buyers like it"}
    )
    joined = " ".join(result.reasons)
    assert "Качество" in joined
    assert "buyers like it" in joined
    assert result.evidence["voice"]["aspects"] == ["Качество", "Удобство"]


def test_analyze_reviews_surfaces_recurring_complaints():
    reviews = [
        ("Крышка протекает, ужасная крышка", 2),
        ("крышка протекает постоянно", 1),
        ("отличная вещь, всем советую", 5),
        ("снова протекает крышка", 2),
    ]
    themes = analyze_reviews(reviews)
    assert any("крышка протекает" in t for t in themes)
