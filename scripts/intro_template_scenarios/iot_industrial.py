"""Build the ``iot_industrial`` introductory template.

A fleet of connected industrial edge gateways: each runs two recurrent on-device
workloads (telemetry collection and local anomaly detection) bundled into one
edge function. The device fleet is represented by the volume of hourly edge
usage-journey starts. Contains edge objects, so loading it latches the edge
modeling toggle on (Step 5).
"""
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


def build_system() -> System:
    edge_storage = EdgeStorage.from_defaults(
        "Gateway storage", base_storage_need=SourceValue(50 * u.GB_stored))
    edge_gateway = EdgeComputer.from_defaults(
        "Industrial edge gateway", storage=edge_storage,
        base_compute_consumption=SourceValue(0.2 * u.cpu_core))

    telemetry_process = RecurrentEdgeProcess.from_defaults(
        "Telemetry collection", edge_device=edge_gateway)
    anomaly_detection_process = RecurrentEdgeProcess.from_defaults(
        "Local anomaly detection", edge_device=edge_gateway)

    edge_function = EdgeFunction(
        "Gateway workload",
        recurrent_edge_device_needs=[telemetry_process, anomaly_detection_process],
        recurrent_server_needs=[])
    edge_usage_journey = EdgeUsageJourney.from_defaults(
        "Gateway operation", edge_functions=[edge_function])

    start_date = datetime(2025, 1, 1)
    # Hourly journey starts scaled to a fleet of devices coming online over the day.
    edge_usage_pattern = EdgeUsagePattern(
        "Connected device fleet",
        edge_usage_journey=edge_usage_journey,
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
            [elt * 100 for elt in [1, 1, 2, 2, 3, 3, 2, 2, 1]], start_date))

    return System("Industrial IoT system", [], edge_usage_patterns=[edge_usage_pattern])
