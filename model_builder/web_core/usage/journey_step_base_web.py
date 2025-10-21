"""Base class for journey step-like objects (MirroredUsageJourneyStepWeb, MirroredEdgeFunctionWeb)."""
from abc import abstractmethod
from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_that_can_be_mirrored import ModelingObjectWebThatCanBeMirrored

if TYPE_CHECKING:
    from model_builder.web_core.usage.journey_base_web import JourneyBaseWeb


class JourneyStepBaseWeb(ModelingObjectWebThatCanBeMirrored):
    """Base class for journey step objects that can be mirrored in journey contexts."""

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for journey step creation forms - link to parent, swap none."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_swap": "none"
        }


class MirroredJourneyStepBaseWeb(JourneyStepBaseWeb):
    """Base class for mirrored journey step objects displayed within a specific journey context."""

    def __init__(self, modeling_obj: ModelingObject, journey: "JourneyBaseWeb"):
        super().__init__(modeling_obj, journey.model_web)
        self.journey = journey

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["journey"]

    @property
    def class_title_style(self):
        return "h7"

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.journey.web_id}"

    @property
    def accordion_parent(self):
        return self.journey

    @property
    @abstractmethod
    def child_object_type_str(self) -> str:
        """Type string of child objects (e.g., 'Job', 'RecurrentEdgeResourceNeed')."""
        pass

    @property
    @abstractmethod
    def child_template_name(self) -> str:
        """Template name for child objects (e.g., 'resource_need')."""
        pass

    @property
    @abstractmethod
    def add_child_label(self) -> str:
        """Label for the 'add child' button (e.g., 'Add new job')."""
        pass

    @property
    @abstractmethod
    def children_property_name(self) -> str:
        """Property name for accessing children (e.g., 'jobs', 'recurrent_edge_resource_needs')."""
        pass
