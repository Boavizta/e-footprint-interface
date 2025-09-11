from typing import TYPE_CHECKING

from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb, \
    ATTRIBUTES_TO_SKIP_IN_FORMS
from model_builder.web_core.usage.recurrent_edge_process_web import MirroredRecurrentEdgeProcessFromFormWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeUsageJourneyWeb(ModelingObjectWeb):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def links_to(self):
        return self.edge_device.web_id

    @property
    def accordion_children(self):
        return self.edge_processes

    @property
    def edge_processes(self):
        web_edge_processes = []
        for edge_process in self._modeling_obj.edge_processes:
            web_edge_processes.append(MirroredRecurrentEdgeProcessFromFormWeb(edge_process, self))

        return web_edge_processes

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        edge_devices_that_are_not_already_linked = [edge_device for edge_device in model_web.edge_devices
                                                    if edge_device.edge_usage_journey is None]
        if len(edge_devices_that_are_not_already_linked) == 0:
            raise PermissionError(
                "You need to have at least one edge device not already linked to an edge usage journey to create a "
                "new edge usage journey.")

        efootprint_class_str = "EdgeUsageJourney"
        form_sections, dynamic_form_data = generate_object_creation_structure(
            efootprint_class_str,
            available_efootprint_classes=[EdgeUsageJourney],
            attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
            model_web=model_web
        )

        # Enforce constraint to only be able to select edge devices that are not already linked to another edge UJ.
        edge_usage_journey_creation_data = form_sections[1]
        for field in edge_usage_journey_creation_data["fields"]:
            if field["attr_name"] == "edge_device":
                selection_options = edge_devices_that_are_not_already_linked
                selected = selection_options[0]
                field.update({
                    "selected": selected.efootprint_id,
                    "options": [
                        {"label": attr_value.name, "value": attr_value.efootprint_id} for attr_value in
                        selection_options]
                })
                break

        context_data = {"form_sections": form_sections,
                        "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
                        "object_type": efootprint_class_str,
                        "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_class_str]["label"]}

        return context_data
