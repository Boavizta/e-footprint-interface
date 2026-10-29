"""Compact structure DSL for AI-generated e-footprint models, and its builder.

The DSL is what the LLM writes. It names objects and their relationships and leaves every
unstated value to the library defaults. `build_system` turns a validated `ModelSpec` into a
real `System` that can be computed and exported to the interface JSON format.
"""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import GPUJob, Job, JobBase
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from catalogs import Resolution, resolve_cloud_instance, resolve_genai

MODELING_START_DATE = "2026-01-01"
MODELING_DURATION_YEARS = 1


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ServerSpec(Strict):
    name: str
    kind: Literal["cpu", "gpu"] = "cpu"
    cores: Optional[float] = None
    ram_gb: Optional[float] = None
    gpus: Optional[int] = None
    storage_gb: Optional[float] = None
    cloud_provider: Optional[str] = None
    instance_type: Optional[str] = None
    carbon_intensity_g_per_kwh: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class GenAIApiSpec(Strict):
    name: str
    provider: str = "openai"
    model_name: Optional[str] = None  # unstated in the description -> provider default, recorded as a resolution
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class JobSpec(Strict):
    name: str
    server: Optional[str] = None
    genai_api: Optional[str] = None
    data_transferred_kb: Optional[float] = None
    data_stored_kb: Optional[float] = None
    request_duration_s: Optional[float] = None
    cpu_cores: Optional[float] = None
    gpus: Optional[float] = None
    ram_mb: Optional[float] = None
    output_tokens: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class StepSpec(Strict):
    name: str
    user_time_spent_min: Optional[float] = None
    jobs: list[str] = Field(default_factory=list)
    comments: dict[str, str] = Field(default_factory=dict)


class JourneySpec(Strict):
    name: str
    steps: list[StepSpec]


class VolumeSpec(Strict):
    value: float
    per: Literal["minute", "hour", "day", "week", "month", "year"]


class UsagePatternSpec(Strict):
    name: str
    journey: str
    device: Optional[str] = "laptop"  # smartphone | laptop | screen | box | none (batch work has no user device)
    network: str = "wifi"             # wifi | mobile; other words are snapped (ethernet -> wifi, 5g -> mobile)
    country: str = "FRANCE"
    volume: VolumeSpec
    growth_pct_per_year: float = 0
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class ModelSpec(Strict):
    system_name: str
    servers: list[ServerSpec] = Field(default_factory=list)
    genai_apis: list[GenAIApiSpec] = Field(default_factory=list)
    jobs: list[JobSpec] = Field(default_factory=list)
    journeys: list[JourneySpec] = Field(default_factory=list)
    usage_patterns: list[UsagePatternSpec] = Field(default_factory=list)


# --- Parsing ---------------------------------------------------------------------------------------

def parse_json(text: str) -> tuple[dict | None, bool, str | None]:
    """Returns (data, first_attempt_ok, error). Repairs only by stripping a code fence or surrounding prose."""
    try:
        return json.loads(text), True, None
    except json.JSONDecodeError as first_error:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0)), False, f"repaired: {first_error}"
            except json.JSONDecodeError:
                pass
        return None, False, str(first_error)


def validate_tolerating_extras(data: dict) -> tuple[ModelSpec, list[str]]:
    """Strict validation, except that unknown fields are stripped and reported instead of failing the run."""
    try:
        return ModelSpec.model_validate(data), []
    except ValidationError as error:
        extras = [e["loc"] for e in error.errors() if e["type"] == "extra_forbidden"]
        if not extras or len(extras) != len(error.errors()):
            raise
    for loc in extras:
        node = data
        for key in loc[:-1]:
            node = node[key]
        del node[loc[-1]]
    return ModelSpec.model_validate(data), [".".join(str(k) for k in loc) for loc in extras]


# --- Builder -------------------------------------------------------------------------------------

class _Comments:
    """The per-field comments of one DSL object; each goes on the ExplainableObject built from that field.

    Comments on fields that produce no value (unset fields, unknown names, device or country choices) are
    reported as resolutions so the run record shows what the model wrote that the user will never see.
    """

    def __init__(self, obj, resolutions: list[Resolution]):
        self.obj, self.resolutions = obj, resolutions
        self.pending = dict(getattr(obj, "comments", {}))

    def take(self, field: str) -> Optional[str]:
        return self.pending.pop(field, None)

    def value(self, field: str):
        return getattr(self.obj, field)

    def close(self):
        for field, text in self.pending.items():
            self.resolutions.append(Resolution("comment", f"{self.obj.name}.{field}", text, "unattached"))


# DSL field -> (library attribute, unit). Read by the builders below and by edit.py.
SERVER_FIELDS = {"carbon_intensity_g_per_kwh": ("average_carbon_intensity", u.g / u.kWh),
                 "gpus": ("compute", u.gpu)}  # gpu servers only
