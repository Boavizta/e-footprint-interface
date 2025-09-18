from copy import deepcopy
from typing import TYPE_CHECKING

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


def generate_attributes_to_skip_in_forms(object_type_in_volume: str):
    return [
        "start_date", "modeling_duration_value", "modeling_duration_unit",
        f"initial_{object_type_in_volume}_volume", f"initial_{object_type_in_volume}_volume_timespan",
        "net_growth_rate_in_percentage"]


class UsagePatternWebBaseClass(ModelingObjectWeb):
    add_template = "../usage_pattern/usage_pattern_add.html"
    edit_template = "../usage_pattern/usage_pattern_edit.html"
    object_type_in_volume = ""
    associated_efootprint_class = None
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
    def turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(cls, dynamic_form_data: dict):
        dynamic_list_options = dynamic_form_data["dynamic_lists"][0]["list_value"]
        dynamic_select = {
            "input_id": "net_growth_rate_timespan",
            "filter_by": f"initial_{cls.object_type_in_volume}_volume_timespan",
            "list_value": {
                key: [{"label": {"day": "Daily", "month": "Monthly", "year": "Yearly"}[elt], "value": elt} for elt in
                      value]
                for key, value in dynamic_list_options.items()
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
        # Normalize initial volume and timespan keys
        del usage_pattern_input_values[f"initial_{cls.object_type_in_volume}_volume"]
        usage_pattern_input_values["initial_volume"] = None
        usage_pattern_input_values["initial_volume_timespan"] = usage_pattern_input_values.pop(
            f"initial_{cls.object_type_in_volume}_volume_timespan")

        context_data = {
                "form_fields": form_sections[1]["fields"],
                "usage_pattern_input_values": usage_pattern_input_values,
                "dynamic_form_data": cls.turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(
                    dynamic_form_data),
                "header_name": f"Add new {FORM_TYPE_OBJECT[efootprint_object_type]["label"].lower()}",
                "object_type": efootprint_object_type,
                "obj_formatting_data": FORM_TYPE_OBJECT[efootprint_object_type],
            }

        return context_data

    def generate_object_edition_context(self):
        context_data = super().generate_object_edition_context()

        context_data["dynamic_form_data"] = self.turn_net_growth_rate_timespan_dynamic_list_into_dynamic_select(
            context_data["dynamic_form_data"])

        return context_data
