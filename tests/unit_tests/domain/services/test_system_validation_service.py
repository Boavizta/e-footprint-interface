from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from model_builder.domain.services.system_validation_service import SystemValidationService


def _model_web(
    *, usage_patterns=(), edge_usage_patterns=(), usage_journeys=(), edge_usage_journeys=(), edge_functions=()
):
    model_web = MagicMock()
    model_web.system.usage_patterns = list(usage_patterns)
    model_web.system.edge_usage_patterns = list(edge_usage_patterns)
    model_web.usage_journeys = list(usage_journeys)
    model_web.edge_usage_journeys = list(edge_usage_journeys)
    model_web.edge_functions = list(edge_functions)
    return model_web


def _edge_usage_journey(name, *, edge_usage_patterns, edge_functions):
    return SimpleNamespace(
        name=name,
        edge_usage_patterns=list(edge_usage_patterns),
        edge_functions=list(edge_functions),
    )


def _edge_function(name, *, edge_usage_patterns, recurrent_edge_device_needs, recurrent_server_needs):
    return SimpleNamespace(
        name=name,
        edge_usage_patterns=list(edge_usage_patterns),
        recurrent_edge_device_needs=list(recurrent_edge_device_needs),
        recurrent_server_needs=list(recurrent_server_needs),
    )


class TestCheckEdgeUsageJourneysHaveFunctions:
    """Tests for SystemValidationService._check_edge_usage_journeys_have_functions."""

    def test_returns_none_when_no_edge_usage_journeys(self):
        result = SystemValidationService()._check_edge_usage_journeys_have_functions(_model_web())
        assert result is None

    def test_returns_none_when_journey_has_functions(self):
        euj = _edge_usage_journey("euj", edge_usage_patterns=["eup"], edge_functions=["ef"])
        result = SystemValidationService()._check_edge_usage_journeys_have_functions(
            _model_web(edge_usage_journeys=[euj]))
        assert result is None

    def test_ignores_journey_not_reached_from_any_pattern(self):
        euj = _edge_usage_journey("wip_euj", edge_usage_patterns=[], edge_functions=[])
        result = SystemValidationService()._check_edge_usage_journeys_have_functions(
            _model_web(edge_usage_journeys=[euj]))
        assert result is None

    def test_flags_journey_with_no_functions(self):
        euj = _edge_usage_journey("empty_euj", edge_usage_patterns=["eup"], edge_functions=[])
        result = SystemValidationService()._check_edge_usage_journeys_have_functions(
            _model_web(edge_usage_journeys=[euj]))
        assert result is not None
        assert result.affected_objects == ["empty_euj"]
        assert "empty_euj" in result.message
        assert "edge function" in result.message


class TestCheckEdgeFunctionsHaveNeeds:
    """Tests for SystemValidationService._check_edge_functions_have_needs."""

    def test_returns_none_when_no_edge_functions(self):
        result = SystemValidationService()._check_edge_functions_have_needs(_model_web())
        assert result is None

    def test_returns_none_when_edge_function_has_device_need(self):
        ef = _edge_function(
            "ef", edge_usage_patterns=["eup"], recurrent_edge_device_needs=["need"], recurrent_server_needs=[])
        result = SystemValidationService()._check_edge_functions_have_needs(
            _model_web(edge_functions=[ef]))
        assert result is None

    def test_returns_none_when_edge_function_has_server_need(self):
        ef = _edge_function(
            "ef", edge_usage_patterns=["eup"], recurrent_edge_device_needs=[], recurrent_server_needs=["need"])
        result = SystemValidationService()._check_edge_functions_have_needs(
            _model_web(edge_functions=[ef]))
        assert result is None

    def test_ignores_edge_function_not_reached_from_any_pattern(self):
        ef = _edge_function(
            "wip_ef", edge_usage_patterns=[], recurrent_edge_device_needs=[], recurrent_server_needs=[])
        result = SystemValidationService()._check_edge_functions_have_needs(
            _model_web(edge_functions=[ef]))
        assert result is None

    def test_flags_edge_function_with_no_needs(self):
        ef = _edge_function(
            "empty_ef", edge_usage_patterns=["eup"], recurrent_edge_device_needs=[], recurrent_server_needs=[])
        result = SystemValidationService()._check_edge_functions_have_needs(
            _model_web(edge_functions=[ef]))
        assert result is not None
        assert result.affected_objects == ["empty_ef"]
        assert "empty_ef" in result.message
        assert "edge device need or server need" in result.message

    def test_flags_multiple_edge_functions_with_no_needs(self):
        ef1 = _edge_function(
            "a", edge_usage_patterns=["eup"], recurrent_edge_device_needs=[], recurrent_server_needs=[])
        ef2 = _edge_function(
            "b", edge_usage_patterns=["eup"], recurrent_edge_device_needs=[], recurrent_server_needs=[])
        result = SystemValidationService()._check_edge_functions_have_needs(
            _model_web(edge_functions=[ef1, ef2]))
        assert result.affected_objects == ["a", "b"]


class TestValidateForComputationIntegratesEdgeCheck:
    """Sanity: validate_for_computation surfaces the edge-function error alongside others."""

    def test_returns_invalid_when_edge_function_has_no_needs(self):
        ef = _edge_function(
            "empty_ef", edge_usage_patterns=["eup"], recurrent_edge_device_needs=[], recurrent_server_needs=[])
        model_web = _model_web(edge_usage_patterns=["eup"], edge_functions=[ef])
        result = SystemValidationService().validate_for_computation(model_web)
        assert not result.is_valid
        assert any("empty_ef" in e.message for e in result.errors)

    def test_returns_valid_when_edge_function_has_needs(self):
        ef = _edge_function(
            "ef", edge_usage_patterns=["eup"], recurrent_edge_device_needs=["n"], recurrent_server_needs=[])
        model_web = _model_web(edge_usage_patterns=["eup"], edge_functions=[ef])
        result = SystemValidationService().validate_for_computation(model_web)
        assert result.is_valid
