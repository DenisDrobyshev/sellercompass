"""Stage 4 — Unit economics.

Turns a selling price (Stage 3's price corridor) into per-unit margin and a
first-batch plan, using a realistic Wildberries fee model. Every assumption is a
parameter with a sensible default, so a seller can plug in their own numbers.

Gate: margin is positive and realistic (>= MIN_MARGIN_PCT), and — if a budget is
given — it funds a viable first batch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median

from core.engine.stages import GateResult, Stage

# Defaults — rough but realistic WB economics; override per category / seller.
DEFAULT_COGS_RATE = 0.35        # purchase cost as a share of price, if not given
DEFAULT_COMMISSION_RATE = 0.20  # WB category commission
DEFAULT_LOGISTICS = 60.0        # WB logistics, RUB per unit
DEFAULT_ACQUIRING_RATE = 0.015  # payment acquiring
DEFAULT_AD_RATE = 0.12          # advertising share of revenue (ДРР)
DEFAULT_TAX_RATE = 0.07         # simplified tax on revenue (USN)

MIN_MARGIN_PCT = 0.10
MIN_BATCH_UNITS = 10


@dataclass
class UnitEconomics:
    price: float
    cogs: float
    commission: float
    logistics: float
    acquiring: float
    ad_cost: float
    tax: float
    payout: float              # what WB transfers per sale, before your own costs
    margin_per_unit: float
    margin_pct: float
    batch_units: int | None
    batch_investment: float | None
    projected_profit: float | None
    roi_pct: float | None


def compute_unit_economics(
    price: float,
    *,
    cogs: float | None = None,
    cogs_rate: float = DEFAULT_COGS_RATE,
    commission_rate: float = DEFAULT_COMMISSION_RATE,
    logistics: float = DEFAULT_LOGISTICS,
    acquiring_rate: float = DEFAULT_ACQUIRING_RATE,
    ad_rate: float = DEFAULT_AD_RATE,
    tax_rate: float = DEFAULT_TAX_RATE,
    budget: float | None = None,
) -> UnitEconomics:
    cogs = round(price * cogs_rate, 2) if cogs is None else cogs
    commission = round(price * commission_rate, 2)
    acquiring = round(price * acquiring_rate, 2)
    ad_cost = round(price * ad_rate, 2)
    tax = round(price * tax_rate, 2)
    payout = round(price - commission - logistics - acquiring, 2)
    margin = round(payout - cogs - ad_cost - tax, 2)
    margin_pct = round(margin / price, 3) if price else 0.0

    batch_units = batch_investment = projected_profit = roi_pct = None
    if budget is not None and cogs > 0:
        batch_units = int(budget // cogs)
        batch_investment = round(batch_units * cogs, 2)
        projected_profit = round(batch_units * margin, 2)
        roi_pct = round(projected_profit / batch_investment, 3) if batch_investment else None

    return UnitEconomics(
        price=round(price, 2), cogs=cogs, commission=commission, logistics=logistics,
        acquiring=acquiring, ad_cost=ad_cost, tax=tax, payout=payout,
        margin_per_unit=margin, margin_pct=margin_pct, batch_units=batch_units,
        batch_investment=batch_investment, projected_profit=projected_profit, roi_pct=roi_pct,
    )


def evaluate_unit_economics(
    query: str, price: float, *, budget: float | None = None, **assumptions: float
) -> GateResult:
    e = compute_unit_economics(price, budget=budget, **assumptions)
    reasons: list[str] = [
        f"price {e.price} - WB fees {round(e.commission + e.logistics + e.acquiring, 2)} "
        f"(commission {e.commission} + logistics {e.logistics} + acquiring {e.acquiring}) "
        f"= payout {e.payout}",
        f"payout {e.payout} - COGS {e.cogs} - ads {e.ad_cost} - tax {e.tax} "
        f"= margin {e.margin_per_unit}/unit ({int(e.margin_pct * 100)}%)",
    ]
    if e.batch_units is not None:
        reasons.append(
            f"budget buys ~{e.batch_units} units (invest {e.batch_investment}); "
            f"if it sells: profit {e.projected_profit} (ROI {int((e.roi_pct or 0) * 100)}%)"
        )

    passed = e.margin_per_unit > 0 and e.margin_pct >= MIN_MARGIN_PCT
    if e.margin_per_unit <= 0:
        reasons.append("negative margin - the numbers do not work at this price")
    elif e.margin_pct < MIN_MARGIN_PCT:
        reasons.append(
            f"margin {int(e.margin_pct * 100)}% is below the {int(MIN_MARGIN_PCT * 100)}% floor - too thin"
        )
    if e.batch_units is not None and e.batch_units < MIN_BATCH_UNITS:
        passed = False
        reasons.append(
            f"budget funds only {e.batch_units} units (< {MIN_BATCH_UNITS}) - too small to start"
        )

    return GateResult(
        stage=Stage.UNIT_ECONOMICS,
        passed=passed,
        score=max(0.0, min(1.0, round(e.margin_pct, 2))),
        reasons=reasons,
        evidence=asdict(e),
    )


def _print(query: str, price: float, result: GateResult) -> None:
    print(f"\nStage 4 . Unit economics - {query!r}  (price {price:.0f} RUB)")
    print(f"  verdict: {'PASS' if result.passed else 'FAIL'}   margin score: {result.score}")
    for reason in result.reasons:
        print(f"   - {reason}")


def _price_from(products: list) -> float | None:
    prices = [p.price for p in products if p.price]
    return median(prices) if prices else None


def _demo(query: str, budget: float | None) -> None:
    from core.collectors.wb_selenium import crawl

    price = _price_from(crawl(query))
    if price is None:
        print(f"No priced products for {query!r}.")
        return
    _print(query, price, evaluate_unit_economics(query, price, budget=budget))


def _demo_db(query: str, budget: float | None) -> None:
    from core.storage.repo import latest_snapshot

    products = latest_snapshot(query)
    if not products:
        print(f"No stored snapshot for {query!r}. Crawl first:")
        print(f'  python -m core.collectors.wb_selenium "{query}"')
        return
    price = _price_from(products)
    if price is None:
        print(f"Stored snapshot for {query!r} has no prices.")
        return
    _print(query, price, evaluate_unit_economics(query, price, budget=budget))


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    use_db = bool(argv) and argv[0] == "--db"
    if use_db:
        argv = argv[1:]
    budget = None
    if len(argv) >= 2 and argv[-1].replace(".", "", 1).isdigit():
        budget = float(argv[-1])
        argv = argv[:-1]
    seed = " ".join(argv) or "термокружка"
    (_demo_db if use_db else _demo)(seed, budget)
