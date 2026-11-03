"""Unit tests for DeleteObjectUseCase.

These tests focus on the generic orchestration behavior of the use case,
not object-specific deletion rules (those belong in entity tests).
"""
from copy import deepcopy
from datetime import datetime

import numpy as np
import pytest
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from pint import Quantity

from model_builder.adapters.presenters.simplified_inputs import input_catalog
from unittest.mock import patch, MagicMock

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.application.use_cases.delete_object import (
    DeleteObjectUseCase, DeleteObjectInput, DeleteCheckResult)
from model_builder.application.use_cases.edit_object import EditObjectInput, EditObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.services.object_linking_service import serialize_weighted_dict_entry
from tests.fixtures.system_builders import create_hourly_usage


def _usage_pattern(name, journeys):
    return UsagePattern(
        name, usage_journeys={journey: SourceValue(1 * u.dimensionless) for journey in journeys},
        devices=[Device.from_defaults(f"{name} device")], network=Network.from_defaults(f"{name} network"),
        country=Countries.FRANCE(), hourly_occurrences=create_hourly_usage())


def _edge_usage_pattern(name, journeys):
    return EdgeUsagePattern(
        name, edge_usage_journeys=journeys, network=Network.wifi_network(), country=Countries.FRANCE(),
        hourly_deployment_starts=create_source_hourly_values_from_list([1000] * 9, datetime(2025, 1, 1)))


def _journey_in_two_journey_pattern(shared_child=True):
    step = UsageJourneyStep.from_defaults("Step", jobs=[])
    journey = UsageJourney("Journey", uj_steps=[step])
    other_step = step if shared_child else UsageJourneyStep.from_defaults("Other step", jobs=[])
    pattern = _usage_pattern("Pattern", [journey, UsageJourney("Other journey", uj_steps=[other_step])])
    return System("System", usage_patterns=[pattern], edge_usage_patterns=[]), journey, ["Pattern"]


def _edge_journey_in_two_journey_edge_pattern(shared_child=True):
    function = EdgeFunction("Function", recurrent_edge_device_needs=[], recurrent_server_needs=[])
    journey = EdgeUsageJourney.from_defaults("Edge journey", edge_functions=[function])
    other_function = function if shared_child else EdgeFunction(
        "Other function", recurrent_edge_device_needs=[], recurrent_server_needs=[])
    pattern = _edge_usage_pattern(
        "Edge pattern", [journey, EdgeUsageJourney.from_defaults("Other edge journey", edge_functions=[other_function])])
    return System("System", usage_patterns=[], edge_usage_patterns=[pattern]), journey, ["Edge pattern"]


def _journey_in_two_patterns():
    step = UsageJourneyStep.from_defaults("Step", jobs=[])
    journey = UsageJourney("Journey", uj_steps=[step])
    shared_pattern = _usage_pattern("Shared pattern", [journey, UsageJourney("Other journey", uj_steps=[step])])
    sole_pattern = _usage_pattern("Sole pattern", [journey])
    system = System("System", usage_patterns=[shared_pattern, sole_pattern], edge_usage_patterns=[])
    return system, journey, ["Shared pattern", "Sole pattern"]


def _edge_component_in_device(with_need=True):
    cpu = EdgeCPUComponent.from_defaults("CPU")
    device = EdgeDevice.from_defaults("Device", components=[cpu])
    cpu_need = RecurrentEdgeComponentNeed(
        "CPU need", edge_component=cpu,
        recurrent_need=SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)))
    device_need = RecurrentEdgeDeviceNeed(
        "Device need", edge_device=device, recurrent_edge_component_needs=[cpu_need] if with_need else [])
    function = EdgeFunction("Function", recurrent_edge_device_needs=[device_need], recurrent_server_needs=[])
    journey = EdgeUsageJourney.from_defaults("Edge journey", edge_functions=[function])
    pattern = _edge_usage_pattern("Edge pattern", [journey])
    return System("System", usage_patterns=[], edge_usage_patterns=[pattern]), cpu, ["CPU need"]


