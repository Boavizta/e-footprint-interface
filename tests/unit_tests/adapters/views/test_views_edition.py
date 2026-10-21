from model_builder.adapters.presenters.simplified_inputs import input_catalog
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import WeeklyPatternValidationError
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.application.use_cases import CreateObjectInput, CreateObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.exceptions import ComputationMemoryLimitExceeded
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.system_builders import create_hourly_usage


def _setup_session(client, system_data: dict) -> None:
    SessionSystemRepository(client.session).save_data(system_data)


def _create_object_in_session(client, post_data: dict, parent_id: str | None = None) -> str:
    repository = SessionSystemRepository(client.session)
    object_type = post_data["type_object_available"]
    parsed_form_data = parse_form_data(post_data, object_type)
    output = CreateObjectUseCase(repository, input_catalog).execute(
        CreateObjectInput(object_type=object_type, form_data=parsed_form_data, parent_id=parent_id)
    )
    return output.created_object_id


def _model_web(client) -> ModelWeb:
    return ModelWeb(SessionSystemRepository(client.session))


def _extract_select_html(response_body: str, select_id: str) -> str:
    marker = f'id="{select_id}"'
    start = response_body.index(marker)
    select_start = response_body.rfind("<select", 0, start)
    select_end = response_body.index("</select>", start) + len("</select>")
    return response_body[select_start:select_end]


def _build_system_with_library_built_relationships() -> System:
    """Objects that builders attach in after_init: an edge computer's components, recurrent edge process and
    workload component needs, and an EcoLogits API server."""
    edge_computer = EdgeComputer.from_defaults("Edge computer", storage=EdgeStorage.from_defaults("Edge storage"))
    edge_appliance = EdgeAppliance.from_defaults("Edge appliance")
    edge_process = RecurrentEdgeProcess.from_defaults("Edge process", edge_device=edge_computer)
    edge_workload = RecurrentEdgeWorkload.from_defaults("Edge workload", edge_device=edge_appliance)
    edge_function = EdgeFunction(
        "Edge function", recurrent_edge_device_needs=[edge_process, edge_workload], recurrent_server_needs=[])
    edge_usage_pattern = EdgeUsagePattern(
        "Edge usage pattern",
        edge_usage_journeys=[EdgeUsageJourney.from_defaults("Edge journey", edge_functions=[edge_function])],
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_deployment_starts=create_hourly_usage(),
    )
    external_api = EcoLogitsGenAIExternalAPI.from_defaults("LLM API")
    step = UsageJourneyStep.from_defaults(
        "Step", jobs=[EcoLogitsGenAIExternalAPIJob.from_defaults("LLM job", external_api=external_api)])
    usage_pattern = UsagePattern(
        "Usage pattern",
        usage_journeys={UsageJourney("Journey", uj_steps=[step]): SourceValue(1 * u.dimensionless)},
        devices=[Device.from_defaults("Device")],
        network=Network.from_defaults("Network"),
        country=Countries.FRANCE(),
        hourly_occurrences=create_hourly_usage(),
    )

    return System("System", usage_patterns=[usage_pattern], edge_usage_patterns=[edge_usage_pattern])


