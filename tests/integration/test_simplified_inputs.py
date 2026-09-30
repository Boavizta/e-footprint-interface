from model_builder.adapters.presenters.simplified_inputs import build_workspace_context, input_catalog
from copy import deepcopy
from unittest.mock import patch

import pytest

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob,
)
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.constants.units import u

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.application.use_cases.simplified_inputs import (
    EditSimplifiedInput, EditSimplifiedInputUseCase, UpdateSimplifiedDefinitionUseCase,
)
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.services.simplified_inputs import FieldAddress, build_catalog


def test_replacement_patch_retained_help_and_clear_use_config_only(minimal_repository):
    model = ModelWeb(minimal_repository)
    server_id = model.servers[0].efootprint_id
    catalog = build_catalog(model, can_edit_timeseries=can_edit_timeseries)
    use_case = UpdateSimplifiedDefinitionUseCase(minimal_repository, catalog)
    original = deepcopy(minimal_repository.get_system_data())
    minimal_repository.interface_config = {"card_order": {"server-list": [server_id]}}
    with patch.object(ModelWeb, "to_json", side_effect=AssertionError("Unexpected serialization")), \
            patch.object(ModelWeb, "__init__", side_effect=AssertionError("Unexpected hydration")):
        output = use_case.execute({"title": "Starter", "guidance": "Adapt the service", "fields": {
            server_id: {"lifespan": {"included": True, "help": "Expected lifetime"}}}}, replace=True)
        assert output.changed_fields is None
        use_case.execute({"fields": {server_id: {"lifespan": {"included": False}}}})
        saved = minimal_repository.interface_config["simplified_inputs"]
        assert saved["fields"][server_id]["lifespan"] == {"included": False, "help": "Expected lifetime"}
        output = use_case.execute({"fields": {server_id: {"lifespan": {"included": True}}}})
        assert output.changed_fields == {FieldAddress(server_id, "lifespan")}
        use_case.execute({"title": saved["title"], "guidance": saved["guidance"], "fields": {}}, replace=True)
    assert minimal_repository.interface_config["simplified_inputs"] == {
        "title": "Starter", "guidance": "Adapt the service", "fields": {}}
    assert minimal_repository.interface_config["card_order"] == {"server-list": [server_id]}
    persisted = deepcopy(minimal_repository.get_system_data())
    persisted.pop("interface_config")
    persisted.pop("efootprint_interface_version")
    assert persisted == original


def test_required_selection_completed_and_locked_exclusion_rejected(minimal_repository):
    model = ModelWeb(minimal_repository)
    server_id = model.servers[0].efootprint_id
    use_case = UpdateSimplifiedDefinitionUseCase(
        minimal_repository, build_catalog(model, can_edit_timeseries=can_edit_timeseries))
    use_case.execute({"fields": {server_id: {"server_type": {"included": True, "help": "Kind"}}}}, replace=True)
    fields = minimal_repository.interface_config["simplified_inputs"]["fields"][server_id]
    assert fields["fixed_nb_of_instances"]["included"] is True
    before = deepcopy(minimal_repository.get_system_data())
    with pytest.raises(ValueError, match="required input"):
        use_case.execute({"fields": {server_id: {"fixed_nb_of_instances": {"included": False}}}})
    with pytest.raises(ValueError, match="Unknown input"):
        use_case.execute({"fields": {"missing": {"lifespan": {"included": True}}}})
    assert minimal_repository.get_system_data() == before


def test_budget_rejection_preserves_definition_and_model(minimal_repository):
    model = ModelWeb(minimal_repository)
    use_case = UpdateSimplifiedDefinitionUseCase(
        minimal_repository, build_catalog(model, can_edit_timeseries=can_edit_timeseries))
    before = deepcopy(minimal_repository.get_system_data())
    config_before = deepcopy(minimal_repository.interface_config)
    minimal_repository._max_payload_size_mb = 0.000001
    with pytest.raises(PayloadSizeLimitExceeded):
        use_case.execute({"title": "Large new title"}, replace=True)
    assert minimal_repository.get_system_data() == before
    assert minimal_repository.interface_config == config_before


def _select(model, *addresses):
    catalog = build_catalog(model, can_edit_timeseries=can_edit_timeseries)
    fields = {}
    for address in addresses:
        fields.setdefault(address.object_id, {})[address.attribute] = {"included": True}
    UpdateSimplifiedDefinitionUseCase(model.repository, catalog).execute({"fields": fields})
    return EditSimplifiedInputUseCase(model, catalog)


