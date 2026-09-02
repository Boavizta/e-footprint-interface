"""Integration tests for edge object creation, linking, and lifecycle."""

import json
from copy import deepcopy

import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.timeseries import ExplainableRecurrentQuantitiesFromWeeklyPattern
from efootprint.constants.units import u

from model_builder.domain.entities.web_core.model_web import ModelWeb
from tests.fixtures.form_data_builders import create_post_data_from_class_default_values
from tests.fixtures.use_case_helpers import create_object, delete_object, edit_object


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
            "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs=""
        ),
        parent_id=edge_usage_journey_id,
    )
    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Computer",
            "EdgeComputer",
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


def test_recurrent_negativity_uses_model_validation(default_system_repository):
    edge_device_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Validation Edge Computer",
            "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Validation Storage", "EdgeStorage"),
        ),
    )

    with pytest.raises(ValueError, match="should be positive but is negative"):
        create_object(
            default_system_repository,
            create_post_data_from_class_default_values(
                "Negative Compute Process",
                "RecurrentEdgeProcess",
                edge_device=edge_device_id,
                recurrent_compute_needed__constant_value="-1",
            ),
        )

    with pytest.raises(ValueError, match="should be positive but is negative"):
        create_object(
            default_system_repository,
            create_post_data_from_class_default_values(
                "Negative Weekly Compute Process",
                "RecurrentEdgeProcess",
                edge_device=edge_device_id,
                recurrent_compute_needed__weekly_pattern={
                    "unit": "cpu_core",
                    "profiles": [{"name": "all week", "days": list(range(7)), "baseline": -1, "ranges": []}],
                },
            ),
        )

    process_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Negative Storage Process",
            "RecurrentEdgeProcess",
            edge_device=edge_device_id,
            recurrent_storage_needed__constant_value="-1",
        ),
    )

    process = ModelWeb(default_system_repository).get_efootprint_object_from_efootprint_id(
        process_id, "RecurrentEdgeProcess"
    )
    assert process.recurrent_storage_needed.magnitude.min() == -1


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


def test_delete_edge_device_with_cpu_component(default_system_repository):
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
    assert edge_device_id in sd["EdgeDevice"]
    assert cpu_id in sd["EdgeDevice"][edge_device_id]["components"]

    delete_object(default_system_repository, edge_device_id)

    sd = _system_data(default_system_repository)
    assert "EdgeDevice" not in sd
    assert "EdgeCPUComponent" not in sd


