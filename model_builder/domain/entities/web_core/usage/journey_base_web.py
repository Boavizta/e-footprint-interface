"""Base class for journey-like objects (UsageJourney, EdgeUsageJourney)."""
from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class JourneyBaseWeb(ModelingObjectWeb):
    """Base class for journey objects that contain journey steps and are displayed with journey_card.html."""
    gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "journey"

    @property
    def class_title_style(self):
        return "h6"

    @property
    def child_template_name(self) -> str:
        """Template name for child objects (e.g., 'journey_step')."""
        return "journey_step"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for journey creation forms - append to #uj-list."""
        return {"hx_target": "#uj-list", "hx_swap": "beforeend"}
