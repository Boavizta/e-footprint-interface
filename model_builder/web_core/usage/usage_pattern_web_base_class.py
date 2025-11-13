import json
from typing import TYPE_CHECKING, List, Tuple, Optional

from django.shortcuts import render

from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class UsagePatternWebBaseClass(ModelingObjectWeb):
    attr_name_in_system = "value to override in subclass"
    object_type_in_volume = "value to override in subclass"

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

    @property
    def mirrored_cards(self):
        # Usage patterns do not have mirrored cards because their container (the System) doesn’t appear in the interface
        return [self]

    @property
    def list_containers_and_attr_name_in_list_container(self) -> Tuple[List, Optional[str]]:
        return [], None


    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        return {"hx_target": "#up-list", "hx_swap": "beforeend"}

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        if len(getattr(model_web, cls.object_type_in_volume + "s")) == 0:
            raise PermissionError(
                f"You need to have created at least one {cls.object_type_in_volume.replace("_", " ")} "
                f"to create a usage pattern.")
        return super().generate_object_creation_context(model_web, efootprint_id_of_parent_to_link_to)

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_type)
        getattr(model_web.system.modeling_obj, cls.attr_name_in_system).append(new_efootprint_obj)
        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        response = render(
            request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
            {"object": added_obj})

        response["HX-Trigger-After-Swap"] = json.dumps({
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
        })

        return response

    def generate_ask_delete_http_response(self, request):
        delete_modal_context = self.generate_ask_delete_modal_context()
        delete_modal_context["modal_id"] = "model-builder-modal"

        http_response = render(
            request, "model_builder/modals/delete_card_modal.html",
            context=delete_modal_context)

        return http_response

    def generate_delete_http_response(self, request):
        system = self.model_web.system
        new_up_list = [up for up in system.get_efootprint_value(self.attr_name_in_system) if up.id != self.efootprint_id]
        system.set_efootprint_value(self.attr_name_in_system, new_up_list)

        return super().generate_delete_http_response(request)
