"""Compact structure DSL for AI-generated e-footprint models, and its builder.

The DSL is what the LLM writes. It names objects and their relationships and leaves every
unstated value to the library defaults. `build_system` turns a validated `ModelSpec` into a
real `System` that can be computed and exported to the interface JSON format.
"""
from __future__ import annotations

from typing import Literal, Optional

import re

import numpy as np
from pint import Quantity
from pydantic import BaseModel, ConfigDict, Field

from efootprint.abstract_modeling_classes.source_objects import (
    SourceHourlyValues, SourceObject, SourceRecurrentValues, SourceValue)
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import GPUJob, Job
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


class EdgeDeviceSpec(Strict):
    name: str
    kind: Literal["computer", "appliance"] = "computer"
    cores: Optional[float] = None
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    power_w: Optional[float] = None
    embodied_kg: Optional[float] = None
    lifespan_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class EdgeServerCallSpec(Strict):
    job: str
    times_per_hour: float
    comment: Optional[str] = None


class EdgeFunctionSpec(Strict):
    name: str
    device: str
    cpu_cores_avg: Optional[float] = None
    ram_gb_avg: Optional[float] = None
    storage_gb_per_week: Optional[float] = None
    storage_retention_weeks: Optional[float] = None  # set for a rolling buffer: occupied = weekly write x retention
    workload_fraction: Optional[float] = None
    server_calls: list[EdgeServerCallSpec] = Field(default_factory=list)
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class EdgeDeploymentSpec(Strict):
    name: str
    functions: list[str]
    country: str = "FRANCE"
    network: str = "wifi"
    new_devices: VolumeSpec
    existing_devices: Optional[float] = None  # installed base at the start of the modeling period
    usage_span_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)  # field name -> why that number


class ModelSpec(Strict):
    system_name: str
    servers: list[ServerSpec] = Field(default_factory=list)
    genai_apis: list[GenAIApiSpec] = Field(default_factory=list)
    jobs: list[JobSpec] = Field(default_factory=list)
    journeys: list[JourneySpec] = Field(default_factory=list)
    usage_patterns: list[UsagePatternSpec] = Field(default_factory=list)
    edge_devices: list[EdgeDeviceSpec] = Field(default_factory=list)
    edge_functions: list[EdgeFunctionSpec] = Field(default_factory=list)
    edge_deployments: list[EdgeDeploymentSpec] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


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


def _opt(kwargs: dict, key: str, c: _Comments, field: str, unit):
    value = c.value(field)
    if value is not None:
        kwargs[key] = SourceValue(value * unit, comment=c.take(field))


def _const_week(value: float, unit, comment: Optional[str] = None) -> SourceRecurrentValues:
    return SourceRecurrentValues(Quantity(np.array([value] * 168, dtype=np.float32), unit), comment=comment)


def _edge_storage_need(f: "EdgeFunctionSpec", c: _Comments, device, spec: "ModelSpec", resolutions: list[Resolution]):
    """Weekly storage curve of an edge function.

    Without retention the library accumulates writes for the whole usage span; a 32 GB gateway writing
    1 GB a week overflows after 32 weeks and the build fails. A rolling buffer (retention given, or fitted
    when the accumulation would overflow) keeps a steady occupied volume on the device storage instead.
    """
    weekly = f.storage_gb_per_week
    capacity_gb = float(device.storage.storage_capacity_per_unit.value.to(u.GB_stored).magnitude)
    span_years = max([d.usage_span_years or 6 for d in spec.edge_deployments if f.name in d.functions] or [6])
    retention = f.storage_retention_weeks
    if retention is None and weekly * 52 * span_years > capacity_gb:
        retention = round(0.8 * capacity_gb / weekly, 1)
        resolutions.append(Resolution(
            "edge_storage", f"{f.name}: {weekly} GB/week over {span_years} y on {capacity_gb:.0f} GB",
            f"rolling buffer, {retention} weeks retention", "fitted"))
    comment = " ".join(filter(None, (c.take("storage_gb_per_week"), c.take("storage_retention_weeks")))) or None
    if retention is None:
        return _const_week(weekly / 168, u.GB_stored, comment)
    occupied = SourceValue(weekly * retention * u.GB_stored, comment=comment)
    device.storage.base_storage_need = (device.storage.base_storage_need + occupied).set_label(
        f"Base storage need incl. {f.name} buffer")
    return _const_week(0, u.GB_stored)


