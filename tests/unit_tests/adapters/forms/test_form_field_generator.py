from types import SimpleNamespace
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES_DICT
from efootprint.constants.units import u

from model_builder.adapters.forms.form_field_generator import (
    build_dict_count_field_from_annotation, generate_dynamic_form, generate_select_multiple_field)
from model_builder.domain.all_efootprint_classes import MODELING_OBJECT_CLASSES_DICT
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class _StubReferencedAPI:
    """Minimal stand-in for an external-API object exposing the dotted-path attribute."""

    def __init__(self, obj_id: str, model_name: str):
        self.id = obj_id
        self.model_name = SourceObject(model_name)


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


class _SyntheticBoolClass(ModelingObject):
    default_values = {}
    list_values = {}
    conditional_list_values = {}

    def __init__(self, name: str, flag: SourceObject):
        pass


class _SyntheticCascadeClass(ModelingObject):
    default_values = {}
    list_values = {"provider": ["openai", "google"]}
    conditional_list_values = {
        "model_name": {
            "depends_on": "provider",
            "conditional_list_values": {
                SourceObject("openai"): [SourceObject("sora-2"), SourceObject("sora-2-pro")],
                SourceObject("google"): [SourceObject("veo-3")],
            },
        },
        "resolution": {
            "depends_on": "model_name",
            "conditional_list_values": {
                SourceObject("sora-2"): [SourceObject("720p"), SourceObject("1080p")],
                SourceObject("sora-2-pro"): [SourceObject("1080p"), SourceObject("4k")],
                SourceObject("veo-3"): [SourceObject("1080p")],
            },
        },
    }

    def __init__(self, name: str, provider: SourceObject, model_name: SourceObject, resolution: SourceObject):
        pass


def _register_synthetic_class(monkeypatch, cls):
    monkeypatch.setitem(MODELING_OBJECT_CLASSES_DICT, cls.__name__, cls)
    monkeypatch.setitem(EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING, cls.__name__, ModelingObjectWeb)
    monkeypatch.setitem(ALL_EFOOTPRINT_CLASSES_DICT, cls.__name__, cls)


@pytest.mark.parametrize("default_value", [True, False])
def test_generate_dynamic_form_emits_bool_input_type_for_boolean_source_object(
        monkeypatch, minimal_model_web, default_value):
    _register_synthetic_class(monkeypatch, _SyntheticBoolClass)
    default_values = {"name": "test", "flag": SourceObject(default_value)}

    fields, _, dynamic_lists = generate_dynamic_form(_SyntheticBoolClass.__name__, default_values, minimal_model_web)

    flag_field = _get_field_by_web_id(fields, f"{_SyntheticBoolClass.__name__}_flag")
    assert flag_field["input_type"] == "bool"
    assert flag_field["default"] is default_value
    assert dynamic_lists == []


# Guards the generator's per-field `dynamic_lists` emission: each conditional_list_values
# field emits its own one-hop entry keyed by its parent's values, so a multi-level cascade
# is just several stacked one-hop entries. (The real video feature splits its
# provider -> model -> resolution cascade across two forms, and dynamic_forms.js only
# propagates a single hop; this synthetic three-level class exercises the form-count-agnostic
# generator emission, not in-form chaining.) Regression net against a future "flattening" refactor.
def test_generate_dynamic_form_emits_chained_dynamic_lists_for_three_level_cascade(monkeypatch, minimal_model_web):
    _register_synthetic_class(monkeypatch, _SyntheticCascadeClass)
    default_values = {
        "name": "test",
        "provider": SourceObject("openai"),
        "model_name": SourceObject("sora-2-pro"),
        "resolution": SourceObject("1080p"),
    }

    fields, _, dynamic_lists = generate_dynamic_form(
        _SyntheticCascadeClass.__name__, default_values, minimal_model_web)

    # provider is in list_values -> select_str_input, no dynamic_lists entry
    provider_field = _get_field_by_web_id(fields, f"{_SyntheticCascadeClass.__name__}_provider")
    assert provider_field["input_type"] == "select_str_input"

    # model_name and resolution are both in conditional_list_values -> two datalist + two dynamic_lists entries
    model_name_field = _get_field_by_web_id(fields, f"{_SyntheticCascadeClass.__name__}_model_name")
    resolution_field = _get_field_by_web_id(fields, f"{_SyntheticCascadeClass.__name__}_resolution")
    assert model_name_field["input_type"] == "datalist"
    assert resolution_field["input_type"] == "datalist"

    by_input_id = {entry["input_id"]: entry for entry in dynamic_lists}
    model_name_entry = by_input_id[f"{_SyntheticCascadeClass.__name__}_model_name"]
    resolution_entry = by_input_id[f"{_SyntheticCascadeClass.__name__}_resolution"]

    assert model_name_entry["filter_by"] == f"{_SyntheticCascadeClass.__name__}_provider"
    assert resolution_entry["filter_by"] == f"{_SyntheticCascadeClass.__name__}_model_name"

    # Chained: resolution's list_value is keyed by model_name values (not by provider values).
    assert set(resolution_entry["list_value"].keys()) == {"sora-2", "sora-2-pro", "veo-3"}
    assert set(model_name_entry["list_value"].keys()) == {"openai", "google"}


