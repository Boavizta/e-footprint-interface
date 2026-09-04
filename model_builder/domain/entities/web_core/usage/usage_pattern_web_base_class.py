from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple, Optional

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


def default_modeling_start_date() -> str:
    """Default modeling start date: January 1st of the current year."""
    return f"{datetime.now().year}-01-01"


class UsagePatternWebBaseClass(ModelingObjectWeb):
    renders_relationship_children_as_nested_cards = False
    attr_name_in_system = "value to override in subclass"
    journey_relationship_attr = "value to override in subclass"

    # Declarative form configuration
    form_creation_config = {
        "strategy": "simple",
        "field_defaults": {
            "country": {"default_by_label": "France"},
        },
    }

    hourly_quantities_from_growth_ui_config = {
        "initial_volume": {
            "label": "Initial volume",
            "tooltip": None,
        },
    }

    @property
    def template_name(self):
        return "basic"

    @property
    def mirrored_cards(self):
        # Usage patterns do not have mirrored cards because their container (the System) doesn't appear in the interface
        return [self]

    @property
    def modeling_obj_containers(self):
        # Mimic having no containers for deletion checks
        return []

    @property
    def list_containers_and_attr_name_in_list_container(self) -> Tuple[List, Optional[str]]:
        # Mimic having no containers for deletion checks
        return [], None

    @property
    def accordion_children(self):
        """Patterns link reusable top-level journeys; they never render them as nested cards."""
        return []

    @property
    def links_to(self):
        """Draw one canvas relationship from the pattern to each selected top-level journey."""
        relationship = self.get_efootprint_value(self.journey_relationship_attr)
        journeys = relationship.keys() if isinstance(relationship, dict) else relationship
        return "".join(
            f"|{self.model_web.get_web_object_from_efootprint_id(journey.id).web_id}"
            for journey in journeys
        )

    @classmethod
    def get_creation_default_values(cls, model_web: "ModelWeb") -> dict:
        """Preselect the first available journey so required relationships start valid."""
        journeys = getattr(model_web, cls.journey_relationship_attr)
        if cls.journey_relationship_attr == "usage_journeys":
            return {cls.journey_relationship_attr: {journeys[0].modeling_obj: SourceValue(1 * u.dimensionless)}}
        return {cls.journey_relationship_attr: [journeys[0].modeling_obj]}

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        return {"hx_target": "#up-list", "hx_swap": "beforeend"}

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> dict:
        """Check prerequisites and return empty dict (no special data needed).

        Raises ValueError if prerequisites not met (last line of defence — the UI
        should have disabled the button before this point).
        """
        if not cls.can_create(model_web):
            raise ValueError("Cannot create usage pattern: prerequisites not met.")
        return {}

    @classmethod
    def pre_add_to_system(cls, new_efootprint_obj, model_web: "ModelWeb"):
        """Link new usage pattern to the system before adding."""
        getattr(model_web.system.modeling_obj, cls.attr_name_in_system).append(new_efootprint_obj)

    @classmethod
    def pre_delete(cls, web_obj, model_web: "ModelWeb"):
        """Unlink usage pattern from system before deletion."""
        system = model_web.system
        new_up_list = [up for up in system.get_efootprint_value(cls.attr_name_in_system) if up.id != web_obj.efootprint_id]
        system.set_efootprint_value(cls.attr_name_in_system, new_up_list)
