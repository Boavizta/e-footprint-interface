from typing import Tuple, List, Optional

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class EdgeApplianceComponentWeb(ModelingObjectWeb):
    @property
    def list_containers_and_attr_name_in_list_container(self) -> Tuple[List["ModelingObjectWeb"], Optional[str]]:
        edge_appliance_web = self.edge_device
        return [edge_appliance_web], "components"
