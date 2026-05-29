"""Build the ``ecommerce`` introductory template.

A classical web service: a three-step shopping journey (browse, add to cart,
checkout) served by a single web server backed by a relational database
(modelled as Storage attached to the Server). Wired into a daily usage pattern
so the template loads as a runnable System whose results compute.
"""
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_hourly_usage_from_frequency
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    storage = Storage.from_defaults(
        "Product database storage", base_storage_need=SourceValue(200 * u.GB_stored))
    web_server = Server.from_defaults(
        "Web server", server_type=ServerTypes.autoscaling(),
        base_ram_consumption=SourceValue(4 * u.GB_ram),
        base_compute_consumption=SourceValue(0.2 * u.cpu_core),
        storage=storage)

    browse_job = Job(
        "Load catalog page", server=web_server,
        request_duration=SourceValue(120 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(80 * u.MB_ram),
        data_transferred=SourceValue(1.5 * u.MB),
        data_stored=SourceValue(1 * u.kB_stored))
    add_to_cart_job = Job(
        "Add to cart", server=web_server,
        request_duration=SourceValue(60 * u.ms),
        compute_needed=SourceValue(0.05 * u.cpu_core),
        ram_needed=SourceValue(40 * u.MB_ram),
        data_transferred=SourceValue(30 * u.kB),
        data_stored=SourceValue(2 * u.kB_stored))
    checkout_job = Job(
        "Submit order", server=web_server,
        request_duration=SourceValue(200 * u.ms),
        compute_needed=SourceValue(0.15 * u.cpu_core),
        ram_needed=SourceValue(120 * u.MB_ram),
        data_transferred=SourceValue(80 * u.kB),
        data_stored=SourceValue(10 * u.kB_stored))

    browse_step = UsageJourneyStep.from_defaults("Browse the catalog", jobs=[browse_job])
    cart_step = UsageJourneyStep.from_defaults("Add an item to the cart", jobs=[add_to_cart_job])
    checkout_step = UsageJourneyStep.from_defaults("Check out", jobs=[checkout_job])
    journey = UsageJourney("Shopping journey", uj_steps=[browse_step, cart_step, checkout_step])

    start_date = datetime(2025, 1, 1)
    usage_pattern = UsagePattern(
        "Daily shoppers", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=5000, frequency="daily", start_date=start_date))

    return System("Classical e-commerce system", [usage_pattern], edge_usage_patterns=[])
