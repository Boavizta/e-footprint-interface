"""Integration tests for edge object creation, linking, and lifecycle."""
import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object


def _system_data(repository) -> dict:
    return repository.get_system_data()


def test_create_edge_usage_journey(default_system_repository):
    create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Edge Usage Journey", "EdgeUsageJourney", edge_functions=""),
    )
    assert len(ModelWeb(default_system_repository).edge_usage_journeys) == 1
    assert ModelWeb(default_system_repository).edge_usage_journeys[0].name == "Test Edge Usage Journey"


def test_recurrent_edge_process_is_linked_through_hierarchy(default_system_repository):
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
    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Computer", "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )
    rep_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Process", "RecurrentEdgeProcess", edge_device=edge_device_id),
        parent_id=edge_function_id,
    )

    sd = _system_data(default_system_repository)
    assert rep_id in sd["EdgeFunction"][edge_function_id]["recurrent_edge_device_needs"]
    assert edge_function_id in sd["EdgeUsageJourney"][edge_usage_journey_id]["edge_functions"]


def test_edge_device_component_lifecycle(default_system_repository):
    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Edge Device", "EdgeDevice", components=""),
    )
    cpu_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test CPU Component", "EdgeCPUComponent"),
        parent_id=edge_device_id,
    )

    sd = _system_data(default_system_repository)
    assert cpu_id in sd["EdgeDevice"][edge_device_id]["components"]

    delete_object(default_system_repository, cpu_id)

    sd = _system_data(default_system_repository)
    assert "EdgeCPUComponent" not in sd
    assert sd["EdgeDevice"][edge_device_id]["components"] == []


def test_recurrent_edge_device_need_with_component_needs(default_system_repository):
    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test Edge Device", "EdgeDevice", components=""),
    )
    cpu_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test CPU Component", "EdgeCPUComponent"),
        parent_id=edge_device_id,
    )
    ram_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values("Test RAM Component", "EdgeRAMComponent"),
        parent_id=edge_device_id,
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
    redn_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test REDN", "RecurrentEdgeDeviceNeed",
            edge_device=edge_device_id, recurrent_edge_component_needs=""),
        parent_id=edge_function_id,
    )
    cpu_need_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "CPU Need", "RecurrentEdgeComponentNeed", edge_component=cpu_id,
            **{"recurrent_need__constant_value": "2.0", "recurrent_need__constant_unit": "cpu_core"}),
        parent_id=redn_id,
    )
    ram_need_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "RAM Need", "RecurrentEdgeComponentNeed", edge_component=ram_id,
            **{"recurrent_need__constant_value": "4.0", "recurrent_need__constant_unit": "GB_ram"}),
        parent_id=redn_id,
    )

    sd = _system_data(default_system_repository)
    assert redn_id in sd["EdgeFunction"][edge_function_id]["recurrent_edge_device_needs"]
    component_needs = sd["RecurrentEdgeDeviceNeed"][redn_id]["recurrent_edge_component_needs"]
    assert set(component_needs) == {cpu_need_id, ram_need_id}


def test_failed_creation_leaves_system_unchanged(default_system_repository):
    """Creating a RecurrentEdgeProcess fails when EdgeComputer.lifespan < EdgeUsageJourney.usage_span."""
    edge_usage_journey_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Long Journey", "EdgeUsageJourney", edge_functions="",
            usage_span=SourceValue(10 * u.yr),  # longer than EdgeComputer default lifespan (6yr)
        ),
    )
    edge_function_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs=""),
        parent_id=edge_usage_journey_id,
    )
    edge_computer_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Short-Lived Computer", "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )

    structure_before = set(_system_data(default_system_repository).keys())

    with pytest.raises(Exception):
        create_object(
            default_system_repository,
            create_post_data_from_class_default_values(
                "Faulty Process", "RecurrentEdgeProcess", edge_device=edge_computer_id),
            parent_id=edge_function_id,
        )

    assert set(_system_data(default_system_repository).keys()) == structure_before