class _SyntheticReferencedAPIClass(ModelingObject):
    default_values = {}
    list_values = {}
    conditional_list_values = {}

    def __init__(self, name: str):
        pass


class _SyntheticCrossObjectJobClass(ModelingObject):
    """A Job-like class whose `resolution` depends on a sub-attribute of a referenced object."""
    default_values = {"resolution": SourceObject("720p")}
    list_values = {}
    conditional_list_values = {
        "resolution": {
            "depends_on": "external_api.model_name",
            "conditional_list_values": {
                SourceObject("model-a"): [SourceObject("720p"), SourceObject("1080p")],
                SourceObject("model-b"): [SourceObject("4k")],
            },
        },
    }

    def __init__(self, name: str, external_api: _SyntheticReferencedAPIClass, resolution: SourceObject):
        pass


class _SyntheticCrossObjectJobWeb(ModelingObjectWeb):
    # `external_api` is chosen via a helper field, not rendered as its own select.
    attributes_to_skip_in_forms = ["external_api"]
    conditional_list_filter_overrides = {"external_api": "service_or_external_api"}


# Guards the generator's cross-object dotted-`depends_on` handling: a `resolution` field keyed on
# `external_api.model_name` (where `external_api` is skipped in the form and selected via a helper)
# is emitted as a single-hop datalist filtered by the helper id and re-keyed by available API object
# id, so the existing one-hop cascade applies with no extra JS.
def test_generate_dynamic_form_rekeys_cross_object_conditional_by_referenced_object_id(
        monkeypatch, minimal_model_web):
    monkeypatch.setitem(
        MODELING_OBJECT_CLASSES_DICT, _SyntheticReferencedAPIClass.__name__, _SyntheticReferencedAPIClass)
    monkeypatch.setitem(
        ALL_EFOOTPRINT_CLASSES_DICT, _SyntheticReferencedAPIClass.__name__, _SyntheticReferencedAPIClass)
    monkeypatch.setitem(
        MODELING_OBJECT_CLASSES_DICT, _SyntheticCrossObjectJobClass.__name__, _SyntheticCrossObjectJobClass)
    monkeypatch.setitem(
        ALL_EFOOTPRINT_CLASSES_DICT, _SyntheticCrossObjectJobClass.__name__, _SyntheticCrossObjectJobClass)
    monkeypatch.setitem(
        EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING, _SyntheticCrossObjectJobClass.__name__,
        _SyntheticCrossObjectJobWeb)

    api_objects = [_StubReferencedAPI("api_1", "model-a"), _StubReferencedAPI("api_2", "model-b")]
    monkeypatch.setattr(
        minimal_model_web, "get_efootprint_objects_from_efootprint_type",
        lambda obj_type: api_objects if obj_type == _SyntheticReferencedAPIClass.__name__ else [])

    default_values = {"name": "test", "resolution": SourceObject("720p")}
    fields, _, dynamic_lists = generate_dynamic_form(
        _SyntheticCrossObjectJobClass.__name__, default_values, minimal_model_web)

    # external_api is skipped; resolution renders as a datalist.
    resolution_field = _get_field_by_web_id(fields, f"{_SyntheticCrossObjectJobClass.__name__}_resolution")
    assert resolution_field["input_type"] == "datalist"
    assert all(
        field["web_id"] != f"{_SyntheticCrossObjectJobClass.__name__}_external_api" for field in fields)

    assert len(dynamic_lists) == 1
    entry = dynamic_lists[0]
    assert entry["input_id"] == f"{_SyntheticCrossObjectJobClass.__name__}_resolution"
    # The cross-object hop collapses onto the helper that carries the API selection,
    assert entry["filter_by"] == "service_or_external_api"
    # and the list is keyed by available API object id, each mapping to that API's model's resolutions.
    assert entry["list_value"] == {"api_1": ["720p", "1080p"], "api_2": ["4k"]}
