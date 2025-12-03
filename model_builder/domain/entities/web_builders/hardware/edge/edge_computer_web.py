import json
from typing import TYPE_CHECKING

from django.http import QueryDict

from model_builder.object_creation_and_edition_utils import edit_object_in_system, create_efootprint_obj_from_post_data
from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb
from model_builder.domain.entities.web_core.hardware.hardware_utils import generate_object_with_storage_edition_context

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class EdgeComputerWeb(EdgeDeviceBaseWeb):
    edit_template = "../server/server_edit.html"

    @property
    def calculated_attributes_values(self):
        return (self.cpu_component.calculated_attributes_values + self.ram_component.calculated_attributes_values
                + super().calculated_attributes_values)

    @classmethod
    def pre_create(cls, form_data, model_web: "ModelWeb"):
        """Create edge storage object before creating edge computer."""
        storage_data = json.loads(form_data.get("storage_form_data"))
        storage = create_efootprint_obj_from_post_data(storage_data, model_web, "EdgeStorage")
        added_storage = model_web.add_new_efootprint_object_to_system(storage)

        # Copy and modify form data to include storage reference
        if isinstance(form_data, QueryDict):
            form_data = form_data.copy()
        else:
            form_data = dict(form_data)
        device_type = form_data.get("type_object_available")
        form_data[device_type + "_storage"] = added_storage.efootprint_id
        return form_data

    def generate_object_edition_context(self):
        return generate_object_with_storage_edition_context(self)

    @classmethod
    def pre_edit(cls, form_data, obj_to_edit, model_web):
        """Edit edge storage before editing edge computer."""
        storage_data = json.loads(form_data.get("storage_form_data"))
        storage = model_web.get_web_object_from_efootprint_id(storage_data["storage_id"])
        edit_object_in_system(storage_data, storage)
