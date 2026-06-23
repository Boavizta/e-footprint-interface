"""Integration coverage for the EcoLogits video-generation trio through the interface layer.

Builds a system containing an EcoLogitsVideoGenExternalAPI + EcoLogitsVideoGenExternalAPIJob,
serializes it, loads it through ModelWeb, and asserts the new classes wrap onto the existing
web wrappers (ExternalAPIWeb / JobWeb), round-trip through JSON persistence, and feed the
standard results pipeline with non-zero footprints — no special casing.

Assertions on EcoLogits outputs are structural (presence, non-negative) per the feature spec.
"""
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    EcoLogitsVideoGenExternalAPI, EcoLogitsVideoGenExternalAPIJob)
from efootprint.constants.countries import country_generator, tz
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_builders.services.external_api_web import ExternalAPIWeb
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.entities.web_core.usage.job_web import JobWeb

from tests.fixtures.system_builders import create_hourly_usage


def _video_api(name: str, provider: str, model_name: str) -> EcoLogitsVideoGenExternalAPI:
    return EcoLogitsVideoGenExternalAPI(
        name=name,
        provider=SourceObject(provider),
        model_name=SourceObject(model_name))


def _system_data_from_jobs(jobs: list) -> dict:
    uj_step = UsageJourneyStep.from_defaults("UJ step", jobs=jobs)
    uj = UsageJourney("Video journey", uj_steps=[uj_step])
    usage_pattern = UsagePattern(
        "Video Usage Pattern",
        usage_journey=uj,
        devices=[Device.from_defaults("Test Device")],
        network=Network.from_defaults("Test Network"),
        country=country_generator("Test Country", "TST", SourceValue(100 * u.g / u.kWh), tz('Europe/Paris'))(),
        hourly_usage_journey_starts=create_hourly_usage())
    system = System("Video system", usage_patterns=[usage_pattern], edge_usage_patterns=[])
    try:
        return system_to_json(system, save_calculated_attributes=True)
    finally:
        system.self_delete()


def _build_video_system_data() -> dict:
    api = _video_api("Sora-2-Pro API", "openai", "sora-2-pro")
    job = EcoLogitsVideoGenExternalAPIJob(
        name="Sora job",
        external_api=api,
        resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(8 * u.s),
        with_audio=SourceObject(True))
    return _system_data_from_jobs([job])


def _build_two_video_apis_system_data() -> dict:
    sora_api = _video_api("Sora-2-Pro API", "openai", "sora-2-pro")
    seedance_api = _video_api("Seedance API", "bytedance", "seedance-1.0")
    sora_job = EcoLogitsVideoGenExternalAPIJob(
        name="Sora job", external_api=sora_api, resolution=SourceObject("720p (1280 x 720)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(True))
    seedance_job = EcoLogitsVideoGenExternalAPIJob(
        name="Seedance job", external_api=seedance_api, resolution=SourceObject("480p (854 x 480)"),
        duration=SourceValue(8 * u.s), with_audio=SourceObject(True))
    return _system_data_from_jobs([sora_job, seedance_job])


def test_video_api_and_job_wrap_onto_existing_web_classes():
    repository = InMemorySystemRepository(initial_data=_build_video_system_data())
    model_web = ModelWeb(repository)

    external_apis = model_web.external_apis
    assert len(external_apis) == 1
    api_web = external_apis[0]
    assert isinstance(api_web, ExternalAPIWeb)
    assert api_web.efootprint_class.__name__ == "EcoLogitsVideoGenExternalAPI"

    jobs = model_web.get_web_objects_from_efootprint_type("JobBase")
    video_jobs = [j for j in jobs if j.efootprint_class.__name__ == "EcoLogitsVideoGenExternalAPIJob"]
    assert len(video_jobs) == 1
    assert isinstance(video_jobs[0], JobWeb)


def test_video_system_feeds_results_pipeline_with_non_zero_footprint():
    repository = InMemorySystemRepository(initial_data=_build_video_system_data())
    model_web = ModelWeb(repository)

    emissions = model_web.system_emissions["values"]
    assert sum(emissions["ExternalAPIs_energy"]) > 0
    assert sum(emissions["ExternalAPIs_fabrication"]) > 0


def test_video_system_round_trips_through_persistence():
    repository = InMemorySystemRepository(initial_data=_build_video_system_data())
    ModelWeb(repository).persist_to_cache()

    # The persisted JSON must carry the Job's per-call calculated attributes, not just its
    # inputs — otherwise a reload would silently recompute them and an emissions>0 check
    # could not tell preservation from recomputation.
    persisted = repository.get_system_data()
    (job_data,) = persisted["EcoLogitsVideoGenExternalAPIJob"].values()
    for calc_attr in ("generation_latency", "request_energy", "request_usage_gwp", "request_embodied_gwp"):
        assert calc_attr in job_data, f"{calc_attr} not preserved in persisted Job JSON"
        assert job_data[calc_attr]["value"] is not None
        assert job_data[calc_attr]["unit"] is not None

    reloaded = ModelWeb(repository)
    api_web = reloaded.external_apis[0]
    assert api_web.efootprint_class.__name__ == "EcoLogitsVideoGenExternalAPI"
    assert sum(reloaded.system_emissions["values"]["ExternalAPIs_energy"]) > 0


def test_job_form_resolution_datalist_is_keyed_by_real_api_with_correct_resolutions():
    # Real-object guard for the cross-object dotted-`depends_on` generator path: the resolution
    # datalist must key on each real API object's id and carry exactly that model's resolutions,
    # which depends on str(api.model_name) matching the library's conditional_list_values keys.
    # Unit/snapshot tests use pre-matched stubs; only this asserts the real str()-keying contract.
    repository = InMemorySystemRepository(initial_data=_build_two_video_apis_system_data())
    model_web = ModelWeb(repository)

    id_by_model = {
        api.model_name.value: api.id
        for api in model_web.get_efootprint_objects_from_efootprint_type("EcoLogitsVideoGenExternalAPI")}

    context = FormContextBuilder(model_web).build_creation_context(JobWeb, "EcoLogitsVideoGenExternalAPIJob")
    resolution_entry = next(
        entry for entry in context["dynamic_form_data"]["dynamic_lists"]
        if entry["input_id"] == "EcoLogitsVideoGenExternalAPIJob_resolution")

    assert resolution_entry["filter_by"] == "service_or_external_api"
    assert resolution_entry["list_value"] == {
        id_by_model["sora-2-pro"]: ["720p (1280 x 720)", "1080p (1920 x 1080)"],
        id_by_model["seedance-1.0"]: ["480p (854 x 480)", "720p (1280 x 720)"]}
