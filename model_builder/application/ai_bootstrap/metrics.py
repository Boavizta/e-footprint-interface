"""Dated monetary factors and an explicit, unscaled parent-model impact estimate."""
import math

from .service import Completion

RATE_CARD_DATE = "2026-11-09"
IMPACT_PROVIDER = "mistralai"
IMPACT_MODEL = "zai-glm-5-3"


def _valid(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def estimate_call(completion: Completion) -> dict:
    metrics = {
        "latency_s": completion.latency_s, "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens, "cached_input_tokens": completion.cached_input_tokens,
        "cost_usd": None, "rate_card_date": RATE_CARD_DATE,
        "cache_discount_unknown": completion.cached_input_tokens is None,
        "impact_kg": None, "impact_provider": IMPACT_PROVIDER, "impact_model": IMPACT_MODEL,
    }
    prompt, output, cached = completion.input_tokens, completion.output_tokens, completion.cached_input_tokens
    if _valid(prompt) and _valid(output) and (cached is None or _valid(cached) and cached <= prompt):
        cached = cached or 0
        cost = ((prompt - cached) * 0.15 + cached * 0.03 + output * 0.50) / 1e6
        if _valid(cost):
            metrics["cost_usd"] = cost
    if not _valid(output) or not _valid(completion.latency_s):
        return metrics
    try:
        from ecologits.tracers.utils import llm_impacts
        value = llm_impacts(IMPACT_PROVIDER, IMPACT_MODEL, output, completion.latency_s).gwp.value
        if hasattr(value, "min") and hasattr(value, "max"):
            if _valid(value.min) and _valid(value.max) and value.min <= value.max:
                metrics["impact_kg"] = value
        elif _valid(value):
            metrics["impact_kg"] = value
    except Exception:
        pass  # Estimation evidence is optional; it must never reject a built modeling.
    return metrics
