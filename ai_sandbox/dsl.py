"""Compact structure DSL for AI-generated e-footprint models, and its builder.

The DSL is what the LLM writes. It names objects and their relationships and leaves every
unstated value to the library defaults. `build_system` turns a validated `ModelSpec` into a
real `System` that can be computed and exported to the interface JSON format.
"""
from __future__ import annotations

from typing import Literal, Optional

import numpy as np
from pint import Quantity
from pydantic import BaseModel, ConfigDict, Field

from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceRecurrentValues, SourceValue
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
    assumption: Optional[str] = None


class GenAIApiSpec(Strict):
    name: str
    provider: str
    model_name: str
    assumption: Optional[str] = None


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
    assumption: Optional[str] = None


class StepSpec(Strict):
    name: str
    user_time_spent_min: Optional[float] = None
    jobs: list[str] = Field(default_factory=list)


class JourneySpec(Strict):
    name: str
    steps: list[StepSpec]


class VolumeSpec(Strict):
    value: float
    per: Literal["hour", "day", "month", "year"]


class UsagePatternSpec(Strict):
    name: str
    journey: str
    device: Literal["smartphone", "laptop", "screen", "box"] = "laptop"
    network: Literal["wifi", "mobile"] = "wifi"
    country: str = "FRANCE"
    volume: VolumeSpec
    growth_pct_per_year: float = 0
    assumption: Optional[str] = None


class EdgeDeviceSpec(Strict):
    name: str
    kind: Literal["computer", "appliance"] = "computer"
    cores: Optional[float] = None
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    power_w: Optional[float] = None
    embodied_kg: Optional[float] = None
    lifespan_years: Optional[float] = None
    assumption: Optional[str] = None


class EdgeServerCallSpec(Strict):
    job: str
    times_per_hour: float


class EdgeFunctionSpec(Strict):
    name: str
    device: str
    cpu_cores_avg: Optional[float] = None
    ram_gb_avg: Optional[float] = None
    storage_gb_per_week: Optional[float] = None
    workload_fraction: Optional[float] = None
    server_calls: list[EdgeServerCallSpec] = Field(default_factory=list)
    assumption: Optional[str] = None


class EdgeDeploymentSpec(Strict):
    name: str
    functions: list[str]
    country: str = "FRANCE"
    network: Literal["wifi", "mobile"] = "wifi"
    new_devices: VolumeSpec
    usage_span_years: Optional[float] = None
    assumption: Optional[str] = None


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

def _opt(kwargs: dict, key: str, value, unit):
    if value is not None:
        kwargs[key] = SourceValue(value * unit)


def _const_week(value: float, unit) -> SourceRecurrentValues:
    return SourceRecurrentValues(Quantity(np.array([value] * 168, dtype=np.float32), unit))


def _volume_timeseries(volume: VolumeSpec, growth_pct_per_year: float = 0):
    value, per = volume.value, volume.per
    if per == "hour":
        value, per = value * 24, "day"
    return ExplainableHourlyQuantitiesFromFormInputs({
        "start_date": MODELING_START_DATE,
        "modeling_duration_value": MODELING_DURATION_YEARS,
        "modeling_duration_unit": "year",
        "initial_volume": value,
        "initial_volume_timespan": per,
        "net_growth_rate_in_percentage": growth_pct_per_year,
        "net_growth_rate_timespan": "year",
    }, source=Sources.USER_DATA)


