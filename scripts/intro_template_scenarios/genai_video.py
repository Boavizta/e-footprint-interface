"""Build the ``genai_video`` introductory template.

A marketing team producing a short social-media video with generative-AI video
tools. There is **no web service of their own** — the team consumes external
GenAI APIs and only publishes the finished clip to a social network's CDN. The
journey mirrors a real production loop: write a prompt with an LLM, explore
several draft clips across two providers (Google Veo + ByteDance Seedance),
generate the two final clips, edit and mix them locally (user time only, no
digital service), then upload the result to the CDN.

Video generation dominates the footprint here, which is the pedagogical point:
the local editing step and the prompt-writing LLM calls are comparatively tiny
next to the GenAI video jobs.
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
    # The only self-hosted infrastructure is the social network's CDN, which stores
    # and serves the published clip. Serverless because the team pays per upload, not
    # for an always-on server; storage sized for a modest library of published videos.
    cdn_storage = Storage.from_defaults(
        "CDN video storage",
        storage_capacity=SourceValue(1 * u.TB_stored),
        data_replication_factor=SourceValue(3 * u.dimensionless),
        data_storage_duration=SourceValue(43830 * u.hour),  # ~5 years of retention
        base_storage_need=SourceValue(0 * u.GB_stored))
    cdn_server = BoaviztaCloudServer.from_defaults(
        "CDN (Content Delivery Network) of social network",
        server_type=ServerTypes.serverless(),
        provider=SourceObject("scaleway"),
        instance_type=SourceObject("dev1-s"),
        power_usage_effectiveness=SourceValue(1.2 * u.dimensionless),
        average_carbon_intensity=SourceValue(100 * u.g / u.kWh),
        base_ram_consumption=SourceValue(0 * u.GB_ram),
        base_compute_consumption=SourceValue(0 * u.cpu_core),
        storage=cdn_storage)

    # Prompt writing uses a small text LLM; two competing video providers are compared.
    llm_api = EcoLogitsGenAIExternalAPI(
        "Text Generation LLM API",
        provider=SourceObject("openai"),
        model_name=SourceObject("gpt-4.1-mini"))
    seedance_api = EcoLogitsVideoGenExternalAPI(
        "Seedance video generation API",
        provider=SourceObject("bytedance"),
        model_name=SourceObject("seedance-1.5-pro"))
    veo_api = EcoLogitsVideoGenExternalAPI(
        "Google Veo video generation API",
        provider=SourceObject("google"),
        model_name=SourceObject("veo-3.0"))

    prompt_iteration_job = EcoLogitsGenAIExternalAPIJob(
        "Prompt writing iteration", external_api=llm_api,
        output_token_count=SourceValue(400 * u.dimensionless))

    # Draft clips: 720p, no audio, same 8s length as the finals — so the draft-vs-final
    # difference is purely count and resolution (720p exploratory vs 1080p deliverable),
    # not duration.
    draft_seedance_job = EcoLogitsVideoGenExternalAPIJob(
        "Draft clip attempt (Seedance)", external_api=seedance_api,
        resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(False))
    draft_veo_job = EcoLogitsVideoGenExternalAPIJob(
        "Draft clip attempt (Veo)", external_api=veo_api,
        resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(False))

    # Final clips: full 1080p, 8s, one per provider — kept for the local edit.
    final_veo_job = EcoLogitsVideoGenExternalAPIJob(
        "Final clip (Veo, 8s)", external_api=veo_api,
        resolution=SourceObject("1080p (1920 x 1080)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(False))
    final_seedance_job = EcoLogitsVideoGenExternalAPIJob(
        "Final clip (Seedance, 8s)", external_api=seedance_api,
        resolution=SourceObject("1080p (1920 x 1080)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(False))

    upload_job = Job(
        "Upload final video to social network CDN", server=cdn_server,
        # The CDN belongs to the social network, not the team. e-footprint allocates a
        # server's fabrication + energy footprint across jobs in proportion to the server
        # time and resources each one occupies — so this brief 2s upload only draws the
        # tiny quota of the CDN's footprint that corresponds to our usage, never its whole impact.
        request_duration=SourceValue(
            2 * u.s,
            comment="Only the fraction of the CDN's footprint matching our usage is counted: "
                    "e-footprint shares the server's impact by occupancy, so this 2s upload claims "
                    "just a tiny quota of the CDN, not its full footprint."),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(150 * u.MB_ram),
        data_transferred=SourceValue(15 * u.MB),
        data_stored=SourceValue(15000 * u.kB_stored))

    # Job weights = "times per step": e.g. 3 prompt iterations, 3 draft renders each provider.
    prompt_step = UsageJourneyStep(
        "Create a prompt for video gen", user_time_spent=SourceValue(5 * u.min),
        jobs={prompt_iteration_job: 3})
    explore_step = UsageJourneyStep(
        "Explore and iterate", user_time_spent=SourceValue(9 * u.min),
        jobs={draft_seedance_job: 3, draft_veo_job: 3})
    generate_step = UsageJourneyStep(
        "Generate the final video", user_time_spent=SourceValue(3 * u.min),
        jobs={final_veo_job: 1, final_seedance_job: 1})
    # Local editing: user time only, no digital service — a deliberate contrast with
    # the API-heavy steps around it.
    edit_step = UsageJourneyStep(
        "Edit and mix the final clips on computer", user_time_spent=SourceValue(15 * u.min),
        jobs={})
    publish_step = UsageJourneyStep(
        "Publish to the social network", user_time_spent=SourceValue(2 * u.min),
        jobs={upload_job: 1})

    journey = UsageJourney(
        "Create a social video",
        uj_steps=[prompt_step, explore_step, generate_step, edit_step, publish_step])

    # Representative cadence: one social video per week (52 / year), flat over a year.
    usage_pattern = UsagePattern(
        "Video production users", journey, [Device.laptop()], Network.wifi_network(),
        Countries.FRANCE(),
        ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": "2026-01-01",
            "modeling_duration_value": 1,
            "modeling_duration_unit": "year",
            "initial_volume": 52,
            "initial_volume_timespan": "year",
            "net_growth_rate_in_percentage": 0,
            "net_growth_rate_timespan": "year",
        }, source=Sources.USER_DATA,
            comment="52 journeys per year = one short social video produced and posted per week."))

    return System("GenAI for Marketing video on social", [usage_pattern], edge_usage_patterns=[])
