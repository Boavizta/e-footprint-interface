from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.usage.edge.recurrent_edge_device_need_base_web import RecurrentEdgeDeviceNeedBaseWeb


class RecurrentEdgeDeviceNeedWeb(RecurrentEdgeDeviceNeedBaseWeb):
    attributes_to_skip_in_forms = ["edge_device", "recurrent_edge_component_needs"]

    @property
    def template_name(self):
        return "resource_need_with_accordion"

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        mutable_post = request.POST.copy()
        request.POST = mutable_post
        request.POST["recurrent_edge_component_needs"] = ""
        return ModelingObjectWeb.add_new_object_and_return_html_response(request, model_web, object_type)