def _volume_timeseries(volume: VolumeSpec, growth_pct_per_year: float = 0, comment: Optional[str] = None,
                       initial_stock: Optional[float] = None):
    """Hourly volume from the DSL period, with an optional installed base put into service in the first hour."""
    value, per = volume.value, volume.per
    if per == "minute":
        value, per = value * 60 * 24, "day"
    elif per == "hour":
        value, per = value * 24, "day"
    elif per == "week":
        value, per = value / 7, "day"
    series = ExplainableHourlyQuantitiesFromFormInputs({
        "start_date": MODELING_START_DATE,
        "modeling_duration_value": MODELING_DURATION_YEARS,
        "modeling_duration_unit": "year",
        "initial_volume": value,
        "initial_volume_timespan": per,
        "net_growth_rate_in_percentage": growth_pct_per_year,
        "net_growth_rate_timespan": "year",
    }, source=Sources.USER_DATA, comment=comment)
    if not initial_stock:
        return series
    hourly = np.array(series.value.magnitude, dtype=np.float32)
    hourly[0] += initial_stock
    return SourceHourlyValues(Quantity(hourly, series.value.units), start_date=series.start_date,
                              source=Sources.USER_DATA, comment=comment)


DEVICE_ARCHETYPES = ("smartphone", "laptop", "screen", "box")
NO_DEVICE_WORDS = ("none", "null", "no", "server", "cpu", "batch", "cron", "appliance", "gateway", "sensor", "edge")
NETWORK_ALIASES = {
    "wifi": "wifi", "wi-fi": "wifi", "wlan": "wifi", "ethernet": "wifi", "wired": "wifi", "fiber": "wifi",
    "fibre": "wifi", "lan": "wifi", "broadband": "wifi", "fixed": "wifi",
    "mobile": "mobile", "cellular": "mobile", "4g": "mobile", "5g": "mobile", "lte": "mobile", "3g": "mobile",
    "zigbee": "mobile", "lora": "mobile", "lorawan": "mobile", "sigfox": "mobile", "nb-iot": "mobile",
    "nbiot": "mobile", "bluetooth": "mobile", "ble": "mobile", "satellite": "mobile",
}


class _Shared:
    """One instance per device archetype, network and country, shared across patterns."""

    def __init__(self, resolutions: list[Resolution]):
        self.devices, self.networks, self.countries = {}, {}, {}
        self.resolutions = resolutions

    def label(self, name: str) -> str:
        """Object names are labels the user reads in a diagram: identifiers get their separators replaced.

        Only identifier shapes are touched (snake_case, or kebab-case without spaces); hyphenated English such as
        "Time-series DB" or "Ask follow-up" is left alone.
        """
        if "_" not in name and not ("-" in name and " " not in name):
            return name
        label = re.sub(r"[_-]+", " ", name).strip()
        label = label[:1].upper() + label[1:]
        self.resolutions.append(Resolution("name", name, label, "humanized"))
        return label

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


