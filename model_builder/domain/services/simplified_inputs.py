"""Repository-owned simplified-input definitions and constructor-derived selection rules."""

from copy import deepcopy
from dataclasses import dataclass, replace
from numbers import Number
from types import UnionType
from typing import TypedDict, Union, get_args, get_origin

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.utils.tools import get_init_signature_params

from model_builder.domain.conditional_inputs import resolve_input_path
from model_builder.domain.type_annotation_utils import resolve_optional_annotation


@dataclass(frozen=True)
class FieldAddress:
    object_id: str
    attribute: str


class FieldSetting(TypedDict):
    included: bool
    help: str


class SimplifiedInputsDefinition(TypedDict):
    title: str
    guidance: str
    fields: dict[str, dict[str, FieldSetting]]


@dataclass(frozen=True)
class FieldDescriptor:
    address: FieldAddress
    eligible: bool
    reason: str | None = None
    controller: FieldAddress | None = None


@dataclass
class FieldCatalog:
    fields: dict[FieldAddress, FieldDescriptor]
    dependents: dict[FieldAddress, list[FieldAddress]]


def normalize_definition(definition: dict | None = None) -> SimplifiedInputsDefinition:
    """Supply empty optional sections, copying settings without adding modeling values."""
    if definition is None:
        definition = {}
    return {"title": definition.get("title", ""), "guidance": definition.get("guidance", ""),
            "fields": deepcopy(definition.get("fields", {}))}


def _is_type(annotation, parent):
    return isinstance(annotation, type) and issubclass(annotation, parent)


def _eligibility(owner, attribute, annotation, can_edit_timeseries):
    if isinstance(owner, (Country, Network, Device)):
        return False, "Reference objects are selected through their owning input."

    annotation = resolve_optional_annotation(annotation)
    # An empty optional quantity is still a number input, not a different editor kind.
    non_empty_types = [arg for arg in get_args(annotation) if arg not in (EmptyExplainableObject, type(None))]
    if len(non_empty_types) == 1 and get_origin(annotation) in (Union, UnionType):
        annotation = non_empty_types[0]
    origin = get_origin(annotation)
    if _is_type(origin, ExplainableObjectDict):
        return False, "Weighted object collections are structural inputs."
    if origin is list:
        child_type, = get_args(annotation)
        if _is_type(child_type, (Country, Network, Device)):
            return True, None
        return False, "Object collections are structural inputs."
    if _is_type(annotation, ModelingObject):
        if _is_type(annotation, (Country, Network, Device)):
            return True, None
        return False, "Object relationships are structural inputs."
    if _is_type(annotation, (ExplainableHourlyQuantities, ExplainableRecurrentQuantities)):
        if can_edit_timeseries(annotation, getattr(owner, attribute)):
            return True, None
        return False, "This timeseries has no supported editor."
    if _is_type(annotation, ExplainableQuantity):
        return True, None
    if _is_type(annotation, Number) and not _is_type(annotation, bool):
        return True, None
    if _is_type(annotation, ExplainableObject):
        value = getattr(owner, attribute).value
        if isinstance(value, bool):
            return False, "Boolean inputs are outside the supported input kinds."
        if attribute in owner.list_values or attribute in owner.conditional_list_values:
            return True, None
        if isinstance(value, Number):
            return True, None
    return False, "This input is neither a number, an eligible select, nor an editable timeseries."


def build_catalog(model_web, *, can_edit_timeseries) -> FieldCatalog:
    """Index constructor fields and model-wide conditional links in O(fields + links)."""
    fields = {}
    dependents = {}
    for owner in model_web.flat_efootprint_objs_dict.values():
        for attribute, parameter in get_init_signature_params(owner.efootprint_class).items():
            if attribute == "self":
                continue
            address = FieldAddress(owner.id, attribute)
            eligible, reason = _eligibility(owner, attribute, parameter.annotation, can_edit_timeseries)
            controller = None
            if attribute in owner.conditional_list_values:
                controller_owner, controller_attribute = resolve_input_path(
                    owner, owner.conditional_list_values[attribute]["depends_on"])
                controller = FieldAddress(controller_owner.id, controller_attribute)
                dependents.setdefault(controller, []).append(address)
            fields[address] = FieldDescriptor(address, eligible, reason, controller)

    # Reject controllers whose required companions cannot be exposed, including chained controllers.
    pending = [address for address, field in fields.items() if not field.eligible]
    for address in pending:
        controller = fields[address].controller
        if controller in fields and fields[controller].eligible:
            reason = (f"Required input {address.object_id}.{address.attribute} cannot be included: "
                      f"{fields[address].reason}")
            fields[controller] = replace(fields[controller], eligible=False, reason=reason)
            pending.append(controller)
    return FieldCatalog(fields, dependents)


def complete_selection(catalog: FieldCatalog, selected) -> set[FieldAddress]:
    """Include every required dependent recursively, rejecting unknown or ineligible inputs."""
    completed = set(selected)
    pending = list(completed)
    for address in pending:
        field = catalog.fields.get(address)
        if field is None:
            raise ValueError(f"Unknown input {address.object_id}.{address.attribute}.")
        if not field.eligible:
            raise ValueError(f"Input {address.object_id}.{address.attribute} cannot be included: {field.reason}")
        for dependent in catalog.dependents.get(address, ()):
            if dependent not in completed:
                completed.add(dependent)
                pending.append(dependent)
    return completed


def validate_definition(catalog: FieldCatalog, definition: dict | None) -> SimplifiedInputsDefinition:
    """Validate saved membership/help and reject removal of a required companion."""
    if definition is not None and not isinstance(definition, dict):
        raise ValueError("Simplified inputs must be an object.")
    if definition is not None and definition.keys() - {"title", "guidance", "fields"}:
        raise ValueError("Simplified inputs may contain only title, guidance, and fields.")
    normalized = normalize_definition(definition)
    for name in ("title", "guidance"):
        if not isinstance(normalized[name], str):
            raise ValueError(f"Simplified inputs {name} must be text.")
    if not isinstance(normalized["fields"], dict):
        raise ValueError("Simplified inputs fields must map owner IDs to inputs.")
    selected = set()
    for object_id, settings in normalized["fields"].items():
        if not isinstance(object_id, str) or not isinstance(settings, dict):
            raise ValueError(f"Invalid input owner {object_id!r}.")
        for attribute, setting in settings.items():
            if not isinstance(attribute, str):
                raise ValueError(f"Invalid input attribute on owner {object_id}.")
            address = FieldAddress(object_id, attribute)
            field = catalog.fields.get(address)
            if field is None:
                raise ValueError(f"Unknown input {object_id}.{attribute}.")
            if not field.eligible:
                raise ValueError(f"Input {object_id}.{attribute} cannot be included: {field.reason}")
            if (not isinstance(setting, dict) or type(setting.get("included")) is not bool
                    or not isinstance(setting.get("help"), str) or setting.keys() - {"included", "help"}):
                raise ValueError(f"Input {object_id}.{attribute} requires an included boolean and help text.")
            if setting["included"]:
                selected.add(address)
    required = complete_selection(catalog, selected) - selected
    if required:
        missing = ", ".join(f"{address.object_id}.{address.attribute}" for address in sorted(
            required, key=lambda address: (address.object_id, address.attribute)))
        raise ValueError(f"Required inputs are missing from the selection: {missing}.")
    return normalized
