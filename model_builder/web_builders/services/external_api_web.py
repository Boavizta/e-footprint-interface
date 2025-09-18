from typing import TYPE_CHECKING

from efootprint.builders.services.generative_ai_ecologits import GenAIModel

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb, \
    ATTRIBUTES_TO_SKIP_IN_FORMS

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ExternalApiWeb(ModelingObjectWeb):
    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        services_dict, dynamic_form_data = generate_object_creation_structure(
            "Service",
            available_efootprint_classes=[GenAIModel],
            attributes_to_skip=ATTRIBUTES_TO_SKIP_IN_FORMS,
            model_web=model_web,
        )

        services_dict[0]["fields"][0]["label"] = "Available services"

        context_data = {
            "form_sections": services_dict,
            "dynamic_form_data": dynamic_form_data,
            "object_type": "ExternalApi",
            "obj_formatting_data": FORM_TYPE_OBJECT["ExternalApi"],
            "header_name": "Add new external API",
        }

        return context_data
