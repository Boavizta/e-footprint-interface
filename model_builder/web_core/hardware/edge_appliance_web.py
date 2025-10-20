from typing import TYPE_CHECKING

from efootprint.core.hardware.edge_appliance import EdgeAppliance

from model_builder.web_core.hardware.edge_device_base_web import EdgeDeviceBaseWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeApplianceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for EdgeAppliance hardware (e.g., routers, IoT gateways with workload-based power)."""
    add_template = "add_object.html"
    edit_template = "edit_object.html"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        from model_builder.class_structure import generate_object_creation_structure
        from model_builder.form_references import FORM_TYPE_OBJECT
        from model_builder.web_abstract_modeling_classes.modeling_object_web import ATTRIBUTES_TO_SKIP_IN_FORMS

        efootprint_class_str = "EdgeAppliance"
        form_sections, dynamic_form_data = generate_object_creation_structure(
            efootprint_class_str,
            available_efootprint_classes=[EdgeAppliance],
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
