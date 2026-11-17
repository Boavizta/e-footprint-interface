"""Web + edge extension of the shared bootstrap DSL, for sandbox experiments only.

The web part (servers, GenAI APIs, jobs, journeys, usage patterns) is validated and built by the production
builders of `model_builder.application.ai_bootstrap.dsl`; this module adds the edge sections, builds them with
`from_defaults`, points edge server calls at the jobs the web builder made, and assembles one `System`.
"""
from __future__ import annotations

from typing import Literal, Optional

import numpy as np
from pint import Quantity
from pydantic import Field, ValidationError

from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues, SourceValue
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
    ExplainableRecurrentQuantitiesFromConstant)
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed

from model_builder.application.ai_bootstrap.catalogs import Resolution
from model_builder.application.ai_bootstrap.dsl import (
    ModelSpec, Strict, VolumeSpec, _Comments, _Shared, _label, _lookup, _volume_timeseries, build_genai_api,
    build_job, build_journey, build_server, build_usage_pattern, parse_json)
from model_builder.application.ai_bootstrap.service import GeneratedModel

DEFAULT_SPAN_YEARS = 6


class EdgeDeviceSpec(Strict):
    name: str
    kind: Literal["computer", "appliance"] = "computer"
    cores: Optional[float] = None
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    power_w: Optional[float] = None
    embodied_kg: Optional[float] = None
    lifespan_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)


class EdgeDeviceGroupSpec(Strict):
    name: str
    device_counts: dict[str, float] = Field(default_factory=dict)     # edge device name -> count per group
    sub_group_counts: dict[str, float] = Field(default_factory=dict)  # group name -> count per group
    comments: dict[str, str] = Field(default_factory=dict)            # device or group name -> why that count


class ServerCallSpec(Strict):
    jobs: list[str]
    times_per_hour: float
    comment: Optional[str] = None


class EdgeFunctionSpec(Strict):
    name: str
    device: str
    cpu_cores_avg: Optional[float] = None
    ram_gb_avg: Optional[float] = None
    storage_gb_per_week: Optional[float] = None
    storage_retention_weeks: Optional[float] = None  # rolling buffer: occupied = weekly write x retention
    workload_fraction: Optional[float] = None
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
    existing_units: Optional[float] = None  # installed base, put into service at the start
    usage_span_years: Optional[float] = None
    comments: dict[str, str] = Field(default_factory=dict)


class WebEdgeSpec(ModelSpec):
    edge_devices: list[EdgeDeviceSpec] = Field(default_factory=list)
    edge_device_groups: list[EdgeDeviceGroupSpec] = Field(default_factory=list)
    edge_functions: list[EdgeFunctionSpec] = Field(default_factory=list)
    edge_journeys: list[EdgeJourneySpec] = Field(default_factory=list)
    edge_deployments: list[EdgeDeploymentSpec] = Field(default_factory=list)


def validate_tolerating_extras(data: dict) -> tuple[WebEdgeSpec, list[str]]:
    """The production rule on the extended schema: unknown fields are stripped and reported, anything else fails."""
    try:
        return WebEdgeSpec.model_validate(data), []
    except ValidationError as error:
        extras = [e["loc"] for e in error.errors() if e["type"] == "extra_forbidden"]
        if not extras or len(extras) != len(error.errors()):
            raise
    for loc in extras:
        node = data
        for key in loc[:-1]:
            node = node[key]
        del node[loc[-1]]
    return WebEdgeSpec.model_validate(data), [".".join(str(k) for k in loc) for loc in extras]


# --- Builder -------------------------------------------------------------------------------------

def _weekly(value: float, unit: str, comment: Optional[str] = None):
    return ExplainableRecurrentQuantitiesFromConstant(
        {"constant_value": value, "constant_unit": unit}, source=Sources.USER_DATA, comment=comment)


def _set(kwargs: dict, attr: str, value, unit, comment: Optional[str]):
    if value is not None:
        kwargs[attr] = SourceValue(value * unit, comment=comment)


def _deployment_spans(spec: WebEdgeSpec) -> dict[str, float]:
    devices = {d.name: d for d in spec.edge_devices}
    functions = {f.name: f for f in spec.edge_functions}
    journeys = {j.name: j for j in spec.edge_journeys}
    spans = {}
    for dep in spec.edge_deployments:
        lifespans = [devices[functions[f].device].lifespan_years or DEFAULT_SPAN_YEARS
                     for f in journeys.get(dep.journey, EdgeJourneySpec(name="", functions=[])).functions
                     if f in functions and functions[f].device in devices]
        spans[dep.name] = dep.usage_span_years or min([DEFAULT_SPAN_YEARS] + lifespans)
    return spans


