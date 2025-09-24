from abc import abstractmethod

from django.shortcuts import render
from efootprint.logger import logger

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ModelingObjectWebThatCanBeMirrored(ModelingObjectWeb):
    @property
    def web_id(self):
        raise PermissionError(f"{type(self).__name__} objects don’t have a web_id attribute because their html "
                             f"representation should be managed by the Mirrored{type(self.__name__)} object")

    @property
    @abstractmethod
    def mirrored_cards(self):
        raise NotImplementedError(
            "Subclasses of ModelingObjectThatCanBeMirrored must implement the mirrored_cards property")

    def generate_ask_delete_modal_context(self):
        context_data = super().generate_ask_delete_modal_context()
        context_data["remove_card_with_hyperscript"] = False
        if len(self.mirrored_cards) > 1:
            context_data["message"] = (f"This {self.class_as_simple_str} is mirrored {len(self.mirrored_cards)} times, "
                       f"this action will delete all mirrored {self.class_as_simple_str}s.")
            context_data["sub_message"] = (f"To delete only one {self.class_as_simple_str}, "
                                           f"break the mirroring link first.")

        return context_data

    def generate_ask_delete_http_response(self, request):
        delete_modal_context = self.generate_ask_delete_modal_context()
        delete_modal_context["modal_id"] = "model-builder-modal"

        http_response = render(
            request, "model_builder/modals/delete_card_modal.html",
            context=delete_modal_context)

        return http_response

    def generate_delete_http_response(self, request):
        from model_builder.edition.edit_object_http_response_generator import \
            compute_edit_object_html_and_event_response
        from model_builder.edition.edit_object_http_response_generator import \
            generate_http_response_from_edit_html_and_events

        toast_and_highlight_data = {"ids": [], "name": self.name, "action_type": "delete_object"}
        response_html = ""
        for contextual_modeling_obj_container in self.contextual_modeling_obj_containers:
            modeling_obj_container = contextual_modeling_obj_container.modeling_obj_container
            attr_name_in_mod_obj_container = contextual_modeling_obj_container.attr_name_in_mod_obj_container
            mutable_post = request.POST.copy()
            logger.info(f"Removing {self.name} from {modeling_obj_container.name}")
            mutable_post['name'] = modeling_obj_container.name
            new_list_attribute_ids = [
                list_attribute.efootprint_id
                for list_attribute in getattr(modeling_obj_container, attr_name_in_mod_obj_container)
                if list_attribute.efootprint_id != self.efootprint_id]
            mutable_post[attr_name_in_mod_obj_container] = ";".join(new_list_attribute_ids)
            request.POST = mutable_post

            partial_response_html = compute_edit_object_html_and_event_response(request.POST, modeling_obj_container)
            response_html += partial_response_html

        http_response = generate_http_response_from_edit_html_and_events(response_html, toast_and_highlight_data)

        return http_response
