from efootprint.constants.sources import Sources

from model_builder.efootprint_extensions.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.usage.edge.recurrent_edge_device_need_base_web import RecurrentEdgeDeviceNeedBaseWeb


class RecurrentEdgeWorkloadWeb(RecurrentEdgeDeviceNeedBaseWeb):
    default_values = {
        "recurrent_workload": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "concurrent"}, source=Sources.HYPOTHESIS
        )
    }

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        return ModelingObjectWeb.add_new_object_and_return_html_response(request, model_web, object_type)
