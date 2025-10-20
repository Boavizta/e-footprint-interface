from typing import TYPE_CHECKING

from efootprint.core.usage.edge_function import EdgeFunction

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeFunctionWeb(ModelingObjectWeb):
    """Web wrapper for EdgeFunction (groups RecurrentEdgeResourceNeeds for an EdgeUsageJourney)."""
    add_template = "add_object.html"
    edit_template = "edit_object.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def class_title_style(self):
        return "h7"

    @property
    def recurrent_edge_resource_needs(self):
        """Returns web-wrapped recurrent edge resource needs contained in this function."""
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return [wrap_efootprint_object(rern, self.model_web) for rern in self._modeling_obj.recurrent_edge_resource_needs]

    @property
    def edge_usage_journeys(self):
        """Returns web-wrapped edge usage journeys that contain this function."""
        from model_builder.efootprint_to_web_mapping import wrap_efootprint_object
        return [wrap_efootprint_object(euj, self.model_web) for euj in self._modeling_obj.edge_usage_journeys]

    @property
    def accordion_children(self):
        """Show recurrent edge resource needs as accordion children."""
        return self.recurrent_edge_resource_needs

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        from model_builder.class_structure import generate_object_creation_structure
        from model_builder.form_references import FORM_TYPE_OBJECT
        from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS

        efootprint_class_str = "EdgeFunction"
        form_sections, dynamic_form_data = generate_object_creation_structure(
            efootprint_class_str,
            available_efootprint_classes=[EdgeFunction],
            attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
            model_web=model_web
        )

        context_data = {
            "form_sections": form_sections,
            "header_name": "Add new " + FORM_TYPE_OBJECT[efootprint_class_str]["label"].lower(),
            "object_type": efootprint_class_str,
            "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_class_str]["label"]
        }

        return context_data
