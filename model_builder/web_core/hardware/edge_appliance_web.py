import json

from django.shortcuts import render

from model_builder.object_creation_and_edition_utils import create_efootprint_obj_from_post_data
from model_builder.web_core.hardware.edge_device_base_web import EdgeDeviceBaseWeb


class EdgeApplianceWeb(EdgeDeviceBaseWeb):
    """Web wrapper for EdgeAppliance hardware (e.g., routers, IoT gateways with workload-based power)."""
    add_template = "add_object.html"

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web, object_type: str):
        new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_type)
        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

        response = render(
            request, f"model_builder/object_cards/{added_obj.template_name}_card.html",
            {added_obj.template_name: added_obj})
        response["HX-Trigger-After-Swap"] = json.dumps({
            "displayToastAndHighlightObjects": {
                "ids": [added_obj.web_id], "name": added_obj.name, "action_type": "add_new_object"}
        })

        return response
