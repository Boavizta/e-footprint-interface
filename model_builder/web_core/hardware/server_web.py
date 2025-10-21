import json
from typing import TYPE_CHECKING

from django.http import QueryDict
from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.object_creation_and_edition_utils import edit_object_in_system
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context, \
    generate_object_with_storage_edition_context, add_new_object_with_storage

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ServerWeb(ModelingObjectWeb):
    add_template = "add_object_with_storage.html"
    edit_template = "../server/server_edit.html"
    attributes_to_skip_in_forms = ["storage", "fixed_nb_of_instances"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "server"

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None):
        return generate_object_with_storage_creation_context(
            model_web, "ServerBase", [GPUServer, BoaviztaCloudServer, Server],
            "Storage", [Storage])

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        return add_new_object_with_storage(request, model_web, storage_type="Storage")

    def generate_object_edition_context(self):
        return generate_object_with_storage_edition_context(self)

    def edit_object_and_return_html_response(self, edit_form_data: QueryDict):
        storage_data = json.loads(edit_form_data.get("storage_form_data"))
        storage = self.model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
        edit_object_in_system(storage_data, storage)

        return super().edit_object_and_return_html_response(edit_form_data)

    def generate_cant_delete_modal_message(self):
        if self.jobs:
            msg = (f"This server is requested by {", ".join([obj.name for obj in self.jobs])}. "
                   f"To delete it, first delete or reorient these jobs making requests to it.")
            return msg
        return super().generate_cant_delete_modal_message()
