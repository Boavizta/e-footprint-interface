"""Compact structure DSL for AI-generated e-footprint models, and its builder.

The DSL is what the LLM writes. It names objects and their relationships and leaves every
unstated value to the library defaults. `build_system` turns a validated `ModelSpec` into a
real `System` that can be computed and exported to the interface JSON format.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import GPUJob, Job, JobBase
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern

from model_builder.narrate import narrate

from .catalogs import Resolution, resolve_cloud_instance, resolve_genai

# The web year: usage and deployments the answer does not date start here, and deployments end with it.
WEB_YEAR_START = date(2027, 1, 1)
WEB_YEAR_END = date(2027, 12, 31)
MAX_DEFAULT_SPAN_YEARS = 6  # the library's own default usage span


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
    start_date: Optional[date] = None  # a usage the description dates otherwise than the shared start
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class ModelSpec(Strict):
    """The Web only schema."""
    system_name: str
    servers: list[ServerSpec] = Field(default_factory=list)
    genai_apis: list[GenAIApiSpec] = Field(default_factory=list)
    jobs: list[JobSpec] = Field(default_factory=list)
    journeys: list[JourneySpec] = Field(default_factory=list)
    usage_patterns: list[UsagePatternSpec] = Field(default_factory=list)


class EdgeDeviceSpec(Strict):
    name: str
    kind: Literal["computer", "appliance"] = "computer"
    cores: Optional[float] = None
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    power_w: Optional[float] = None
    idle_power_w: Optional[float] = None
    base_ram_gb: Optional[float] = None      # computer only
    base_storage_gb: Optional[float] = None  # computer only
    embodied_kg: Optional[float] = None
    lifespan_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)


class EdgeDeviceGroupSpec(Strict):
    name: str
    device_counts: dict[str, float] = Field(default_factory=dict)     # edge device name -> count per group
    sub_group_counts: dict[str, float] = Field(default_factory=dict)  # group name -> count per group
    comments: dict[str, str] = Field(default_factory=dict)            # device or group name -> why that count


class ServerCallSpec(Strict):
    jobs: list[str]  # every job one call triggers, the database write included
    times_per_hour: float
    comment: Optional[str] = None


class EdgeFunctionSpec(Strict):
    name: str
    device: str
    cpu_cores_avg: Optional[float] = None
    ram_gb_avg: Optional[float] = None
    workload_fraction: Optional[float] = None  # appliance only
    server_calls: list[ServerCallSpec] = Field(default_factory=list)
    comments: dict[str, str] = Field(default_factory=dict)


class EdgeJourneySpec(Strict):
    name: str
    functions: list[str]


class EdgeDeploymentSpec(Strict):
    name: str
    journey: str
    country: str = "FRANCE"
    network: str = "wifi"
    new_units: VolumeSpec
    start_date: Optional[date] = None  # a fleet already in service starts in the past
    usage_span_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)


class WebEdgeSpec(ModelSpec):
    """The Web + edge schema: the web sections, then the devices, what they run and how many are deployed."""
    edge_devices: list[EdgeDeviceSpec] = Field(default_factory=list)
    edge_device_groups: list[EdgeDeviceGroupSpec] = Field(default_factory=list)
    edge_functions: list[EdgeFunctionSpec] = Field(default_factory=list)
    edge_journeys: list[EdgeJourneySpec] = Field(default_factory=list)
    edge_deployments: list[EdgeDeploymentSpec] = Field(default_factory=list)


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


def validate_tolerating_extras(data: dict, schema: type[ModelSpec]) -> tuple[ModelSpec, list[str]]:
    """Strict validation against `schema`, except that unknown fields are stripped and reported instead of failing
    the run: a Web only answer's edge sections are dropped this way."""
    try:
        return schema.model_validate(data), []
    except ValidationError as error:
        extras = [e["loc"] for e in error.errors() if e["type"] == "extra_forbidden"]
        if not extras or len(extras) != len(error.errors()):
            raise
    for loc in extras:
        node = data
        for key in loc[:-1]:
            node = node[key]
        del node[loc[-1]]
    return schema.model_validate(data), [".".join(str(k) for k in loc) for loc in extras]


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


# DSL field -> (library attribute, unit). Read by the builders below and the development evaluator.
SERVER_FIELDS = {"carbon_intensity_g_per_kwh": ("average_carbon_intensity", u.g / u.kWh),
                 "gpus": ("compute", u.gpu)}  # gpu servers only
STORAGE_FIELDS = {"storage_gb": ("base_storage_need", u.GB_stored)}  # on server.storage
JOB_FIELDS = {"data_transferred_kb": ("data_transferred", u.kB), "data_stored_kb": ("data_stored", u.kB_stored),
              "request_duration_s": ("request_duration", u.s), "ram_mb": ("ram_needed", u.MB_ram),
              "cpu_cores": ("compute_needed", u.cpu_core), "gpus": ("compute_needed", u.gpu),
              "output_tokens": ("output_token_count", u.dimensionless)}
