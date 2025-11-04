from efootprint.constants.sources import Sources

from model_builder.efootprint_extensions.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant
from model_builder.web_core.usage.edge.recurrent_edge_device_need_web import RecurrentEdgeDeviceNeedBaseWeb


class RecurrentEdgeProcessWeb(RecurrentEdgeDeviceNeedBaseWeb):
    default_values = {
        "recurrent_compute_needed": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "cpu_core"}, source=Sources.HYPOTHESIS
        ),
        "recurrent_ram_needed": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "GB_ram"}, source=Sources.HYPOTHESIS
        ),
        "recurrent_storage_needed": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 0, "constant_unit": "GB"}, source=Sources.HYPOTHESIS
        )
    }
