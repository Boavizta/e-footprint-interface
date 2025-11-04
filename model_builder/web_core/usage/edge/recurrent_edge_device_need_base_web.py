from typing import TYPE_CHECKING

from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.builders.usage.edge.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

from model_builder.class_structure import generate_object_creation_structure
from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_core.usage.resource_need_base_web import ResourceNeedBaseWeb, MirroredResourceNeedBaseWeb

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class RecurrentEdgeDeviceNeedBaseWeb(ResourceNeedBaseWeb):
    """Web wrapper for RecurrentEdgeDeviceNeed and its subclasses (RecurrentEdgeProcess, RecurrentEdgeWorkload)."""
    attributes_to_skip_in_forms = ["edge_device"]

    @property
    def template_name(self):
        return "resource_need"

    @property
    def mirrored_cards(self):
        """Create mirrored cards for each edge function this resource need is linked to."""
        mirrored_cards = []
        for edge_function in self.edge_functions:
            for mirrored_edge_function_card in edge_function.mirrored_cards:
                mirrored_cards.append(
                    MirroredRecurrentEdgeDeviceNeedWeb(self._modeling_obj, mirrored_edge_function_card))

        return mirrored_cards

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        edge_devices = model_web.edge_devices
        if len(edge_devices) == 0:
            raise ValueError("Please create an edge device before adding a recurrent edge resource need")

        # RecurrentEdgeProcess works with EdgeComputer, RecurrentEdgeWorkload works with EdgeAppliance,
        # RecurrentEdgeDeviceNeed works with EdgeDevice.
        available_resource_need_classes = [RecurrentEdgeProcess, RecurrentEdgeWorkload, RecurrentEdgeDeviceNeed]

        base_object_type = "RecurrentEdgeDeviceNeedBase"

        form_sections, dynamic_form_data = generate_object_creation_structure(
            base_object_type,
            available_efootprint_classes=available_resource_need_classes,
            model_web=model_web,
        )

        additional_item = {
            "category": "resource_need_creation_helper",
            "header": "Resource need creation helper",
            "fields": [
                {
                    "input_type": "select_object",
                    "web_id": "edge_device",
                    "name": "Edge Device",
                    "options": [
                        {"label": edge_device.name, "value": edge_device.efootprint_id}
                        for edge_device in edge_devices],
                    "label": "Choose an edge device",
                },
            ]
        }
        form_sections = [additional_item] + form_sections

        # Define which resource need types are compatible with which edge device types
        possible_resource_need_types_per_device = {}
        for edge_device in edge_devices:
            device_class = edge_device.class_as_simple_str
            if device_class == "EdgeComputer":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeProcess"]["label"], "value": "RecurrentEdgeProcess"}
                ]
            elif device_class == "EdgeAppliance":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeWorkload"]["label"], "value": "RecurrentEdgeWorkload"}
                ]
            elif device_class == "EdgeDevice":
                possible_resource_need_types_per_device[edge_device.efootprint_id] = [
                    {"label": FORM_TYPE_OBJECT["RecurrentEdgeDeviceNeed"]["label"], "value": "RecurrentEdgeDeviceNeed"}
                ]
            else:
                raise ValueError(f"Unknown edge device class: {device_class}")

        dynamic_form_data["dynamic_selects"] = [
            {
                "input_id": "type_object_available",
                "filter_by": "edge_device",
                "list_value": possible_resource_need_types_per_device
            }
        ]

        context_data = {
            "form_sections": form_sections,
            "dynamic_form_data": dynamic_form_data,
            "object_type": base_object_type,
            "obj_formatting_data": FORM_TYPE_OBJECT[base_object_type],
            "header_name": "Add new " + FORM_TYPE_OBJECT[base_object_type]["label"].lower()
        }

        return context_data

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        from model_builder.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING

        object_creation_type = request.POST.get("type_object_available", object_type)
        child_object_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_creation_type]
        http_response = child_object_web_class.add_new_object_and_return_html_response(
            request, model_web, object_creation_type)

        return http_response


class MirroredRecurrentEdgeDeviceNeedWeb(MirroredResourceNeedBaseWeb):
    """Mirrored version of RecurrentEdgeDeviceNeed shown within a specific EdgeFunction context."""

    @property
    def links_to(self):
        return self.edge_device.web_id
