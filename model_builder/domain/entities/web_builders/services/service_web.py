from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ServiceWeb(ModelingObjectWeb):
    attributes_to_skip_in_forms = ["gpu_latency_alpha", "gpu_latency_beta", "server"]
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False
    skip_parent_linking = True  # Service links to server via 'server' field, not via parent list

    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'child_of_parent',
        'get_available_classes_from_parent': 'installable_services',  # Dynamic: calls server.installable_services()
        'parent_context_key': 'server',
    }

    @property
    def class_title_style(self):
        return "h8"

    @property
    def template_name(self):
        return "service"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for service creation forms - link to parent server, swap beforebegin."""
        server = context_data.get("server")
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_target": f"#add-service-to-{server.web_id}" if server else None,
            "hx_swap": "beforebegin"
        }

    @classmethod
    def prepare_creation_input(cls, form_data):
        """Map server ID from parent_to_link_to to service-specific server field.

        Note: form_data is pre-parsed, so we set clean key 'server' instead of prefixed key.
        """
        server_efootprint_id = form_data.get("efootprint_id_of_parent_to_link_to")

        form_data = dict(form_data)
        form_data["server"] = server_efootprint_id
        return form_data
