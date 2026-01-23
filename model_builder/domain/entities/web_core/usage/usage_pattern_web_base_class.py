from typing import TYPE_CHECKING, List, Tuple, Optional

from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class UsagePatternWebBaseClass(ModelingObjectWeb):
    attr_name_in_system = "value to override in subclass"
    object_type_in_volume = "value to override in subclass"

    # Declarative form configuration
    form_creation_config = {
        'strategy': 'simple',
        'field_defaults': {
            'country': {'default_by_label': 'France'},
        },
    }

    @property
    def class_title_style(self):
        return "h6"

    @property
    def template_name(self):
        return "usage_pattern"

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
        return []

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        return {"hx_target": "#up-list", "hx_swap": "beforeend"}

    @classmethod
    def get_creation_prerequisites(cls, model_web: "ModelWeb") -> dict:
        """Check prerequisites and return empty dict (no special data needed).

        Raises PermissionError if prerequisites not met.
        """
        if len(getattr(model_web, cls.object_type_in_volume + "s")) == 0:
            raise PermissionError(
                f"You need to have created at least one {cls.object_type_in_volume.replace('_', ' ')} "
                f"to create a usage pattern.")
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
