"""Tests for onboarding recommendation ranking — pure logic, no network."""

from core.engine.decide import GO, KILL
from core.engine.onboarding import SellerProfile, recommend
from core.models.product import Product


def _p(reviews, rating, *, brand="B", name="термокружка стальная", price=1000):
    return Product(
        marketplace="wildberries", external_id=1, name=name,
        reviews=reviews, rating=rating, price=price, brand=brand,
    )


def test_ranks_go_above_pivot_above_kill():
    go = [_p(500, 4.2, brand=f"B{i}") for i in range(12)]
    pivot = [_p(100000, 4.2, brand="Giant")] + [_p(500, 4.2, brand=f"C{i}") for i in range(11)]
    kill = [_p(5, 4.2, brand=f"D{i}") for i in range(3)]
    snapshots = {"go_q": go, "pivot_q": pivot, "kill_q": kill}
    profile = SellerProfile(budget=100000, interests=["kill_q", "pivot_q", "go_q"])

    ranked = recommend(profile, snapshots)

    assert [r.query for r in ranked] == ["go_q", "pivot_q", "kill_q"]
    assert ranked[0].decision.verdict == GO
    assert ranked[-1].decision.verdict == KILL


def test_skips_interests_without_snapshots():
    profile = SellerProfile(budget=100000, interests=["missing"])
    assert recommend(profile, {}) == []
