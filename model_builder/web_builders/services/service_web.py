from typing import TYPE_CHECKING

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb, \
    ATTRIBUTES_TO_SKIP_IN_FORMS

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ServiceWeb(ModelingObjectWeb):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def class_title_style(self):
        return "h8"

    @property
    def template_name(self):
        return "service"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        server = model_web.get_web_object_from_efootprint_id(efootprint_id_of_parent_to_link_to)

        installable_services = server.installable_services()
        services_dict, dynamic_form_data = generate_object_creation_structure(
            "Service",
            available_efootprint_classes=installable_services,
            attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
            model_web=model_web,
        )

        context_data = {
            "server": server,
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "Service",
            "obj_formatting_data": FORM_TYPE_OBJECT["Service"],
            "header_name": "Add new service"
        }

        return context_data
