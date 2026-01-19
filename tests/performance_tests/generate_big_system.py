from time import time

import numpy as np
from pint import Quantity

from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern

from model_builder.domain.entities.efootprint_extensions.explainable_hourly_quantities_from_form_inputs import \
    ExplainableHourlyQuantitiesFromFormInputs

start = time()

import os
os.environ["USE_BOAVIZTAPI_PACKAGE"] = "true"

from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.tools import time_it
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceRecurrentValues
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.services.video_streaming import VideoStreaming, VideoStreamingJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job, GPUJob
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.constants.countries import country_generator, tz, Countries
from efootprint.constants.units import u
from efootprint.logger import logger
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")

root_dir = os.path.dirname(os.path.abspath(__file__))


def generate_big_system(
        nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3,
        nb_of_edge_usage_patterns=3, nb_of_edge_processes_per_edge_computer=3, nb_years=5):
    start = time()
    usage_patterns = []
    for server_index in range(1, nb_of_servers_of_each_type + 1):
        autoscaling_server = Server.from_defaults(
            f"server {server_index}",
            server_type=ServerTypes.autoscaling(),
            storage=Storage.ssd(f"storage of autoscaling server {server_index}")
        )

        serverless_server = BoaviztaCloudServer.from_defaults(
            f"serverless cloud functions {server_index}",
            server_type=ServerTypes.serverless(),
            storage=Storage.ssd(f"storage of serverless server {server_index}")
        )

        on_premise_gpu_server = GPUServer.from_defaults(
            f"on premise GPU server {server_index}",
            server_type=ServerTypes.on_premise(),
            storage=Storage.ssd(f"storage of on-premise GPU server {server_index}")
        )

        video_streaming = VideoStreaming.from_defaults(f"Video streaming service {server_index}",
                                                       server=autoscaling_server)

        for uj_index in range(1, nb_of_uj_per_each_server_type + 1):
            uj_steps = []
            for uj_step_index in range(1, nb_of_uj_steps_per_uj + 1):
                video_streaming_job = VideoStreamingJob.from_defaults(
                    f"Video streaming job", service=video_streaming, video_duration=SourceValue(2.5 * u.hour))
                manually_written_job = Job.from_defaults(
                    f"Manually defined job uj {uj_index} uj_step {uj_step_index} server {server_index}",
                    server=serverless_server)
                custom_gpu_job = GPUJob.from_defaults(
                    f"Manually defined GPU job uj {uj_index} uj_step {uj_step_index} server {server_index}",
                    server=on_premise_gpu_server)

                uj_steps.append(UsageJourneyStep(
                    f"step {uj_step_index} of uj {uj_index}",
                    user_time_spent=SourceValue(20 * u.min, source=None),
                    jobs=[video_streaming_job, manually_written_job, custom_gpu_job]
                    ))

            usage_journey = UsageJourney(f"user journey {uj_index} of server {server_index}", uj_steps=uj_steps)

            network = Network(
                    f"network {uj_index}",
                    bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), source=None))
            for up_nb in range(1, nb_of_up_per_uj + 1):
                usage_patterns.append(
                    UsagePattern(
                        f"usage pattern {up_nb} of uj {uj_index}",
                        usage_journey=usage_journey,
                        devices=[
                            Device(name=f"device on which the user journey {uj_index} is made",
                                   carbon_footprint_fabrication=SourceValue(156 * u.kg, source=None),
                                   power=SourceValue(50 * u.W, source=None),
                                   lifespan=SourceValue(6 * u.year, source=None),
                                   fraction_of_usage_time=SourceValue(7 * u.hour / u.day, source=None))],
                        network=network,
                        country=country_generator(
                            f"devices country {uj_index}", "its 3 letter shortname, for example FRA",
                            SourceValue(85 * u.g / u.kWh, source=None), tz('Europe/Paris'))(),
                        hourly_usage_journey_starts=ExplainableHourlyQuantitiesFromFormInputs(
                            {"start_date": "2024-01-01", "modeling_duration_value": nb_years,
                             "modeling_duration_unit": "year",
                             "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "month",
                             "initial_volume": 1000, "initial_volume_timespan": "month"}
                        )
                    )
                )

    edge_usage_patterns = []
    for edge_usage_pattern_index in range(1, nb_of_edge_usage_patterns + 1):
        edge_storage = EdgeStorage(
            f"Edge SSD storage {edge_usage_pattern_index}",
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB),
            power_per_storage_capacity=SourceValue(1.3 * u.W / u.TB),
            lifespan=SourceValue(6 * u.years),
            idle_power=SourceValue(0.1 * u.W),
            storage_capacity=SourceValue(1 * u.TB),
            base_storage_need=SourceValue(10 * u.GB),
        )

        edge_computer = EdgeComputer(
            f"Default edge device {edge_usage_pattern_index}",
            carbon_footprint_fabrication=SourceValue(60 * u.kg),
            power=SourceValue(30 * u.W),
            lifespan=SourceValue(8 * u.year),
            idle_power=SourceValue(5 * u.W),
            ram=SourceValue(16 * u.GB_ram),
            compute=SourceValue(8 * u.cpu_core),
            base_ram_consumption=SourceValue(1 * u.GB_ram),
            base_compute_consumption=SourceValue(0.1 * u.cpu_core),
            storage=edge_storage
        )
        edge_processes = []
        for edge_process_index in range(1, nb_of_edge_processes_per_edge_computer + 1):
            edge_process = RecurrentEdgeProcess(
                f"Default edge process {edge_process_index} for edge device {edge_usage_pattern_index}",
                edge_device=edge_computer,
                recurrent_compute_needed=SourceRecurrentValues(
                    Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
                recurrent_ram_needed=SourceRecurrentValues(
                    Quantity(np.array([2] * 168, dtype=np.float32), u.GB_ram)),
                recurrent_storage_needed=SourceRecurrentValues(
                    Quantity(np.array([200] * 168, dtype=np.float32), u.kB))
            )
            edge_processes.append(edge_process)

        edge_function = EdgeFunction(
            f"Default edge function {edge_usage_pattern_index}",
            recurrent_edge_device_needs=edge_processes
        )

        edge_usage_journey = EdgeUsageJourney(
            f"Default edge usage journey {edge_usage_pattern_index}",
            edge_functions=[edge_function],
            usage_span=SourceValue(6 * u.year)
        )

        edge_usage_pattern = EdgeUsagePattern(
            f"Default edge usage pattern {edge_usage_pattern_index}",
            edge_usage_journey=edge_usage_journey,
            country=Countries.FRANCE(),
            hourly_edge_usage_journey_starts=ExplainableHourlyQuantitiesFromFormInputs(
                            {"start_date": "2024-01-01", "modeling_duration_value": nb_years,
                             "modeling_duration_unit": "year",
                             "net_growth_rate_in_percentage": 0, "net_growth_rate_timespan": "month",
                             "initial_volume": 1000, "initial_volume_timespan": "month"}
                        )
                )
        edge_usage_patterns.append(edge_usage_pattern)

    system = System("system", usage_patterns=usage_patterns, edge_usage_patterns=edge_usage_patterns)
    logger.info(f"Finished generating system in {round((time() - start), 3)} seconds")

    timed_system_to_json(system, save_calculated_attributes=False,
                         output_filepath=os.path.join(root_dir, "big_system.json"))
    timed_system_to_json(system, save_calculated_attributes=True,
                         output_filepath=os.path.join(root_dir, "big_system_with_calc_attr.json"))

    return system

@time_it
def timed_system_to_json(system, *args, **kwargs):
    return system_to_json(system, *args, **kwargs)


if __name__ == "__main__":
    nb_years = 5
    system = generate_big_system(
        nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3,
        nb_of_edge_usage_patterns=3, nb_of_edge_processes_per_edge_computer=3, nb_years=nb_years)