class TestDeleteObjectUseCase:
    """Tests for DeleteObjectUseCase orchestration behavior."""

    # --- check_can_delete ---

    def test_check_can_delete_returns_delete_check_result(self, minimal_model_web):
        """check_can_delete returns a DeleteCheckResult."""
        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)

        result = use_case.check_can_delete(minimal_model_web.servers[0].efootprint_id)

        assert isinstance(result, DeleteCheckResult)

    def test_check_can_delete_blocked_object_returns_container_names(self, minimal_model_web):
        """When blocked, result includes blocking container names as strings."""
        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)
        uj = minimal_model_web.usage_journeys[0]

        result = use_case.check_can_delete(uj.efootprint_id)

        assert result.can_delete is False
        assert len(result.blocking_containers) > 0
        assert all(isinstance(name, str) for name in result.blocking_containers)

    def test_check_can_delete_uses_class_can_delete_hook(self, minimal_model_web):
        """Uses web class can_delete hook when available."""
        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)
        server = minimal_model_web.servers[0]

        result = use_case.check_can_delete(server.efootprint_id)

        # ServerWeb.can_delete checks jobs specifically, not generic containers
        assert result.can_delete is False
        assert "Test Job" in result.blocking_containers

    # --- execute ---

    def test_execute_returns_deleted_object_info(self, minimal_model_web):
        """execute returns info about the deleted object."""
        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)
        up = minimal_model_web.usage_patterns[0]

        output = use_case.execute(DeleteObjectInput(object_id=up.efootprint_id))

        assert output.deleted_object_name == up.name
        assert output.deleted_object_type == "UsagePattern"

    def test_execute_persists_deletion_to_repository(self, minimal_repository, minimal_model_web):
        """execute persists the deletion to the repository."""
        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)
        up_id = minimal_model_web.usage_patterns[0].efootprint_id

        use_case.execute(DeleteObjectInput(object_id=up_id))

        updated_data = minimal_repository.get_system_data()
        assert up_id not in updated_data.get("UsagePattern", {})

    def test_execute_calls_pre_delete_hook_when_defined(self, minimal_model_web):
        """execute calls pre_delete hook on web class when defined."""
        from model_builder.domain.entities.web_core.usage.usage_pattern_web import UsagePatternWeb

        use_case = DeleteObjectUseCase(minimal_model_web, input_catalog)
        up = minimal_model_web.usage_patterns[0]
        original_pre_delete = UsagePatternWeb.pre_delete

        # Wrap original to track calls while preserving behavior
        with patch.object(
            UsagePatternWeb, 'pre_delete',
            wraps=original_pre_delete
        ) as mock_pre_delete:
            use_case.execute(DeleteObjectInput(object_id=up.efootprint_id))

            mock_pre_delete.assert_called_once()

    # --- referenced objects ---

    @pytest.mark.parametrize("build", [
        _journey_in_two_journey_pattern, _edge_journey_in_two_journey_edge_pattern, _journey_in_two_patterns,
        _edge_component_in_device], ids=lambda build: build.__name__.strip("_"))
    def test_check_can_delete_blocks_referenced_objects_naming_every_holder(self, build):
        """Confirmation names every blocking reference without changing the model."""
        system, target, holders = build()
        repository = InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False))
        use_case = DeleteObjectUseCase(ModelWeb(repository), input_catalog)

        data_before = deepcopy(repository.get_system_data())
        model_before = deepcopy(use_case.model_web.to_json(save_computed_state=False))

        result = use_case.check_can_delete(target.id)

        assert result.can_delete is False
        assert sorted(result.blocking_containers) == holders
        assert repository.get_system_data() == data_before
        assert use_case.model_web.to_json(save_computed_state=False) == model_before

    @pytest.mark.parametrize("build, relationship, child_type", [
        (_journey_in_two_journey_pattern, "usage_journeys", "UsageJourneyStep"),
        (_edge_journey_in_two_journey_edge_pattern, "edge_usage_journeys", "EdgeFunction"),
    ], ids=["journey", "edge_journey"])
    def test_detached_journey_passes_check_and_deletes_with_unshared_children(self, build, relationship, child_type):
        system, target, _ = build(shared_child=False)
        repository = InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False))
        model_web = ModelWeb(repository)
        target_web = model_web.get_web_object_from_efootprint_id(target.id)
        child_ids = {child.efootprint_id for child in target_web.accordion_children}
        pattern = target_web.modeling_obj_containers[0]
        members = pattern.get_efootprint_value(relationship)
        remaining_ids = [journey.id for journey in members if journey.id != target.id]
        value = {journey.id: serialize_weighted_dict_entry(weight) for journey, weight in members.items()
                 if journey.id != target.id} if isinstance(members, dict) else remaining_ids

        EditObjectUseCase(model_web, input_catalog).execute(EditObjectInput(
            object_id=pattern.efootprint_id, form_data={"name": pattern.name, relationship: value}))
        model_web = ModelWeb(repository)
        assert target.id in model_web.flat_efootprint_objs_dict
        use_case = DeleteObjectUseCase(model_web, input_catalog)
        assert use_case.check_can_delete(target.id).can_delete is True

        use_case.execute(DeleteObjectInput(object_id=target.id))

        saved = repository.get_system_data()
        assert target.id not in saved.get(target.class_as_simple_str, {})
        assert child_ids
        assert child_ids.isdisjoint(saved.get(child_type, {}))
        assert all(journey_id in saved[target.class_as_simple_str] for journey_id in remaining_ids)

    def test_component_without_need_passes_check_and_deletes_from_device(self):
        system, target, _ = _edge_component_in_device(with_need=False)
        repository = InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False))
        model_web = ModelWeb(repository)
        device = model_web.get_web_object_from_efootprint_id(target.id).modeling_obj_containers[0]
        use_case = DeleteObjectUseCase(model_web, input_catalog)
        assert use_case.check_can_delete(target.id).can_delete is True

        use_case.execute(DeleteObjectInput(object_id=target.id))

        reopened = ModelWeb(repository)
        assert target.id not in reopened.flat_efootprint_objs_dict
        assert reopened.get_web_object_from_efootprint_id(device.efootprint_id).components == []
