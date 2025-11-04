from efootprint.constants.sources import Sources

from model_builder.efootprint_extensions.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant
from model_builder.web_core.usage.edge.recurrent_edge_device_need_web import RecurrentEdgeDeviceNeedBaseWeb


class RecurrentEdgeWorkloadWeb(RecurrentEdgeDeviceNeedBaseWeb):
    default_values = {
        "recurrent_workload": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "concurrent"}, source=Sources.HYPOTHESIS
        )
    }