@pytest.fixture
def video_model(minimal_model_web):
    api = EcoLogitsVideoGenExternalAPI.from_defaults("Video API")
    jobs = [EcoLogitsVideoGenExternalAPIJob.from_defaults(
        name, external_api=api, resolution=SourceObject(resolution, confidence="high", comment="Authored resolution"))
        for name, resolution in (("Retained", "720p (1280 x 720)"),
                                 ("Adjusted A", "1080p (1920 x 1080)"),
                                 ("Adjusted B", "1080p (1920 x 1080)"))]
    for owner in [api, *jobs]:
        minimal_model_web.add_new_efootprint_object_to_system(owner)
    minimal_model_web.persist_to_cache()
    return ModelWeb(minimal_model_web.repository), api.id, [job.id for job in jobs]


def test_provider_reconciles_chain_and_every_linked_job_in_one_batch(video_model):
    model, api_id, job_ids = video_model
    api = model.flat_efootprint_objs_dict[api_id]
    jobs = [model.flat_efootprint_objs_dict[object_id] for object_id in job_ids]
    provider = FieldAddress(api_id, "provider")
    use_case = _select(model, provider)

    def assert_conditional_editors(addresses=None):
        context = build_workspace_context(model, addresses=addresses)
        editors = {field["address"]: field["editor"]
                   for group in context["groups"] for obj in group["objects"] for field in obj["fields"]}
        for owner, attribute, controller in [(api, "model_name", api.provider),
                                              *((job, "resolution", api.model_name) for job in jobs)]:
            editor = editors[FieldAddress(owner.id, attribute)]
            choices = owner.conditional_list_values[attribute]["conditional_list_values"][controller]
            assert {"selected": editor["selected"], "options": editor["options"]} == {
                "selected": getattr(owner, attribute).value,
                "options": [{"label": str(choice), "value": str(choice)} for choice in choices],
            }

    assert_conditional_editors()
    old_resolution = jobs[0].resolution
    new_provider = SourceObject("bytedance")
    expected_model = api.conditional_list_values["model_name"]["conditional_list_values"][new_provider][0]
    allowed = jobs[0].conditional_list_values["resolution"]["conditional_list_values"][expected_model]
    with (
        patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update,
        patch.object(model, "persist_to_cache", wraps=model.persist_to_cache) as persist,
        patch.object(model.repository, "save_data", wraps=model.repository.save_data) as save,
    ):
        result = use_case.execute(EditSimplifiedInput(provider, {"value": new_provider.value, "confidence": "medium"}))
    update.assert_called_once()
    persist.assert_called_once()
    save.assert_called_once()
    assert len(update.call_args.args[0]) == 4
    assert api.model_name == expected_model
    assert jobs[0].resolution is old_resolution
    assert jobs[1].resolution == jobs[2].resolution == allowed[0]
    assert jobs[1].resolution is not jobs[2].resolution
    assert jobs[1].resolution is not allowed[0]
    assert result.changed_fields == {provider, FieldAddress(api_id, "model_name"),
                                     *(FieldAddress(job.id, "resolution") for job in jobs)}
    assert len(result.notices) == 3
    assert "Adjusted A" in result.notices[1] and str(allowed[0]) in result.notices[1]
    assert_conditional_editors(result.changed_fields)
    restored = ModelWeb(model.repository)
    for job in jobs:
        value = restored.flat_efootprint_objs_dict[job.id].resolution
        assert value == job.resolution
        assert value.confidence == "high" and value.comment == "Authored resolution"
        assert value.source.id == old_resolution.source.id
    assert restored.flat_efootprint_objs_dict[api_id].provider.confidence == "medium"


