"""Tests for Stage 5 (Decide) — pure logic, no network."""

from core.engine.decide import GO, KILL, PIVOT, decide, to_gate_result
from core.engine.stages import Stage
from core.models.product import Product


def _p(reviews, rating, *, price=1000, brand="B", name="товар"):
    return Product(
        marketplace="wildberries", external_id=1, name=name,
        reviews=reviews, rating=rating, price=price, brand=brand,
    )


def test_all_gates_pass_gives_go():
    products = [_p(500, 4.2, brand=f"B{i}") for i in range(12)]
    d = decide("q", products, budget=100000)
    assert d.verdict == GO
    result = to_gate_result(d)
    assert result.stage == Stage.DECIDE
    assert result.passed is True
    assert result.evidence["plan"]["batch_units"] > 0


def test_no_demand_gives_kill():
    products = [_p(10, 4.2, brand=f"B{i}") for i in range(3)]
    d = decide("q", products, budget=100000)
    assert d.verdict == KILL
    assert to_gate_result(d).passed is False


def test_demand_but_saturated_market_gives_pivot():
    products = [_p(100000, 4.2, brand="Giant")] + [_p(500, 4.2, brand=f"B{i}") for i in range(11)]
    d = decide("q", products, budget=100000)
    assert d.demand.passed is True
    assert d.competition.passed is False
    assert d.verdict == PIVOT
