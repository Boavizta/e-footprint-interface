from efootprint.builders.external_apis.ecologits.ecologits_external_api import EcoLogitsGenAIExternalAPI

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class ExternalAPIWeb(ModelingObjectWeb):
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False
    # Declarative form configuration - used by FormContextBuilder in adapters layer
    form_creation_config = {
        'strategy': 'simple',
        'available_classes': [EcoLogitsGenAIExternalAPI],
    }

    @property
    def template_name(self):
        return "basic"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for external API creation forms - append to #server-list."""
        return {"hx_target": "#external-api-list", "hx_swap": "beforeend"}
