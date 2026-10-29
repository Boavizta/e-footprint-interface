"""Reading an interface model back into the DSL vocabulary of dsl.py, and applying an edit answer to it.

The read-back is lossy on purpose: what the DSL cannot say (plain servers' sizing, other job kinds, step weights
within a journey, extra journeys of a pattern...) is omitted, so the assistant cannot see or change it.
`apply_edits` mutates the hydrated library model in place through the dsl.py builders and field tables; the
library validates every assignment and nothing is persisted here.
"""
from __future__ import annotations

from collections import Counter

from efootprint.abstract_modeling_classes.explainable_object_dict import to_weighted_explainable_object_dict
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.system import System
from efootprint.core.usage.job import GPUJob, Job

from model_builder.adapters.presenters.simplified_inputs import input_catalog
from model_builder.application.use_cases import DeleteObjectInput, DeleteObjectUseCase
from model_builder.domain.entities.web_core.model_web import ModelWeb

from catalogs import resolve_cloud_instance, resolve_genai
from dsl import (
    JOB_FIELDS, SERVER_FIELDS, SERVER_JOB_FIELDS, STEP_FIELDS, STORAGE_FIELDS, GenAIApiSpec, JobSpec, JourneySpec,
    ServerSpec, StepSpec, UsagePatternSpec, VolumeSpec, _Shared, _volume_timeseries, build_genai_api, build_job,
    build_journey, build_server, build_step, build_usage_pattern)

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
        entry[field] = _number(value.value.to(unit).magnitude)  # ExplainableQuantity.to would convert the model
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


# --- Applying an answer --------------------------------------------------------------------------

SECTIONS = {"servers": ServerSpec, "genai_apis": GenAIApiSpec, "jobs": JobSpec, "journeys": JourneySpec,
            "usage_patterns": UsagePatternSpec}
KINDS = {"servers": "server", "genai_apis": "GenAI API", "jobs": "job", "journeys": "journey",
         "usage_patterns": "usage pattern", "steps": "step"}
NOT_SUPPORTED = "not supported by the assistant in this experiment; change it by hand"
SIZING_FIELDS = ("cores", "ram_gb", "cloud_provider", "instance_type")
HORIZON_KEYS = ("start_date", "modeling_duration_value", "modeling_duration_unit")


def apply_edits(answer: dict, model_web: ModelWeb) -> list[str]:
    """Applies the `changed` and `removed` sections of an edit answer to the live model; returns one line per change.

    Objects are matched by name within their section; a known name sets the listed fields, an unknown one is a
    complete new object. Steps and jobs a re-list leaves out are deleted once nothing uses them, as the form
    path's cascade does. Removals come last so a job re-listed and removed in one answer ends up removed. Any
    problem raises before persistence, leaving the session's model as it was.
    """
    if not isinstance(answer, dict):
        raise ValueError("The answer must be a JSON object")
    changed, removed = answer.get("changed") or {}, answer.get("removed") or {}
    for section in set(changed) | set(removed):
        if section not in SECTIONS:
            raise ValueError(f"Unknown section '{section}' (known: {sorted(SECTIONS)})")
    edits = _Edits(model_web)
    for section in SECTIONS:  # dependency order: servers and APIs before jobs, jobs before steps, journeys before patterns
        for entry in changed.get(section) or []:
            edits.change(section, entry)
    for section, obj in edits.dropped:  # after every re-list, so a job moved to another step survives
        if not obj.modeling_obj_containers:
            edits.remove(section, obj)
    for section in reversed(SECTIONS):  # referrers first: a pattern before its journey, a job before its server
        for name in removed.get(section) or []:
            edits.remove(section, edits.lookup(section, name))
    return edits.lines


