"""Base class for journey-like objects (UsageJourney, EdgeUsageJourney)."""
from abc import abstractmethod

from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class JourneyBaseWeb(ModelingObjectWeb):
    """Base class for journey objects that contain journey steps and are displayed with journey_card.html."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gets_deleted_if_unique_mod_obj_container_gets_deleted = False

    @property
    def template_name(self):
        return "journey"

    @property
    def class_title_style(self):
        return "h6"

    @property
    def accordion_parent(self):
        return None

    @property
    @abstractmethod
    def child_object_type_str(self) -> str:
        """Type string of child objects (e.g., 'UsageJourneyStep', 'EdgeFunction')."""
        pass

    @property
    @abstractmethod
    def child_template_name(self) -> str:
        """Template name for child objects (e.g., 'journey_step')."""
        pass

    @property
    @abstractmethod
    def add_child_label(self) -> str:
        """Label for the 'add child' button (e.g., 'Add usage journey step')."""
        pass

    @property
    @abstractmethod
    def children_property_name(self) -> str:
        """Property name for accessing children (e.g., 'uj_steps', 'edge_functions')."""
        pass

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for journey creation forms - append to #uj-list."""
        return {"hx_target": "#uj-list", "hx_swap": "beforeend"}
