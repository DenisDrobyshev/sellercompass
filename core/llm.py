"""Optional LLM explanation layer.

The pipeline decides; the language model only explains. Given a finished
Decision, this produces a plain-language summary grounded strictly in the numbers
the gates already computed. It is optional: with no API key configured it returns
a deterministic template, so the product runs fully offline. When a key is set it
calls Claude (bring your own key) with the gate evidence and an instruction to
reason only from those numbers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.config import get_settings

if TYPE_CHECKING:
    from core.engine.decide import Decision

DEFAULT_MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You are an analyst assistant for a marketplace-seller tool. You are given a "
    "product-niche verdict and the exact numbers behind it. Explain the verdict to a "
    "beginning seller in three to five plain sentences. Use only the numbers provided; "
    "do not invent data, prices, or competitors. Be direct and practical."
)


def _brief(decision: Decision) -> str:
    """A compact, factual summary of the decision for the model to explain."""
    from core.engine.decide import to_gate_result

    result = to_gate_result(decision)
    lines = [f"Query: {decision.query}", f"Verdict: {decision.verdict}"]
    for gate in (decision.demand, decision.competition, decision.economics):
        lines.append(
            f"- {gate.stage.value}: {'PASS' if gate.passed else 'FAIL'} (score {gate.score})"
        )
    lines.append("Reasons:")
    lines.extend(f"  {r}" for r in result.reasons if not r.startswith("verdict"))
    plan = decision.plan
    if plan.get("batch_units"):
        lines.append(
            f"First-batch plan: {plan['batch_units']} units at price {plan['price']} RUB, "
            f"invest {plan['batch_investment']} RUB, projected profit {plan['projected_profit']} "
            f"RUB (ROI {int((plan['roi_pct'] or 0) * 100)}%)."
        )
    return "\n".join(lines)


def _template(decision: Decision) -> str:
    """Deterministic explanation used when no LLM key is configured."""
    query, verdict = decision.query, decision.verdict
    if verdict == "KILL":
        return (
            f"{query!r}: not worth pursuing. Demand is too weak to build a business on, so "
            "there is no point spending on inventory here. Look for a niche people actively buy."
        )
    if verdict == "GO":
        plan = decision.plan
        tail = ""
        if plan.get("batch_units"):
            tail = (
                f" A first batch of about {plan['batch_units']} units "
                f"(~{plan['batch_investment']} RUB) could return roughly "
                f"{int((plan['roi_pct'] or 0) * 100)}% if it sells through."
            )
        return (
            f"{query!r}: worth starting. Demand is proven, the market has room to enter, and "
            f"the unit economics clear the margin floor.{tail}"
        )
    blockers = []
    if not decision.demand.passed:
        blockers.append("demand is slipping")
    if not decision.competition.passed:
        blockers.append("a few brands dominate the market")
    if not decision.economics.passed:
        blockers.append("the margins do not work at the current price")
    reason = "; ".join(blockers) or "one of the gates did not pass"
    return (
        f"{query!r}: demand is real, but {reason}. Rather than fighting that head-on, pivot to "
        "an adjacent niche (see the Discover candidates) and re-check it."
    )


def explain_decision(decision: Decision, *, settings=None, client=None) -> str:
    """Return a plain-language explanation of a Decision.

    Uses Claude when an LLM key is configured (bring your own key); otherwise
    returns a deterministic template. Any error falls back to the template, so the
    caller always gets a usable string.
    """
    settings = settings or get_settings()
    if client is None and not settings.llm_api_key:
        return _template(decision)
    try:
        return _llm_explain(decision, settings, client) or _template(decision)
    except Exception:
        return _template(decision)


def _llm_explain(decision: Decision, settings, client) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.llm_api_key)
    message = client.messages.create(
        model=settings.llm_model or DEFAULT_MODEL,
        max_tokens=600,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _brief(decision)}],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    ).strip()
