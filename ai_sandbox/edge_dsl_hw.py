"""Variant of edge_dsl.py where the AI may state an edge device's idle power, base RAM and base storage.

Experiment only (ai-bootstrap-edge plan, #edge-device-sizing): each stated value replaces the builder's derivation
of edge_dsl.build_edge_device; an unstated one falls back to it. Everything else is edge_dsl's.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, ValidationError

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney

from model_builder.application.ai_bootstrap.catalogs import Resolution
from model_builder.application.ai_bootstrap.dsl import (
    _Comments, _Shared, _label, _lookup, build_genai_api, build_job, build_journey, build_server, build_usage_pattern,
    parse_json)
from model_builder.application.ai_bootstrap.service import GeneratedModel

from . import edge_dsl
from .edge_dsl import (
    EdgeDeviceSpec, WebEdgeSpec, _deployment_spans, _set, _storage_buffers, build_edge_deployment, build_edge_function,
    build_edge_groups)

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt_web_edge_hw.md"


class EdgeDeviceSpecHW(EdgeDeviceSpec):
    idle_power_w: Optional[float] = None
    base_ram_gb: Optional[float] = None
    base_storage_gb: Optional[float] = None


class WebEdgeSpecHW(WebEdgeSpec):
    edge_devices: list[EdgeDeviceSpecHW] = Field(default_factory=list)


def system_prompt() -> str:
    return PROMPT_PATH.read_text()


def validate_tolerating_extras(data: dict) -> tuple[WebEdgeSpecHW, list[str]]:
    try:
        return WebEdgeSpecHW.model_validate(data), []
    except ValidationError as error:
        extras = [e["loc"] for e in error.errors() if e["type"] == "extra_forbidden"]
        if not extras or len(extras) != len(error.errors()):
            raise
    for loc in extras:
        node = data
        for key in loc[:-1]:
            node = node[key]
        del node[loc[-1]]
    return WebEdgeSpecHW.model_validate(data), [".".join(str(k) for k in loc) for loc in extras]


def build_edge_device(d: EdgeDeviceSpecHW, buffer_gb: float, resolutions: list[Resolution]):
    c = _Comments(d, resolutions)
    name = _label(d.name, resolutions)
    kwargs = {}
    _set(kwargs, "power", d.power_w, u.W, c.take("power_w"))
    _set(kwargs, "carbon_footprint_manufacturing", d.embodied_kg, u.kg, c.take("embodied_kg"))
    _set(kwargs, "lifespan", d.lifespan_years, u.year, c.take("lifespan_years"))
    cls = EdgeAppliance if d.kind == "appliance" else EdgeComputer
    if d.idle_power_w is not None:
        kwargs["idle_power"] = SourceValue(d.idle_power_w * u.W, comment=c.take("idle_power_w"))
    elif d.power_w is not None:  # variant A's derivation
        kwargs["idle_power"] = SourceValue(min(cls.default_values["idle_power"].value.to(u.W).magnitude, d.power_w) * u.W)
    if d.kind == "computer":
        base_gb = (d.base_storage_gb or 0) + buffer_gb if d.base_storage_gb is not None else buffer_gb
        storage_kwargs = {"base_storage_need": SourceValue(base_gb * u.GB_stored, comment=c.take("base_storage_gb"))}
        _set(storage_kwargs, "storage_capacity_per_unit", d.storage_gb, u.GB_stored, c.take("storage_gb"))
        kwargs["storage"] = EdgeStorage.from_defaults(f"{name} storage", **storage_kwargs)
        _set(kwargs, "compute", d.cores, u.cpu_core, c.take("cores"))
        _set(kwargs, "ram", d.ram_gb, u.GB_ram, c.take("ram_gb"))
        if d.base_ram_gb is not None:
            kwargs["base_ram_consumption"] = SourceValue(d.base_ram_gb * u.GB_ram, comment=c.take("base_ram_gb"))
        elif d.ram_gb is not None:  # variant A's derivation
            kwargs["base_ram_consumption"] = SourceValue(min(1, d.ram_gb / 4) * u.GB_ram)
    device = cls.from_defaults(name, **kwargs)
    c.close()
    return device


def build_system(spec: WebEdgeSpecHW) -> tuple[System, list[Resolution]]:
    """edge_dsl.build_system with this module's device builder."""
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


device_totals = edge_dsl.device_totals
