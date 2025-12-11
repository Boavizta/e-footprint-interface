"""Form context builder for generating form structures.

This module provides the FormContextBuilder class which generates form contexts
for object creation and edition. It dispatches to strategy classes based on
the form_creation_config declared in domain entities.

The key principle is:
- Domain entities declare WHAT (configuration/data)
- Strategy classes decide HOW (generates actual form structures)
"""
from typing import TYPE_CHECKING, Type

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
        return strategy.build_creation_context(
            web_class, object_type, config, efootprint_id_of_parent_to_link_to
        )

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
        return strategy.build_edition_context(obj_to_edit, config)
