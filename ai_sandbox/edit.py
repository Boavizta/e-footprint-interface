"""Reading an interface model back into the DSL vocabulary of dsl.py.

The read-back is lossy on purpose: what the DSL cannot say (plain servers' sizing, other job kinds, step weights
within a journey, extra journeys of a pattern...) is omitted, so the assistant cannot see or change it.
"""
from __future__ import annotations

from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.system import System
from efootprint.core.usage.job import GPUJob, Job

from model_builder.domain.entities.web_core.model_web import ModelWeb

from dsl import JOB_FIELDS, SERVER_FIELDS, SERVER_JOB_FIELDS, STEP_FIELDS, STORAGE_FIELDS

HOURS_PER_YEAR = 365 * 24
DAYS_PER_TIMESPAN = {"day": 1, "month": 30, "year": 365}  # as ExplainableHourlyQuantitiesFromFormInputs counts them
DEVICE_ARCHETYPE_BY_NAME = {f"Default {kind}": kind for kind in ("smartphone", "laptop", "screen", "box")}


def library_objects(system: System) -> dict[str, list]:
    """The library objects behind each DSL section, in model order."""
    return {
        "servers": list(system.servers),
        "genai_apis": [api for api in system.external_apis if isinstance(api, EcoLogitsGenAIExternalAPI)],
        "jobs": list(system.jobs),
        "journeys": list(system.usage_journeys),
        "usage_patterns": list(system.usage_patterns),
    }


def system_to_dsl(model_web: ModelWeb) -> dict:
    """A JSON-ready dict in the DSL vocabulary that `validate_tolerating_extras` accepts."""
    system = model_web.system.modeling_obj
    objects = library_objects(system)
    return {
        "system_name": system.name,
        "servers": [_server(s) for s in objects["servers"]],
        "genai_apis": [_genai_api(a) for a in objects["genai_apis"]],
        "jobs": [_job(j) for j in objects["jobs"]],
        "journeys": [_journey(jo) for jo in objects["journeys"]],
        "usage_patterns": [_usage_pattern(p) for p in objects["usage_patterns"]],
    }


def _read_fields(entry: dict, obj, table: dict, fields=None):
    """The inverse of dsl._apply_fields: each value as a plain number in the DSL unit, its comment alongside."""
    for field in fields or table:
        attr, unit = table[field]
        value = getattr(obj, attr)
        entry[field] = _number(value.to(unit).magnitude)
        if value.comment:
            entry["comments"][field] = value.comment


def _number(magnitude) -> float:
    return float(f"{float(magnitude):.6g}")  # drops unit-conversion noise such as 0.30000000000000004


def _source_object(entry: dict, field: str, value):
    entry[field] = value.value
    if value.comment:
        entry["comments"][field] = value.comment


def _without_empty_comments(entry: dict) -> dict:
    comments = entry.pop("comments")  # re-added last, where the DSL writes it
    if comments:
        entry["comments"] = comments
    return entry


def _server(server) -> dict:
    entry = {"name": server.name, "comments": {}}
    if isinstance(server, GPUServer):
        entry["kind"] = "gpu"
        _read_fields(entry, server, SERVER_FIELDS)
    else:
        _read_fields(entry, server, SERVER_FIELDS, ["carbon_intensity_g_per_kwh"])
    if isinstance(server, BoaviztaCloudServer):
        _source_object(entry, "cloud_provider", server.provider)
        _source_object(entry, "instance_type", server.instance_type)
    _read_fields(entry, server.storage, STORAGE_FIELDS)
    return _without_empty_comments(entry)


def _genai_api(api) -> dict:
    entry = {"name": api.name, "comments": {}}
    _source_object(entry, "provider", api.provider)
    _source_object(entry, "model_name", api.model_name)
    return _without_empty_comments(entry)


def _job(job) -> dict:
    entry = {"name": job.name, "comments": {}}
    if isinstance(job, EcoLogitsGenAIExternalAPIJob):
        entry["genai_api"] = job.external_api.name
        _read_fields(entry, job, JOB_FIELDS, ["output_tokens"])
    elif isinstance(job, (GPUJob, Job)):
        entry["server"] = job.server.name
        compute_field = "gpus" if isinstance(job, GPUJob) else "cpu_cores"
        _read_fields(entry, job, JOB_FIELDS, SERVER_JOB_FIELDS + (compute_field,))
    return _without_empty_comments(entry)


def _journey(journey) -> dict:
    return {"name": journey.name, "steps": [_step(step) for step in journey.uj_steps]}


def _step(step) -> dict:
    # A job triggered n times per step is listed n times, the way the DSL writes it.
    jobs = [job.name for job, weight in step.jobs.items() for _ in range(max(1, round(weight.value.magnitude)))]
    entry = {"name": step.name, "jobs": jobs, "comments": {}}
    _read_fields(entry, step, STEP_FIELDS)
    return _without_empty_comments(entry)


def _usage_pattern(pattern) -> dict:
    devices = list(pattern.devices)
    occurrences = pattern.hourly_occurrences
    entry = {
        "name": pattern.name,
        "journey": next(iter(pattern.usage_journeys)).name,
        "device": DEVICE_ARCHETYPE_BY_NAME.get(devices[0].name, devices[0].name) if devices else "none",
        "network": "mobile" if pattern.network.name == "Default mobile network" else "wifi",
        "country": pattern.country.name.upper().replace(" ", "_"),
        "comments": {},
    }
    if isinstance(occurrences, ExplainableHourlyQuantitiesFromFormInputs):
        form = occurrences.form_inputs
        entry["volume"] = {"value": float(form["initial_volume"]), "per": form["initial_volume_timespan"]}
        growth_per_timespan = 1 + float(form["net_growth_rate_in_percentage"]) / 100
        yearly_growth = growth_per_timespan ** (365 / DAYS_PER_TIMESPAN[form["net_growth_rate_timespan"]])
        entry["growth_pct_per_year"] = _number(yearly_growth * 100 - 100)
    else:
        yearly = occurrences.sum().value.magnitude * HOURS_PER_YEAR / len(occurrences)
        entry["volume"] = {"value": _number(yearly), "per": "year"}
        entry["growth_pct_per_year"] = 0.0
    if occurrences.comment:
        entry["comments"]["volume"] = occurrences.comment
    return _without_empty_comments(entry)
