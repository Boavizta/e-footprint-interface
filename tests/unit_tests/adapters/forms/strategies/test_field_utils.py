"""Unit tests for field_utils."""
from model_builder.adapters.forms.strategies.field_utils import convert_multiselect_to_single


class TestConvertMultiselectToSingle:
    """Tests for convert_multiselect_to_single function."""

    def test_creation_context_uses_unselected_options(self):
        """When selected is empty, should use unselected options and select the first one."""
        field = {
            "input_type": "multiselect",
            "selected": [],
            "unselected": [{"value": "id1", "label": "Option 1"}, {"value": "id2", "label": "Option 2"}],
        }

        convert_multiselect_to_single(field)

        assert field["input_type"] == "select_object"
        assert field["options"] == [{"value": "id1", "label": "Option 1"}, {"value": "id2", "label": "Option 2"}]
        assert field["selected"] == "id1"
        assert "unselected" not in field

    def test_edition_context_combines_selected_and_unselected(self):
        """When selected is non-empty, should combine selected + unselected and keep first selected."""
        field = {
            "input_type": "multiselect",
            "selected": [{"value": "id2", "label": "Option 2"}],
            "unselected": [{"value": "id1", "label": "Option 1"}],
        }

        convert_multiselect_to_single(field)

        assert field["input_type"] == "select_object"
        assert field["options"] == [{"value": "id2", "label": "Option 2"}, {"value": "id1", "label": "Option 1"}]
        assert field["selected"] == "id2"
        assert "unselected" not in field