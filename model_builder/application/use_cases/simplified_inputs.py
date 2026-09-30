"""Save repository-owned simplified-input settings against the caller's field catalog."""
from copy import deepcopy
from dataclasses import dataclass

from model_builder.domain.interfaces import ISystemRepository
from model_builder.domain.services.simplified_inputs import (
    FieldAddress, FieldCatalog, complete_selection, normalize_definition, validate_definition,
)


@dataclass
class SimplifiedInputsOutput:
    notices: list[str]
    changed_fields: set[FieldAddress] | None = None


class UpdateSimplifiedDefinitionUseCase:
    def __init__(self, repository: ISystemRepository, catalog: FieldCatalog):
        self.repository = repository
        self.catalog = catalog

    def execute(self, settings: dict, *, replace: bool = False) -> SimplifiedInputsOutput:
        if not isinstance(settings, dict) or settings.keys() - {"title", "guidance", "fields"}:
            raise ValueError("Simplified inputs may contain only title, guidance, and fields.")
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
                raise ValueError("Simplified inputs fields must map owner IDs to inputs.")
            for object_id, attributes in fields.items():
                if not isinstance(object_id, str) or not isinstance(attributes, dict):
                    raise ValueError("Simplified inputs fields must map owner IDs to inputs.")
                for attribute, patch in attributes.items():
                    if not isinstance(attribute, str) or not isinstance(patch, dict):
                        raise ValueError("Each input patch must be an object.")
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
            raise ValueError("A required input cannot be excluded while its controlling input is included.")
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
            self.repository.save_interface_config()
        except Exception:
            self.repository.interface_config = current_config
            raise
        return SimplifiedInputsOutput(notices=[], changed_fields=None if replace else changed)
