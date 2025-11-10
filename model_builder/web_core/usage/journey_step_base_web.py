from efootprint.utils.tools import get_init_signature_params

from model_builder.form_references import FORM_TYPE_OBJECT
from model_builder.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class JourneyStepBaseWeb(ModelingObjectWeb):
    """Base class for journey step objects that can be mirrored in journey contexts."""

    @property
    def class_title_style(self):
        return "h7"

    @property
    def child_object_type_str(self) -> str:
        """Type string of child objects (e.g., 'Job', 'RecurrentEdgeDeviceNeed')."""
        init_signature = get_init_signature_params(self.efootprint_class)
        child_object_type = init_signature[self.children_property_name].annotation.__args__[0].__name__

        return child_object_type

    @property
    def child_template_name(self) -> str:
        return "resource_need"

    @property
    def add_child_label(self) -> str:
        """Label for the 'add child' button (e.g., 'Add new job')."""
        return f"Add {FORM_TYPE_OBJECT[self.child_object_type_str]}"

    @property
    def children_property_name(self) -> str:
        """Property name for accessing children (e.g., 'jobs', 'recurrent_edge_device_needs')."""
        list_attr_names = self.list_attr_names
        assert len(list_attr_names) == 1, (
            f"{self} should have exactly one list attribute, found: {list_attr_names}.")

        return list_attr_names[0]

    @property
    def icon_links_to(self):
        """Returns the web_id of the icon this journey step's icon should link to (next step or add button)."""
        journey_steps = self.list_container.accordion_children
        index = journey_steps.index(self)
        if index < len(journey_steps) - 1:
            link_to = f"icon-{journey_steps[index + 1].web_id}"
        else:
            link_to = f"icon-add-step-to-{self.list_container.web_id}"

        return link_to

    @property
    def icon_leaderline_style(self):
        """Returns the CSS class name for the leaderline style between journey step icons."""
        journey_steps = self.list_container.accordion_children
        index = journey_steps.index(self)
        if index < len(journey_steps) - 1:
            class_name = "vertical-step-swimlane"
        else:
            class_name = "step-dot-line"

        return class_name

    @property
    def data_attributes_as_list_of_dict(self):
        """Returns list of data attributes for leaderline rendering, including icon leaderline."""
        data_attribute_updates = super().data_attributes_as_list_of_dict
        data_attribute_updates.append({"id": f"icon-{self.web_id}", "data-link-to": self.icon_links_to,
                                       "data-line-opt": self.icon_leaderline_style})

        return data_attribute_updates

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """HTMX configuration for journey step creation forms - link to parent, swap none."""
        return {
            "hx_vals": {"efootprint_id_of_parent_to_link_to": context_data.get("efootprint_id_of_parent_to_link_to")},
            "hx_swap": "none"
        }
