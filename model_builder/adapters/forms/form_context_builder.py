"""Form context builder for generating form structures.

This module provides the FormContextBuilder class which generates form contexts
for object creation and edition. It dispatches to strategy classes based on
the form_creation_config declared in domain entities.

The key principle is:
- Domain entities declare WHAT (configuration/data)
- Strategy classes decide HOW (generates actual form structures)
"""
import json
from typing import TYPE_CHECKING, Type

from model_builder.adapters.ui_config.field_ui_config_provider import FieldUIConfigProvider
from model_builder.adapters.forms.strategies import (
    SimpleFormStrategy,
    WithStorageFormStrategy,
    ChildOfParentFormStrategy,
    ParentSelectionFormStrategy,
    NestedParentSelectionFormStrategy,
)

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


# Registry mapping strategy names to strategy classes
CREATION_STRATEGIES = {
    'simple': SimpleFormStrategy,
    'with_storage': WithStorageFormStrategy,
    'child_of_parent': ChildOfParentFormStrategy,
    'parent_selection': ParentSelectionFormStrategy,
    'nested_parent_selection': NestedParentSelectionFormStrategy,
}

EDITION_STRATEGIES = {
    'simple': SimpleFormStrategy,
    'with_storage': WithStorageFormStrategy,
}


class FormContextBuilder:
    """Builds form contexts for domain objects.

    This class reads declarative configuration from domain entities and dispatches
    to the appropriate strategy class. Domain entities should not call form generation
    functions directly - they provide configuration, strategies do the generation.

    Supported strategies:
    - "simple": Basic single-class creation form (default)
    - "with_storage": Object + storage dual form (for Server, EdgeDevice, EdgeComputer)
    - "child_of_parent": Child object with parent already known (for Service, EdgeComponent)
    - "parent_selection": Complex parent selection with cascading dynamic selects (for Job, RecurrentEdgeDeviceNeed)
    - "nested_parent_selection": Child with parent already known, but needs internal selection (RecurrentEdgeComponentNeed)
    """

    def __init__(self, model_web: "ModelWeb"):
        """Initialize with a ModelWeb instance.

        Args:
            model_web: The ModelWeb instance for accessing system data
        """
        self.model_web = model_web

    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build form context for object creation.

        Reads the form_creation_config from the web class and dispatches
        to the appropriate strategy.

        Args:
            web_class: The web wrapper class (e.g., ServerWeb, JobWeb)
            object_type: The efootprint class name string
            efootprint_id_of_parent_to_link_to: Optional parent object ID

        Returns:
            Dictionary with form context data ready for template rendering
        """
        config = getattr(web_class, 'form_creation_config', None)
        strategy_name = config.get('strategy', 'simple') if config else 'simple'

        strategy_class = CREATION_STRATEGIES.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown form creation strategy: {strategy_name}")

        strategy = strategy_class(self.model_web)
        context = strategy.build_creation_context(
            web_class, object_type, config, efootprint_id_of_parent_to_link_to
        )
        if web_class and config and config.get("dict_count_fields"):
            prerequisites = web_class.get_creation_prerequisites(self.model_web)
            context["dict_count_fields"] = self._build_dict_count_fields(object_type, config, prerequisites)
        return context

    def build_edition_context(self, obj_to_edit: "ModelingObjectWeb") -> dict:
        """Build form context for object edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit

        Returns:
            Dictionary with form context data ready for template rendering
        """
        web_class = type(obj_to_edit)
        config = getattr(web_class, 'form_edition_config', None)
        strategy_name = config.get('strategy', 'simple') if config else 'simple'

        strategy_class = EDITION_STRATEGIES.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown form edition strategy: {strategy_name}")

        strategy = strategy_class(self.model_web)
        context = strategy.build_edition_context(obj_to_edit, config)
        context.update(obj_to_edit.get_edition_context_overrides())
        if context.get("dict_count_fields"):
            context["dict_count_fields"] = self._hydrate_dict_count_fields(
                context["dict_count_fields"],
                obj_to_edit.class_as_simple_str,
            )
        if context.get("group_memberships"):
            context["group_memberships"] = self._hydrate_group_memberships(context["group_memberships"])
        return context

    @staticmethod
    def _build_dict_count_fields(object_type: str, config: dict, prerequisites: dict) -> list[dict]:
        fields = []
        for attr_name, prerequisite_key in config["dict_count_fields"].items():
            available_objects = prerequisites.get(prerequisite_key, [])
            options = FormContextBuilder._build_select_options(available_objects)
            fields.append({
                "web_id": f"{object_type}_{attr_name}",
                "attr_name": attr_name,
                "label": FieldUIConfigProvider.get_label(attr_name),
                "tooltip": FieldUIConfigProvider.get_tooltip(attr_name),
                "input_type": "dict_count",
                "options": options,
                "options_json": json.dumps(options),
                "selected_json": json.dumps({}),
            })
        return fields

    @staticmethod
    def _hydrate_dict_count_fields(fields: list[dict], object_type: str) -> list[dict]:
        hydrated_fields = []
        for field in fields:
            hydrated_field = dict(field)
            attr_name = hydrated_field["attr_name"]
            hydrated_field.setdefault("web_id", f"{object_type}_{attr_name}")
            if "available_objects" in hydrated_field:
                hydrated_field["options"] = FormContextBuilder._build_select_options(
                    hydrated_field.pop("available_objects")
                )
            selected_counts = hydrated_field.pop("selected_counts", None)
            if selected_counts is not None:
                hydrated_field["selected_json"] = json.dumps({
                    key_id: FormContextBuilder._normalize_count_value(count)
                    for key_id, count in selected_counts.items()
                })
            if "options" in hydrated_field and "options_json" not in hydrated_field:
                hydrated_field["options_json"] = json.dumps(hydrated_field["options"])
            hydrated_field.setdefault("label", FieldUIConfigProvider.get_label(attr_name))
            hydrated_field.setdefault("tooltip", FieldUIConfigProvider.get_tooltip(attr_name))
            hydrated_field.setdefault("input_type", "dict_count")
            hydrated_fields.append(hydrated_field)
        return hydrated_fields

    @staticmethod
    def _hydrate_group_memberships(group_memberships: list[dict]) -> list[dict]:
        return [
            {
                **membership,
                "count": FormContextBuilder._normalize_count_value(membership["count"]),
            }
            for membership in group_memberships
        ]

    @staticmethod
    def _build_select_options(objects) -> list[dict]:
        return sorted(
            [{"value": obj.efootprint_id, "label": obj.name} for obj in objects],
            key=lambda option: option["label"].lower(),
        )

    @staticmethod
    def _normalize_count_value(count) -> int | float:
        return int(count) if float(count).is_integer() else count