STORAGE_FIELDS = {"storage_gb": ("base_storage_need", u.GB_stored)}  # on server.storage
JOB_FIELDS = {"data_transferred_kb": ("data_transferred", u.kB), "data_stored_kb": ("data_stored", u.kB_stored),
              "request_duration_s": ("request_duration", u.s), "ram_mb": ("ram_needed", u.MB_ram),
              "cpu_cores": ("compute_needed", u.cpu_core), "gpus": ("compute_needed", u.gpu),
              "output_tokens": ("output_token_count", u.dimensionless)}
STEP_FIELDS = {"user_time_spent_min": ("user_time_spent", u.min)}
SERVER_JOB_FIELDS = ("data_transferred_kb", "data_stored_kb", "request_duration_s", "ram_mb")  # + cpu_cores or gpus


def _apply_fields(kwargs: dict, c: _Comments, table: dict, fields=None):
    """Sets each stated field of `fields` (default: the whole table) as a SourceValue carrying its comment."""
    for field in fields or table:
        attr, unit = table[field]
        value = c.value(field)
        if value is not None:
            kwargs[attr] = SourceValue(value * unit, comment=c.take(field))


def _volume_timeseries(volume: VolumeSpec, growth_pct_per_year: float = 0, comment: Optional[str] = None):
    """Hourly volume from the DSL period."""
    value, per = volume.value, volume.per
    if per == "minute":
        value, per = value * 60 * 24, "day"
    elif per == "hour":
        value, per = value * 24, "day"
    elif per == "week":
        value, per = value / 7, "day"
    return ExplainableHourlyQuantitiesFromFormInputs({
        "start_date": MODELING_START_DATE,
        "modeling_duration_value": MODELING_DURATION_YEARS,
        "modeling_duration_unit": "year",
        "initial_volume": value,
        "initial_volume_timespan": per,
        "net_growth_rate_in_percentage": growth_pct_per_year,
        "net_growth_rate_timespan": "year",
    }, source=Sources.USER_DATA, comment=comment)


DEVICE_ARCHETYPES = ("smartphone", "laptop", "screen", "box")
NO_DEVICE_WORDS = ("none", "null", "no", "server", "cpu", "batch", "cron")
NETWORK_ALIASES = {
    "wifi": "wifi", "wi-fi": "wifi", "wlan": "wifi", "ethernet": "wifi", "wired": "wifi", "fiber": "wifi",
    "fibre": "wifi", "lan": "wifi", "broadband": "wifi", "fixed": "wifi",
    "mobile": "mobile", "cellular": "mobile", "4g": "mobile", "5g": "mobile", "lte": "mobile", "3g": "mobile",
    "satellite": "mobile",
}


def _label(name: str, resolutions: list[Resolution]) -> str:
    """Object names are labels the user reads in a diagram: identifiers get their separators replaced.

    Only identifier shapes are touched (snake_case, or kebab-case without spaces); hyphenated English such as
    "Time-series DB" or "Ask follow-up" is left alone.
    """
    if "_" not in name and not ("-" in name and " " not in name):
        return name
    label = re.sub(r"[_-]+", " ", name).strip()
    label = label[:1].upper() + label[1:]
    resolutions.append(Resolution("name", name, label, "humanized"))
    return label


class _Shared:
    """One instance per device archetype, network and country, shared across patterns.

    Seeding it with a model's existing instances (keyed by archetype, network kind and country key) makes new
    patterns reuse them instead of adding a second "Default smartphone".
    """

    def __init__(self, resolutions: list[Resolution], devices: dict = None, networks: dict = None,
                 countries: dict = None):
        self.devices, self.networks, self.countries = dict(devices or {}), dict(networks or {}), dict(countries or {})
        self.resolutions = resolutions

    def devices_for(self, kind: str | None) -> list:
        """Returns the device list of a usage pattern: one archetype, or none for batch work."""
        key = (kind or "none").strip().lower()
        if key in DEVICE_ARCHETYPES:
            return [self.devices.setdefault(key, getattr(Device, key)())]
        if key in NO_DEVICE_WORDS:
            if key != "none":
                self.resolutions.append(Resolution("device", kind, "none", "normalized"))
            return []
        self.resolutions.append(Resolution("device", kind, "laptop", "fallback"))
        return [self.devices.setdefault("laptop", Device.laptop())]

    def network(self, kind: str):
        key = NETWORK_ALIASES.get(kind.strip().lower())
        if key is None:
            key = "wifi"
            self.resolutions.append(Resolution("network", kind, key, "fallback"))
        elif key != kind:
            self.resolutions.append(Resolution("network", kind, key, "normalized"))
        factory = Network.wifi_network if key == "wifi" else Network.mobile_network
        return self.networks.setdefault(key, factory())

    def country(self, name):
        key = name.strip().upper().replace(" ", "_")
        if not hasattr(Countries, key):
            raise ValueError(f"Unknown country '{name}'")
        return self.countries.setdefault(key, getattr(Countries, key)())


def _lookup(mapping: dict, name: str, kind: str):
    if name not in mapping:
        raise ValueError(f"Unknown {kind} '{name}' (known: {sorted(mapping)})")
    return mapping[name]


