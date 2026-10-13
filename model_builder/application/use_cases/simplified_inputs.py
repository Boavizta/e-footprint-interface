"""Save simplified-input settings and atomic value edits against the caller's field catalog."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from model_builder.domain.exceptions import InputValidationError

from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.object_factory import apply_input_edits
from model_builder.domain.services.simplified_inputs import (
    FieldAddress, FieldCatalog, complete_selection, normalize_definition, validate_definition,
)


@dataclass
class SimplifiedInputsOutput:
    notices: list[str]
    changed_fields: set[FieldAddress] | None = None


@dataclass
class EditSimplifiedInput:
    address: FieldAddress
    parsed_value: Any  # Normalized explainable data, reference ID, or reference-ID list.


class EditSimplifiedInputUseCase:
    def __init__(self, model_web: ModelWeb, catalog: FieldCatalog):
        self.model_web = model_web
        self.catalog = catalog

    def execute(self, command: EditSimplifiedInput) -> SimplifiedInputsOutput:
        address = command.address
        complete_selection(self.catalog, {address})
        definition = normalize_definition(self.model_web.repository.interface_config.get("simplified_inputs"))
        setting = definition["fields"].get(address.object_id, {}).get(address.attribute, {})
        if not setting.get("included"):
            raise InputValidationError(f"Input {address.object_id}.{address.attribute} is not selected.")

        owner = self.model_web.get_web_object_from_efootprint_id(address.object_id)
        result = apply_input_edits({address.attribute: command.parsed_value}, owner)
        self.model_web.persist_to_cache()
        notices = [f"{change.input[0].name}: {change.accepted_value.label} changed to {change.accepted_value}."
                   for change in result.automatic_changes]
        affected = {FieldAddress(owner.id, attribute) for owner, attribute in result.affected_inputs}
        return SimplifiedInputsOutput(notices=notices, changed_fields=affected)


class UpdateSimplifiedDefinitionUseCase:
    def __init__(self, repository: ISystemRepository, catalog: FieldCatalog):
        self.repository = repository
        self.catalog = catalog

    def execute(self, settings: dict, *, replace: bool = False, persist: bool = True) -> SimplifiedInputsOutput:
        if not isinstance(settings, dict) or settings.keys() - {"title", "guidance", "fields"}:
            raise InputValidationError("Simplified inputs may contain only title, guidance, and fields.")
        current_config = deepcopy(self.repository.interface_config)
        previous = normalize_definition(current_config.get("simplified_inputs"))
        candidate = normalize_definition(settings) if replace else deepcopy(previous)
        explicitly_excluded = set()
        if not replace:
            for name in ("title", "guidance"):
                if name in settings:
                    candidate[name] = settings[name]
            fields = settings.get("fields", {})
            if not isinstance(fields, dict):
                raise InputValidationError("Simplified inputs fields must map owner IDs to inputs.")
            for object_id, attributes in fields.items():
                if not isinstance(object_id, str) or not isinstance(attributes, dict):
                    raise InputValidationError("Simplified inputs fields must map owner IDs to inputs.")
                for attribute, patch in attributes.items():
                    if not isinstance(attribute, str) or not isinstance(patch, dict):
                        raise InputValidationError("Each input patch must be an object.")
                    setting = candidate["fields"].setdefault(object_id, {}).setdefault(
                        attribute, {"included": False, "help": ""})
                    setting.update(patch)
                    if patch.get("included") is False:
                        explicitly_excluded.add(FieldAddress(object_id, attribute))

        # Check shape and eligibility before completing an incomplete selection.
        unselected = deepcopy(candidate)
        if isinstance(unselected["fields"], dict):
            for attributes in unselected["fields"].values():
                if isinstance(attributes, dict):
                    for setting in attributes.values():
                        if isinstance(setting, dict) and type(setting.get("included")) is bool:
                            setting["included"] = False
        validate_definition(self.catalog, unselected)
        selected = {FieldAddress(owner, attribute) for owner, attributes in candidate["fields"].items()
                    for attribute, setting in attributes.items() if setting["included"]}
        completed = complete_selection(self.catalog, selected)
        if completed & explicitly_excluded:
            raise InputValidationError("A required input cannot be excluded while its controlling input is included.")
        for address in completed:
            candidate["fields"].setdefault(address.object_id, {}).setdefault(
                address.attribute, {"included": False, "help": ""})["included"] = True
        candidate = validate_definition(self.catalog, candidate)
        candidate["fields"] = {
            owner: kept for owner, attributes in candidate["fields"].items()
            if (kept := {attribute: setting for attribute, setting in attributes.items()
                         if setting["included"] or setting["help"]})}
        changed = {FieldAddress(owner, attribute)
                   for definition in (previous, candidate) for owner, attributes in definition["fields"].items()
                   for attribute in attributes
                   if (previous["fields"].get(owner, {}).get(attribute)
                       != candidate["fields"].get(owner, {}).get(attribute))}
        self.repository.interface_config = {**current_config, "simplified_inputs": candidate}
        try:
            if persist:
                self.repository.save_interface_config()
        except Exception:
            self.repository.interface_config = current_config
            raise
        return SimplifiedInputsOutput(notices=[], changed_fields=None if replace else changed)


def reconcile_simplified_definition(model_web, catalog_factory, pending=None, created_object=None):
    """Keep settings on surviving owners and complete selection before the model's final save."""
    definition = normalize_definition(model_web.repository.interface_config.get("simplified_inputs"))
    catalog = catalog_factory(model_web)
    definition["fields"] = {owner: settings for owner, settings in definition["fields"].items()
                            if owner in model_web.flat_efootprint_objs_dict}
    for setting in pending or []:
        if not isinstance(setting, dict) or setting.keys() != {"owner", "attribute", "included", "help"}:
            raise InputValidationError("Invalid pending simplified input.")
        owner = created_object
        if setting["owner"] in created_object.nested_input_owner_attributes:
            owner = getattr(created_object, setting["owner"])
        elif setting["owner"] != "object":
            raise InputValidationError("Unknown pending input owner.")
        definition["fields"].setdefault(owner.efootprint_id, {})[setting["attribute"]] = {
            "included": setting["included"], "help": setting["help"]}
    submitted = {FieldAddress(owner, attribute) for owner, fields in definition["fields"].items()
                 for attribute, setting in fields.items() if setting["included"]}
    UpdateSimplifiedDefinitionUseCase(model_web.repository, catalog).execute(definition, replace=True, persist=False)
    return complete_selection(catalog, submitted) - submitted


def persist_structural_change(model_web, catalog_factory, pending=None, created_object=None):
    previous = deepcopy(model_web.repository.interface_config)
    try:
        added = reconcile_simplified_definition(model_web, catalog_factory, pending, created_object)
        model_web.persist_to_cache()
        return added
    except Exception:
        model_web.repository.interface_config = previous
        raise
