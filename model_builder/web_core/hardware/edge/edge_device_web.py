from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb


class EdgeDeviceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for custom EdgeDevice hardware (made of custom components)."""
    attributes_to_skip_in_forms = ["components"]

    @property
    def template_name(self):
        return "edge_device_with_accordion"

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        mutable_post = request.POST.copy()
        request.POST = mutable_post
        request.POST["components"] = ""
        return ModelingObjectWeb.add_new_object_and_return_html_response(request, model_web, object_type)