STEP_FIELDS = {"user_time_spent_min": ("user_time_spent", u.min)}
SERVER_JOB_FIELDS = ("data_transferred_kb", "data_stored_kb", "request_duration_s", "ram_mb")  # + cpu_cores or gpus
EDGE_DEVICE_FIELDS = {"power_w": ("power", u.W), "idle_power_w": ("idle_power", u.W),
                      "embodied_kg": ("carbon_footprint_manufacturing", u.kg), "lifespan_years": ("lifespan", u.year),
                      "cores": ("compute", u.cpu_core), "ram_gb": ("ram", u.GB_ram),
                      "base_ram_gb": ("base_ram_consumption", u.GB_ram)}  # the last three: computers only
EDGE_STORAGE_FIELDS = {"storage_gb": ("storage_capacity_per_unit", u.GB_stored),
                       "base_storage_gb": ("base_storage_need", u.GB_stored)}  # on computer.storage


def _apply_fields(kwargs: dict, c: _Comments, table: dict, fields=None):
    """Sets each stated field of `fields` (default: the whole table) as a SourceValue carrying its comment."""
    for field in fields or table:
        attr, unit = table[field]
        value = c.value(field)
        if value is not None:
            kwargs[attr] = SourceValue(value * unit, comment=c.take(field))


def _duration(start: date, end: date) -> tuple[int, str]:
    """`start` to `end` inclusive as the editor's duration: whole years when it is one (the library's year being
    365 days), else whole months of 30 days."""
    days = (end - start).days + 1
    years = round(days / 365)
    if years and abs(days - 365 * years) <= 15:
        return years, "year"
    return max(1, round(days / 30)), "month"


def _volume_timeseries(volume: VolumeSpec, period: tuple[date, date], growth_pct_per_year: float = 0,
                       comment: Optional[str] = None):
    """Hourly volume from the DSL period over `period`, as the Growth projection inputs the hourly editor prefills:
    a raw series would open empty."""
    value, per = volume.value, volume.per
    if per == "minute":
        value, per = value * 60 * 24, "day"
    elif per == "hour":
        value, per = value * 24, "day"
    elif per == "week":
        value, per = value / 7, "day"
    duration, unit = _duration(*period)
    return ExplainableHourlyQuantitiesFromFormInputs({
        "start_date": period[0].isoformat(),
        "modeling_duration_value": duration,
        "modeling_duration_unit": unit,
        "initial_volume": value,
        "initial_volume_timespan": per,
        "net_growth_rate_in_percentage": growth_pct_per_year,
        "net_growth_rate_timespan": "year",
    }, source=Sources.USER_DATA, comment=comment)


def _weekly(value: float, unit: str, comment: Optional[str] = None):
    """A constant need over the typical week, as the inputs the weekly editor prefills."""
    return ExplainableRecurrentQuantitiesFromConstant(
        {"constant_value": value, "constant_unit": unit}, source=Sources.USER_DATA, comment=comment)


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
    """One instance per device archetype, network and country, shared across patterns."""

    def __init__(self, resolutions: list[Resolution]):
        self.devices, self.networks, self.countries = {}, {}, {}
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
    """Resolve a reference by its declared name before display labels are humanized."""
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


def build_usage_pattern(p: UsagePatternSpec, journeys: dict, shared: _Shared, period: tuple[date, date],
                        resolutions: list[Resolution]) -> UsagePattern:
    """`period` is the shared one: the usage runs from its own start date when it has one, else the shared start."""
    c = _Comments(p, resolutions)
    volume_comment = " ".join(filter(None, (c.take("volume"), c.take("growth_pct_per_year"), c.take("start_date")))) or None
    pattern = UsagePattern(
        _label(p.name, resolutions), [_lookup(journeys, p.journey, "journey")], shared.devices_for(p.device),
        shared.network(p.network), shared.country(p.country),
        _volume_timeseries(p.volume, (p.start_date or period[0], period[1]), p.growth_pct_per_year, volume_comment))
    c.close()
    return pattern


def _reserve(kwargs: dict, attr: str, stated, capacity, share: float, cls, comment: str):
    """A reserve the answer omits is the library default, at most `share` of the stated capacity: the default idle
    power (5 W) exceeds a sensor's whole power, the default base RAM (1 GB) all of a small gateway's, the default
    base storage (30 GB) a gateway's flash. Without a stated capacity the library default stands."""
    if stated is None and capacity is not None:
        default = cls.default_values[attr].value
        kwargs[attr] = SourceValue(min(default, capacity * share * default.units), comment=comment)


