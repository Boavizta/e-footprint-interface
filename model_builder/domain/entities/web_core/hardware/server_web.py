import json
from typing import TYPE_CHECKING

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.domain.object_factory import (
    edit_object_in_system, create_efootprint_obj_from_post_data, make_form_data_mutable)
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb
from model_builder.domain.entities.web_core.hardware.hardware_utils import (
    generate_object_with_storage_creation_context, generate_object_with_storage_edition_context)

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ServerWeb(ModelingObjectWeb):
    add_template = "add_object_with_storage.html"
    edit_template = "../server/server_edit.html"
    attributes_to_skip_in_forms = ["storage", "fixed_nb_of_instances"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "server"

    @property
    def class_title_style(self):
        return "h6"

    @classmethod
    def generate_object_creation_context(
    cls, model_web: "ModelWeb", efootprint_id_of_parent_to_link_to=None, object_type: str=None):
        return generate_object_with_storage_creation_context(
            model_web, "ServerBase", [GPUServer, BoaviztaCloudServer, Server],
            "Storage", [Storage])

    @classmethod
    def pre_create(cls, form_data, model_web: "ModelWeb"):
        """Create storage object before creating server."""
        storage_data = json.loads(form_data.get("storage_form_data"))
        storage = create_efootprint_obj_from_post_data(storage_data, model_web, "Storage")
        added_storage = model_web.add_new_efootprint_object_to_system(storage)

        # Copy and modify form data to include storage reference
        form_data = make_form_data_mutable(form_data)
        server_type = form_data.get("type_object_available")
        form_data[server_type + "_storage"] = added_storage.efootprint_id
        return form_data

    def generate_object_edition_context(self):
        return generate_object_with_storage_edition_context(self)

    @classmethod
    def pre_edit(cls, form_data, obj_to_edit, model_web):
        """Edit storage before editing server."""
        storage_data = json.loads(form_data.get("storage_form_data"))
        storage = model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
        edit_object_in_system(storage_data, storage)

    @classmethod
    def can_delete(cls, web_obj) -> tuple:
        """Check if server can be deleted. Only blocked by jobs, not services.

        Services installed on this server will be cascade-deleted via self_delete().

        Returns:
            Tuple of (can_delete: bool, blocking_names: List[str])
        """
        if web_obj.jobs:
            return False, [obj.name for obj in web_obj.jobs]
        return True, []

    def generate_cant_delete_modal_message(self):
        if self.jobs:
            msg = (f"This server is requested by {", ".join([obj.name for obj in self.jobs])}. "
                   f"To delete it, first delete or reorient these jobs making requests to it.")
            return msg
        return super().generate_cant_delete_modal_message()

    def self_delete(self):
        services = self.installed_services
        for service in services:
            service.self_delete()
        super().self_delete()