def test_empty_choice_rejects_before_any_value_or_provenance_is_published(video_model, monkeypatch):
    model, api_id, _ = video_model
    provider = FieldAddress(api_id, "provider")
    use_case = _select(model, provider)
    new_provider = SourceObject("bytedance")
    models = EcoLogitsVideoGenExternalAPI.conditional_list_values["model_name"]["conditional_list_values"]
    new_model = models[new_provider][0]
    branches = EcoLogitsVideoGenExternalAPIJob.conditional_list_values["resolution"]["conditional_list_values"]
    monkeypatch.setitem(branches, new_model, [])
    before = deepcopy(model.repository.get_system_data())
    with (
        patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update,
        patch.object(model.repository, "save_data", wraps=model.repository.save_data) as save,
    ):
        with pytest.raises(ValueError, match="No allowed value"):
            use_case.execute(EditSimplifiedInput(provider, {
                "value": new_provider.value, "comment": "Unpublished", "confidence": "low",
                "source": {"id": "rejected-source", "name": "New source"}}))
    update.assert_not_called()
    save.assert_not_called()
    assert model.repository.get_system_data() == before
    assert ModelWeb(model.repository).flat_efootprint_objs_dict[api_id].provider.value == "openai"


def test_library_rejection_rolls_back_batch_without_publishing_metadata(video_model):
    model, api_id, _ = video_model
    address = FieldAddress(api_id, "provider")
    use_case = _select(model, address)
    before = deepcopy(model.repository.get_system_data())
    api = model.flat_efootprint_objs_dict[api_id]
    original = api.provider
    with (
        patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update,
        patch.object(model, "persist_to_cache", wraps=model.persist_to_cache) as persist,
    ):
        with pytest.raises(ValueError, match="not in the list"):
            use_case.execute(EditSimplifiedInput(address, {"value": "unknown-provider", "comment": "Unpublished"}))
    update.assert_called_once()
    persist.assert_not_called()
    assert api.provider is original
    assert model.repository.get_system_data() == before


def test_optional_server_count_and_unrestricted_branch_round_trip(minimal_model_web):
    model = minimal_model_web
    server = model.servers[0].modeling_obj
    kind = FieldAddress(server.id, "server_type")
    count = FieldAddress(server.id, "fixed_nb_of_instances")
    use_case = _select(model, kind)
    assert isinstance(server.fixed_nb_of_instances, EmptyExplainableObject)
    result = use_case.execute(EditSimplifiedInput(kind, {"value": ServerTypes.on_premise().value}))
    assert result.notices == []
    assert isinstance(server.fixed_nb_of_instances, EmptyExplainableObject)
    parsed = parse_form_data({"Server_fixed_nb_of_instances": "1000000",
                             "Server_fixed_nb_of_instances__unit": "concurrent",
                             "Server_fixed_nb_of_instances__comment": "Fleet count"}, "Server")
    use_case.execute(EditSimplifiedInput(count, parsed["fixed_nb_of_instances"]))
    assert ModelWeb(model.repository).flat_efootprint_objs_dict[server.id].fixed_nb_of_instances.magnitude == 1000000
    with patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update:
        result = use_case.execute(EditSimplifiedInput(kind, {"value": ServerTypes.autoscaling().value}))
    update.assert_called_once()
    assert len(update.call_args.args[0]) == 2
    assert result.changed_fields == {kind, count}
    assert len(result.notices) == 1 and "no value" in result.notices[0]
    restored = ModelWeb(model.repository).flat_efootprint_objs_dict[server.id]
    assert isinstance(restored.fixed_nb_of_instances, EmptyExplainableObject)
    assert restored.fixed_nb_of_instances.comment == "Fleet count"


def test_empty_server_count_to_zero_reaches_capacity_validation(minimal_model_web):
    model = minimal_model_web
    server = model.servers[0].modeling_obj
    kind = FieldAddress(server.id, "server_type")
    use_case = _select(model, kind)
    use_case.execute(EditSimplifiedInput(kind, {"value": ServerTypes.on_premise().value}))
    before = deepcopy(model.repository.get_system_data())
    with patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update:
        with pytest.raises(InsufficientCapacityError, match="capacity"):
            use_case.execute(EditSimplifiedInput(FieldAddress(server.id, "fixed_nb_of_instances"), {
                "value": 0, "unit": "concurrent", "comment": "Unpublished zero"}))
    update.assert_called_once()
    assert isinstance(server.fixed_nb_of_instances, EmptyExplainableObject)
    assert model.repository.get_system_data() == before


