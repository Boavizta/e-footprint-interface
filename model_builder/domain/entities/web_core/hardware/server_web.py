import json
from typing import TYPE_CHECKING

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.domain.object_factory import (
    edit_object_in_system, create_efootprint_obj_from_post_data, make_form_data_mutable)
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class ServerWeb(ModelingObjectWeb):
    add_template = "add_object_with_storage.html"
    edit_template = "../server/server_edit.html"
    attributes_to_skip_in_forms = ["storage", "fixed_nb_of_instances"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'with_storage',
        'available_classes': [GPUServer, BoaviztaCloudServer, Server],
        'storage_type': 'Storage',
        'storage_classes': [Storage],
    }
    form_edition_config = {
        'strategy': 'with_storage',
    }

    @property
    def template_name(self):
        return "server"

    @property
    def class_title_style(self):
        return "h6"

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

    def self_delete(self):
        services = self.installed_services
        for service in services:
            service.self_delete()
        super().self_delete()
