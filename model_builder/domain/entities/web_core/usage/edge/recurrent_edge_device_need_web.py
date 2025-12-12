from model_builder.domain.entities.web_core.usage.edge.recurrent_edge_device_need_base_web import RecurrentEdgeDeviceNeedBaseWeb


class RecurrentEdgeDeviceNeedWeb(RecurrentEdgeDeviceNeedBaseWeb):
    attributes_to_skip_in_forms = ["edge_device", "recurrent_edge_component_needs"]

    @property
    def template_name(self):
        return "resource_need_with_accordion"

    @classmethod
    def prepare_creation_input(cls, form_data):
        """Add empty recurrent_edge_component_needs list.

        Note: form_data is pre-parsed, so we set clean key directly.
        """
        form_data = dict(form_data)
        form_data["recurrent_edge_component_needs"] = ""
        return form_data
