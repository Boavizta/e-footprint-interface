"""Build the ``iot_industrial`` introductory template.

Factory sensors measure machine data, upload readings to a server, and analysts
open a web dashboard to review the stored readings. Contains both edge and web
objects, so loading it latches the edge modeling toggle on (Step 5).
"""

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromConstant,
)
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerTypes
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


def _recurrent_constant(value: float, unit: str) -> ExplainableRecurrentQuantitiesFromConstant:
    return ExplainableRecurrentQuantitiesFromConstant(
        {"constant_value": value, "constant_unit": unit}, source=Sources.HYPOTHESIS)


def _default_sensor_process_kwargs() -> dict:
    return {
        "recurrent_compute_needed": _recurrent_constant(1, "cpu_core"),
        "recurrent_ram_needed": _recurrent_constant(1, "GB_ram"),
        "recurrent_storage_needed": _recurrent_constant(0, "GB_stored"),
    }


def build_system() -> System:
    server_storage = Storage.from_defaults(
        "Sensor readings storage", base_storage_need=SourceValue(500 * u.GB_stored))
    data_server = BoaviztaCloudServer.from_defaults(
        "Sensor data server", server_type=ServerTypes.on_premise(),
        provider=SourceObject("scaleway"),
        instance_type=SourceObject("ent1-l"),
        base_ram_consumption=SourceValue(4 * u.GB_ram),
        base_compute_consumption=SourceValue(0.25 * u.cpu_core),
        average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
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
        "Measure temperature and vibration",
        edge_device=factory_sensor,
        **_default_sensor_process_kwargs())
    keep_recent_readings = RecurrentEdgeProcess.from_defaults(
        "Keep recent readings on the sensor",
        edge_device=factory_sensor,
        **_default_sensor_process_kwargs())
    upload_sensor_data = RecurrentServerNeed.from_defaults(
        "Upload sensor readings", edge_device=factory_sensor,
        recurrent_volume_per_edge_device=_recurrent_constant(1, "occurrence"),
        jobs=[receive_sensor_data, store_sensor_data])

    edge_function = EdgeFunction(
        "Sensor records and uploads readings",
        recurrent_edge_device_needs=[measure_machine_data, keep_recent_readings],
        recurrent_server_needs=[upload_sensor_data])
    edge_usage_journey = EdgeUsageJourney.from_defaults(
        "Sensor working week", edge_functions=[edge_function])

    laptop = Device.laptop()
    network = Network.wifi_network()
    france = Countries.FRANCE()

    analyst_usage_pattern = UsagePattern(
        "Daily analyst sessions", analyst_journey, [laptop],
        network, france,
        ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": "2025-01-01",
            "modeling_duration_value": 3,
            "modeling_duration_unit": "year",
            "initial_volume": 14400,
            "initial_volume_timespan": "year",
            "net_growth_rate_in_percentage": 5,
            "net_growth_rate_timespan": "year",
        }, source=Sources.USER_DATA))

    edge_usage_pattern = EdgeUsagePattern(
        "Factory sensors starting up",
        edge_usage_journey=edge_usage_journey,
        network=network,
        country=france,
        hourly_edge_usage_journey_starts=ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": "2025-01-01",
            "modeling_duration_value": 1,
            "modeling_duration_unit": "month",
            "initial_volume": 750,
            "initial_volume_timespan": "month",
            "net_growth_rate_in_percentage": 0,
            "net_growth_rate_timespan": "month",
        }, source=Sources.USER_DATA))

    return System(
        "Factory sensors and analysis system",
        [analyst_usage_pattern],
        edge_usage_patterns=[edge_usage_pattern])