def build_server(s: ServerSpec, resolutions: list[Resolution]) -> ServerBase:
    c = _Comments(s, resolutions)
    name = _label(s.name, resolutions)
    storage_kwargs = {}
    _apply_fields(storage_kwargs, c, STORAGE_FIELDS)
    kwargs = {"storage": Storage.from_defaults(f"{name} storage", **storage_kwargs)}
    if s.kind == "gpu":
        _apply_fields(kwargs, c, SERVER_FIELDS)
        server = GPUServer.from_defaults(name, **kwargs)
    else:
        _apply_fields(kwargs, c, SERVER_FIELDS, ["carbon_intensity_g_per_kwh"])
        # Always a catalog cloud instance: the library's plain Server default is a whole physical machine, 30-40x
        # the footprint of a small instance, so naming a provider or not would swing the result. Cores and RAM
        # then come from Boavizta, the stated ones only drive the pick.
        provider, instance = resolve_cloud_instance(s.cloud_provider, s.instance_type, s.cores, s.ram_gb, resolutions)
        sizing = " ".join(filter(None, (c.take("cores"), c.take("ram_gb"), c.take("instance_type")))) or None
        server = BoaviztaCloudServer.from_defaults(
            name, provider=SourceObject(provider, comment=c.take("cloud_provider")),
            instance_type=SourceObject(instance, comment=sizing), **kwargs)
    c.close()
    return server


def build_genai_api(a: GenAIApiSpec, resolutions: list[Resolution]) -> EcoLogitsGenAIExternalAPI:
    c = _Comments(a, resolutions)
    provider, model_name = resolve_genai(a.provider, a.model_name, resolutions)
    api = EcoLogitsGenAIExternalAPI.from_defaults(
        _label(a.name, resolutions), provider=SourceObject(provider, comment=c.take("provider")),
        model_name=SourceObject(model_name, comment=c.take("model_name")))
    c.close()
    return api


def build_job(j: JobSpec, servers: dict, apis: dict, resolutions: list[Resolution]) -> JobBase:
    if (j.server is None) == (j.genai_api is None):
        raise ValueError(f"Job '{j.name}' must reference exactly one of server or genai_api")
    c = _Comments(j, resolutions)
    name = _label(j.name, resolutions)
    if j.genai_api:
        kwargs = {"external_api": _lookup(apis, j.genai_api, "genai_api")}
        _apply_fields(kwargs, c, JOB_FIELDS, ["output_tokens"])
        job = EcoLogitsGenAIExternalAPIJob.from_defaults(name, **kwargs)
    else:
        server = _lookup(servers, j.server, "server")
        kwargs = {"server": server}
        if isinstance(server, GPUServer):
            _apply_fields(kwargs, c, JOB_FIELDS, SERVER_JOB_FIELDS + ("gpus",))
            job = GPUJob.from_defaults(name, **kwargs)
        else:
            _apply_fields(kwargs, c, JOB_FIELDS, SERVER_JOB_FIELDS + ("cpu_cores",))
            job = Job.from_defaults(name, **kwargs)
    c.close()
    return job


def build_step(st: StepSpec, jobs: dict, resolutions: list[Resolution]) -> UsageJourneyStep:
    c = _Comments(st, resolutions)
    kwargs = {"jobs": [_lookup(jobs, name, "job") for name in st.jobs]}
    _apply_fields(kwargs, c, STEP_FIELDS)
    step = UsageJourneyStep.from_defaults(_label(st.name, resolutions), **kwargs)
    c.close()
    return step


def build_journey(jo: JourneySpec, jobs: dict, resolutions: list[Resolution]) -> UsageJourney:
    steps = [build_step(st, jobs, resolutions) for st in jo.steps]
    return UsageJourney(_label(jo.name, resolutions), uj_steps=steps)


def build_usage_pattern(p: UsagePatternSpec, journeys: dict, shared: _Shared,
                        resolutions: list[Resolution]) -> UsagePattern:
    c = _Comments(p, resolutions)
    volume_comment = " ".join(filter(None, (c.take("volume"), c.take("growth_pct_per_year")))) or None
    pattern = UsagePattern(
        _label(p.name, resolutions), [_lookup(journeys, p.journey, "journey")], shared.devices_for(p.device),
        shared.network(p.network), shared.country(p.country),
        _volume_timeseries(p.volume, p.growth_pct_per_year, volume_comment))
    c.close()
    return pattern


def build_system(spec: ModelSpec) -> tuple[System, list[Resolution]]:
    """Returns the system and the catalog resolutions made on the way (see catalogs.py)."""
    resolutions: list[Resolution] = []
    shared = _Shared(resolutions)
    servers = {s.name: build_server(s, resolutions) for s in spec.servers}
    apis = {a.name: build_genai_api(a, resolutions) for a in spec.genai_apis}
    jobs = {j.name: build_job(j, servers, apis, resolutions) for j in spec.jobs}
    journeys = {jo.name: build_journey(jo, jobs, resolutions) for jo in spec.journeys}
    usage_patterns = [build_usage_pattern(p, journeys, shared, resolutions) for p in spec.usage_patterns]
    return System(_label(spec.system_name, resolutions), usage_patterns, []), resolutions


def json_schema() -> dict:
    return ModelSpec.model_json_schema()
