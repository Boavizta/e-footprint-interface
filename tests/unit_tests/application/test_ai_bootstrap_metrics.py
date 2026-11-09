from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from model_builder.application.ai_bootstrap.metrics import estimate_call
from model_builder.application.ai_bootstrap.service import Completion


def estimator(monkeypatch, value):
    stub = Mock(return_value=NS(gwp=NS(value=value)))
    monkeypatch.setattr("ecologits.tracers.utils.llm_impacts", stub)
    return stub


@pytest.mark.parametrize("value", [0.001, NS(min=0.001, max=0.003)])
def test_parent_estimate_preserves_scalar_or_range_and_actual_output_total(monkeypatch, value):
    stub = estimator(monkeypatch, value)
    result = estimate_call(Completion("", 1000, 2000, None, 10))
    stub.assert_called_once_with("mistralai", "zai-glm-5-3", 2000, 10)
    assert result["impact_kg"] is value
    assert result["cost_usd"] == pytest.approx(0.00115)
    assert result["cache_discount_unknown"]


def test_known_cache_count_uses_discount(monkeypatch):
    estimator(monkeypatch, 1)
    result = estimate_call(Completion("", 1000, 2000, 800, 10))
    assert result["cost_usd"] == pytest.approx(0.001054)
    assert not result["cache_discount_unknown"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, NS(min=1, max=float("inf")), None])
def test_invalid_estimator_evidence_is_unavailable(monkeypatch, value):
    estimator(monkeypatch, value)
    assert estimate_call(Completion("", 100, 200, None, 10))["impact_kg"] is None


def test_missing_usage_and_estimation_failure_are_unavailable(monkeypatch):
    stub = estimator(monkeypatch, 1)
    result = estimate_call(Completion(""))
    assert result["cost_usd"] is result["impact_kg"] is None
    stub.assert_not_called()
    stub.side_effect = RuntimeError("estimator failed")
    result = estimate_call(Completion("", 100, 200, None, 10))
    assert result["impact_kg"] is None
    assert result["cost_usd"] is not None