def _storage_buffers(spec: WebEdgeSpec, spans: dict[str, float], resolutions: list[Resolution]) -> dict[str, float]:
    """Retention weeks per edge function that writes storage.

    Without retention the library accumulates writes over the whole usage span, so a 32 GB gateway writing 1 GB a
    week overflows after 32 weeks and compute fails. When accumulation would overflow, a rolling buffer filling 80 %
    of the device storage is fitted instead and recorded as a resolution.
    """
    devices = {d.name: d for d in spec.edge_devices}
    span_of_function = {}
    for dep in spec.edge_deployments:
        for journey in spec.edge_journeys:
            if journey.name == dep.journey:
                for f in journey.functions:
                    span_of_function[f] = max(span_of_function.get(f, 0), spans[dep.name])
    retention = {}
    for f in spec.edge_functions:
        if not f.storage_gb_per_week or f.device not in devices:
            continue
        capacity_gb = devices[f.device].storage_gb or 1000
        span = span_of_function.get(f.name, DEFAULT_SPAN_YEARS)
        if f.storage_retention_weeks is not None:
            retention[f.name] = f.storage_retention_weeks
        elif f.storage_gb_per_week * 52 * span > capacity_gb:
            retention[f.name] = round(0.8 * capacity_gb / f.storage_gb_per_week, 1)
            resolutions.append(Resolution(
                "edge_storage", f"{f.name}: {f.storage_gb_per_week} GB/week over {span} y on {capacity_gb:g} GB",
                f"rolling buffer, {retention[f.name]} weeks retention", "fitted"))
    return retention


def build_edge_device(d: EdgeDeviceSpec, buffer_gb: float, resolutions: list[Resolution]):
    c = _Comments(d, resolutions)
    name = _label(d.name, resolutions)
    kwargs = {}
    _set(kwargs, "power", d.power_w, u.W, c.take("power_w"))
    _set(kwargs, "carbon_footprint_manufacturing", d.embodied_kg, u.kg, c.take("embodied_kg"))
    _set(kwargs, "lifespan", d.lifespan_years, u.year, c.take("lifespan_years"))
    cls = EdgeAppliance if d.kind == "appliance" else EdgeComputer
    if d.power_w is not None:  # the library idle default (5 W) exceeds a small device's whole power
        kwargs["idle_power"] = SourceValue(min(cls.default_values["idle_power"].value.to(u.W).magnitude, d.power_w) * u.W)
    if d.kind == "computer":
        # The library storage default reserves 30 GB of base need, more than a small gateway's flash: start from
        # the fitted rolling buffers only.
        storage_kwargs = {"base_storage_need": SourceValue(buffer_gb * u.GB_stored)}
        _set(storage_kwargs, "storage_capacity_per_unit", d.storage_gb, u.GB_stored, c.take("storage_gb"))
        kwargs["storage"] = EdgeStorage.from_defaults(f"{name} storage", **storage_kwargs)
        _set(kwargs, "compute", d.cores, u.cpu_core, c.take("cores"))
        _set(kwargs, "ram", d.ram_gb, u.GB_ram, c.take("ram_gb"))
        if d.ram_gb is not None:  # the library reserves 1 GB of base RAM, all of a small gateway's: cap at a quarter
            kwargs["base_ram_consumption"] = SourceValue(min(1, d.ram_gb / 4) * u.GB_ram)
    device = cls.from_defaults(name, **kwargs)
    c.close()
    return device


def build_edge_function(f: EdgeFunctionSpec, devices: dict, jobs: dict, retention: Optional[float],
                        resolutions: list[Resolution]) -> EdgeFunction:
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
        if f.storage_gb_per_week:
            comment = " ".join(filter(None, (c.take("storage_gb_per_week"), c.take("storage_retention_weeks")))) or None
            # A rolling buffer sits in the device's base storage need; only unbounded writes accumulate here.
            per_hour = 0 if retention is not None else f.storage_gb_per_week / 168
            kwargs["recurrent_storage_needed"] = _weekly(per_hour, "GB_stored", comment)
        need = RecurrentEdgeProcess.from_defaults(f"{name} process", **kwargs)
    server_needs = [
        RecurrentServerNeed(f"{name}: {', '.join(_label(job, resolutions) for job in call.jobs)}", edge_device=device,
                            recurrent_volume_per_edge_device=_weekly(call.times_per_hour, "occurrence", call.comment),
                            jobs={_lookup(jobs, job, "job"): 1 for job in call.jobs})
        for call in f.server_calls]
    function = EdgeFunction(name, [need], server_needs)
    c.close()
    return function


