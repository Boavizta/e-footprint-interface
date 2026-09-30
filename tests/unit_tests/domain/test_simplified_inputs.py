from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob,
)
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent

from model_builder.adapters.forms.timeseries_builder_registry import (
    EDITABLE_TIMESERIES_BUILDERS, can_edit_timeseries, find_editable_builder,
)
from model_builder.domain.conditional_inputs import resolve_input_path
from model_builder.domain.services.simplified_inputs import (
    FieldAddress, build_catalog, complete_selection, normalize_definition, validate_definition,
)
from model_builder.version_upgrade_handlers import upgrade_interface_config


def _catalog(model_web):
    return build_catalog(model_web, can_edit_timeseries=can_edit_timeseries)


def _definition(selected, *, excluded=()):
    fields = {}
    for address in selected:
        fields.setdefault(address.object_id, {})[address.attribute] = {"included": True, "help": "Keep My Capitals"}
    for address in excluded:
        fields.setdefault(address.object_id, {})[address.attribute] = {"included": False, "help": "Retained Help"}
    return {"title": "Adapt Me", "guidance": "Keep This Guidance", "fields": fields}


def test_catalog_distinguishes_reference_selectors_and_structural_inputs(minimal_model_web):
    catalog = _catalog(minimal_model_web)
    usage = minimal_model_web.usage_patterns[0].modeling_obj
    server = minimal_model_web.servers[0].modeling_obj
    storage = server.storage
    job = minimal_model_web.jobs[0].modeling_obj
    for owner, attribute in [(usage, "country"), (usage, "network"), (usage, "devices"),
                             (usage, "hourly_occurrences"), (server, "lifespan"), (storage, "storage_capacity")]:
        assert catalog.fields[FieldAddress(owner.id, attribute)].eligible
    for owner, attribute in [(usage, "usage_journeys"), (usage, "name"), (server, "storage"), (job, "server"),
                             (usage.country, "average_carbon_intensity"), (usage.network, "bandwidth_energy_intensity"),
                             (usage.devices[0], "power")]:
        assert not catalog.fields[FieldAddress(owner.id, attribute)].eligible
    owner, attribute = resolve_input_path(server, "storage.storage_capacity")
    assert owner is storage
    assert FieldAddress(owner.id, attribute) in catalog.fields
    assert FieldAddress(server.id, "storage_capacity") not in catalog.fields


