"""Base class for form generation strategies."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb
    from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class FormStrategy(ABC):
    """Abstract base class for form generation strategies.

    Each strategy handles a specific pattern of form generation for object
    creation and edition. Strategies receive configuration from domain entities
    and generate presentation-ready form structures.
    """

    def __init__(self, model_web: "ModelWeb"):
        """Initialize strategy with ModelWeb instance.

        Args:
            model_web: The ModelWeb instance for accessing system data
        """
        self.model_web = model_web

    @abstractmethod
    def build_creation_context(
        self,
        web_class: Type["ModelingObjectWeb"],
        object_type: str,
        config: dict,
        efootprint_id_of_parent_to_link_to: str = None
    ) -> dict:
        """Build form context for object creation.

        Args:
            web_class: The web wrapper class (e.g., ServerWeb, JobWeb)
            object_type: The efootprint class name string
            config: The form_creation_config from the web class
            efootprint_id_of_parent_to_link_to: Optional parent object ID

        Returns:
            Dictionary with form context data ready for template rendering
        """
        pass

    def build_edition_context(
        self,
        obj_to_edit: "ModelingObjectWeb",
        config: dict = None
    ) -> dict:
        """Build form context for object edition.

        Default implementation raises NotImplementedError. Override in subclasses
        that support edition.

        Args:
            obj_to_edit: The web wrapper of the object to edit
            config: Optional form_edition_config from the web class

        Returns:
            Dictionary with form context data ready for template rendering
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support edition context")
