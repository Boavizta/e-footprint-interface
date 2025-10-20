from typing import TYPE_CHECKING

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.usage.edge_function_web import EdgeFunctionWeb


class RecurrentEdgeResourceNeedWeb(ModelingObjectWeb):
    """Base web wrapper for RecurrentEdgeResourceNeed and its subclasses (RecurrentEdgeProcess, RecurrentEdgeWorkload)."""

    @property
    def edge_functions(self):
        """Returns web-wrapped edge functions that contain this resource need."""
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return [wrap_efootprint_object(ef, self.model_web) for ef in self._modeling_obj.edge_functions]

    @property
    def edge_usage_journeys(self):
        """Returns web-wrapped edge usage journeys related to this resource need."""
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return [wrap_efootprint_object(euj, self.model_web) for euj in self._modeling_obj.edge_usage_journeys]

    @property
    def edge_device(self):
        """Returns the web-wrapped edge device this resource need is associated with."""
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return wrap_efootprint_object(self._modeling_obj.edge_device, self.model_web)
