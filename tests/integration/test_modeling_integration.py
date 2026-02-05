import json

import numpy as np

from efootprint.constants.units import u

from model_builder.adapters.forms.form_data_parser import parse_form_data
from model_builder.application.use_cases.create_object import CreateObjectInput, CreateObjectUseCase
from model_builder.application.use_cases.delete_object import DeleteObjectInput, DeleteObjectUseCase
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_DEVICES, DEFAULT_NETWORKS
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values


def _extract_structure_from_repository(model_web: ModelWeb) -> dict[str, set[str]]:
    system_data = model_web.repository.get_system_data()
    assert system_data is not None

    structure = {}
    for class_name, objects_dict in system_data.items():
        if class_name == "efootprint_version":
            continue
        if isinstance(objects_dict, dict):
            structure[class_name] = set(objects_dict.keys())
    return structure


def test_integration_create_edit_delete_flow(default_system_repository):
    baseline_model_web = ModelWeb(default_system_repository)
    usage_journey_step_id = baseline_model_web.usage_journey_steps[0].efootprint_id
    usage_journey_id = baseline_model_web.usage_journeys[0].efootprint_id
    initial_total_footprint = baseline_model_web.system.total_footprint.efootprint_object

    # --- Create a server with nested storage (exercise form parsing + ServerWeb.pre_create) ---
    server_post_data = create_post_data_from_class_default_values(
        "Test Server","Server", server_type="autoscaling")
    storage_post_data = create_post_data_from_class_default_values("Test Storage", "Storage")
    server_post_data["Storage_form_data"] = json.dumps(storage_post_data)
    parsed_server_form = parse_form_data(server_post_data, server_post_data["type_object_available"])
    create_use_case = CreateObjectUseCase(default_system_repository)
    server_output = create_use_case.execute(CreateObjectInput(object_type="Server", form_data=parsed_server_form))
    server_id = server_output.created_object_id

    # --- Create a job and link it to the default usage journey step ---
    job_post_data = create_post_data_from_class_default_values("Test Job","Job", server=server_id)
    parsed_job_form = parse_form_data(job_post_data, job_post_data["type_object_available"])
    job_output = create_use_case.execute(
        CreateObjectInput(object_type="Job", form_data=parsed_job_form, parent_id=usage_journey_step_id))
    job_id = job_output.created_object_id

    # --- Create a usage pattern pointing to the existing usage journey ---
    device_id = next(iter(DEFAULT_DEVICES.keys()))
    network_id = next(iter(DEFAULT_NETWORKS.keys()))
    country_id = next(iter(DEFAULT_COUNTRIES.keys()))

    usage_pattern_post_data = create_post_data_from_class_default_values(
        "Test Usage Pattern", "UsagePattern", usage_journey=usage_journey_id, devices=device_id,
        network=network_id, country=country_id, hourly_usage_journey_starts__initial_volume=1000)
    parsed_up_form = parse_form_data(usage_pattern_post_data, usage_pattern_post_data["type_object_available"])
    up_output = create_use_case.execute(CreateObjectInput(object_type="UsagePattern", form_data=parsed_up_form))
    usage_pattern_id = up_output.created_object_id

    model_web_before_edit = ModelWeb(default_system_repository)
    previous_network_energy = model_web_before_edit.system.usage_patterns[0].network.energy_footprint.sum()

    # --- Edit job data_transferred and verify it impacts computed footprints ---
    edit_form_raw = {"data_transferred": "20", "data_transferred_unit": str(u.MB)}
    parsed_edit_form = parse_form_data(edit_form_raw, "Job")

    edit_use_case = EditObjectUseCase(model_web_before_edit)
    edit_use_case.execute(EditObjectInput(object_id=job_id, form_data=parsed_edit_form))

    model_web_after_edit = ModelWeb(default_system_repository)
    updated_network_energy = model_web_after_edit.system.usage_patterns[0].network.energy_footprint.sum()
    assert updated_network_energy > previous_network_energy

    # --- Delete created objects and verify system is back to baseline structure ---
    delete_use_case = DeleteObjectUseCase(ModelWeb(default_system_repository))
    delete_use_case.execute(DeleteObjectInput(object_id=usage_pattern_id))

    delete_use_case = DeleteObjectUseCase(ModelWeb(default_system_repository))
    delete_use_case.execute(DeleteObjectInput(object_id=job_id))

    delete_use_case = DeleteObjectUseCase(ModelWeb(default_system_repository))
    delete_use_case.execute(DeleteObjectInput(object_id=server_id))

    final_model_web = ModelWeb(default_system_repository)
    assert _extract_structure_from_repository(final_model_web) == _extract_structure_from_repository(
        baseline_model_web)
    assert final_model_web.system.total_footprint.efootprint_object == initial_total_footprint


