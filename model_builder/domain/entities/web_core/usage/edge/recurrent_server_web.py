from efootprint.constants.sources import Sources
from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import \
    ExplainableRecurrentQuantitiesFromConstant

from model_builder.domain.entities.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb


class RecurrentServerNeedWeb(ResourceNeedBaseWeb):
    default_values = {
        "recurrent_volume_per_edge_device": ExplainableRecurrentQuantitiesFromConstant(
            {"constant_value": 1, "constant_unit": "occurrence"}, source=Sources.HYPOTHESIS
        )
    }

    form_creation_config = {
        'strategy': 'simple',
    }

    @property
    def template_name(self):
        return "resource_need_with_accordion"

    @classmethod
    def can_create(cls, model_web: "ModelWeb") -> bool:
        return bool(model_web.edge_devices)

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> None:
        """Raise error if no edge devices exist in the model."""
        if not cls.can_create(model_web):
            raise ValueError("Cannot create recurrent server need: no edge devices available.")
