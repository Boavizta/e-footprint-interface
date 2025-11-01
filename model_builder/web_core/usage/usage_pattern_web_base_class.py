from typing import TYPE_CHECKING

from django.shortcuts import render

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class UsagePatternWebBaseClass(ModelingObjectWeb):
    attr_name_in_system = "value to override in subclass"

    @property
    def links_to(self):
        raise NotImplementedError("Subclasses must implement the links_to property.")

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

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