def build_edge_groups(spec: WebEdgeSpec, devices: dict, resolutions: list[Resolution]) -> dict:
    """Groups are built children first, since a group takes its sub-groups at construction."""
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


def _deployment_starts(dep: EdgeDeploymentSpec, comment: Optional[str]):
    """Deployment starts per hour, with the installed base put into service at noon on the first day.

    Not in the first hour: the library converts local hours to UTC by a circular roll, so a base put at hour 0 east
    of UTC would land in the last hour of the modeling period.
    """
    series = _volume_timeseries(dep.new_units, comment=comment)
    if not dep.existing_units:
        return series
    hourly = np.array(series.value.magnitude, dtype=np.float32)
    hourly[12] += dep.existing_units
    return SourceHourlyValues(Quantity(hourly, series.value.units), start_date=series.start_date,
                              source=Sources.USER_DATA, comment=comment)


def build_edge_deployment(dep: EdgeDeploymentSpec, journeys: dict, span_years: float, shared: _Shared,
                          resolutions: list[Resolution]) -> EdgeUsagePattern:
    c = _Comments(dep, resolutions)
    comment = " ".join(filter(None, (c.take("new_units"), c.take("existing_units")))) or None
    pattern = EdgeUsagePattern(
        _label(dep.name, resolutions), [_lookup(journeys, dep.journey, "edge journey")], shared.network(dep.network),
        shared.country(dep.country), _deployment_starts(dep, comment),
        usage_span=SourceValue(span_years * u.year, comment=c.take("usage_span_years")))
    c.close()
    return pattern


def build_system(spec: WebEdgeSpec) -> tuple[System, list[Resolution]]:
    for section in (spec.servers, spec.genai_apis, spec.jobs, spec.journeys, spec.edge_devices,
                    spec.edge_device_groups, spec.edge_functions, spec.edge_journeys):
        names = [obj.name for obj in section]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate declaration names")
    resolutions: list[Resolution] = []
    shared = _Shared(resolutions)
    servers = {s.name: build_server(s, resolutions) for s in spec.servers}
    apis = {a.name: build_genai_api(a, resolutions) for a in spec.genai_apis}
    jobs = {j.name: build_job(j, servers, apis, resolutions) for j in spec.jobs}
    journeys = {jo.name: build_journey(jo, jobs, resolutions) for jo in spec.journeys}
    usage_patterns = [build_usage_pattern(p, journeys, shared, resolutions) for p in spec.usage_patterns]

    spans = _deployment_spans(spec)
    retention = _storage_buffers(spec, spans, resolutions)
    weekly_write = {f.name: f.storage_gb_per_week for f in spec.edge_functions}
    devices = {d.name: build_edge_device(
        d, sum(weekly_write[f.name] * retention[f.name] for f in spec.edge_functions
               if f.device == d.name and f.name in retention), resolutions) for d in spec.edge_devices}
    build_edge_groups(spec, devices, resolutions)
    functions = {f.name: build_edge_function(f, devices, jobs, retention.get(f.name), resolutions)
                 for f in spec.edge_functions}
    edge_journeys = {j.name: EdgeUsageJourney(_label(j.name, resolutions),
                                              [_lookup(functions, n, "edge function") for n in j.functions])
                     for j in spec.edge_journeys}
    edge_patterns = [build_edge_deployment(dep, edge_journeys, spans[dep.name], shared, resolutions)
                     for dep in spec.edge_deployments]
    return System(_label(spec.system_name, resolutions), usage_patterns, edge_patterns), resolutions


def build_answer(text: str) -> GeneratedModel:
    data, _, error = parse_json(text)
    if data is None:
        raise ValueError("Invalid JSON answer")
    spec, ignored = validate_tolerating_extras(data)
    system, resolutions = build_system(spec)
    return GeneratedModel(system, resolutions, ignored)


def device_totals(system: System) -> dict[str, float]:
    """Devices in service per edge device name at the start: deployments in parallel in the first week x units."""
    totals = {}
    for device in system.edge_devices:
        units = float(device.total_nb_of_units.value.magnitude)
        totals[device.name] = sum(
            units * float(np.max(p.nb_deployments_in_parallel.value.magnitude[:168])) for p in device.edge_usage_patterns)
    return totals