def test_optional_empty_numbers_and_server_count_companion_are_eligible(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    assert isinstance(server.fixed_nb_of_instances, EmptyExplainableObject)
    cpu = EdgeCPUComponent.from_defaults("Empty CPU", nb_of_units=EmptyExplainableObject())
    minimal_model_web.flat_efootprint_objs_dict[cpu.id] = cpu
    catalog = _catalog(minimal_model_web)
    count = FieldAddress(server.id, "fixed_nb_of_instances")
    kind = FieldAddress(server.id, "server_type")
    assert catalog.fields[count].eligible
    assert catalog.fields[FieldAddress(cpu.id, "nb_of_units")].eligible
    assert complete_selection(catalog, {kind}) == {kind, count}


def test_timeseries_support_uses_current_builder_without_initializing_drafts(minimal_model_web):
    usage = minimal_model_web.usage_patterns[0].modeling_obj
    address = FieldAddress(usage.id, "hourly_occurrences")
    initializer = Mock(side_effect=AssertionError)
    builder = replace(EDITABLE_TIMESERIES_BUILDERS[ExplainableHourlyQuantities][0], default_inputs=initializer)
    with patch.dict(EDITABLE_TIMESERIES_BUILDERS, {ExplainableHourlyQuantities: (builder,)}):
        assert find_editable_builder(ExplainableHourlyQuantities, usage.hourly_occurrences)
        assert _catalog(minimal_model_web).fields[address].eligible
    usage._set_input_passively("hourly_occurrences", ExplainableHourlyQuantities(
        usage.hourly_occurrences.value, usage.hourly_occurrences.start_date, label="Read-only hourly values"))
    initializer.assert_not_called()
    assert not _catalog(minimal_model_web).fields[address].eligible
    assert not can_edit_timeseries(ExplainableRecurrentQuantities, object())


def test_real_cross_owner_chain_includes_every_linked_jobs_resolution(minimal_model_web):
    api = EcoLogitsVideoGenExternalAPI.from_defaults("Video API")
    jobs = [EcoLogitsVideoGenExternalAPIJob.from_defaults(name, external_api=api)
            for name in ("Video A", "Video B")]
    for owner in [api, *jobs]:
        minimal_model_web.flat_efootprint_objs_dict[owner.id] = owner
    catalog = _catalog(minimal_model_web)
    provider = FieldAddress(api.id, "provider")
    model = FieldAddress(api.id, "model_name")
    resolutions = {FieldAddress(job.id, "resolution") for job in jobs}
    assert complete_selection(catalog, {provider}) == {provider, model, *resolutions}
    assert complete_selection(catalog, {model}) == {model, *resolutions}
    assert complete_selection(catalog, {next(iter(resolutions))}) == {next(iter(resolutions))}
    for job in jobs:
        assert catalog.fields[FieldAddress(job.id, "resolution")].controller == model
        assert not catalog.fields[FieldAddress(job.id, "external_api")].eligible
        assert not catalog.fields[FieldAddress(job.id, "with_audio")].eligible
    definition = _definition(complete_selection(catalog, {provider}))
    assert validate_definition(catalog, definition) == definition
    incomplete = _definition({provider, model}, excluded=resolutions)
    with pytest.raises(ValueError, match="Required inputs.*resolution"):
        validate_definition(catalog, incomplete)


class ConditionalInputs(ModelingObject):
    list_values = {"provider": [SourceObject("provider")]}
    conditional_list_values = {
        "model": {"depends_on": "provider", "conditional_list_values": {}},
        "unsupported": {"depends_on": "model", "conditional_list_values": {}},
    }

    def __init__(
        self, name: str, provider: ExplainableObject, model: ExplainableObject, unsupported: ExplainableObject
    ):
        super().__init__(name)
        self.provider = provider
        self.model = model
        self.unsupported = unsupported


def test_ineligible_required_input_propagates_to_all_controllers():
    owner = ConditionalInputs("Conditional", SourceObject("provider"), SourceObject("model"), SourceObject(False))
    catalog = _catalog(SimpleNamespace(flat_efootprint_objs_dict={owner.id: owner}))
    provider = FieldAddress(owner.id, "provider")
    model = FieldAddress(owner.id, "model")
    assert not catalog.fields[model].eligible
    assert not catalog.fields[provider].eligible
    assert "unsupported" in catalog.fields[provider].reason
    with pytest.raises(ValueError, match="cannot be included"):
        complete_selection(catalog, {provider})


def test_empty_definition_is_independent_and_adds_no_values():
    assert normalize_definition() == normalize_definition({}) == {"title": "", "guidance": "", "fields": {}}
    original = _definition({FieldAddress("owner", "lifespan")})
    normalized = normalize_definition(original)
    normalized["fields"]["owner"]["lifespan"]["help"] = "Changed"
    assert original["fields"]["owner"]["lifespan"]["help"] == "Keep My Capitals"


@pytest.mark.parametrize("definition, message", [
    ([], "must be an object"), ({"title": 1}, "title must be text"),
    ({"guidance": False}, "guidance must be text"),
    ({"values": {}}, "only title, guidance, and fields"), ({"fields": []}, "fields must map"),
    ({"fields": {"missing-owner": {"lifespan": {"included": True, "help": ""}}}}, "missing-owner.lifespan"),
])
def test_validation_rejects_malformed_and_stale_definitions(minimal_model_web, definition, message):
    with pytest.raises(ValueError, match=message):
        validate_definition(_catalog(minimal_model_web), definition)


@pytest.mark.parametrize("setting", [
    None, {}, {"included": "true", "help": ""}, {"included": True, "help": 3},
    {"included": True, "help": "", "value": 7},
])
def test_validation_identifies_malformed_field_settings(minimal_model_web, setting):
    server = minimal_model_web.servers[0].modeling_obj
    definition = {"fields": {server.id: {"lifespan": setting}}}
    with pytest.raises(ValueError, match=f"{server.id}.lifespan"):
        validate_definition(_catalog(minimal_model_web), definition)


def test_retained_help_requires_a_real_eligible_address(minimal_model_web):
    server = minimal_model_web.servers[0].modeling_obj
    catalog = _catalog(minimal_model_web)
    assert validate_definition(catalog, None) == normalize_definition()
    definition = _definition(set(), excluded={FieldAddress(server.id, "lifespan")})
    assert validate_definition(catalog, definition) == definition
    with pytest.raises(ValueError, match="structural"):
        validate_definition(catalog, _definition(set(), excluded={FieldAddress(server.id, "storage")}))
    with pytest.raises(ValueError, match="Unknown input"):
        complete_selection(catalog, {FieldAddress(server.id, "missing")})


def test_current_version_config_normalizes_without_mutating_saved_data(minimal_repository):
    from e_footprint_interface import __version__

    config = {"card_order": {"server-list": ["server"]}}
    before = deepcopy(config)
    assert upgrade_interface_config(config, int(__version__.split(".")[0])) == {
        **config, "simplified_inputs": normalize_definition()}
    assert config == before
    data = deepcopy(minimal_repository.get_system_data())
    assert minimal_repository.interface_config["simplified_inputs"] == normalize_definition()
    assert minimal_repository.get_system_data() == data