def build_edge_device(d: EdgeDeviceSpec, resolutions: list[Resolution]):
    """A gateway, sensor or controller, built from the hardware and the reserved resources the answer states."""
    c = _Comments(d, resolutions)
    name = _label(d.name, resolutions)
    cls = EdgeAppliance if d.kind == "appliance" else EdgeComputer
    kwargs = {}
    _apply_fields(kwargs, c, EDGE_DEVICE_FIELDS, ("power_w", "idle_power_w", "embodied_kg", "lifespan_years"))
    _reserve(kwargs, "idle_power", d.idle_power_w, d.power_w, 1, cls, "At most the device's power")
    if cls is EdgeComputer:
        storage_kwargs = {}
        _apply_fields(storage_kwargs, c, EDGE_STORAGE_FIELDS)
        _reserve(storage_kwargs, "base_storage_need", d.base_storage_gb, d.storage_gb, 0.25, EdgeStorage,
                 "A quarter of the device's storage at most")
        kwargs["storage"] = EdgeStorage.from_defaults(f"{name} storage", **storage_kwargs)
        _apply_fields(kwargs, c, EDGE_DEVICE_FIELDS, ("cores", "ram_gb", "base_ram_gb"))
        _reserve(kwargs, "base_ram_consumption", d.base_ram_gb, d.ram_gb, 0.25, cls,
                 "A quarter of the device's RAM at most")
    device = cls.from_defaults(name, **kwargs)
    c.close()
    return device


def build_edge_groups(spec: WebEdgeSpec, devices: dict, resolutions: list[Resolution]) -> dict:
    """The optional groups, children first, each holding its devices and sub-groups with their counts."""
    pending, groups = {g.name: g for g in spec.edge_device_groups}, {}
    while pending:
        ready = [g for g in pending.values() if all(sub in groups for sub in g.sub_group_counts)]
        if not ready:
            missing = {sub for g in pending.values() for sub in g.sub_group_counts if sub not in groups}
            raise ValueError(f"Unknown or cyclic edge device groups: {sorted(missing)}")
        for g in ready:
            c = _Comments(g, resolutions)
            groups[g.name] = EdgeDeviceGroup(
                _label(g.name, resolutions),
                sub_group_counts={groups[n]: SourceValue(v * u.dimensionless, comment=c.take(n))
                                  for n, v in g.sub_group_counts.items()},
                edge_device_counts={_lookup(devices, n, "edge device"): SourceValue(v * u.dimensionless, comment=c.take(n))
                                    for n, v in g.device_counts.items()})
            c.close()
            del pending[g.name]
    return groups


def build_edge_function(f: EdgeFunctionSpec, devices: dict, jobs: dict, resolutions: list[Resolution]) -> EdgeFunction:
    """What a device runs, and its server calls: each call is one server need on the web builder's jobs it lists,
    so a server devices and people share is built once."""
    c = _Comments(f, resolutions)
    name = _label(f.name, resolutions)
    device = _lookup(devices, f.device, "edge device")
    kwargs = {"edge_device": device}
    if isinstance(device, EdgeAppliance):
        if f.workload_fraction is not None:
            kwargs["recurrent_workload"] = _weekly(f.workload_fraction, "concurrent", c.take("workload_fraction"))
        need = RecurrentEdgeWorkload.from_defaults(f"{name} workload", **kwargs)
    else:
        if f.cpu_cores_avg is not None:
            kwargs["recurrent_compute_needed"] = _weekly(f.cpu_cores_avg, "cpu_core", c.take("cpu_cores_avg"))
        if f.ram_gb_avg is not None:
            kwargs["recurrent_ram_needed"] = _weekly(f.ram_gb_avg, "GB_ram", c.take("ram_gb_avg"))
        need = RecurrentEdgeProcess.from_defaults(f"{name} process", **kwargs)
    server_needs = []
    for call in f.server_calls:
        called = {_lookup(jobs, job, "job"): 1 for job in call.jobs}
        server_needs.append(RecurrentServerNeed(
            f"{name}: {', '.join(job.name for job in called)}", edge_device=device,
            recurrent_volume_per_edge_device=_weekly(call.times_per_hour, "occurrence", call.comment), jobs=called))
    function = EdgeFunction(name, [need], server_needs)
    c.close()
    return function


def _deployment_spans(spec: WebEdgeSpec) -> dict[str, float]:
    """Years each deployment's units stay in service: as stated, else the shortest lifespan of the devices its
    journey runs on, six years at most."""
    devices = {d.name: d for d in spec.edge_devices}
    device_of = {f.name: f.device for f in spec.edge_functions}
    functions_of = {j.name: j.functions for j in spec.edge_journeys}
    spans = {}
    for dep in spec.edge_deployments:  # an unknown name is refused by the builders, not here
        lifespans = [devices[device_of[f]].lifespan_years for f in functions_of.get(dep.journey, [])
                     if device_of.get(f) in devices]
        spans[dep.name] = dep.usage_span_years or min([MAX_DEFAULT_SPAN_YEARS] + [years for years in lifespans if years])
    return spans


