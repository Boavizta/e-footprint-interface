"""Base class for resource need-like objects (JobWeb, RecurrentEdgeDeviceNeedBaseWeb and their mirrored versions)."""
from abc import abstractmethod
from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

from model_builder.web_abstract_modeling_classes.modeling_object_that_can_be_mirrored import ModelingObjectWebThatCanBeMirrored

if TYPE_CHECKING:
    from model_builder.web_core.usage.journey_step_base_web import MirroredJourneyStepBaseWeb


class ResourceNeedBaseWeb(ModelingObjectWebThatCanBeMirrored):
    """Base class for resource need objects that can be mirrored in journey step contexts."""

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for resource need creation forms - link to parent, swap none."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_swap": "none"
        }


class MirroredResourceNeedBaseWeb(ResourceNeedBaseWeb):
    """Base class for mirrored resource need objects displayed within a specific journey step context."""

    def __init__(self, modeling_obj: ModelingObject, journey_step: "MirroredJourneyStepBaseWeb"):
        super().__init__(modeling_obj, journey_step.model_web)
        self.journey_step = journey_step

    @property
    def settable_attributes(self):
        return super().settable_attributes + ["journey_step"]

    @property
    def template_name(self):
        return "resource_need"

    @property
    def class_title_style(self):
        return "h8"

    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self.efootprint_id}_in_{self.journey_step.web_id}"

    @property
    def accordion_parent(self):
        return self.journey_step

    @property
    @abstractmethod
    def links_to(self) -> str:
        """Returns the web_id(s) of the hardware this resource need links to."""
        pass
