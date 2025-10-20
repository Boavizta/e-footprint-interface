import json
from typing import TYPE_CHECKING

from django.http import QueryDict
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.hardware.edge_storage import EdgeStorage

from model_builder.object_creation_and_edition_utils import edit_object_in_system
from model_builder.web_core.hardware.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context, \
    generate_object_with_storage_edition_context, add_new_object_with_storage

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class EdgeComputerWeb(EdgeDeviceBaseWeb):
    add_template = "add_object_with_storage.html"
    edit_template = "../server/server_edit.html"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        return generate_object_with_storage_creation_context(
            model_web, "EdgeComputer", [EdgeComputer],
            "EdgeStorage", [EdgeStorage])

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