class _Edits:
    """One answer applied to one hydrated model: the name lookups, the builders' inputs and the reported lines."""

    def __init__(self, model_web: ModelWeb):
        self.model_web = model_web
        self.system = model_web.system.modeling_obj
        self.objects = library_objects(self.system)
        self.lines: list[str] = []
        self.dropped: list[tuple[str, object]] = []  # steps and jobs a re-list left out, deleted if then unused
        self.removed_ids: set[str] = set()
        self.resolutions: list = []  # catalog resolutions of the builders, not shown in this experiment
        self.delete_use_case = DeleteObjectUseCase(model_web, input_catalog)

    # --- lookups ---

    def find(self, section: str, name: str, candidates: list = None):
        matches = [obj for obj in (self.objects[section] if candidates is None else candidates) if obj.name == name]
        if len(matches) > 1:
            raise ValueError(f"Two {KINDS[section]}s are named '{name}'; rename one by hand first")
        return matches[0] if matches else None

    def lookup(self, section: str, name: str, candidates: list = None):
        obj = self.find(section, name, candidates)
        if obj is None:
            raise ValueError(f"Unknown {KINDS[section]} '{name}'")
        return obj

    def by_name(self, section: str) -> dict:
        return {obj.name: obj for obj in self.objects[section]}

    # --- changed entries ---

    def change(self, section: str, entry):
        fields = _fields(entry, SECTIONS[section], section)
        obj = self.find(section, entry["name"])
        if obj is None:
            self.add(section, SECTIONS[section].model_validate(entry))
        else:
            getattr(self, f"_set_{section}")(obj, entry, fields)
            if fields:
                raise ValueError(f"Changing {obj.name}.{', '.join(fields)} is {NOT_SUPPORTED}")

    def add(self, section: str, spec):
        if section == "servers":
            obj = build_server(spec, self.resolutions)
        elif section == "genai_apis":
            obj = build_genai_api(spec, self.resolutions)
        elif section == "jobs":
            obj = build_job(spec, self.by_name("servers"), self.by_name("genai_apis"), self.resolutions)
        elif section == "journeys":
            obj = build_journey(spec, self.by_name("jobs"), self.resolutions)
        else:
            obj = build_usage_pattern(spec, self.by_name("journeys"), self._shared(), self.resolutions)
            self.system.usage_patterns.append(obj)
        self.model_web.add_new_efootprint_object_to_system(obj)
        self.objects[section].append(obj)
        self.lines.append(f"added {KINDS[section]} {obj.name}{_added_detail(section, obj)}")

    def _shared(self) -> _Shared:
        """The model's existing devices, networks and countries, so a new pattern reuses them."""
        patterns = self.objects["usage_patterns"]
        read = [_usage_pattern(p) for p in patterns]
        return _Shared(
            self.resolutions,
            devices={entry["device"]: p.devices[0] for p, entry in zip(patterns, read) if p.devices},
            networks={entry["network"]: p.network for p, entry in zip(patterns, read)},
            countries={entry["country"]: p.country for p, entry in zip(patterns, read)})

    def _set_servers(self, server, entry: dict, fields: dict):
        _refuse_unless_unchanged(server, fields, _server(server), ("kind",))
        if "gpus" in fields and not isinstance(server, GPUServer):
            raise ValueError(f"{server.name} is not a GPU server; gpus is {NOT_SUPPORTED}")
        self._set_fields(server, entry, fields, SERVER_FIELDS)
        self._set_fields(server.storage, entry, fields, STORAGE_FIELDS, owner_name=server.name)
        if not any(field in fields for field in SIZING_FIELDS):
            return
        if not isinstance(server, BoaviztaCloudServer):
            raise ValueError(f"{server.name} is not a cloud instance; its sizing is {NOT_SUPPORTED}")
        provider = fields.pop("cloud_provider", server.provider.value)
        instance_type = fields.pop("instance_type", None)
        cores, ram_gb = fields.pop("cores", None), fields.pop("ram_gb", None)
        if instance_type is None and cores is None and ram_gb is None:
            instance_type = server.instance_type.value  # a provider change alone: keep the instance, snapped to its catalog
        provider, instance_type = resolve_cloud_instance(provider, instance_type, cores, ram_gb, self.resolutions)
        if (provider, instance_type) == (server.provider.value, server.instance_type.value):
            return
        comments = entry.get("comments", {})
        sizing = " ".join(filter(None, (comments.get(f) for f in ("cores", "ram_gb", "instance_type")))) or None
        ModelingUpdate([[server.provider, SourceObject(provider, comment=comments.get("cloud_provider"))],
                        [server.instance_type, SourceObject(instance_type, comment=sizing)]])
        self.lines.append(f"set {server.name} to {provider} {instance_type}")

    def _set_genai_apis(self, api, entry: dict, fields: dict):
        if "provider" not in fields and "model_name" not in fields:
            return
        provider = fields.pop("provider", api.provider.value)
        model_name = fields.pop("model_name", api.model_name.value if provider == api.provider.value else None)
        provider, model_name = resolve_genai(provider, model_name, self.resolutions)
        if (provider, model_name) == (api.provider.value, api.model_name.value):
            return
        comments = entry.get("comments", {})
        ModelingUpdate([[api.provider, SourceObject(provider, comment=comments.get("provider"))],
                        [api.model_name, SourceObject(model_name, comment=comments.get("model_name"))]])
        self.lines.append(f"set {api.name} to {provider}/{model_name}")

    def _set_jobs(self, job, entry: dict, fields: dict):
        current = _job(job)
        if "server" not in current and "genai_api" not in current and fields:
            raise ValueError(f"{job.name} is a job kind the assistant cannot edit; changing it is {NOT_SUPPORTED}")
        _refuse_unless_unchanged(job, fields, current, ("server", "genai_api"))
        if isinstance(job, EcoLogitsGenAIExternalAPIJob):
            allowed = ("output_tokens",)
        else:
            allowed = SERVER_JOB_FIELDS + ("gpus" if isinstance(job, GPUJob) else "cpu_cores",)
        self._set_fields(job, entry, fields, JOB_FIELDS, allowed)

    def _set_journeys(self, journey, entry: dict, fields: dict):
        steps = fields.pop("steps", None)
        if steps is None:
            return
        current_steps = list(journey.uj_steps)
        weights = dict(journey.uj_steps.items())
        new_steps = {}
        for step_entry in steps:
            step_fields = _fields(step_entry, StepSpec, "steps")
            step = self.find("steps", step_entry["name"], current_steps)
            if step is None:
                step = build_step(StepSpec.model_validate(step_entry), self.by_name("jobs"), self.resolutions)
                self.model_web.add_new_efootprint_object_to_system(step)
                self.lines.append(f"added step {step.name} to {journey.name}")
                new_steps[step] = 1
            else:
                self._set_step(step, step_entry, step_fields)
                new_steps[step] = weights[step]  # the DSL cannot say a step's weight: a surviving step keeps its own
        if list(new_steps) != current_steps:
            journey.uj_steps = to_weighted_explainable_object_dict(new_steps, weight_label=journey.weight_labels["uj_steps"])
            self.lines.append(f"set {journey.name}.steps to {', '.join(step.name for step in new_steps)}")
            self.dropped += [("steps", step) for step in current_steps if step not in new_steps]

    def _set_step(self, step, entry: dict, fields: dict):
        self._set_fields(step, entry, fields, STEP_FIELDS)
        job_names = fields.pop("jobs", None)
        if job_names is None:
            return
        jobs = [self.lookup("jobs", name) for name in job_names]
        for job, weight in step.jobs.items():
            if job in jobs and not float(weight.value.magnitude).is_integer():
                raise ValueError(f"{job.name} runs {weight.value.magnitude} times per {step.name}; re-listing it is "
                                 f"{NOT_SUPPORTED}")
        if jobs != [job for job, weight in step.jobs.items() for _ in range(int(weight.value.magnitude))]:
            current_weights = dict(step.jobs.items())
            new_jobs = {job: current_weights[job] if job in current_weights and current_weights[job].value.magnitude == count
                        else count for job, count in Counter(jobs).items()}  # an unchanged count keeps its weight
            self.dropped += [("jobs", job) for job in current_weights if job not in new_jobs]
            step.jobs = to_weighted_explainable_object_dict(new_jobs, weight_label=step.weight_labels["jobs"])
            self.lines.append(f"set {step.name}.jobs to {', '.join(job.name for job in jobs) or 'none'}")
        if fields:
            raise ValueError(f"Changing {step.name}.{', '.join(fields)} is {NOT_SUPPORTED}")

    def _set_usage_patterns(self, pattern, entry: dict, fields: dict):
        current = _usage_pattern(pattern)
        _refuse_unless_unchanged(pattern, fields, current, ("journey", "device", "network", "country"))
        volume, growth = fields.pop("volume", None), fields.pop("growth_pct_per_year", None)
        if volume is None and growth is None:
            return
        comments = entry.get("comments", {})
        volume_comment = comments.get("volume") if volume is not None else pattern.hourly_occurrences.comment
        comment = " ".join(filter(None, (volume_comment, comments.get("growth_pct_per_year")))) or None
        volume_spec = VolumeSpec.model_validate(volume if volume is not None else current["volume"])
        pattern.hourly_occurrences = _volume_timeseries(
            volume_spec, current["growth_pct_per_year"] if growth is None else growth, comment,
            horizon=_horizon(pattern.hourly_occurrences))
        if volume is not None:
            self.lines.append(f"set {pattern.name}.volume to {_number_text(volume_spec.value)} per {volume_spec.per}")
        if growth is not None:
            self.lines.append(f"set {pattern.name}.growth_pct_per_year to {_number_text(growth)}")

    def _set_fields(self, obj, entry: dict, fields: dict, table: dict, allowed=None, owner_name: str = None):
        """The inverse of _read_fields: each listed field of the table becomes a SourceValue carrying its comment."""
        comments = entry.get("comments", {})
        for field in allowed or table:
            if field in fields:
                attr, unit = table[field]
                setattr(obj, attr, SourceValue(fields.pop(field) * unit, comment=comments.get(field)))
                self.lines.append(f"set {owner_name or obj.name}.{field} to {_number_text(entry[field])}")

    # --- removals ---

    def remove(self, section: str, obj):
        if obj.id in self.removed_ids:
            return
        if obj.id in self.model_web.flat_efootprint_objs_dict:  # else already deleted with its journey or step
            check = self.delete_use_case.check_can_delete(obj.id)
            if not check.can_delete:
                raise ValueError(
                    f"Cannot remove {KINDS[section]} {obj.name}: still used by {', '.join(check.blocking_containers)}")
            self.delete_use_case._delete(DeleteObjectInput(obj.id))
        self.removed_ids.add(obj.id)
        self.lines.append(f"removed {KINDS[section]} {obj.name}")