class _Shared:
    """One instance per device archetype, network and country, shared across patterns."""

    def __init__(self):
        self.devices, self.networks, self.countries = {}, {}, {}

    def device(self, kind):
        return self.devices.setdefault(kind, getattr(Device, kind)())

    def network(self, kind):
        factory = Network.wifi_network if kind == "wifi" else Network.mobile_network
        return self.networks.setdefault(kind, factory())

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
    shared = _Shared()
    resolutions: list[Resolution] = []

    servers = {}
    for s in spec.servers:
        storage_kwargs = {}
        _opt(storage_kwargs, "base_storage_need", s.storage_gb, u.GB_stored)
        storage = Storage.from_defaults(f"{s.name} storage", **storage_kwargs)
        kwargs = {"storage": storage}
        _opt(kwargs, "average_carbon_intensity", s.carbon_intensity_g_per_kwh, u.g / u.kWh)
        if s.kind == "gpu":
            _opt(kwargs, "compute", s.gpus, u.gpu)
            servers[s.name] = GPUServer.from_defaults(s.name, **kwargs)
        elif s.cloud_provider:
            # Catalog instance: cores and RAM then come from Boavizta, the stated ones only drive the pick.
            provider, instance = resolve_cloud_instance(s.cloud_provider, s.instance_type, s.cores, s.ram_gb, resolutions)
            servers[s.name] = BoaviztaCloudServer.from_defaults(
                s.name, provider=SourceObject(provider), instance_type=SourceObject(instance), **kwargs)
        else:
            _opt(kwargs, "compute", s.cores, u.cpu_core)
            _opt(kwargs, "ram", s.ram_gb, u.GB_ram)
            servers[s.name] = Server.from_defaults(s.name, **kwargs)

    apis = {}
    for a in spec.genai_apis:
        provider, model_name = resolve_genai(a.provider, a.model_name, resolutions)
        apis[a.name] = EcoLogitsGenAIExternalAPI.from_defaults(
            a.name, provider=SourceObject(provider), model_name=SourceObject(model_name))

    jobs = {}
    for j in spec.jobs:
        if (j.server is None) == (j.genai_api is None):
            raise ValueError(f"Job '{j.name}' must reference exactly one of server or genai_api")
        if j.genai_api:
            kwargs = {"external_api": _lookup(apis, j.genai_api, "genai_api")}
            _opt(kwargs, "output_token_count", j.output_tokens, u.dimensionless)
            jobs[j.name] = EcoLogitsGenAIExternalAPIJob.from_defaults(j.name, **kwargs)
            continue
        server = _lookup(servers, j.server, "server")
        kwargs = {"server": server}
        _opt(kwargs, "data_transferred", j.data_transferred_kb, u.kB)
        _opt(kwargs, "data_stored", j.data_stored_kb, u.kB_stored)
        _opt(kwargs, "request_duration", j.request_duration_s, u.s)
        _opt(kwargs, "ram_needed", j.ram_mb, u.MB_ram)
        if isinstance(server, GPUServer):
            _opt(kwargs, "compute_needed", j.gpus, u.gpu)
            jobs[j.name] = GPUJob.from_defaults(j.name, **kwargs)
        else:
            _opt(kwargs, "compute_needed", j.cpu_cores, u.cpu_core)
            jobs[j.name] = Job.from_defaults(j.name, **kwargs)

    journeys = {}
    for jo in spec.journeys:
        steps = []
        for st in jo.steps:
            kwargs = {"jobs": [_lookup(jobs, name, "job") for name in st.jobs]}
            _opt(kwargs, "user_time_spent", st.user_time_spent_min, u.min)
            steps.append(UsageJourneyStep.from_defaults(st.name, **kwargs))
        journeys[jo.name] = UsageJourney(jo.name, uj_steps=steps)

    usage_patterns = [
        UsagePattern(
            p.name, [_lookup(journeys, p.journey, "journey")], [shared.device(p.device)], shared.network(p.network),
            shared.country(p.country), _volume_timeseries(p.volume, p.growth_pct_per_year))
        for p in spec.usage_patterns]

    edge_devices = {}
    for d in spec.edge_devices:
        kwargs = {}
        _opt(kwargs, "power", d.power_w, u.W)
        _opt(kwargs, "carbon_footprint_manufacturing", d.embodied_kg, u.kg)
        _opt(kwargs, "lifespan", d.lifespan_years, u.year)
        if d.kind == "appliance":
            edge_devices[d.name] = EdgeAppliance.from_defaults(d.name, **kwargs)
        else:
            # The library default reserves 30 GB of base need, more than a small gateway's flash: start at 0.
            storage_kwargs = {"base_storage_need": SourceValue(0 * u.GB_stored)}
            _opt(storage_kwargs, "storage_capacity_per_unit", d.storage_gb, u.GB_stored)
            kwargs["storage"] = EdgeStorage.from_defaults(f"{d.name} storage", **storage_kwargs)
            _opt(kwargs, "compute", d.cores, u.cpu_core)
            _opt(kwargs, "ram", d.ram_gb, u.GB_ram)
            edge_devices[d.name] = EdgeComputer.from_defaults(d.name, **kwargs)

    edge_functions = {}
    for f in spec.edge_functions:
        device = _lookup(edge_devices, f.device, "edge_device")
        if isinstance(device, EdgeAppliance):
            kwargs = {"edge_device": device}
            if f.workload_fraction is not None:
                kwargs["recurrent_workload"] = _const_week(f.workload_fraction, u.concurrent)
            device_needs = [RecurrentEdgeWorkload.from_defaults(f"{f.name} workload", **kwargs)]
        else:
            kwargs = {"edge_device": device}
            if f.cpu_cores_avg is not None:
                kwargs["recurrent_compute_needed"] = _const_week(f.cpu_cores_avg, u.cpu_core)
            if f.ram_gb_avg is not None:
                kwargs["recurrent_ram_needed"] = _const_week(f.ram_gb_avg, u.GB_ram)
            if f.storage_gb_per_week is not None:
                kwargs["recurrent_storage_needed"] = _const_week(f.storage_gb_per_week / 168, u.GB_stored)
            device_needs = [RecurrentEdgeProcess.from_defaults(f"{f.name} process", **kwargs)]
        server_needs = [
            RecurrentServerNeed(
                f"{f.name}: {call.job}", edge_device=device,
                recurrent_volume_per_edge_device=_const_week(call.times_per_hour, u.occurrence),
                jobs=[_lookup(jobs, call.job, "job")])
            for call in f.server_calls]
        edge_functions[f.name] = EdgeFunction(f.name, device_needs, server_needs)

    edge_patterns = []
    for dep in spec.edge_deployments:
        bundle = EdgeUsageJourney(
            f"{dep.name} functions", [_lookup(edge_functions, name, "edge_function") for name in dep.functions])
        kwargs = {}
        _opt(kwargs, "usage_span", dep.usage_span_years, u.year)
        edge_patterns.append(EdgeUsagePattern(
            dep.name, [bundle], shared.network(dep.network), shared.country(dep.country),
            _volume_timeseries(dep.new_devices), **kwargs))

    return System(spec.system_name, usage_patterns, edge_patterns), resolutions


def json_schema() -> dict:
    return ModelSpec.model_json_schema()
