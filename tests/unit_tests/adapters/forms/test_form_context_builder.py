"""Unit tests for FormContextBuilder-specific custom context."""

from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup

from model_builder.adapters.forms.form_context_builder import FormContextBuilder
from model_builder.domain.efootprint_to_web_mapping import EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING
from model_builder.domain.entities.web_core.hardware.edge.edge_device_group_web import EdgeDeviceGroupWeb
from model_builder.domain.entities.web_core.hardware.edge.edge_device_web import EdgeDeviceWeb


def _fields_by_attr(form_sections: list, category: str) -> dict:
    section = next(section for section in form_sections if section["category"] == category)
    return {field["attr_name"]: field for field in section["fields"] if "attr_name" in field}


class TestFormContextBuilder:
    """Tests for annotation-driven dict_count field generation."""

    def test_build_creation_context_for_edge_device_group_emits_dict_count_fields_from_annotations(
        self, minimal_model_web):
        existing_group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Existing Group"))
        existing_device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Existing Device", components=[]))

        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EdgeDeviceGroupWeb, "EdgeDeviceGroup")

        fields_by_attr = _fields_by_attr(context["form_sections"], "EdgeDeviceGroup")
        assert fields_by_attr["sub_group_counts"]["input_type"] == "dict_count"
        assert fields_by_attr["sub_group_counts"]["options"] == [
            {"value": existing_group.efootprint_id, "label": "Existing Group"}
        ]
        assert fields_by_attr["edge_device_counts"]["options"] == [
            {"value": existing_device.efootprint_id, "label": "Existing Device"}
        ]

    def test_build_edition_context_sorts_dict_count_options_and_excludes_self(self, minimal_model_web):
        parent = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Parent"))
        zeta = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Zeta"))
        alpha = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Alpha"))
        device_b = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Device B", components=[]))
        device_a = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Device A", components=[]))
        del zeta, alpha, device_b, device_a

        context = FormContextBuilder(minimal_model_web).build_edition_context(parent)

        fields_by_attr = {field["attr_name"]: field for field in context["form_fields"] if "attr_name" in field}
        assert [option["label"] for option in fields_by_attr["sub_group_counts"]["options"]] == ["Alpha", "Zeta"]
        assert [option["label"] for option in fields_by_attr["edge_device_counts"]["options"]] == ["Device A", "Device B"]

    def test_build_edition_context_dict_count_field_shape(self, minimal_model_web):
        group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Group"))

        context = FormContextBuilder(minimal_model_web).build_edition_context(group)

        fields_by_attr = {field["attr_name"]: field for field in context["form_fields"] if "attr_name" in field}
        sub_group_field = fields_by_attr["sub_group_counts"]
        assert sub_group_field["web_id"] == "EdgeDeviceGroup_sub_group_counts"
        assert sub_group_field["input_type"] == "dict_count"
        assert sub_group_field["label"]
        assert "tooltip" in sub_group_field
        assert sub_group_field["options_json"].startswith("[")
        assert sub_group_field["selected_json"].startswith("{")


class TestParentGroupMembershipField:
    """Tests for the parent_group_memberships UI-only field override."""

    def test_returns_none_when_no_available_groups(self):
        assert FormContextBuilder._build_parent_group_membership_field([]) is None

    def test_tooltip_is_resolved_ui_text_with_no_raw_tokens(self, minimal_model_web):
        existing_group = minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Existing Group"))

        field = FormContextBuilder._build_parent_group_membership_field([existing_group])

        assert field["attr_name"] == "parent_group_memberships"
        assert field["label"] == "Add to parent groups"
        assert field["tooltip"]
        # The library param_descriptions for sub_group_counts/edge_device_counts must NOT leak in.
        assert "Mapping from" not in field["tooltip"]
        # Placeholder tokens must be fully resolved before reaching the template.
        assert "{class:" not in field["tooltip"]
        assert "{param:" not in field["tooltip"]

    def test_same_tooltip_for_group_and_device_creation_contexts(self, minimal_model_web):
        """The override is class-agnostic: same UI text from either child perspective."""
        minimal_model_web.add_new_efootprint_object_to_system(EdgeDeviceGroup("Existing Group"))

        group_context = FormContextBuilder(minimal_model_web).build_creation_context(
            EdgeDeviceGroupWeb, "EdgeDeviceGroup")
        device_context = FormContextBuilder(minimal_model_web).build_creation_context(
            EdgeDeviceWeb, "EdgeDevice")

        assert group_context["parent_group_membership_field"]["tooltip"] \
            == device_context["parent_group_membership_field"]["tooltip"]


class TestParentLinkCountField:
    """Creation panels opened from a dict-relationship parent offer a multiplier field prefilled at 1."""

    def test_step_creation_from_journey_offers_times_per_journey_field(self, minimal_model_web):
        journey = minimal_model_web.usage_journeys[0]

        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING["UsageJourneyStep"], "UsageJourneyStep",
            journey.efootprint_id)

        assert context["parent_link_count_field"] == {"label": "Times per journey", "parent_name": journey.name}

    def test_job_creation_from_step_offers_times_per_step_field(self, minimal_model_web):
        step = minimal_model_web.usage_journey_steps[0]

        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING["JobBase"], "JobBase", step.efootprint_id)

        assert context["parent_link_count_field"] == {"label": "Times per step", "parent_name": step.name}

    def test_no_field_for_list_relationship_parent(self, minimal_model_web):
        device = minimal_model_web.add_new_efootprint_object_to_system(
            EdgeDevice.from_defaults("Bare Device", components=[]))

        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING["EdgeComponent"], "EdgeComponent", device.efootprint_id)

        assert context["parent_link_count_field"] is None

    def test_no_field_without_parent(self, minimal_model_web):
        context = FormContextBuilder(minimal_model_web).build_creation_context(
            EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING["UsageJourneyStep"], "UsageJourneyStep")

        assert "parent_link_count_field" not in context