def build_edge_deployment(dep: EdgeDeploymentSpec, journeys: dict, shared: _Shared, start: date, span_years: float,
                          resolutions: list[Resolution]) -> EdgeUsagePattern:
    """Deployments per period from the deployment's own start date, else the shared `start`, until the end of the
    web year, and their usage span."""
    c = _Comments(dep, resolutions)
    comment = " ".join(filter(None, (c.take("new_units"), c.take("start_date")))) or None
    pattern = EdgeUsagePattern(
        _label(dep.name, resolutions), [_lookup(journeys, dep.journey, "edge journey")], shared.network(dep.network),
        shared.country(dep.country), _volume_timeseries(dep.new_units, (dep.start_date or start, WEB_YEAR_END), 0, comment),
        usage_span=SourceValue(span_years * u.year, comment=c.take("usage_span_years")))
    c.close()
    return pattern


def build_system(spec: ModelSpec) -> tuple[System, list[Resolution]]:
    """Returns the system and the catalog resolutions made on the way (see catalogs.py)."""
    edge = isinstance(spec, WebEdgeSpec)
    sections = [spec.servers, spec.genai_apis, spec.jobs, spec.journeys]
    if edge:
        sections += [spec.edge_devices, spec.edge_device_groups, spec.edge_functions, spec.edge_journeys]
    for section in sections:
        names = [obj.name for obj in section]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate declaration names")
    resolutions: list[Resolution] = []
    shared = _Shared(resolutions)
    spans = _deployment_spans(spec) if edge else {}
    dated = [p.start_date for p in spec.usage_patterns] + ([d.start_date for d in spec.edge_deployments] if edge else [])
    start = min([d for d in dated if d] or [WEB_YEAR_START])
    web_end = max([WEB_YEAR_END] + [WEB_YEAR_END + timedelta(days=round(365 * span)) for span in spans.values()])
    narrate("**One period for people and devices**: web usage runs from the earliest start date the answer gives, the "
            "web year's first day without one, until the last deployed device retires; deployments run to the web "
            "year's end, so a fleet in service since a past date is counted from it. A usage dated on its own starts "
            "when it says.", lambda: {"start": start.isoformat(), "web_end": web_end.isoformat(), "spans_years": spans})
    narrate("A fresh library system is built **in dependency order**: servers and external APIs, the jobs that run "
            "on them, the journeys made of those jobs, the usage patterns. Each name the answer gives a catalog is "
            "snapped to an entry the library knows, and each snap kept as a `Resolution`.",
            lambda: {"servers": len(spec.servers), "genai_apis": len(spec.genai_apis), "jobs": len(spec.jobs),
                     "journeys": len(spec.journeys), "usage_patterns": len(spec.usage_patterns)})
    servers = {s.name: build_server(s, resolutions) for s in spec.servers}
    apis = {a.name: build_genai_api(a, resolutions) for a in spec.genai_apis}
    jobs = {j.name: build_job(j, servers, apis, resolutions) for j in spec.jobs}
    journeys = {jo.name: build_journey(jo, jobs, resolutions) for jo in spec.journeys}
    usage_patterns = [build_usage_pattern(p, journeys, shared, (start, web_end), resolutions) for p in spec.usage_patterns]
    edge_patterns = []
    if edge:
        narrate("A Web + edge answer's **edge sections follow, on the web jobs**: the devices and their optional groups, "
                "what each device runs with its server calls to the jobs it lists, the edge journeys, the deployments. "
                "A server devices and people share is built once.",
                lambda: {"edge_devices": len(spec.edge_devices), "edge_device_groups": len(spec.edge_device_groups),
                         "edge_functions": len(spec.edge_functions), "edge_deployments": len(spec.edge_deployments)})
        devices = {d.name: build_edge_device(d, resolutions) for d in spec.edge_devices}
        build_edge_groups(spec, devices, resolutions)
        functions = {f.name: build_edge_function(f, devices, jobs, resolutions) for f in spec.edge_functions}
        edge_journeys = {j.name: EdgeUsageJourney(_label(j.name, resolutions),
                                                  [_lookup(functions, n, "edge function") for n in j.functions])
                         for j in spec.edge_journeys}
        edge_patterns = [build_edge_deployment(dep, edge_journeys, shared, start, spans[dep.name], resolutions)
                         for dep in spec.edge_deployments]
    return System(_label(spec.system_name, resolutions), usage_patterns, edge_patterns), resolutions
