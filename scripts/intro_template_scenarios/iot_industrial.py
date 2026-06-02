"""Build the ``iot_industrial`` introductory template.

Factory sensors measure machine data, upload readings to a server, and analysts
open a web dashboard to review the stored readings. Contains both edge and web
objects, so loading it latches the edge modeling toggle on (Step 5).
"""
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.time_builders import create_hourly_usage_from_frequency, create_source_hourly_values_from_list
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    server_storage = Storage.from_defaults(
        "Sensor readings storage", base_storage_need=SourceValue(500 * u.GB_stored))
    data_server = Server.from_defaults(
        "Sensor data server", server_type=ServerTypes.on_premise(),
        base_ram_consumption=SourceValue(4 * u.GB_ram),
        base_compute_consumption=SourceValue(0.25 * u.cpu_core),
        storage=server_storage)

    receive_sensor_data = Job(
        "Receive sensor upload", server=data_server,
        request_duration=SourceValue(200 * u.ms),
        compute_needed=SourceValue(0.05 * u.cpu_core),
        ram_needed=SourceValue(80 * u.MB_ram),
        data_transferred=SourceValue(30 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    store_sensor_data = Job(
        "Store sensor reading", server=data_server,
        request_duration=SourceValue(250 * u.ms),
        compute_needed=SourceValue(0.08 * u.cpu_core),
        ram_needed=SourceValue(100 * u.MB_ram),
        data_transferred=SourceValue(8 * u.kB),
        data_stored=SourceValue(25 * u.kB_stored))

    open_dashboard = Job(
        "Open analysis dashboard", server=data_server,
        request_duration=SourceValue(150 * u.ms),
        compute_needed=SourceValue(0.08 * u.cpu_core),
        ram_needed=SourceValue(120 * u.MB_ram),
        data_transferred=SourceValue(800 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    load_recent_readings = Job(
        "Load recent sensor readings", server=data_server,
        request_duration=SourceValue(600 * u.ms),
        compute_needed=SourceValue(0.25 * u.cpu_core),
        ram_needed=SourceValue(300 * u.MB_ram),
        data_transferred=SourceValue(2 * u.MB),
        data_stored=SourceValue(0 * u.kB_stored))
    run_daily_report = Job(
        "Prepare daily analysis report", server=data_server,
        request_duration=SourceValue(2 * u.s),
        compute_needed=SourceValue(0.5 * u.cpu_core),
        ram_needed=SourceValue(512 * u.MB_ram),
        data_transferred=SourceValue(1 * u.MB),
        data_stored=SourceValue(200 * u.kB_stored))

    dashboard_steps = [
        UsageJourneyStep.from_defaults("Open the dashboard", jobs=[open_dashboard]),
        UsageJourneyStep.from_defaults("Review recent readings", jobs=[load_recent_readings]),
        UsageJourneyStep.from_defaults("Create a daily report", jobs=[run_daily_report]),
    ]
    analyst_journey = UsageJourney("Analyst reviews sensor data", uj_steps=dashboard_steps)

    edge_storage = EdgeStorage.from_defaults(
        "Sensor local storage", base_storage_need=SourceValue(2 * u.GB_stored))
    factory_sensor = EdgeComputer.from_defaults(
        "Factory sensor", storage=edge_storage,
        base_compute_consumption=SourceValue(0.02 * u.cpu_core))

    measure_machine_data = RecurrentEdgeProcess.from_defaults(
        "Measure temperature and vibration", edge_device=factory_sensor)
    keep_recent_readings = RecurrentEdgeProcess.from_defaults(
        "Keep recent readings on the sensor", edge_device=factory_sensor)
    upload_sensor_data = RecurrentServerNeed.from_defaults(
        "Upload sensor readings", edge_device=factory_sensor,
        jobs=[receive_sensor_data, store_sensor_data])

    edge_function = EdgeFunction(
        "Sensor records and uploads readings",
        recurrent_edge_device_needs=[measure_machine_data, keep_recent_readings],
        recurrent_server_needs=[upload_sensor_data])
    edge_usage_journey = EdgeUsageJourney.from_defaults(
        "Sensor working day", edge_functions=[edge_function])

    start_date = datetime(2025, 1, 1)
    analyst_usage_pattern = UsagePattern(
        "Daily analyst sessions", analyst_journey, [Device.laptop("Analyst laptop")],
        Network.from_defaults("Office network"), Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=40, frequency="daily", start_date=start_date))

    # Sensors are added during the first day and then keep running for their usage span.
    edge_usage_pattern = EdgeUsagePattern(
        "Factory sensors starting up",
        edge_usage_journey=edge_usage_journey,
        network=Network.wifi_network(),
        country=Countries.FRANCE(),
        hourly_edge_usage_journey_starts=create_source_hourly_values_from_list(
            [elt * 50 for elt in [1, 1, 2, 2, 3, 3, 2, 2, 1]], start_date))

    return System(
        "Factory sensors and analysis system",
        [analyst_usage_pattern],
        edge_usage_patterns=[edge_usage_pattern])
