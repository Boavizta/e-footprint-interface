"""Base class for resource need-like objects (JobWeb, RecurrentEdgeDeviceNeedBaseWeb and their mirrored versions)."""
from abc import abstractmethod

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ResourceNeedBaseWeb(ModelingObjectWeb):
    """Base class for resource need objects that can be mirrored in journey step contexts."""
    @property
    def template_name(self):
        return "resource_need"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for resource need creation forms - link to parent, swap none."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_swap": "none"
        }