def test_edge_computer_cpu_component_fixed_inputs_are_excluded_from_source_table(default_system_repository):
    edge_computer_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Computer",
            "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )
    model_web = ModelWeb(default_system_repository)
    edge_computer = model_web.get_web_object_from_efootprint_id(edge_computer_id)
    cpu_component = edge_computer.cpu_component
    cpu_component_id = cpu_component.efootprint_id

    source_table_rows = {
        (row.modeling_obj_container.efootprint_id, row.attr_name_in_mod_obj_container)
        for row in model_web.web_explainable_quantities_sources
    }

    # The CPU component's per-unit fabrication carries a source but is a fixed spec, not a constructor
    # input, so it is excluded from the editable source table — a non-trivial exclusion (the value is
    # genuinely sourced, it is filtered out by not being an init/computed attribute, not by lacking a
    # source).
    assert cpu_component.modeling_obj.carbon_footprint_fabrication_per_unit.source is not None
    assert (cpu_component_id, "carbon_footprint_fabrication_per_unit") not in source_table_rows


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
            "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs=""
        ),
        parent_id=edge_usage_journey_id,
    )
    redn_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test REDN", "RecurrentEdgeDeviceNeed", edge_device=edge_device_id, recurrent_edge_component_needs=""
        ),
        parent_id=edge_function_id,
    )
    cpu_need_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "CPU Need",
            "RecurrentEdgeComponentNeed",
            edge_component=cpu_id,
            **{
                "recurrent_need__weekly_pattern": {
                    "unit": "cpu_core",
                    "profiles": [
                        {
                            "name": "weekday",
                            "days": [0, 1, 2, 3, 4],
                            "baseline": 2,
                            "ranges": [{"start": 8, "end": 18, "value": 5}],
                        },
                        {"name": "weekend", "days": [5, 6], "baseline": 1, "ranges": []},
                        {"name": "unused", "days": [], "baseline": 0, "ranges": []},
                    ],
                }
            },
        ),
        parent_id=redn_id,
    )
    ram_need_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "RAM Need",
            "RecurrentEdgeComponentNeed",
            edge_component=ram_id,
            **{"recurrent_need__constant_value": "4.0", "recurrent_need__constant_unit": "GB_ram"},
        ),
        parent_id=redn_id,
    )

    sd = _system_data(default_system_repository)
    assert redn_id in sd["EdgeFunction"][edge_function_id]["recurrent_edge_device_needs"]
    component_needs = sd["RecurrentEdgeDeviceNeed"][redn_id]["recurrent_edge_component_needs"]
    assert set(component_needs) == {cpu_need_id, ram_need_id}

    reopened = ModelWeb(default_system_repository)
    cpu_need = reopened.get_efootprint_object_from_efootprint_id(cpu_need_id, "RecurrentEdgeComponentNeed")
    assert isinstance(cpu_need.recurrent_need, ExplainableRecurrentQuantitiesFromWeeklyPattern)
    assert [profile["name"] for profile in cpu_need.recurrent_need.form_inputs["profiles"]] == [
        "weekday",
        "weekend",
        "unused",
    ]
    assert len(cpu_need.recurrent_need.value.magnitude) == 168
    assert cpu_need.recurrent_need.value.magnitude[8] == 5

    edited_authored_state = deepcopy(cpu_need.recurrent_need.form_inputs)
    edited_authored_state["profiles"][2].update(
        {"name": "unused audit profile", "baseline": 7, "ranges": [{"start": 2, "end": 3, "value": 9}]}
    )
    edit_object(
        default_system_repository,
        cpu_need_id,
        "RecurrentEdgeComponentNeed",
        {"recurrent_need__weekly_pattern": json.dumps(edited_authored_state)},
    )

    reopened = ModelWeb(default_system_repository)
    cpu_need = reopened.get_efootprint_object_from_efootprint_id(cpu_need_id, "RecurrentEdgeComponentNeed")
    assert cpu_need.recurrent_need.form_inputs["profiles"][2] == edited_authored_state["profiles"][2]
    assert cpu_need.recurrent_need.value.magnitude[8] == 5

    same_output_weekly_pattern = {
        "unit": "GB_ram",
        "profiles": [
            {"name": "all week", "days": list(range(7)), "baseline": 4, "ranges": []},
            {"name": "unused", "days": [], "baseline": 0, "ranges": []},
        ],
    }
    edit_object(
        default_system_repository,
        ram_need_id,
        "RecurrentEdgeComponentNeed",
        {"recurrent_need__weekly_pattern": json.dumps(same_output_weekly_pattern)},
    )

    reopened = ModelWeb(default_system_repository)
    ram_need = reopened.get_efootprint_object_from_efootprint_id(ram_need_id, "RecurrentEdgeComponentNeed")
    assert isinstance(ram_need.recurrent_need, ExplainableRecurrentQuantitiesFromWeeklyPattern)
    assert ram_need.recurrent_need.form_inputs == same_output_weekly_pattern


def test_failed_creation_leaves_system_unchanged(default_system_repository):
    """Creating a RecurrentEdgeProcess fails when EdgeComputer.lifespan < EdgeUsageJourney.usage_span."""
    edge_usage_journey_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Long Journey",
            "EdgeUsageJourney",
            edge_functions="",
            usage_span=SourceValue(10 * u.yr),  # longer than EdgeComputer default lifespan (6yr)
        ),
    )
    edge_function_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Test Edge Function", "EdgeFunction", recurrent_edge_device_needs="", recurrent_server_needs=""
        ),
        parent_id=edge_usage_journey_id,
    )
    edge_computer_id = create_object(
        default_system_repository,
        create_post_data_from_class_default_values(
            "Short-Lived Computer",
            "EdgeComputer",
            EdgeStorage_form_data=create_post_data_from_class_default_values("Test Edge Storage", "EdgeStorage"),
        ),
    )

    structure_before = set(_system_data(default_system_repository).keys())

    with pytest.raises(Exception):
        create_object(
            default_system_repository,
            create_post_data_from_class_default_values(
                "Faulty Process", "RecurrentEdgeProcess", edge_device=edge_computer_id
            ),
            parent_id=edge_function_id,
        )

    assert set(_system_data(default_system_repository).keys()) == structure_before
