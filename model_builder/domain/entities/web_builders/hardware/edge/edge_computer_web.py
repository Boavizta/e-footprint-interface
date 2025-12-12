from typing import TYPE_CHECKING

from model_builder.domain.object_factory import edit_object_from_parsed_data, create_efootprint_obj_from_parsed_data
from model_builder.domain.entities.web_core.hardware.edge.edge_device_base_web import EdgeDeviceBaseWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class EdgeComputerWeb(EdgeDeviceBaseWeb):
    edit_template = "../server/server_edit.html"

    # Declarative form configuration for edition - used by FormContextBuilder in adapters layer
    form_edition_config = {
        'strategy': 'with_storage',
    }

    @property
    def calculated_attributes_values(self):
        return (self.cpu_component.calculated_attributes_values + self.ram_component.calculated_attributes_values
                + super().calculated_attributes_values)

    @classmethod
    def pre_create(cls, form_data, model_web: "ModelWeb"):
        """Create edge storage object before creating edge computer.

        Note: form_data is pre-parsed by the adapter layer. Nested storage data
        is available under _parsed_storage key.
        """
        parsed_storage = form_data.get("_parsed_storage")
        storage = create_efootprint_obj_from_parsed_data(parsed_storage, model_web, "EdgeStorage")
        added_storage = model_web.add_new_efootprint_object_to_system(storage)

        # Copy and modify form data to include storage reference (clean key, no prefix)
        form_data = dict(form_data)
        form_data["storage"] = added_storage.efootprint_id
        return form_data

    @classmethod
    def pre_edit(cls, form_data, obj_to_edit, model_web):
        """Edit edge storage before editing edge computer.

        Note: form_data is pre-parsed by the adapter layer. Nested storage data
        is available under _parsed_storage key.
        """
        parsed_storage = form_data.get("_parsed_storage")
        storage_id = parsed_storage.get("storage_id")
        storage = model_web.get_web_object_from_efootprint_id(storage_id)
        edit_object_from_parsed_data(parsed_storage, storage)
