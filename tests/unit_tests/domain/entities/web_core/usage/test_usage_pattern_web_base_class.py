"""Unit tests for UsagePatternWebBaseClass behavior."""
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.usage_journey import UsageJourney


class _UsagePatternWeb(UsagePatternWebBaseClass):
    attr_name_in_system = "usage_patterns"
    object_type_in_volume = "usage_journey"

    @classmethod
    def can_create(cls, model_web) -> bool:
        return bool(model_web.usage_journeys)


@dataclass
class _StubModelingObject:
    id: str


class _SystemStub:
    def __init__(self):
        self.modeling_obj = MagicMock()
        self.modeling_obj.usage_patterns = []
        self._values = {"usage_patterns": []}

    def get_efootprint_value(self, name):
        return list(self._values[name])

    def set_efootprint_value(self, name, value):
        self._values[name] = value


class TestUsagePatternWebBaseClass:
    """Tests for UsagePatternWebBaseClass behavior."""
    # --- get_creation_prerequisites ---

    def test_get_creation_prerequisites_requires_usage_journey(self):
        """No journeys should block usage pattern creation."""
        model_web = MagicMock()
        model_web.usage_journeys = []

        with pytest.raises(ValueError):
            _UsagePatternWeb.get_creation_prerequisites(model_web)

    def test_get_creation_prerequisites_passes_with_journey(self):
        """At least one journey allows usage pattern creation."""
        model_web = MagicMock()
        model_web.usage_journeys = [MagicMock()]

        assert _UsagePatternWeb.get_creation_prerequisites(model_web) == {}

    def test_links_to_every_selected_top_level_journey(self, minimal_model_web):
        pattern = minimal_model_web.usage_patterns[0]
        second_journey = UsageJourney("Second journey", uj_steps=[])
        pattern.modeling_obj.usage_journeys[second_journey] = SourceValue(0.5 * u.dimensionless)
        minimal_model_web.flat_efootprint_objs_dict[second_journey.id] = second_journey

        links = pattern.links_to.split("|")[1:]

        assert links == [
            minimal_model_web.get_web_object_from_efootprint_id(journey.id).web_id
            for journey in pattern.modeling_obj.usage_journeys
        ]
        assert pattern.accordion_children == []
        assert minimal_model_web.get_web_object_from_efootprint_id(second_journey.id).mirrored_cards[0].dict_container is None

    def test_reverse_membership_keeps_last_required_journey_link(self, minimal_model_web):
        pattern = minimal_model_web.usage_patterns[0]
        journey = minimal_model_web.usage_journeys[0]

        membership = next(
            section for section in journey.dict_membership_sections
            if section["parent_class_name"] == "UsagePattern"
        )["memberships"][0]

        assert membership["unlink_disabled"] is True

        second_journey = UsageJourney("Second journey", uj_steps=[])
        pattern.modeling_obj.usage_journeys[second_journey] = SourceValue(1 * u.dimensionless)
        minimal_model_web.flat_efootprint_objs_dict[second_journey.id] = second_journey

        membership = next(
            section for section in journey.dict_membership_sections
            if section["parent_class_name"] == "UsagePattern"
        )["memberships"][0]
        assert membership["unlink_disabled"] is False

    # --- pre_add_to_system ---

    def test_pre_add_to_system_appends_to_system_list(self):
        """New usage pattern should be appended to the system list."""
        model_web = MagicMock()
        model_web.system = _SystemStub()
        new_obj = _StubModelingObject(id="new-id")

        _UsagePatternWeb.pre_add_to_system(new_obj, model_web)

        assert new_obj in model_web.system.modeling_obj.usage_patterns

    # --- pre_delete ---

    def test_pre_delete_removes_from_system_list(self):
        """Deleting usage pattern should update the system list."""
        model_web = MagicMock()
        model_web.system = _SystemStub()

        keep_obj = _StubModelingObject(id="keep-id")
        delete_obj = _StubModelingObject(id="delete-id")
        model_web.system._values["usage_patterns"] = [keep_obj, delete_obj]

        web_obj = MagicMock()
        web_obj.efootprint_id = "delete-id"

        _UsagePatternWeb.pre_delete(web_obj, model_web)

        assert model_web.system._values["usage_patterns"] == [keep_obj]
