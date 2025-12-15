from typing import TYPE_CHECKING

from efootprint.builders.hardware.boavizta_cloud_server import BoaviztaCloudServer
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage

from model_builder.domain.object_factory import edit_object_from_parsed_data, create_efootprint_obj_from_parsed_data
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
        """Create storage object before creating server.

        Note: form_data is pre-parsed by the adapter layer. Nested storage data
        is available under _parsed_Storage key.
        """
        parsed_storage = form_data.get("_parsed_Storage")
        storage = create_efootprint_obj_from_parsed_data(parsed_storage, model_web, "Storage")
        added_storage = model_web.add_new_efootprint_object_to_system(storage)

        # Copy and modify form data to include storage reference (clean key, no prefix)
        form_data = dict(form_data)
        form_data["storage"] = added_storage.efootprint_id
        return form_data

    def pre_edit(self, form_data):
        """Edit storage before editing server.

        Note: form_data is pre-parsed by the adapter layer. Nested storage data
        is available under _parsed_Storage key.
        """
        parsed_storage = form_data.get("_parsed_Storage")
        edit_object_from_parsed_data(parsed_storage, self.storage)

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