@pytest.mark.django_db
class TestViewsEdition:

    def test_weekly_library_validation_error_uses_standard_modal_without_mutating_session(
        self, client, minimal_system_data, monkeypatch
    ):
        _setup_session(client, minimal_system_data)
        object_id = "recurrent-process"
        saved_before = SessionSystemRepository(client.session).get_system_data()
        model_web = MagicMock()
        model_web.get_web_object_from_efootprint_id.return_value = SimpleNamespace(
            class_as_simple_str="RecurrentEdgeProcess"
        )
        monkeypatch.setattr("model_builder.adapters.views.views_edition.ModelWeb", MagicMock(return_value=model_web))
        execute = MagicMock(
            side_effect=WeeklyPatternValidationError(
                [
                    {
                        "path": "profiles",
                        "code": "missing_day_assignment",
                        "message": "Day 1 must be assigned to exactly one profile.",
                    }
                ]
            )
        )
        monkeypatch.setattr("model_builder.adapters.views.views_edition.EditObjectUseCase.execute", execute)
        invalid_pattern = {
            "unit": "cpu_core",
            "profiles": [{"name": "incomplete", "days": [0], "baseline": 1, "ranges": []}],
        }

        response = client.post(
            f"/model_builder/edit-object/{object_id}/",
            {
                "RecurrentEdgeProcess_name": "Invalid process",
                "RecurrentEdgeProcess_recurrent_compute_needed__weekly_pattern": json.dumps(invalid_pattern),
            },
        )

        assert response.status_code == 422
        assert response.headers["HX-Reswap"] == "none"
        assert "Day 1 must be assigned to exactly one profile" in response.content.decode()
        execute.assert_called_once()
        assert SessionSystemRepository(client.session).get_system_data() == saved_before

    def test_memory_limited_edit_uses_generic_modal_and_preserves_persisted_model(
        self, client, minimal_system_data, monkeypatch
    ):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        object_id = model_web.servers[0].efootprint_id
        saved_before = SessionSystemRepository(client.session).get_system_data()
        exception = ComputationMemoryLimitExceeded(
            working_set_bytes=3500 * 1024**2,
            limit_bytes=3400 * 1024**2,
            capacity_bytes=4 * 1024**3,
        )
        monkeypatch.setattr(
            "model_builder.adapters.views.views_edition.EditObjectUseCase.execute",
            MagicMock(side_effect=exception),
        )

        response = client.post(f"/model_builder/edit-object/{object_id}/", {})

        assert response.status_code == 500
        assert response.headers["HX-Reswap"] == "none"
        assert ComputationMemoryLimitExceeded.safe_message in response.content.decode()
        assert SessionSystemRepository(client.session).get_system_data() == saved_before

    def test_open_edit_object_panel_for_edge_device_renders_group_memberships(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Shared Sensor", "EdgeDevice", components=""),
        )
        group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Alpha", "EdgeDeviceGroup"),
        )
        model_web = _model_web(client)
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")
        group = model_web.get_efootprint_object_from_efootprint_id(group_id, "EdgeDeviceGroup")
        group.edge_device_counts[device] = SourceValue(4 * u.dimensionless)
        model_web.persist_to_cache()

        response = client.get(f"/model_builder/open-edit-object-panel/{device_id}/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "Group membership" in body
        assert "Alpha" in body
        assert f"/model_builder/update-dict-count/{group_id}/{device_id}/" in body
        assert f"/model_builder/unlink-dict-entry/{group_id}/{device_id}/" in body

    def test_open_edit_object_panel_for_group_excludes_illegal_sub_group_choices(
        self, client, default_system_repository
    ):
        _setup_session(client, default_system_repository.get_system_data())
        campus_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Campus", "EdgeDeviceGroup"),
        )
        building_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
        )
        floor_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
        )
        room_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Room", "EdgeDeviceGroup"),
        )
        annex_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Annex", "EdgeDeviceGroup"),
        )
        del annex_id

        model_web = _model_web(client)
        campus = model_web.get_efootprint_object_from_efootprint_id(campus_id, "EdgeDeviceGroup")
        building = model_web.get_efootprint_object_from_efootprint_id(building_id, "EdgeDeviceGroup")
        floor = model_web.get_efootprint_object_from_efootprint_id(floor_id, "EdgeDeviceGroup")
        room = model_web.get_efootprint_object_from_efootprint_id(room_id, "EdgeDeviceGroup")
        campus.sub_group_counts[building] = SourceValue(1 * u.dimensionless)
        building.sub_group_counts[floor] = SourceValue(1 * u.dimensionless)
        floor.sub_group_counts[room] = SourceValue(2 * u.dimensionless)
        model_web.persist_to_cache()

        response = client.get(f"/model_builder/open-edit-object-panel/{floor_id}/")

        body = response.content.decode()
        subgroup_select_html = _extract_select_html(body, "select-new-object-EdgeDeviceGroup_sub_group_counts")
        assert response.status_code == 200
        assert "Group members" in body
        assert ">Annex<" in subgroup_select_html
        assert ">Campus<" not in subgroup_select_html
        assert ">Building<" not in subgroup_select_html
        assert ">Floor<" not in subgroup_select_html
        assert ">Room<" in subgroup_select_html

    @pytest.mark.xfail(strict=True, reason="bug-fixes-2026-10 Task 6")
    @pytest.mark.parametrize(("class_str", "owner_name"), [
        ("EdgeStorage", "Edge computer"),
        ("RecurrentEdgeProcessCPUNeed", "Edge process"),
        ("RecurrentEdgeWorkloadNeed", "Edge workload"),
        ("EcoLogitsGenAIExternalAPIServer", "LLM API"),
    ])
    def test_library_built_child_panel_opens_and_delete_is_blocked_by_its_owner(
        self, client, monkeypatch, class_str, owner_name
    ):
        monkeypatch.delenv("RAISE_EXCEPTIONS", raising=False)
        system = _build_system_with_library_built_relationships()
        _setup_session(client, system_to_json(system, save_computed_state=False))
        object_id = _model_web(client).get_efootprint_objects_from_efootprint_type(class_str)[0].id

        panel_response = client.get(f"/model_builder/open-edit-object-panel/{object_id}/")

        assert panel_response.status_code == 200
        assert 'id="btn-ask-delete"' in panel_response.content.decode()

        delete_response = client.get(f"/model_builder/ask-delete-object/{object_id}/")

        delete_body = delete_response.content.decode()
        assert delete_response.status_code == 200
        assert "is referenced by" in delete_body
        assert owner_name in delete_body
        assert "Yes, delete" not in delete_body

    def test_edit_group_refreshes_root_groups_and_ungrouped_devices_lists(self, client, default_system_repository):
        _setup_session(client, default_system_repository.get_system_data())
        parent_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Building", "EdgeDeviceGroup"),
        )
        child_group_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Floor", "EdgeDeviceGroup"),
        )
        device_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Lobby Sensor", "EdgeDevice", components=""),
        )

        response = client.post(
            f"/model_builder/edit-object/{parent_group_id}/",
            {
                "EdgeDeviceGroup_name": "Building",
                "EdgeDeviceGroup_sub_group_counts": f'{{"{child_group_id}": 2}}',
                "EdgeDeviceGroup_edge_device_counts": f'{{"{device_id}": 4}}',
            },
        )

        body = response.content.decode()
        assert response.status_code == 200
        assert "hx-swap-oob='outerHTML:#edge-device-groups-list'" in body
        assert "hx-swap-oob='outerHTML:#edge-devices-list'" in body

        model_web = _model_web(client)
        parent = model_web.get_efootprint_object_from_efootprint_id(parent_group_id, "EdgeDeviceGroup")
        child = model_web.get_efootprint_object_from_efootprint_id(child_group_id, "EdgeDeviceGroup")
        device = model_web.get_efootprint_object_from_efootprint_id(device_id, "EdgeDevice")

        assert parent.sub_group_counts[child].value.magnitude == 2
        assert parent.edge_device_counts[device].value.magnitude == 4
        assert [group.efootprint_id for group in model_web.root_edge_device_groups] == [parent_group_id]
        assert [edge_device.efootprint_id for edge_device in model_web.ungrouped_edge_devices] == []


