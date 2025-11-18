from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb


class EdgeApplianceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for EdgeAppliance hardware (e.g., routers, IoT gateways with workload-based power)."""
    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        return ModelingObjectWeb.add_new_object_and_return_html_response(request, model_web, object_type)

    @property
    def calculated_attributes(self):
        return ["instances_fabrication_footprint_per_usage_pattern", "instances_fabrication_footprint"]

    @property
    def calculated_attributes_values(self):
        appliance_calculated_attributes_but_fabrication = [
            elt for elt in self.appliance_component.calculated_attributes_values
            if elt.attr_name_in_mod_obj_container not in self.calculated_attributes]
        return appliance_calculated_attributes_but_fabrication + super().calculated_attributes_values