def build_system(spec: ModelSpec) -> tuple[System, list[Resolution]]:
    """Returns the system and the catalog resolutions made on the way (see catalogs.py)."""
    resolutions: list[Resolution] = []
    shared = _Shared(resolutions)
    L = shared.label

    servers = {}
    for s in spec.servers:
        c = _Comments(s, resolutions)
        storage_kwargs = {}
        _opt(storage_kwargs, "base_storage_need", c, "storage_gb", u.GB_stored)
        storage = Storage.from_defaults(f"{L(s.name)} storage", **storage_kwargs)
        kwargs = {"storage": storage}
        _opt(kwargs, "average_carbon_intensity", c, "carbon_intensity_g_per_kwh", u.g / u.kWh)
        if s.kind == "gpu":
            _opt(kwargs, "compute", c, "gpus", u.gpu)
            servers[s.name] = GPUServer.from_defaults(L(s.name), **kwargs)
        elif s.cloud_provider:
            # Catalog instance: cores and RAM then come from Boavizta, the stated ones only drive the pick.
            provider, instance = resolve_cloud_instance(s.cloud_provider, s.instance_type, s.cores, s.ram_gb, resolutions)
            sizing = " ".join(filter(None, (c.take("cores"), c.take("ram_gb"), c.take("instance_type")))) or None
            servers[s.name] = BoaviztaCloudServer.from_defaults(
                L(s.name), provider=SourceObject(provider, comment=c.take("cloud_provider")),
                instance_type=SourceObject(instance, comment=sizing), **kwargs)
        else:
            _opt(kwargs, "compute", c, "cores", u.cpu_core)
            _opt(kwargs, "ram", c, "ram_gb", u.GB_ram)
            servers[s.name] = Server.from_defaults(L(s.name), **kwargs)
        c.close()

    apis = {}
    for a in spec.genai_apis:
        c = _Comments(a, resolutions)
        provider, model_name = resolve_genai(a.provider, a.model_name, resolutions)
        apis[a.name] = EcoLogitsGenAIExternalAPI.from_defaults(
            L(a.name), provider=SourceObject(provider, comment=c.take("provider")),
            model_name=SourceObject(model_name, comment=c.take("model_name")))
        c.close()

    jobs = {}
    for j in spec.jobs:
        if (j.server is None) == (j.genai_api is None):
            raise ValueError(f"Job '{j.name}' must reference exactly one of server or genai_api")
        c = _Comments(j, resolutions)
        if j.genai_api:
            kwargs = {"external_api": _lookup(apis, j.genai_api, "genai_api")}
            _opt(kwargs, "output_token_count", c, "output_tokens", u.dimensionless)
            jobs[j.name] = EcoLogitsGenAIExternalAPIJob.from_defaults(L(j.name), **kwargs)
            c.close()
            continue
        server = _lookup(servers, j.server, "server")
        kwargs = {"server": server}
        _opt(kwargs, "data_transferred", c, "data_transferred_kb", u.kB)
        _opt(kwargs, "data_stored", c, "data_stored_kb", u.kB_stored)
        _opt(kwargs, "request_duration", c, "request_duration_s", u.s)
        _opt(kwargs, "ram_needed", c, "ram_mb", u.MB_ram)
        if isinstance(server, GPUServer):
            _opt(kwargs, "compute_needed", c, "gpus", u.gpu)
            jobs[j.name] = GPUJob.from_defaults(L(j.name), **kwargs)
        else:
            _opt(kwargs, "compute_needed", c, "cpu_cores", u.cpu_core)
            jobs[j.name] = Job.from_defaults(L(j.name), **kwargs)
        c.close()

    journeys = {}
    for jo in spec.journeys:
        steps = []
        for st in jo.steps:
            c = _Comments(st, resolutions)
            kwargs = {"jobs": [_lookup(jobs, name, "job") for name in st.jobs]}
            _opt(kwargs, "user_time_spent", c, "user_time_spent_min", u.min)
            steps.append(UsageJourneyStep.from_defaults(L(st.name), **kwargs))
            c.close()
        journeys[jo.name] = UsageJourney(L(jo.name), uj_steps=steps)

    usage_patterns = []
    for p in spec.usage_patterns:
        c = _Comments(p, resolutions)
        volume_comment = " ".join(filter(None, (c.take("volume"), c.take("growth_pct_per_year")))) or None
        usage_patterns.append(UsagePattern(
            L(p.name), [_lookup(journeys, p.journey, "journey")], shared.devices_for(p.device), shared.network(p.network),
            shared.country(p.country), _volume_timeseries(p.volume, p.growth_pct_per_year, volume_comment)))
        c.close()

    edge_devices = {}
    for d in spec.edge_devices:
        c = _Comments(d, resolutions)
        kwargs = {}
        _opt(kwargs, "power", c, "power_w", u.W)
        _opt(kwargs, "carbon_footprint_manufacturing", c, "embodied_kg", u.kg)
        _opt(kwargs, "lifespan", c, "lifespan_years", u.year)
        if d.kind == "appliance":
            edge_devices[d.name] = EdgeAppliance.from_defaults(L(d.name), **kwargs)
        else:
            # The library default reserves 30 GB of base need, more than a small gateway's flash: start at 0.
            storage_kwargs = {"base_storage_need": SourceValue(0 * u.GB_stored)}
            _opt(storage_kwargs, "storage_capacity_per_unit", c, "storage_gb", u.GB_stored)
            kwargs["storage"] = EdgeStorage.from_defaults(f"{L(d.name)} storage", **storage_kwargs)
            _opt(kwargs, "compute", c, "cores", u.cpu_core)
            _opt(kwargs, "ram", c, "ram_gb", u.GB_ram)
            if d.ram_gb is not None:
                # The library default reserves 1 GB of base RAM, all of a small gateway's: cap it at a quarter.
                kwargs["base_ram_consumption"] = SourceValue(min(1, d.ram_gb / 4) * u.GB_ram)
            edge_devices[d.name] = EdgeComputer.from_defaults(L(d.name), **kwargs)
        c.close()

    edge_functions = {}
    for f in spec.edge_functions:
        c = _Comments(f, resolutions)
        device = _lookup(edge_devices, f.device, "edge_device")
        if isinstance(device, EdgeAppliance):
            kwargs = {"edge_device": device}
            if f.workload_fraction is not None:
                kwargs["recurrent_workload"] = _const_week(f.workload_fraction, u.concurrent, c.take("workload_fraction"))
            device_needs = [RecurrentEdgeWorkload.from_defaults(f"{L(f.name)} workload", **kwargs)]
        else:
            kwargs = {"edge_device": device}
            if f.cpu_cores_avg is not None:
                kwargs["recurrent_compute_needed"] = _const_week(f.cpu_cores_avg, u.cpu_core, c.take("cpu_cores_avg"))
            if f.ram_gb_avg is not None:
                kwargs["recurrent_ram_needed"] = _const_week(f.ram_gb_avg, u.GB_ram, c.take("ram_gb_avg"))
            if f.storage_gb_per_week:
                kwargs["recurrent_storage_needed"] = _edge_storage_need(f, c, device, spec, resolutions)
            device_needs = [RecurrentEdgeProcess.from_defaults(f"{L(f.name)} process", **kwargs)]
        server_needs = [
            RecurrentServerNeed(
                f"{L(f.name)}: {L(call.job)}", edge_device=device,
                recurrent_volume_per_edge_device=_const_week(call.times_per_hour, u.occurrence, call.comment),
                jobs=[_lookup(jobs, call.job, "job")])
            for call in f.server_calls]
        edge_functions[f.name] = EdgeFunction(L(f.name), device_needs, server_needs)
        c.close()

    edge_patterns = []
    for dep in spec.edge_deployments:
        c = _Comments(dep, resolutions)
        bundle = EdgeUsageJourney(
            f"{L(dep.name)} functions", [_lookup(edge_functions, name, "edge_function") for name in dep.functions])
        kwargs = {}
        _opt(kwargs, "usage_span", c, "usage_span_years", u.year)
        edge_patterns.append(EdgeUsagePattern(
            L(dep.name), [bundle], shared.network(dep.network), shared.country(dep.country),
            _volume_timeseries(
                dep.new_devices, comment=" ".join(filter(None, (c.take("new_devices"), c.take("existing_devices")))) or None,
                initial_stock=dep.existing_devices),
            **kwargs))
        c.close()

    return System(L(spec.system_name), usage_patterns, edge_patterns), resolutions


def json_schema() -> dict:
    return ModelSpec.model_json_schema()
