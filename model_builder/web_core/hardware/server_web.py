from typing import TYPE_CHECKING

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.web_core.hardware.hardware_utils import generate_object_with_storage_creation_context, \
    generate_object_with_storage_edition_context, add_new_object_with_storage

if TYPE_CHECKING:
    from model_builder.web_core.model_web import ModelWeb


class ServerWeb(ModelingObjectWeb):
    add_template = "add_object_with_storage.html"
    edit_template = "../server/server_edit.html"

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

    def generate_object_edition_context(self):
        return generate_object_with_storage_edition_context(self)

    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web: "ModelWeb", object_type: str):
        return add_new_object_with_storage(request, model_web, storage_type="Storage")
