"""Stage 5 — Decide.

The exit of the pipeline: combines the verdicts of Stages 2-4 into a single
Go / Pivot / Kill call, a concrete first-batch plan, and a launch checklist.

No gate — this is where the route ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from core.engine.competition import evaluate_competition
from core.engine.demand import validate_demand
from core.engine.stages import GateResult, Stage
from core.engine.unit_economics import evaluate_unit_economics
from core.models.product import Product

GO, PIVOT, KILL = "GO", "PIVOT", "KILL"

CHECKLIST = [
    "Order samples from 2-3 suppliers and compare quality",
    "Shoot your own photos - the card is the entire shopfront",
    "Write the card around the gap you found (title, bullets, keywords)",
    "Register as a seller and set up the WB account",
    "Ship the first batch to the warehouse closest to your buyers",
    "Budget the first month of ads separately from the batch",
]


@dataclass
class Decision:
    verdict: str
    query: str
    demand: GateResult
    competition: GateResult
    economics: GateResult
    plan: dict
    checklist: list[str]


def decide(
    query: str,
    products: list[Product],
    *,
    budget: float | None = None,
    trend: str | None = None,
) -> Decision:
    """Run the remaining gates over a snapshot and return a combined verdict."""
    demand = validate_demand(query, products, trend=trend)
    competition = evaluate_competition(query, products)
    prices = [p.price for p in products if p.price]
    economics = evaluate_unit_economics(
        query, median(prices) if prices else 0.0, budget=budget
    )

    if not demand.passed:
        verdict = KILL
    elif competition.passed and economics.passed:
        verdict = GO
    else:
        verdict = PIVOT

    e = economics.evidence
    plan = {
        "price": e.get("price"),
        "margin_per_unit": e.get("margin_per_unit"),
        "batch_units": e.get("batch_units"),
        "batch_investment": e.get("batch_investment"),
        "projected_profit": e.get("projected_profit"),
        "roi_pct": e.get("roi_pct"),
    }
    return Decision(verdict, query, demand, competition, economics, plan, CHECKLIST)


def to_gate_result(d: Decision) -> GateResult:
    """Flatten a Decision into the engine's GateResult shape."""
    reasons = [
        f"verdict: {d.verdict}",
        f"stage 2 demand:      {'PASS' if d.demand.passed else 'FAIL'} (score {d.demand.score})",
        f"stage 3 competition: {'PASS' if d.competition.passed else 'FAIL'} (score {d.competition.score})",
        f"stage 4 economics:   {'PASS' if d.economics.passed else 'FAIL'} (score {d.economics.score})",
    ]
    if d.verdict == KILL:
        reasons.append("no proven demand - do not spend money here")
    elif d.verdict == PIVOT:
        blockers = []
        if not d.competition.passed:
            blockers.append("the market has no entry window")
        if not d.economics.passed:
            blockers.append("the unit economics do not work")
        reasons.append(
            "demand exists, but " + " and ".join(blockers) + " - try an adjacent niche"
        )
    else:
        reasons.append("all gates pass - proceed with the first batch below")

    scores = [s for s in (d.demand.score, d.competition.score, d.economics.score) if s is not None]
    return GateResult(
        stage=Stage.DECIDE,
        passed=d.verdict == GO,
        score=round(sum(scores) / len(scores), 2) if scores else None,
        reasons=reasons,
        evidence={"verdict": d.verdict, "plan": d.plan, "checklist": d.checklist},
    )


def _print(d: Decision) -> None:
    result = to_gate_result(d)
    print(f"\nStage 5 . Decide - {d.query!r}")
    for reason in result.reasons:
        print(f"   {reason}")
    p = d.plan
    if p.get("batch_units"):
        print("\n  First-batch plan:")
        print(f"   price {p['price']} RUB | margin {p['margin_per_unit']} RUB/unit")
        print(f"   {p['batch_units']} units for {p['batch_investment']} RUB")
        print(f"   projected profit {p['projected_profit']} RUB (ROI {int((p['roi_pct'] or 0) * 100)}%)")
    if d.verdict != KILL:
        print("\n  Launch checklist:")
        for item in d.checklist:
            print(f"   [ ] {item}")


def _demo_db(query: str, budget: float | None) -> None:
    from core.engine.demand import compute_trend
    from core.storage.repo import latest_snapshot, snapshot_totals_over_time

    products = latest_snapshot(query)
    if not products:
        print(f"No stored snapshot for {query!r}. Crawl first:")
        print(f'  python -m core.collectors.wb_selenium "{query}"')
        return
    trend = compute_trend(snapshot_totals_over_time(query))
    _print(decide(query, products, budget=budget, trend=trend))


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "--db":
        argv = argv[1:]
    budget = None
    if len(argv) >= 2 and argv[-1].replace(".", "", 1).isdigit():
        budget = float(argv[-1])
        argv = argv[:-1]
    _demo_db(" ".join(argv) or "термокружка", budget)
