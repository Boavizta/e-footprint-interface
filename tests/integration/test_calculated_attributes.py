"""Integration tests for calculated attributes computation and chart data preparation.

Ported from tests__old/model_builder/test_views_calculated_attributes.py.
Dropped:
  - Django request/session scaffolding: replaced by ModelWeb(repository) directly.
  - HTTP status-code assertions: replaced by domain-level output assertions.
"""
import pytest
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities

from model_builder.domain.entities.efootprint_extensions.explainable_start_date import ExplainableStartDate
from model_builder.domain.entities.web_core.explainable_timeseries_utils import (
    prepare_timeseries_chart_context, prepare_hourly_quantity_data)
from model_builder.domain.entities.web_core.model_web import ModelWeb


def test_hourly_quantity_dict_attribute_produces_chart_data(minimal_repository):
    """Preparing chart data for one key of an ExplainableObjectDict attribute works."""
    model_web = ModelWeb(minimal_repository)
    for efootprint_obj in model_web.flat_efootprint_objs_dict.values():
        for attr_name in efootprint_obj.calculated_attributes:
            calc_attr = getattr(efootprint_obj, attr_name)
            if isinstance(calc_attr, ExplainableObjectDict):
                key = next(iter(calc_attr.keys()))
                context, _ = prepare_timeseries_chart_context(
                    model_web, efootprint_obj.id, attr_name, prepare_hourly_quantity_data, key.id)
                assert "data_timeseries" in context
                return
    pytest.skip("No ExplainableObjectDict attribute found in system")


def test_all_calculated_attributes_produce_valid_outputs(minimal_repository):
    """All calculated attributes on all objects can be accessed and produce valid domain outputs."""
    model_web = ModelWeb(minimal_repository)
    for efootprint_obj in model_web.flat_efootprint_objs_dict.values():
        container_id = efootprint_obj.id
        for attr_name in efootprint_obj.calculated_attributes:
            calc_attr = getattr(efootprint_obj, attr_name)
            if isinstance(calc_attr, ExplainableHourlyQuantities):
                context, _ = prepare_timeseries_chart_context(
                    model_web, container_id, attr_name, prepare_hourly_quantity_data)
                assert "data_timeseries" in context
            elif isinstance(calc_attr, (ExplainableQuantity, ExplainableStartDate)):
                web_obj = model_web.get_web_object_from_efootprint_id(container_id)
                explained_obj = getattr(web_obj, attr_name)
                literal_formula, ancestors = (
                    explained_obj.compute_literal_formula_and_ancestors_mapped_to_symbols_list())
                assert literal_formula is not None
            elif isinstance(calc_attr, ExplainableObjectDict):
                for key in calc_attr.keys():
                    context, _ = prepare_timeseries_chart_context(
                        model_web, container_id, attr_name, prepare_hourly_quantity_data, key.id)
                    assert "data_timeseries" in context
