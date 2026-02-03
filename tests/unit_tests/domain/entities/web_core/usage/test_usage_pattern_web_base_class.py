"""Unit tests for UsagePatternWebBaseClass behavior."""
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from model_builder.domain.entities.web_core.usage.usage_pattern_web_base_class import UsagePatternWebBaseClass


class _UsagePatternWeb(UsagePatternWebBaseClass):
    attr_name_in_system = "usage_patterns"
    object_type_in_volume = "usage_journey"


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

        with pytest.raises(PermissionError):
            _UsagePatternWeb.get_creation_prerequisites(model_web)

    def test_get_creation_prerequisites_passes_with_journey(self):
        """At least one journey allows usage pattern creation."""
        model_web = MagicMock()
        model_web.usage_journeys = [MagicMock()]

        assert _UsagePatternWeb.get_creation_prerequisites(model_web) == {}

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
