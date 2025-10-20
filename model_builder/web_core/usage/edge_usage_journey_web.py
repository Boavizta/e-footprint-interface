from typing import TYPE_CHECKING

from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb, \
    ATTRIBUTES_TO_SKIP_IN_FORMS

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeUsageJourneyWeb(ModelingObjectWeb):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def links_to(self):
        linked_edge_device_ids = set()
        for edge_function in self.edge_functions:
            for recurrent_edge_resource_need in edge_function.recurrent_edge_resource_needs:
                linked_edge_device_ids.add(recurrent_edge_resource_need.edge_device.web_id)

        return "|".join(sorted(linked_edge_device_ids))

    @property
    def accordion_children(self):
        return self.edge_functions

    @property
    def class_title_style(self):
        return "h6"