def test_zero_count_is_replaced_by_empty_when_switching_to_autoscaling(minimal_model_web):
    model = minimal_model_web
    server = Server.from_defaults(
        "Idle fixed server", storage=Storage.from_defaults("Idle storage"),
        server_type=ServerTypes.on_premise(), fixed_nb_of_instances=SourceValue(0 * u.concurrent))
    model.add_new_efootprint_object_to_system(server)
    model.persist_to_cache()
    address = FieldAddress(server.id, "server_type")
    use_case = _select(model, address)
    with patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update:
        result = use_case.execute(EditSimplifiedInput(address, {"value": ServerTypes.autoscaling().value}))
    update.assert_called_once()
    assert len(update.call_args.args[0]) == 2
    assert result.changed_fields == {address, FieldAddress(server.id, "fixed_nb_of_instances")}
    assert len(result.notices) == 1 and "no value" in result.notices[0]
    restored = ModelWeb(model.repository).flat_efootprint_objs_dict[server.id]
    assert isinstance(restored.fixed_nb_of_instances, EmptyExplainableObject)


@pytest.mark.parametrize("simplified", [False, True], ids=["normal-edit", "selected-edit"])
def test_equal_timeseries_authored_inputs_and_provenance_round_trip(minimal_model_web, simplified):
    model = minimal_model_web
    pattern = model.get_efootprint_objects_from_efootprint_type("UsagePattern")[0]
    original = pattern.hourly_occurrences
    form_inputs = {**original.form_inputs, "net_growth_rate_timespan": "month"}
    post_data = {f"UsagePattern_hourly_occurrences__{name}": value for name, value in form_inputs.items()}
    post_data.update({
        "UsagePattern_hourly_occurrences__confidence": "high",
        "UsagePattern_hourly_occurrences__comment": "Reviewed monthly growth",
        "UsagePattern_hourly_occurrences__source_id": "monthly-projection",
        "UsagePattern_hourly_occurrences__source_name": "Monthly projection",
    })
    parsed = parse_form_data(post_data, "UsagePattern")
    if simplified:
        address = FieldAddress(pattern.id, "hourly_occurrences")
        _select(model, address).execute(EditSimplifiedInput(address, parsed["hourly_occurrences"]))
    else:
        EditObjectUseCase(model, input_catalog).execute(EditObjectInput(pattern.id, parsed))
    restored = ModelWeb(model.repository).flat_efootprint_objs_dict[pattern.id].hourly_occurrences
    assert restored == original
    assert restored.form_inputs == form_inputs
    assert (restored.label, restored.confidence, restored.comment, restored.source.to_json()) == (
        original.label, "high", "Reviewed monthly growth",
        {"id": "monthly-projection", "name": "Monthly projection", "link": None})


@pytest.mark.parametrize("metadata_only", [False, True])
def test_same_value_provenance_save_does_not_reconcile_other_inputs(video_model, metadata_only):
    model, api_id, _ = video_model
    address = FieldAddress(api_id, "provider")
    use_case = _select(model, address)
    parsed = {"confidence": "low", "comment": "Reviewed"}
    parsed.update({"_metadata_only": True} if metadata_only else {"value": "openai"})
    with (
        patch("model_builder.application.use_cases.simplified_inputs.ModelingUpdate", wraps=ModelingUpdate) as update,
        patch.object(model, "persist_to_cache", wraps=model.persist_to_cache) as persist,
    ):
        result = use_case.execute(EditSimplifiedInput(address, parsed))
    update.assert_not_called()
    persist.assert_called_once()
    assert result.changed_fields == {address} and result.notices == []
    restored = ModelWeb(model.repository).flat_efootprint_objs_dict[api_id].provider
    assert restored.confidence == "low" and restored.comment == "Reviewed"


def test_nested_storage_owner_and_omitted_metadata_are_preserved(minimal_model_web):
    model = minimal_model_web
    storage = model.servers[0].modeling_obj.storage
    current = storage.storage_capacity
    current.confidence, current.comment = "high", "Original source"
    model.persist_to_cache()
    address = FieldAddress(storage.id, "storage_capacity")
    use_case = _select(model, address)
    result = use_case.execute(EditSimplifiedInput(address, {
        "value": current.magnitude + 1, "unit": str(current.unit), "label": "no label"}))
    restored = ModelWeb(model.repository).flat_efootprint_objs_dict[storage.id].storage_capacity
    assert restored.magnitude == current.magnitude + 1
    assert restored.source.id == current.source.id
    assert restored.confidence == "high" and restored.comment == "Original source"
    assert result.changed_fields == {address}


