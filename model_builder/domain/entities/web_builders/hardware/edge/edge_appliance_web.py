from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb


class EdgeApplianceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for EdgeAppliance hardware (e.g., routers, IoT gateways with workload-based power)."""

    @property
    def calculated_attributes_without_validations(self):
        return ["instances_manufacturing_footprint_per_usage_pattern", "instances_manufacturing_footprint"]

    @property
    def calculated_attributes_values(self):
        appliance_calculated_attributes_but_manufacturing = [
            elt for elt in self.appliance_component.calculated_attributes_values
            if elt.attr_name_in_mod_obj_container not in self.calculated_attributes_without_validations]
        return appliance_calculated_attributes_but_manufacturing + super().calculated_attributes_values
