from types import SimpleNamespace
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u

from model_builder.adapters.forms.form_field_generator import (
    build_dict_count_field_from_annotation, generate_dynamic_form, generate_select_multiple_field)


def _get_field_by_web_id(fields: list[dict], web_id: str) -> dict:
    return next(field for field in fields if field["web_id"] == web_id)


def test_select_multiple_field_is_hidden_when_nothing_to_pick_and_nothing_selected():
    model_web = MagicMock()
    model_web.get_efootprint_objects_from_efootprint_type.return_value = []

    field = generate_select_multiple_field(
        "recurrent_server_needs", "EdgeFunction", [], "RecurrentServerNeed", model_web)

    assert field["selected"] == []
    assert field["unselected"] == []
    assert field["hide_field"] is True


def test_select_multiple_field_is_shown_when_options_are_available():
    option = SimpleNamespace(id="opt1", name="Option 1")
    model_web = MagicMock()
    model_web.get_efootprint_objects_from_efootprint_type.return_value = [option]

    field = generate_select_multiple_field(
        "recurrent_server_needs", "EdgeFunction", [], "RecurrentServerNeed", model_web)

    assert field["unselected"] == [{"value": "opt1", "label": "Option 1"}]
    assert field["hide_field"] is False


def test_dict_count_field_is_hidden_when_no_options_and_nothing_selected():
    model_web = MagicMock()
    model_web.get_web_objects_from_efootprint_type.return_value = []

    field = build_dict_count_field_from_annotation(
        "uj_steps", "UsageJourney", "UsageJourneyStep", {}, model_web)

    assert field["options"] == []
    assert field["hide_field"] is True


def test_generate_dynamic_form_preserves_imported_decimal_precision(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    server.power = ExplainableQuantity(250.37 * u.W, label="power")

    _, advanced_fields, _ = generate_dynamic_form("Server", server.__dict__, minimal_model_web)

    power_field = _get_field_by_web_id(advanced_fields, "Server_power")

    assert power_field["default"] == "250.37"
    assert power_field["step"] == "0.01"


def test_generate_dynamic_form_keeps_integer_step_for_integral_values(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    server.power = ExplainableQuantity(250 * u.W, label="power")

    _, advanced_fields, _ = generate_dynamic_form("Server", server.__dict__, minimal_model_web)

    power_field = _get_field_by_web_id(advanced_fields, "Server_power")

    assert power_field["default"] == "250"
    assert power_field["step"] == "1"


def test_generate_dynamic_form_builds_weighted_dict_fields_with_count_wording(minimal_model_web):
    journey = minimal_model_web.usage_journeys[0].modeling_obj
    fields, _, _ = generate_dynamic_form("UsageJourney", journey.__dict__, minimal_model_web)
    uj_steps_field = _get_field_by_web_id(fields, "UsageJourney_uj_steps")
    assert uj_steps_field["input_type"] == "dict_count"
    assert uj_steps_field["count_label"] == "Times per journey"

    step = next(iter(journey.uj_steps))
    fields, _, _ = generate_dynamic_form("UsageJourneyStep", step.__dict__, minimal_model_web)
    jobs_field = _get_field_by_web_id(fields, "UsageJourneyStep_jobs")
    assert jobs_field["input_type"] == "dict_count"
    assert jobs_field["count_label"] == "Times per step"


def test_generate_dynamic_form_dict_field_selected_json_preserves_journey_order(minimal_model_web):
    import json

    from efootprint.abstract_modeling_classes.source_objects import SourceValue
    from efootprint.constants.units import u as units
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep

    journey = minimal_model_web.usage_journeys[0].modeling_obj
    extra_step = UsageJourneyStep.from_defaults("Aardvark step", jobs={})
    journey.uj_steps[extra_step] = SourceValue(2 * units.dimensionless)

    fields, _, _ = generate_dynamic_form("UsageJourney", journey.__dict__, minimal_model_web)
    uj_steps_field = _get_field_by_web_id(fields, "UsageJourney_uj_steps")

    selected = json.loads(uj_steps_field["selected_json"])
    assert list(selected) == [step.id for step in journey.uj_steps]
    assert list(selected)[-1] == extra_step.id
    assert selected[extra_step.id] == 2