def _efootprint_obj_by_name(model_web: ModelWeb, class_str: str, name: str):
    return next(obj for obj in model_web.get_efootprint_objects_from_efootprint_type(class_str) if obj.name == name)


@pytest.mark.django_db
class TestEditPanelMembershipSections:
    """Child panels render generic dict-membership sections for the weighted relationships."""

    def test_step_panel_renders_journey_membership_section(self, client, minimal_system_data):
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        journey_id = _efootprint_obj_by_name(model_web, "UsageJourney", "Test Journey").id
        step_id = _efootprint_obj_by_name(model_web, "UsageJourneyStep", "Test Step").id

        response = client.get(f"/model_builder/open-edit-object-panel/{step_id}/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "Used in usage journeys" in body
        assert "Test Journey" in body
        assert f"/model_builder/update-dict-count/{journey_id}/{step_id}/" in body
        assert f"/model_builder/unlink-dict-entry/{journey_id}/{step_id}/" in body

    def test_job_panel_renders_step_membership_section_with_add_to_step_select(self, client, minimal_system_data):
        _setup_session(client, minimal_system_data)
        model_web = _model_web(client)
        journey_id = _efootprint_obj_by_name(model_web, "UsageJourney", "Test Journey").id
        step_id = _efootprint_obj_by_name(model_web, "UsageJourneyStep", "Test Step").id
        job_id = _efootprint_obj_by_name(model_web, "Job", "Test Job").id
        second_step_id = _create_object_in_session(
            client,
            create_post_data_from_class_default_values("Second Step", "UsageJourneyStep", jobs=""),
            parent_id=journey_id,
        )

        response = client.get(f"/model_builder/open-edit-object-panel/{job_id}/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "Used in usage journey steps" in body
        assert f"/model_builder/update-dict-count/{step_id}/{job_id}/" in body
        assert f"/model_builder/unlink-dict-entry/{step_id}/{job_id}/" in body
        assert "Add to step" in body
        assert f'<option value="{second_step_id}">Second Step</option>' in body
        # No recurrent server need exists, so the job's other membership section is not rendered.
        assert "Used in recurrent server needs" not in body