def _fields(entry, spec_class, section: str) -> dict:
    """The fields of a changed entry besides its name and comments, checked against the section's DSL class."""
    if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
        raise ValueError(f"Each entry of '{section}' must be an object with a name")
    unknown = set(entry) - set(spec_class.model_fields)
    if unknown:
        raise ValueError(f"Unknown field '{sorted(unknown)[0]}' on {section} '{entry['name']}'")
    fields = {field: value for field, value in entry.items() if field not in ("name", "comments")}
    for field, value in fields.items():
        if value is None:
            raise ValueError(f"{entry['name']}.{field}: a null value is {NOT_SUPPORTED}")
    return fields


def _refuse_unless_unchanged(obj, fields: dict, current: dict, names: tuple):
    """Fields the DSL only describes (device, server...): accepted when they repeat the model, refused otherwise."""
    for name in names:
        if name in fields:
            if fields[name] != current.get(name, "cpu" if name == "kind" else None):
                raise ValueError(f"Changing {obj.name}.{name} is {NOT_SUPPORTED}")
            fields.pop(name)


def _horizon(occurrences) -> dict:
    """The start date and duration a rebuilt volume series keeps from the current one."""
    if isinstance(occurrences, ExplainableHourlyQuantitiesFromFormInputs):
        return {key: occurrences.form_inputs[key] for key in HORIZON_KEYS}
    return {"start_date": occurrences.start_date.strftime("%Y-%m-%d"),
            "modeling_duration_value": max(1, round(len(occurrences) / HOURS_PER_YEAR)), "modeling_duration_unit": "year"}


def _added_detail(section: str, obj) -> str:
    if section == "jobs":
        return f" on {obj.external_api.name if isinstance(obj, EcoLogitsGenAIExternalAPIJob) else obj.server.name}"
    if section == "journeys":
        return f" with steps {', '.join(step.name for step in obj.uj_steps)}"
    if section == "usage_patterns":
        return f" on {next(iter(obj.usage_journeys)).name}"
    if isinstance(obj, BoaviztaCloudServer):
        return f" ({obj.provider.value} {obj.instance_type.value})"
    if isinstance(obj, EcoLogitsGenAIExternalAPI):
        return f" ({obj.provider.value}/{obj.model_name.value})"
    return ""


def _number_text(value) -> str:
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.4g}"
