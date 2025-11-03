import json
from typing import TYPE_CHECKING

from django.http import QueryDict

from model_builder.object_creation_and_edition_utils import edit_object_in_system
from model_builder.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.web_core.hardware.hardware_utils import (generate_object_with_storage_edition_context,
                                                            add_new_object_with_storage)

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeComputerWeb(EdgeDeviceBaseWeb):
    edit_template = "../server/server_edit.html"

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        return add_new_object_with_storage(request, model_web, storage_type="EdgeStorage")

    def generate_object_edition_context(self):
        return generate_object_with_storage_edition_context(self)

    def edit_object_and_return_html_response(self, edit_form_data: QueryDict):
        storage_data = json.loads(edit_form_data.get("storage_form_data"))
        storage = self.model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
        edit_object_in_system(storage_data, storage)

        return super().edit_object_and_return_html_response(edit_form_data)
