import json
from copy import deepcopy
from typing import TYPE_CHECKING

from django.shortcuts import render

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


def generate_attributes_to_skip_in_forms(object_type_in_volume: str):
    return [
        "start_date", "modeling_duration_value", "modeling_duration_unit",
        f"initial_{object_type_in_volume}_volume", f"initial_{object_type_in_volume}_volume_timespan",
        "net_growth_rate_in_percentage", "net_growth_rate_timespan"]


class UsagePatternWebBaseClass(ModelingObjectWeb):
    add_template = "../usage_pattern/usage_pattern_add.html"
    edit_template = "../usage_pattern/usage_pattern_edit.html"
    associated_efootprint_class = None
    attr_name_in_system = "value to override in subclass"
    object_type_in_volume = ""
    attributes_to_skip_in_forms = generate_attributes_to_skip_in_forms(object_type_in_volume)

    @property
    def links_to(self):
        raise NotImplementedError("Subclasses must implement the links_to property.")

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

    @classmethod
    def generate_net_growth_rate_timespan_dynamic_select_dict(cls):
        dynamic_select_options = {
            str(conditional_value): [str(possible_value) for possible_value in possible_values]
            for conditional_value, possible_values in
            cls.associated_efootprint_class.conditional_list_values[
                "net_growth_rate_timespan"]["conditional_list_values"].items()
        }
        dynamic_select = {
            "input_id": "net_growth_rate_timespan",
            "filter_by": "initial_usage_journey_volume_timespan",
            "list_value": {
                key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in
                      value]
                for key, value in dynamic_select_options.items()
            }
        }

        return {"dynamic_selects": [dynamic_select]}


    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        if len(model_web.usage_journeys) == 0:
            raise PermissionError("You need to have created at least one usage journey to create a usage pattern.")
        efootprint_object_type = cls.associated_efootprint_class.__name__
        form_sections, dynamic_form_data = generate_object_creation_structure(
            efootprint_object_type,
            available_efootprint_classes=[cls.associated_efootprint_class],
            attributes_to_skip=cls.attributes_to_skip_in_forms,
            model_web=model_web
        )

        usage_pattern_input_values = deepcopy(cls.associated_efootprint_class.default_values)

        context_data = {
                "form_fields": form_sections[1]["fields"],
                "usage_pattern_input_values": usage_pattern_input_values,
                "dynamic_form_data": cls.generate_net_growth_rate_timespan_dynamic_select_dict(),
                "header_name": f"Add new {FORM_TYPE_OBJECT[efootprint_object_type]["label"].lower()}",
                "object_type": efootprint_object_type,
                "object_type_in_volume": cls.object_type_in_volume,
                "object_type_in_volume_label": cls.object_type_in_volume.replace("_", " "),
                "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_object_type],
                "initial_volume": None,
                "initial_volume_timespan": usage_pattern_input_values[f"initial_{cls.object_type_in_volume}_volume"],
            }

        return context_data

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_type)
        getattr(model_web.system.modeling_obj, cls.attr_name_in_system).append(new_efootprint_obj)
        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        response = render(
            request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
            {added_obj.template_name: added_obj})

        response["HX-Trigger-After-Swap"] = json.dumps({
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [added_obj.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
        })

        return response


    def generate_object_edition_context(self):
            context_data = super().generate_object_edition_context()

            context_data["dynamic_form_data"] = self.generate_net_growth_rate_timespan_dynamic_select_dict()
            context_data["object_type_in_volume"] = self.object_type_in_volume,
            context_data["object_type_in_volume_label"] = self.object_type_in_volume.replace("_", " ")
            context_data["initial_volume"] = getattr(self, f"initial_{self.object_type_in_volume}_volume")
            context_data["initial_volume_timespan"] = getattr(self, f"initial_{self.object_type_in_volume}_volume_timespan")

            return context_data
