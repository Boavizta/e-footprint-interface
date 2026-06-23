"""Build the ``ai_chatbot`` introductory template.

An LLM assistant served by a web application and two external AI APIs: a small
model handles routing and short replies, while a larger model handles detailed
answers. The web tier is modeled separately so its impact can be compared with
the AI API impact in the Sankey diagram.
"""

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    web_storage = Storage.from_defaults(
        "Chat logs storage", base_storage_need=SourceValue(20 * u.GB_stored))
    web_server = BoaviztaCloudServer.from_defaults(
        "Chat web application server", server_type=ServerTypes.autoscaling(),
        provider=SourceObject("scaleway"),
        instance_type=SourceObject("dev1-s"),
        base_ram_consumption=SourceValue(1 * u.GB_ram),
        base_compute_consumption=SourceValue(0.1 * u.cpu_core),
        average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
        storage=web_storage)

    small_llm = EcoLogitsGenAIExternalAPI(
        "Small LLM API",
        provider=SourceObject("openai"),
        model_name=SourceObject("gpt-4.1-nano"))
    big_llm = EcoLogitsGenAIExternalAPI(
        "Big LLM API",
        provider=SourceObject("openai"),
        model_name=SourceObject("gpt-4.1"))
    video_llm = EcoLogitsVideoGenExternalAPI(
        "GenAI video API",
        provider=SourceObject("klingai"),
        model_name=SourceObject("kling-v3"))

    open_chat_job = Job(
        "Serve chat interface", server=web_server,
        request_duration=SourceValue(120 * u.ms),
        compute_needed=SourceValue(0.05 * u.cpu_core),
        ram_needed=SourceValue(80 * u.MB_ram),
        data_transferred=SourceValue(300 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    quick_request_job = Job(
        "Handle quick question", server=web_server,
        request_duration=SourceValue(180 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(120 * u.MB_ram),
        data_transferred=SourceValue(20 * u.kB),
        data_stored=SourceValue(2 * u.kB_stored))
    detailed_request_job = Job(
        "Prepare detailed question", server=web_server,
        request_duration=SourceValue(350 * u.ms),
        compute_needed=SourceValue(0.2 * u.cpu_core),
        ram_needed=SourceValue(200 * u.MB_ram),
        data_transferred=SourceValue(80 * u.kB),
        data_stored=SourceValue(8 * u.kB_stored))
    render_video_job = Job(
        "Render video", server=web_server,
        request_duration=SourceValue(0.5 * u.s),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(120 * u.MB_ram),
        data_transferred=SourceValue(2 * u.kB),
        data_stored=SourceValue(2 * u.kB_stored)
    )

    quick_answer_job = EcoLogitsGenAIExternalAPIJob(
        "Small LLM short answer", external_api=small_llm,
        output_token_count=SourceValue(1000 * u.dimensionless))
    route_question_job = EcoLogitsGenAIExternalAPIJob(
        "Small LLM route complex request", external_api=small_llm,
        output_token_count=SourceValue(300 * u.dimensionless))
    detailed_answer_job = EcoLogitsGenAIExternalAPIJob(
        "Big LLM detailed answer", external_api=big_llm,
        output_token_count=SourceValue(10000 * u.dimensionless))
    video_generation_job = EcoLogitsVideoGenExternalAPIJob(
        "GenAI video generation", external_api=video_llm, resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(1 * u.s), with_audio=SourceObject(True))

    open_step = UsageJourneyStep.from_defaults("Open the assistant", jobs=[open_chat_job])
    quick_question_step = UsageJourneyStep.from_defaults(
        "Ask a quick question", jobs=[quick_request_job, quick_answer_job])
    detailed_question_step = UsageJourneyStep.from_defaults(
        "Ask a detailed question", jobs=[detailed_request_job, route_question_job, detailed_answer_job])
    video_generation_step = UsageJourneyStep.from_defaults(
        "Generate a 1s video", jobs=[video_generation_job, render_video_job]
    )
    journey = UsageJourney(
        "Chatbot conversation",
        uj_steps=[open_step, quick_question_step, detailed_question_step, video_generation_step])

    usage_pattern = UsagePattern(
        "Daily conversations", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": "2025-01-01",
            "modeling_duration_value": 3,
            "modeling_duration_unit": "year",
            "initial_volume": 720000,
            "initial_volume_timespan": "year",
            "net_growth_rate_in_percentage": 35,
            "net_growth_rate_timespan": "year",
        }, source=Sources.USER_DATA))

    return System("AI chatbot system", [usage_pattern], edge_usage_patterns=[])
