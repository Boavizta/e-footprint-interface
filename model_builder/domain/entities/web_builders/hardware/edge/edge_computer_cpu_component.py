from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeComputerCPUComponentWeb(ModelingObjectWeb):
    @property
    def list_containers_and_attr_name_in_list_container(self):
        edge_computer_web = self.edge_device
        return [edge_computer_web], "components"

    @property
    def calculated_attributes(self):
        return [elt for elt in self.modeling_obj.calculated_attributes
                if elt not in ["compute", "base_compute_consumption", "lifespan", "power", "idle_power",
                               "instances_fabrication_footprint_per_usage_pattern", "instances_fabrication_footprint"]]
