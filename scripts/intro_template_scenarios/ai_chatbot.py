"""Build the ``ai_chatbot`` introductory template.

An inference-heavy LLM assistant: a short conversation journey (open the chat,
send a message) whose message step drives a GPUJob on a self-hosted autoscaling
GPU server. Wired into a daily usage pattern so the template loads as a runnable
System whose results compute.
"""
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_hourly_usage_from_frequency
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import GPUJob
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    storage = Storage.from_defaults(
        "Model weights storage", base_storage_need=SourceValue(2 * u.TB_stored))
    inference_server = GPUServer.from_defaults(
        "Inference GPU server", server_type=ServerTypes.autoscaling(),
        compute=SourceValue(4 * u.gpu), storage=storage)

    open_chat_job = GPUJob(
        "Open the chat", server=inference_server,
        request_duration=SourceValue(200 * u.ms),
        compute_needed=SourceValue(0.1 * u.gpu),
        ram_needed=SourceValue(4 * u.GB_ram),
        data_transferred=SourceValue(50 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    answer_job = GPUJob(
        "Answer a message", server=inference_server,
        request_duration=SourceValue(3 * u.s),
        compute_needed=SourceValue(1 * u.gpu),
        ram_needed=SourceValue(40 * u.GB_ram),
        data_transferred=SourceValue(20 * u.kB),
        data_stored=SourceValue(1 * u.kB_stored))

    open_step = UsageJourneyStep.from_defaults("Open the assistant", jobs=[open_chat_job])
    message_step = UsageJourneyStep.from_defaults("Send a message", jobs=[answer_job])
    journey = UsageJourney("Chatbot conversation", uj_steps=[open_step, message_step])

    start_date = datetime(2025, 1, 1)
    usage_pattern = UsagePattern(
        "Daily conversations", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=2000, frequency="daily", start_date=start_date))

    return System("AI chatbot system", [usage_pattern], edge_usage_patterns=[])
