from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.domain.object_factory import make_form_data_mutable


class EdgeDeviceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for custom EdgeDevice hardware (made of custom components)."""
    attributes_to_skip_in_forms = ["components"]

    @property
    def template_name(self):
        return "edge_device_with_accordion"

    @classmethod
    def prepare_creation_input(cls, form_data):
        """Add empty components list for edge device creation."""
        form_data = make_form_data_mutable(form_data)
        form_data["components"] = ""
        return form_data
