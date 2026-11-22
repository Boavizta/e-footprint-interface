"""Compact structure DSL for AI-generated e-footprint models, and its builder.

The DSL is what the LLM writes. It names objects and their relationships and leaves every
unstated value to the library defaults. `build_system` turns a validated `ModelSpec` into a
real `System` that can be computed and exported to the interface JSON format.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, timedelta
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

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

from comprehension_harness.python import narrate
from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import GROWTH_DURATION_LIMITS

from .catalogs import Resolution, resolve_cloud_instance, resolve_genai

# The web year: usage and deployments the answer does not date start here, and deployments end with it by default.
WEB_YEAR_START = date(2027, 1, 1)
WEB_YEAR_END = date(2027, 12, 31)
MAX_DEFAULT_SPAN_YEARS = 6  # the library's own default usage span
# The longest period the Growth projection editor holds, in the longer of its two units (3,650 days against 3,600).
EDITOR_LIMIT = (GROWTH_DURATION_LIMITS["year"], "year")
EDITOR_LIMIT_HOW = "Growth projection holds 10 years at most"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _number_as_text(value):
    """A comment written as a number (`"data_stored_kb": 2500`) is read as its text; any other non-string fails."""
    return str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value


Comment = Annotated[str, BeforeValidator(_number_as_text)]  # every comment of the schemas


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
    comments: dict[str, Comment] = Field(default_factory=dict)  # field name -> why that number


class GenAIApiSpec(Strict):
    name: str
    provider: str = "openai"
    model_name: Optional[str] = None  # unstated in the description -> provider default, recorded as a resolution
    comments: dict[str, Comment] = Field(default_factory=dict)  # field name -> why that number


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
    comments: dict[str, Comment] = Field(default_factory=dict)  # field name -> why that number


class StepSpec(Strict):
    name: str
    user_time_spent_min: Optional[float] = None
    jobs: list[str] = Field(default_factory=list)
    comments: dict[str, Comment] = Field(default_factory=dict)


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
    comments: dict[str, Comment] = Field(default_factory=dict)  # field name -> why that number


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
    comments: dict[str, Comment] = Field(default_factory=dict)


class EdgeDeviceGroupSpec(Strict):
    name: str
    device_counts: dict[str, float] = Field(default_factory=dict)     # edge device name -> count per group
    sub_group_counts: dict[str, float] = Field(default_factory=dict)  # group name -> count per group
    comments: dict[str, Comment] = Field(default_factory=dict)            # device or group name -> why that count


class ServerCallSpec(Strict):
    jobs: list[str]  # every job one call triggers, the database write included
    times_per_hour: float
    comment: Optional[Comment] = None


class EdgeFunctionSpec(Strict):
    name: str
    device: str
    cpu_cores_avg: Optional[float] = None
    ram_gb_avg: Optional[float] = None
    workload_fraction: Optional[float] = None  # appliance only
    server_calls: list[ServerCallSpec] = Field(default_factory=list)
    comments: dict[str, Comment] = Field(default_factory=dict)


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
    end_date: Optional[date] = None    # the last installation of a fleet that no longer grows
    usage_span_years: Optional[float] = None
    comments: dict[str, Comment] = Field(default_factory=dict)


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


DAYS_PER_UNIT = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}  # Growth projection's
EDITOR_TIMESPANS = ("day", "month", "year")  # the hourly editor's volume periods
VOLUME_TOLERANCE = 0.005  # the most a volume moves when rounded to the editor's whole number
ROUNDING_DAYS = 15  # a duration is whole years within this many days; a move or a loss this short is not listed


def _duration(start: date, end: date, round_up: bool = False) -> tuple[int, str]:
    """`start` to `end` inclusive as the editor's duration: whole years when it is one within 15 days, else whole
    months, rounded to the nearest or, with `round_up`, so that the period reaches `end`. A start after the end
    refuses the answer."""
    days = (end - start).days + 1
    if days <= 0:
        raise ValueError(f"A start date ({start}) falls after the end of its period ({end})")
    years = round(days / 365)
    if years and abs(days - 365 * years) <= ROUNDING_DAYS and not (round_up and days > 365 * years):
        return years, "year"
    return max(1, math.ceil(days / 30) if round_up else round(days / 30)), "month"


def _end(start: date, duration: tuple[int, str]) -> date:
    """The last day a Growth projection period starting on `start` covers."""
    value, unit = duration
    return start + timedelta(days=value * DAYS_PER_UNIT[unit] - 1)


def _start(end: date, duration: tuple[int, str]) -> date:
    """The first day of a Growth projection period ending on `end`: the inverse of `_end`."""
    value, unit = duration
    return end - timedelta(days=value * DAYS_PER_UNIT[unit] - 1)


EARLIEST_WEB_START = _start(WEB_YEAR_END, EDITOR_LIMIT)  # an earlier web usage cut to 10 years misses the web year


def _period_volume(days: float, growth_pct_per_year: float) -> float:
    """What `days` days hold when the first holds 1, as Growth projection compounds a yearly growth day by day."""
    rate = (1 + growth_pct_per_year / 100) ** (1 / 365)
    return days if rate == 1 else (rate ** days - 1) / (rate - 1)


def _editor_volume(volume: VolumeSpec, growth_pct_per_year: float) -> tuple[int, str]:
    """A volume as the whole number the hourly editor's step takes, over its stated day, month or year (a day for a
    shorter period) or the first longer one that rounding moves by 0.5 % at most, a year failing that: a week's
    volume opens per day, a small one per month or year rather than as 0."""
    first_day = volume.value / _period_volume(DAYS_PER_UNIT[volume.per], growth_pct_per_year)
    spans = EDITOR_TIMESPANS[EDITOR_TIMESPANS.index(volume.per):] if volume.per in EDITOR_TIMESPANS else EDITOR_TIMESPANS
    for per in spans:
        value = first_day * _period_volume(DAYS_PER_UNIT[per], growth_pct_per_year)
        if abs(round(value) - value) <= VOLUME_TOLERANCE * value or per == "year":
            return round(value), per


def _amount(value: float) -> str:
    """A volume as a comment reads it: whole above 100, three significant figures below."""
    return f"{value:,.0f}" if abs(value) >= 100 else f"{value:.3g}"


def _volume_timeseries(volume: VolumeSpec, start: date, duration: tuple[int, str], growth_pct_per_year: float = 0,
                       comment: Optional[str] = None):
    """Hourly volume from the DSL period over `duration` from `start`, as the Growth projection inputs the hourly
    editor prefills: a raw series would open empty."""
    value, per = _editor_volume(volume, growth_pct_per_year)
    return ExplainableHourlyQuantitiesFromFormInputs({
        "start_date": start.isoformat(),
        "modeling_duration_value": duration[0],
        "modeling_duration_unit": duration[1],
        "initial_volume": value,
        "initial_volume_timespan": per,
        "net_growth_rate_in_percentage": growth_pct_per_year,
        "net_growth_rate_timespan": "year",
    }, source=Sources.USER_DATA, comment=comment)


def _weekly(value: float, unit: str, comment: Optional[str] = None):
    """A constant need over the typical week, as the inputs the weekly editor prefills, to the hundredth its step
    takes."""
    return ExplainableRecurrentQuantitiesFromConstant(
        {"constant_value": round(value, 2), "constant_unit": unit}, source=Sources.USER_DATA, comment=comment)


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
    """`period` is the shared one: the usage runs from its own start date when it has one, else the shared start,
    until the period's end. It starts no earlier than the editor's 10 years before the web year's end, a stated start
    moved there listed beyond the rounding's 15 days; a usage still longer loses its end, listed, so that a cut never
    ends it before the web year does. Within 10 years, a usage the month unit cannot hold is 10 years, reaching past
    its end. The stated volume is the one of the web year's first day, or of the usage's own start when later: a
    usage that starts before it with a growth starts from that volume discounted by the growth between the two dates,
    its comment saying so. The growth is the whole percent the editor's step takes; a negative one, which the editor
    refuses, is set to 0 and listed."""
    c = _Comments(p, resolutions)
    start = p.start_date or max(period[0], EARLIEST_WEB_START)
    if start < EARLIEST_WEB_START:
        if (EARLIEST_WEB_START - start).days > ROUNDING_DAYS:
            resolutions.append(Resolution("usage period", f"{p.name}: from {start}", f"from {EARLIEST_WEB_START}",
                                          f"{EDITOR_LIMIT_HOW}: the 10 ending with 2027 are kept"))
        start = EARLIEST_WEB_START
    growth = round(p.growth_pct_per_year)
    if growth < 0:
        resolutions.append(Resolution("growth", f"{p.name}: {p.growth_pct_per_year:g} % a year", "0 % a year",
                                      "the editor accepts no negative growth"))
        growth = 0
    volume, discounted = p.volume, None
    if growth and start < WEB_YEAR_START:
        factor = (1 + growth / 100) ** ((WEB_YEAR_START - start).days / 365)
        volume = VolumeSpec(value=p.volume.value / factor, per=p.volume.per)
        value, per = _editor_volume(volume, growth)
        article = "an" if p.volume.per == "hour" else "a"
        discounted = (f"{_amount(p.volume.value)} {article} {p.volume.per} on {WEB_YEAR_START.isoformat()} as stated: "
                      f"{value:,} a {per} on {start.isoformat()} at {growth} % a year.")
    volume_comment = " ".join(filter(None, (c.take("volume"), c.take("growth_pct_per_year"), c.take("start_date"),
                                            discounted))) or None
    duration = _duration(start, period[1], round_up=True)
    if period[1] > _end(start, EDITOR_LIMIT):
        resolutions.append(Resolution("usage period", f"{p.name}: {start} to {period[1]}",
                                      f"{start} to {_end(start, EDITOR_LIMIT)}", EDITOR_LIMIT_HOW))
    if duration[0] > GROWTH_DURATION_LIMITS[duration[1]]:  # beyond 10 years, or above 120 months within them
        duration = EDITOR_LIMIT
    pattern = UsagePattern(
        _label(p.name, resolutions), [_lookup(journeys, p.journey, "journey")], shared.devices_for(p.device),
        shared.network(p.network), shared.country(p.country),
        _volume_timeseries(volume, start, duration, growth, volume_comment))
    c.close()
    return pattern


def _reserve(kwargs: dict, attr: str, stated, capacity, share: float, cls, bound: str):
    """A reserve the answer omits is the library default, at most `bound` (`share` of the stated capacity): the
    default idle power (5 W) exceeds a sensor's whole power, the default base RAM (1 GB) all of a small gateway's,
    the default base storage (30 GB) a gateway's flash. Its comment says which applied. Without a stated capacity
    the library default stands."""
    if stated is None and capacity is not None:
        default = cls.default_values[attr].value
        cap = capacity * share * default.units
        comment = (f"The library default, within {bound}" if default <= cap
                   else f"{bound[0].upper()}{bound[1:]}, the library default being more")
        kwargs[attr] = SourceValue(min(default, cap), comment=comment)


def _device_class(d: EdgeDeviceSpec):
    return EdgeAppliance if d.kind == "appliance" else EdgeComputer


def build_edge_device(d: EdgeDeviceSpec, resolutions: list[Resolution]):
    """A gateway, sensor or controller, built from the hardware and the reserved resources the answer states."""
    c = _Comments(d, resolutions)
    name = _label(d.name, resolutions)
    cls = _device_class(d)
    kwargs = {}
    _apply_fields(kwargs, c, EDGE_DEVICE_FIELDS, ("power_w", "idle_power_w", "embodied_kg", "lifespan_years"))
    _reserve(kwargs, "idle_power", d.idle_power_w, d.power_w, 1, cls, "the device's power")
    if cls is EdgeComputer:
        storage_kwargs = {}
        _apply_fields(storage_kwargs, c, EDGE_STORAGE_FIELDS)
        _reserve(storage_kwargs, "base_storage_need", d.base_storage_gb, d.storage_gb, 0.25, EdgeStorage,
                 "a quarter of the device's storage")
        kwargs["storage"] = EdgeStorage.from_defaults(f"{name} storage", **storage_kwargs)
        _apply_fields(kwargs, c, EDGE_DEVICE_FIELDS, ("cores", "ram_gb", "base_ram_gb"))
        _reserve(kwargs, "base_ram_consumption", d.base_ram_gb, d.ram_gb, 0.25, cls,
                 "a quarter of the device's RAM")
    device = cls.from_defaults(name, **kwargs)
    c.close()
    return device


def build_edge_groups(spec: WebEdgeSpec, devices: dict, resolutions: list[Resolution]) -> dict:
    """The optional groups, children first, each holding its devices and sub-groups with their counts. A declared
    device written as a sub-group, and named by no group, is counted as that device in the group."""
    declared = {g.name for g in spec.edge_device_groups}
    pending, groups, held = {g.name: g for g in spec.edge_device_groups}, {}, {}
    for g in spec.edge_device_groups:
        slips = {n: v for n, v in g.sub_group_counts.items() if n in devices and n not in declared}
        if set(slips) & set(g.device_counts):
            raise ValueError(f"Edge device group {g.name} names {sorted(set(slips) & set(g.device_counts))} as both "
                             f"a device and a sub-group")
        held[g.name] = ({n: v for n, v in g.sub_group_counts.items() if n not in slips}, {**g.device_counts, **slips})
        resolutions.extend(Resolution("edge device group", f"{g.name} sub-group {n}", f"device {n}", "moved")
                           for n in slips)
    while pending:
        ready = [g for g in pending.values() if all(sub in groups for sub in held[g.name][0])]
        if not ready:
            missing = {sub for g in pending.values() for sub in held[g.name][0] if sub not in groups}
            raise ValueError(f"Unknown or cyclic edge device groups: {sorted(missing)}")
        for g in ready:
            c = _Comments(g, resolutions)
            sub_group_counts, device_counts = held[g.name]
            groups[g.name] = EdgeDeviceGroup(
                _label(g.name, resolutions),
                sub_group_counts={groups[n]: SourceValue(v * u.dimensionless, comment=c.take(n))
                                  for n, v in sub_group_counts.items()},
                edge_device_counts={_lookup(devices, n, "edge device"): SourceValue(v * u.dimensionless, comment=c.take(n))
                                    for n, v in device_counts.items()})
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


def _deployment_spans(spec: WebEdgeSpec, resolutions: list[Resolution]) -> dict[str, float]:
    """Years each deployment's units stay in service: as stated, else the shortest lifespan of the devices its
    journey runs on, six years at most. A device without a stated lifespan has its class default. A stated span
    above the shortest lifespan, which the library refuses, is cut to it and the cut listed."""
    devices = {d.name: d for d in spec.edge_devices}
    device_of = {f.name: f.device for f in spec.edge_functions}
    functions_of = {j.name: j.functions for j in spec.edge_journeys}
    spans = {}
    for dep in spec.edge_deployments:  # an unknown name is refused by the builders, not here
        run = [devices[device_of[f]] for f in functions_of.get(dep.journey, []) if device_of.get(f) in devices]
        shortest = min((d.lifespan_years or _device_class(d).default_values["lifespan"].value.to(u.year).magnitude
                        for d in run), default=math.inf)
        stated = dep.usage_span_years
        if stated and stated > shortest:
            resolutions.append(Resolution("usage span", f"{dep.name}: {stated:g} years", f"{shortest:g} years",
                                          "cut to its devices' shortest lifespan"))
            stated = shortest
        spans[dep.name] = stated or min(MAX_DEFAULT_SPAN_YEARS, shortest)
    return spans


def _deployment_period(dep: EdgeDeploymentSpec, start: date,
                       resolutions: list[Resolution]) -> tuple[date, tuple[int, str]]:
    """A deployment's start and its duration to its end date, the web year's end without one. A deployment longer
    than the editor's 10 years keeps, at the same rate, the 10 nearest the web year: its last 10 when it ends by the
    web year's end, its first 10 when those cover the web year, else the 10 ending with it. The installations outside
    them are left out, a stated date's loss listed beyond the rounding's 15 days. Within 10 years, a deployment the month unit cannot hold is 120 months to its end."""
    end = dep.end_date or WEB_YEAR_END
    if end > _end(start, EDITOR_LIMIT):
        cut_end = min(end, max(WEB_YEAR_END, _end(start, EDITOR_LIMIT)))
        cut_start = _start(cut_end, EDITOR_LIMIT)
        lost = [f"before {cut_start}"] if dep.start_date and (cut_start - start).days > ROUNDING_DAYS else []
        if dep.end_date and (end - cut_end).days > ROUNDING_DAYS:
            lost.append(f"after {cut_end}")
        if lost:
            resolutions.append(Resolution("usage period", f"{dep.name}: {start} to {end}", f"{cut_start} to {cut_end}",
                                          f"{EDITOR_LIMIT_HOW}: installations {' and '.join(lost)} are not counted"))
        return cut_start, EDITOR_LIMIT
    duration = _duration(start, end)
    if duration[0] > GROWTH_DURATION_LIMITS[duration[1]]:  # above 120 months within 10 years
        duration = (GROWTH_DURATION_LIMITS["month"], "month")
        return _start(end, duration), duration
    return start, duration


def _deployment_periods(usage_patterns: list[UsagePatternSpec], deployments: list[EdgeDeploymentSpec],
                        resolutions: list[Resolution]) -> tuple[date, dict]:
    """The shared start, the earliest date the answer gives once the dated deployments are cut (the web year's first
    day without one), and each deployment's period: a dated one from its start date, the others from the shared
    start, cut silently on that side."""
    periods = {dep.name: _deployment_period(dep, dep.start_date, resolutions) for dep in deployments if dep.start_date}
    start = min([p.start_date for p in usage_patterns if p.start_date] + [s for s, _ in periods.values()]
                or [WEB_YEAR_START])
    for dep in deployments:
        if not dep.start_date:
            periods[dep.name] = _deployment_period(dep, start, resolutions)
    return start, periods


def build_edge_deployment(dep: EdgeDeploymentSpec, journeys: dict, shared: _Shared,
                          period: tuple[date, tuple[int, str]], span_years: float,
                          resolutions: list[Resolution]) -> EdgeUsagePattern:
    """Deployments per period over `period` (its start and duration), and their usage span."""
    c = _Comments(dep, resolutions)
    comment = " ".join(filter(None, (c.take("new_units"), c.take("start_date"), c.take("end_date")))) or None
    pattern = EdgeUsagePattern(
        _label(dep.name, resolutions), [_lookup(journeys, dep.journey, "edge journey")], shared.network(dep.network),
        shared.country(dep.country), _volume_timeseries(dep.new_units, *period, 0, comment),
        usage_span=SourceValue(span_years * u.year, comment=c.take("usage_span_years")))
    c.close()
    return pattern


def build_system(spec: ModelSpec) -> tuple[System, list[Resolution]]:
    """Returns the system and the catalog resolutions made on the way (see catalogs.py)."""
    edge = isinstance(spec, WebEdgeSpec)
    sections = [spec.servers, spec.genai_apis, spec.jobs, spec.journeys]
    if edge:
        sections += [spec.edge_devices, spec.edge_device_groups, spec.edge_functions, spec.edge_journeys,
                     spec.edge_deployments]
    for section in sections:
        names = [obj.name for obj in section]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate declaration names")
    resolutions: list[Resolution] = []
    shared = _Shared(resolutions)
    spans = _deployment_spans(spec, resolutions) if edge else {}
    start, periods = _deployment_periods(spec.usage_patterns, spec.edge_deployments if edge else [], resolutions)
    web_end = max([WEB_YEAR_END] + [_end(*periods[name]) + timedelta(days=round(365 * span))
                                    for name, span in spans.items()])
    narrate("**One period for people and devices**: deployments run to their end date, else the web year's end, "
            "keeping at most the editor's 10 years, those nearest the web year. Web usage runs from the earliest "
            "start after those cuts, or its own, no earlier than 2018-01-03, until the last device retires, within "
            "10 years.",
            lambda: {"start": start.isoformat(), "web_end": web_end.isoformat(), "spans_years": spans})
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
        edge_patterns = [build_edge_deployment(dep, edge_journeys, shared, periods[dep.name], spans[dep.name], resolutions)
                         for dep in spec.edge_deployments]
        resolutions.extend(Resolution("edge device", name, "left out of the footprint", "no deployment runs it")
                           for name, device in devices.items() if not device.edge_usage_patterns)
    return System(_label(spec.system_name, resolutions), usage_patterns, edge_patterns), resolutions
