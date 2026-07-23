"""Full pipeline — run every stage over one snapshot and assemble a report.

This is the product-level entry point. One call takes a stored snapshot and
returns the combined Go / Pivot / Kill decision together with the Stage 1
candidate niches, so a user does not have to invoke the five stages by hand.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.engine.decide import Decision, decide, to_gate_result
from core.engine.discover import CandidateNiche, discover_from_products
from core.models.product import Product


@dataclass
class PipelineReport:
    query: str
    decision: Decision
    candidates: list[CandidateNiche]


def run_pipeline(
    query: str,
    products: list[Product],
    *,
    budget: float | None = None,
    trend: str | None = None,
) -> PipelineReport:
    """Run Stages 1-5 over a snapshot and return the assembled report."""
    decision = decide(query, products, budget=budget, trend=trend)
    candidates = discover_from_products(query, products, budget=budget)
    return PipelineReport(query=query, decision=decision, candidates=candidates)


def _print(report: PipelineReport) -> None:
    decision = report.decision
    result = to_gate_result(decision)
    print(f"\n=== SellerHelper pipeline: {report.query!r} ===")
    print(f"verdict: {result.evidence['verdict']}   (combined score {result.score})")
    for reason in result.reasons:
        print(f"   {reason}")
    plan = decision.plan
    if plan.get("batch_units"):
        print("\n  First-batch plan:")
        print(f"   price {plan['price']} RUB | margin {plan['margin_per_unit']} RUB/unit")
        print(
            f"   {plan['batch_units']} units for {plan['batch_investment']} RUB "
            f"(ROI {int((plan['roi_pct'] or 0) * 100)}%)"
        )
    if report.candidates:
        print("\n  Adjacent niches to consider (Stage 1):")
        for c in report.candidates[:6]:
            price = f"{c.price_median:.0f} RUB" if c.price_median else "-"
            print(f"   - {c.query:<32} x{c.products:<3} median {price:<10} reviews {c.total_reviews}")


def _demo_db(query: str, budget: float | None) -> None:
    from core.engine.demand import trend_from_db
    from core.storage.repo import latest_snapshot

    products = latest_snapshot(query)
    if not products:
        print(f"No stored snapshot for {query!r}. Crawl first:")
        print(f'  python -m core.collectors.wb_selenium "{query}"')
        return
    _print(run_pipeline(query, products, budget=budget, trend=trend_from_db(query)))


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