def test_integration_edge_modeling_emissions_non_zero(default_system_repository):
    create_use_case = CreateObjectUseCase(default_system_repository)

    network_id = next(iter(DEFAULT_NETWORKS.keys()))
    country_id = next(iter(DEFAULT_COUNTRIES.keys()))

    edge_storage_post_data = create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage")
    edge_device_post_data = create_post_data_from_class_default_values(
        "Test Edge Device", "EdgeComputer", EdgeStorage_form_data=edge_storage_post_data)
    parsed_edge_device_form = parse_form_data(edge_device_post_data, edge_device_post_data["type_object_available"])
    edge_device_output = create_use_case.execute(
        CreateObjectInput(object_type="EdgeComputer", form_data=parsed_edge_device_form)
    )
    edge_device_id = edge_device_output.created_object_id

    edge_usage_journey_post_data = create_post_data_from_class_default_values(
        "Test Edge Usage Journey", "EdgeUsageJourney", edge_functions=""
    )
    parsed_edge_uj_form = parse_form_data(
        edge_usage_journey_post_data,
        edge_usage_journey_post_data["type_object_available"],
    )
    edge_usage_journey_output = create_use_case.execute(
        CreateObjectInput(object_type="EdgeUsageJourney", form_data=parsed_edge_uj_form)
    )
    edge_usage_journey_id = edge_usage_journey_output.created_object_id

    edge_function_post_data = create_post_data_from_class_default_values(
        "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs="")
    parsed_edge_function_form = parse_form_data(
        edge_function_post_data,
        edge_function_post_data["type_object_available"],
    )
    edge_function_output = create_use_case.execute(
        CreateObjectInput(
            object_type="EdgeFunction",
            form_data=parsed_edge_function_form,
            parent_id=edge_usage_journey_id,
        )
    )
    edge_function_id = edge_function_output.created_object_id

    recurrent_process_post_data = create_post_data_from_class_default_values(
        "Test Process", "RecurrentEdgeProcess", edge_device=edge_device_id)
    parsed_recurrent_process_form = parse_form_data(
        recurrent_process_post_data, recurrent_process_post_data["type_object_available"]
    )
    create_use_case.execute(
        CreateObjectInput(
            object_type="RecurrentEdgeProcess",
            form_data=parsed_recurrent_process_form,
            parent_id=edge_function_id,
        )
    )

    edge_usage_pattern_post_data = create_post_data_from_class_default_values(
        "Test Edge Usage Pattern", "EdgeUsagePattern", edge_usage_journey=edge_usage_journey_id, network=network_id,
        country=country_id, hourly_edge_usage_journey_starts__initial_volume=100
    )
    parsed_edge_up_form = parse_form_data(
        edge_usage_pattern_post_data, edge_usage_pattern_post_data["type_object_available"]
    )
    create_use_case.execute(CreateObjectInput(object_type="EdgeUsagePattern", form_data=parsed_edge_up_form))

    computed_model_web = ModelWeb(default_system_repository)
    emissions = computed_model_web.system_emissions
    for key, values in emissions["values"].items():
        assert len(values) > 0
        if key in ["Edge_devices_energy", "Edge_devices_fabrication"]:
            assert np.max(np.abs(values)) > 0


def test_raise_incomplete_modeling_errors_for_empty_system():
    from model_builder.adapters.repositories import InMemorySystemRepository

    repository = InMemorySystemRepository(
        initial_data={
            "efootprint_version": "14.1.0",
            "System": {
                "uuid-system-1": {
                    "name": "system 1",
                    "id": "uuid-system-1",
                    "usage_patterns": [],
                    "edge_usage_patterns": [],
                }
            },
        }
    )

    model_web = ModelWeb(repository)
    try:
        model_web.raise_incomplete_modeling_errors()
    except ValueError as exc:
        assert "No impact could be computed" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete modeling")
