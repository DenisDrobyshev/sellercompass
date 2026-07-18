"""Tests for Stage 4 (Unit economics) — pure logic, no network."""

from core.engine.stages import Stage
from core.engine.unit_economics import (
    MIN_MARGIN_PCT,
    compute_unit_economics,
    evaluate_unit_economics,
)


def test_healthy_price_passes():
    result = evaluate_unit_economics("q", 1000, budget=100000)
    assert result.stage == Stage.UNIT_ECONOMICS
    assert result.passed is True
    assert result.evidence["margin_per_unit"] > 0
    assert result.evidence["margin_pct"] >= MIN_MARGIN_PCT
    assert result.evidence["batch_units"] > 0
    assert result.evidence["projected_profit"] > 0


def test_low_price_negative_margin_fails():
    result = evaluate_unit_economics("q", 100)
    assert result.passed is False
    assert result.evidence["margin_per_unit"] < 0


def test_higher_cogs_reduces_margin():
    cheap = compute_unit_economics(1000, cogs=100)
    pricey = compute_unit_economics(1000, cogs=500)
    assert cheap.margin_per_unit > pricey.margin_per_unit


def test_tiny_budget_fails_batch():
    result = evaluate_unit_economics("q", 1000, budget=200)  # buys < 10 units
    assert result.evidence["batch_units"] < 10
    assert result.passed is False