def test_failed_persistence_discards_request_local_metadata_patch(minimal_model_web):
    model = minimal_model_web
    address = FieldAddress(model.servers[0].efootprint_id, "compute")
    use_case = _select(model, address)
    before = deepcopy(model.repository.get_system_data())
    model.repository._max_payload_size_mb = 0.000001
    with pytest.raises(PayloadSizeLimitExceeded):
        use_case.execute(EditSimplifiedInput(address, {"_metadata_only": True, "comment": "Unpublished"}))
    assert model.repository.get_system_data() == before


@pytest.mark.parametrize("target", ["unknown", "wrong_owner", "structural", "unselected"])
def test_rejects_unavailable_or_unselected_inputs(minimal_model_web, target):
    model = minimal_model_web
    server = model.servers[0].modeling_obj
    address = {"unknown": FieldAddress("missing", "lifespan"),
               "wrong_owner": FieldAddress(server.id, "storage_capacity"),
               "structural": FieldAddress(server.id, "storage"),
               "unselected": FieldAddress(server.id, "lifespan")}[target]
    catalog = build_catalog(model, can_edit_timeseries=can_edit_timeseries)
    before = deepcopy(model.repository.get_system_data())
    with patch.object(model, "persist_to_cache", wraps=model.persist_to_cache) as persist:
        with pytest.raises(ValueError):
            EditSimplifiedInputUseCase(model, catalog).execute(EditSimplifiedInput(address, {}))
    persist.assert_not_called()
    assert model.repository.get_system_data() == before


def test_creation_resolves_nested_settings_and_saves_model_once(minimal_repository):
    from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
    pending = [{"owner": "object", "attribute": "lifespan", "included": True, "help": "Server lifetime"},
               {"owner": "storage", "attribute": "storage_capacity", "included": False, "help": "Retained capacity"}]
    with (patch.object(minimal_repository, "save_data", wraps=minimal_repository.save_data) as save,
          patch.object(minimal_repository, "save_interface_config", wraps=minimal_repository.save_interface_config) as config):
        result = CreateObjectUseCase(minimal_repository, input_catalog).execute(CreateObjectInput(
            "Server", {"name": "New server", "type_object_available": "Server", "_parsed_Storage": {"name": "Nested storage"}},
            simplified_settings=pending))
    save.assert_called_once()
    config.assert_not_called()
    restored = ModelWeb(minimal_repository)
    server = restored.get_web_object_from_efootprint_id(result.created_object_id)
    fields = minimal_repository.interface_config["simplified_inputs"]["fields"]
    assert fields[server.efootprint_id]["lifespan"] == {"included": True, "help": "Server lifetime"}
    assert fields[server.storage.efootprint_id]["storage_capacity"] == {"included": False, "help": "Retained capacity"}


@pytest.mark.parametrize("failure", ["hook", "settings", "budget"])
def test_failed_creation_publishes_neither_object_nor_pending_settings(minimal_repository, failure):
    from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
    from model_builder.domain.entities.web_core.hardware.storage_web import StorageWeb
    pending = [{"owner": "object", "attribute": "storage_capacity", "included": True, "help": "Pending"}]
    original = deepcopy(minimal_repository.get_system_data())
    config = deepcopy(minimal_repository.interface_config)
    if failure == "settings":
        pending[0]["attribute"] = "missing"
    if failure == "budget":
        minimal_repository._max_payload_size_mb = 0.000001
    with patch.object(StorageWeb, "post_create", create=True,
                      side_effect=ValueError("Rejected hook") if failure == "hook" else None):
        with pytest.raises((ValueError, PayloadSizeLimitExceeded)):
            CreateObjectUseCase(minimal_repository, input_catalog).execute(CreateObjectInput(
                "Storage", {"name": "Rejected", "type_object_available": "Storage"}, simplified_settings=pending))
    assert minimal_repository.get_system_data() == original
    assert minimal_repository.interface_config == config


def test_new_dependents_are_completed_after_creation_hooks(video_model):
    from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
    model, api_id, _ = video_model
    _select(model, FieldAddress(api_id, "model_name"))
    result = CreateObjectUseCase(model.repository, input_catalog).execute(CreateObjectInput(
        "Job", {"name": "New video", "type_object_available": "EcoLogitsVideoGenExternalAPIJob",
                "service_or_external_api": api_id, "server_or_external_api": api_id},
        simplified_settings=[{"owner": "object", "attribute": "resolution", "included": False, "help": "New help"}]))
    setting = model.repository.interface_config["simplified_inputs"]["fields"][result.created_object_id]["resolution"]
    assert setting == {"included": True, "help": "New help"}


