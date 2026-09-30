from copy import deepcopy
from unittest.mock import patch

import pytest

from model_builder.adapters.forms.timeseries_builder_registry import can_edit_timeseries
from model_builder.application.use_cases.simplified_inputs import UpdateSimplifiedDefinitionUseCase
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
