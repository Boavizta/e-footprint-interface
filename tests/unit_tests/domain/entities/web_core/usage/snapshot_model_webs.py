"""Helpers for building deterministic ModelWeb stubs for snapshot tests."""
from copy import deepcopy
from dataclasses import dataclass
from unittest.mock import MagicMock

from efootprint.constants.units import u


@dataclass
class _MockModelingObjectWeb:
    id: str
    name: str


def build_basic_model_web():
    """Basic model_web stub with deterministic option lists."""
    model_web = MagicMock()
    option1 = _MockModelingObjectWeb(id="efootprint_id1", name="option1")
    option2 = _MockModelingObjectWeb(id="efootprint_id2", name="option2")
    model_web.get_efootprint_objects_from_efootprint_type.side_effect = lambda _: [option1, option2]
    model_web.get_web_objects_from_efootprint_type.return_value = []
    return model_web


def build_usage_pattern_model_web():
    """Model web stub with journeys for usage pattern prerequisites."""
    model_web = build_basic_model_web()
    mock_journey = MagicMock()
    mock_journey.name = "mock_journey"
    mock_journey.id = "mock_journey_efootprint_id"
    model_web.usage_journeys = [mock_journey]
    model_web.edge_usage_journeys = [mock_journey]
    return model_web


def build_recurrent_edge_device_need_model_web():
    """Model web stub with edge devices for recurrent edge device need snapshots."""
    model_web = build_basic_model_web()

    mock_edge_device = MagicMock()
    mock_edge_device.configure_mock(
        name="mock_edge_device",
        efootprint_id="mock_edge_device_efootprint_id",
        class_as_simple_str="EdgeComputer",
    )
    mock_edge_device2 = MagicMock()
    mock_edge_device2.configure_mock(
        name="mock_edge_device2",
        efootprint_id="mock_edge_device2_efootprint_id",
        class_as_simple_str="EdgeAppliance",
    )
    mock_edge_device3 = MagicMock()
    mock_edge_device3.configure_mock(
        name="mock_edge_device3",
        efootprint_id="mock_edge_device3_efootprint_id",
        class_as_simple_str="EdgeDevice",
    )
    model_web.edge_devices = [mock_edge_device, mock_edge_device2, mock_edge_device3]
    return model_web


def build_recurrent_edge_component_need_model_web():
    """Model web stub for recurrent edge component need snapshots."""
    model_web = build_basic_model_web()

    mock_edge_component = MagicMock()
    mock_edge_component.configure_mock(
        name="mock_edge_component",
        efootprint_id="mock_edge_component_efootprint_id",
    )
    mock_edge_component.get_efootprint_value.return_value = [u.cpu_core]

    mock_recurrent_edge_device_need = MagicMock()
    mock_edge_device = MagicMock()
    mock_edge_device.configure_mock(
        name="mock_edge_device",
        efootprint_id="mock_edge_device_efootprint_id",
    )
    mock_recurrent_edge_device_need.edge_device = mock_edge_device
    mock_edge_device.components = [mock_edge_component]

    model_web.get_web_object_from_efootprint_id.return_value = mock_recurrent_edge_device_need
    return model_web


def build_basic_edge_devices_model_web():
    """Model web stub exposing edge devices for recurrent server need tests."""
    model_web = build_basic_model_web()
    mock_edge_device = MagicMock()
    mock_edge_device.configure_mock(
        name="edge_device",
        efootprint_id="edge_device_efootprint_id",
        class_as_simple_str="EdgeDevice",
    )
    model_web.edge_devices = [mock_edge_device]
    return model_web
