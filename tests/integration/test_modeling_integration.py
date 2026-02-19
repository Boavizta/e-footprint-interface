import json

import numpy as np

from efootprint.constants.units import u

from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_COUNTRIES, DEFAULT_DEVICES, DEFAULT_NETWORKS
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object, edit_object


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
    server_post_data = create_post_data_from_class_default_values("Test Server", "Server", server_type="autoscaling")
    server_post_data["Storage_form_data"] = json.dumps(
        create_post_data_from_class_default_values("Test Storage", "Storage"))
    server_id = create_object(default_system_repository, server_post_data)

    # --- Create a job and link it to the default usage journey step ---
    job_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Job", "Job", server=server_id),
        parent_id=usage_journey_step_id,
    )

    # --- Create a usage pattern pointing to the existing usage journey ---
    usage_pattern_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Usage Pattern", "UsagePattern",
            usage_journey=usage_journey_id,
            devices=next(iter(DEFAULT_DEVICES.keys())),
            network=next(iter(DEFAULT_NETWORKS.keys())),
            country=next(iter(DEFAULT_COUNTRIES.keys())),
            hourly_usage_journey_starts__initial_volume=1000,
        ),
    )

    previous_network_energy = (
        ModelWeb(default_system_repository).system.usage_patterns[0].network.energy_footprint.sum())

    # --- Edit job data_transferred and verify it impacts computed footprints ---
    edit_object(default_system_repository, job_id, "Job", {"data_transferred": "20", "data_transferred_unit": str(u.MB)})

    updated_network_energy = (
        ModelWeb(default_system_repository).system.usage_patterns[0].network.energy_footprint.sum())
    assert updated_network_energy > previous_network_energy

    # --- Delete created objects and verify system is back to baseline structure ---
    delete_object(default_system_repository, usage_pattern_id)
    delete_object(default_system_repository, job_id)
    delete_object(default_system_repository, server_id)

    final_model_web = ModelWeb(default_system_repository)
    assert _extract_structure_from_repository(final_model_web) == _extract_structure_from_repository(baseline_model_web)
    assert final_model_web.system.total_footprint.efootprint_object == initial_total_footprint


def test_integration_edge_modeling_emissions_non_zero(default_system_repository):
    network_id = next(iter(DEFAULT_NETWORKS.keys()))
    country_id = next(iter(DEFAULT_COUNTRIES.keys()))

    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Device", "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )

    edge_usage_journey_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Edge Usage Journey", "EdgeUsageJourney", edge_functions=""),
    )

    edge_function_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs=""),
        parent_id=edge_usage_journey_id,
    )

    create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Process", "RecurrentEdgeProcess", edge_device=edge_device_id),
        parent_id=edge_function_id,
    )

    create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Usage Pattern", "EdgeUsagePattern",
            edge_usage_journey=edge_usage_journey_id,
            network=network_id,
            country=country_id,
            hourly_edge_usage_journey_starts__initial_volume=100,
        ),
    )

    emissions = ModelWeb(default_system_repository).system_emissions
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
