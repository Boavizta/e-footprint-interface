from model_builder.domain.entities.web_abstract_modeling_classes.modeling_object_web import ModelingObjectWeb


class JourneyStepBaseWeb(ModelingObjectWeb):
    """Base class for journey step objects that can be mirrored in journey contexts."""

    # Declarative form configuration
    form_creation_config = {
        'strategy': 'simple',
    }

    @property
    def class_title_style(self):
        return "h7"

    @property
    def template_name(self):
        return "journey_step"

    @property
    def child_template_name(self) -> str:
        return "resource_need"

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