def test_deletion_warning_and_cleanup_follow_actual_cascade_and_keep_shared_children(minimal_model_web):
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep
    from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase

    model = minimal_model_web
    shared = UsageJourneyStep.from_defaults("Shared", jobs={})
    removed = UsageJourneyStep.from_defaults("Removed", jobs={})
    removed_help = UsageJourneyStep.from_defaults("Removed help", jobs={})
    first = UsageJourney("First", uj_steps={shared: SourceValue(1 * u.dimensionless), removed: SourceValue(1 * u.dimensionless),
                                            removed_help: SourceValue(1 * u.dimensionless)})
    second = UsageJourney("Second", uj_steps={shared: SourceValue(1 * u.dimensionless)})
    for owner in [first, second]:
        model.add_new_efootprint_object_to_system(owner)
    model.persist_to_cache()
    # Steps have eligible scalar timing fields; keep deselected help on another field as well.
    catalog = input_catalog(model)
    removed_address = next(address for address, descriptor in catalog.fields.items()
                           if address.object_id == removed.id and descriptor.eligible)
    shared_address = FieldAddress(shared.id, removed_address.attribute)
    _select(model, removed_address, shared_address)
    UpdateSimplifiedDefinitionUseCase(model.repository, catalog).execute({"fields": {
        removed_help.id: {"user_time_spent": {"included": False, "help": "Removed owner help"}}}})
    original = deepcopy(model.repository.get_system_data())
    use_case = DeleteObjectUseCase(model, input_catalog)
    check = use_case.check_can_delete(first.id)
    assert check.selected_fields_removed == [removed_address]
    assert model.repository.get_system_data() == original
    use_case.execute(DeleteObjectInput(first.id))
    fields = model.repository.interface_config["simplified_inputs"]["fields"]
    assert first.id not in fields and removed.id not in fields and removed_help.id not in fields
    assert fields[shared.id][shared_address.attribute]["included"]


def test_server_deletion_warns_about_nested_storage_and_prunes_its_retained_help(minimal_model_web):
    from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase
    model = minimal_model_web
    server = model.add_new_efootprint_object_to_system(Server.from_defaults(
        "Independent server", storage=Storage.from_defaults("Independent storage")))
    model.persist_to_cache()
    catalog = input_catalog(model)
    address = FieldAddress(server.storage.efootprint_id, "storage_capacity")
    _select(model, address)
    UpdateSimplifiedDefinitionUseCase(model.repository, catalog).execute({"fields": {
        server.storage.efootprint_id: {"data_storage_duration": {"included": False, "help": "Stored only as help"}}}})
    use_case = DeleteObjectUseCase(model, input_catalog)
    with patch.object(model.repository, "save_data", wraps=model.repository.save_data) as save:
        warning = use_case.check_can_delete(server.efootprint_id)
        assert warning.selected_fields_removed == [address]
        save.assert_not_called()
        use_case.execute(DeleteObjectInput(server.efootprint_id))
        save.assert_called_once()
    fields = model.repository.interface_config["simplified_inputs"]["fields"]
    assert server.efootprint_id not in fields and server.storage.efootprint_id not in fields


def test_structural_relink_completes_current_controller_dependencies(video_model):
    model, api_a_id, job_ids = video_model
    api_b = model.add_new_efootprint_object_to_system(EcoLogitsVideoGenExternalAPI.from_defaults("Unselected API"))
    model.persist_to_cache()
    _select(model, FieldAddress(api_a_id, "model_name"))
    job_id = job_ids[0]
    EditObjectUseCase(model, input_catalog).execute(EditObjectInput(job_id, {"external_api": api_b.efootprint_id}))
    # Membership survives a released requirement; deselection retains help and is now allowed.
    catalog = input_catalog(model)
    use_case = UpdateSimplifiedDefinitionUseCase(model.repository, catalog)
    use_case.execute({"fields": {job_id: {"resolution": {"included": False, "help": "Kept after reorienting"}}}})
    EditObjectUseCase(model, input_catalog).execute(EditObjectInput(job_id, {"external_api": api_a_id}))
    setting = model.repository.interface_config["simplified_inputs"]["fields"][job_id]["resolution"]
    assert setting == {"included": True, "help": "Kept after reorienting"}
