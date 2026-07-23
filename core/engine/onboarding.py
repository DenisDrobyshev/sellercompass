"""Onboarding — turn a seller profile into a ranked recommendation.

Collects the inputs the methodology assumes at Stage 1 (budget, interests,
goal) and runs the full pipeline over each interest, then ranks the results so
the strongest niche surfaces first. Verdict dominates the ordering, combined
score breaks ties.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.engine.decide import GO, KILL, PIVOT, to_gate_result
from core.engine.pipeline import PipelineReport, run_pipeline
from core.models.product import Product

_VERDICT_RANK = {GO: 2, PIVOT: 1, KILL: 0}


@dataclass
class SellerProfile:
    budget: float | None = None
    interests: list[str] = field(default_factory=list)
    goal: str = "side"        # "side" income or "main" business; captured for later tuning
    risk: str = "medium"      # "low", "medium" or "high"; captured for later tuning


def _combined_score(report: PipelineReport) -> float:
    return to_gate_result(report.decision).score or 0.0


def recommend(
    profile: SellerProfile,
    snapshots: dict[str, list[Product]],
    *,
    trends: dict[str, str] | None = None,
) -> list[PipelineReport]:
    """Run the pipeline over each interest that has a snapshot and rank the results."""
    trends = trends or {}
    reports = [
        run_pipeline(interest, products, budget=profile.budget, trend=trends.get(interest))
        for interest in profile.interests
        if (products := snapshots.get(interest))
    ]
    reports.sort(
        key=lambda report: (_VERDICT_RANK.get(report.decision.verdict, 0), _combined_score(report)),
        reverse=True,
    )
    return reports


def _print(profile: SellerProfile, reports: list[PipelineReport]) -> None:
    budget = f"{profile.budget:.0f} RUB" if profile.budget else "unset"
    print(f"\n=== Recommendation (budget {budget}) ===")
    for rank, report in enumerate(reports, start=1):
        score = to_gate_result(report.decision).score
        print(f"  {rank}. {report.query:<26} {report.decision.verdict:<6} combined score {score}")
    top = reports[0]
    print(f"\nStart with {top.query!r} ({top.decision.verdict}):")
    for reason in to_gate_result(top.decision).reasons[1:5]:
        print(f"   {reason}")


def _demo_db(interests: list[str], budget: float | None) -> None:
    from core.engine.demand import trend_from_db
    from core.storage.repo import latest_snapshot

    snapshots: dict[str, list[Product]] = {}
    trends: dict[str, str] = {}
    for interest in interests:
        products = latest_snapshot(interest)
        if products:
            snapshots[interest] = products
            trends[interest] = trend_from_db(interest)
    if not snapshots:
        print("No stored snapshots for these interests. Crawl them first, for example:")
        print(f'  python -m core.collectors.wb_selenium "{interests[0]}"')
        return
    profile = SellerProfile(budget=budget, interests=interests)
    _print(profile, recommend(profile, snapshots, trends=trends))


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    if argv and argv[0] == "--db":
        argv = argv[1:]
    budget = None
    if argv and argv[-1].replace(".", "", 1).isdigit():
        budget = float(argv[-1])
        argv = argv[:-1]
    _demo_db(argv or ["термокружка"], budget)
