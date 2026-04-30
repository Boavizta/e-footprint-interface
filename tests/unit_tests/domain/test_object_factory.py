"""Unit tests for object_factory helpers."""
import pytest

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.source_objects import Sources

from model_builder.adapters.repositories import InMemorySystemRepository
from model_builder.domain.entities.web_core.model_web import ModelWeb
from model_builder.domain.reference_data import DEFAULT_SYSTEM_DATA
from model_builder.domain.object_factory import (
    create_efootprint_obj_from_parsed_data, edit_object_from_parsed_data, _apply_metadata,
)


class TestCreateEfootprintObjFromParsedData:
    """Tests for constructor-time dict input support."""

    def test_builds_input_explainable_object_dicts_from_parsed_data(self, minimal_model_web):
        group = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Parent"}, minimal_model_web, "EdgeDeviceGroup")
        )
        device = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data(
                {"name": "Device", "components": []},
                minimal_model_web,
                "EdgeDevice",
            )
        )

        created_group = create_efootprint_obj_from_parsed_data(
            {
                "name": "Campus",
                "sub_group_counts": {
                    group.efootprint_id: {"value": 2, "unit": "dimensionless", "label": "no label"}
                },
                "edge_device_counts": {
                    device.efootprint_id: {"value": 3, "unit": "dimensionless", "label": "no label"}
                },
            },
            minimal_model_web,
            "EdgeDeviceGroup",
        )

        assert group.modeling_obj in created_group.sub_group_counts
        assert created_group.sub_group_counts[group.modeling_obj].value.magnitude == 2
        assert created_group.sub_group_counts[group.modeling_obj].source == Sources.USER_DATA
        assert device.modeling_obj in created_group.edge_device_counts
        assert created_group.edge_device_counts[device.modeling_obj].value.magnitude == 3
        assert created_group.edge_device_counts[device.modeling_obj].source == Sources.USER_DATA

    def test_rejects_unknown_ids_in_input_explainable_object_dicts(self, minimal_model_web):
        with pytest.raises(ValueError, match="Unknown modeling object id 'missing-id'"):
            create_efootprint_obj_from_parsed_data(
                {
                    "name": "Campus",
                    "sub_group_counts": {
                        "missing-id": {"value": 1, "unit": "dimensionless", "label": "no label"}
                    },
                },
                minimal_model_web,
                "EdgeDeviceGroup",
            )

    def test_edit_updates_explainable_object_dicts_from_parsed_data(self, minimal_model_web):
        parent = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Parent"}, minimal_model_web, "EdgeDeviceGroup")
        )
        child = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Child"}, minimal_model_web, "EdgeDeviceGroup")
        )
        device = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Device", "components": []}, minimal_model_web, "EdgeDevice")
        )

        edit_object_from_parsed_data(
            {
                "sub_group_counts": {
                    child.efootprint_id: {"value": 2, "unit": "dimensionless", "label": "no label"}
                },
                "edge_device_counts": {
                    device.efootprint_id: {"value": 3, "unit": "dimensionless", "label": "no label"}
                },
            },
            parent,
        )

        assert parent.modeling_obj.sub_group_counts[child.modeling_obj].value.magnitude == 2
        assert parent.modeling_obj.edge_device_counts[device.modeling_obj].value.magnitude == 3

    def test_edit_updates_explainable_object_dicts_without_breaking_serialization(self):
        model_web = ModelWeb(InMemorySystemRepository(initial_data=DEFAULT_SYSTEM_DATA))

        parent = model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Parent"}, model_web, "EdgeDeviceGroup")
        )
        child = model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Child"}, model_web, "EdgeDeviceGroup")
        )
        device = model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Device", "components": []}, model_web, "EdgeDevice")
        )

        edit_object_from_parsed_data(
            {
                "sub_group_counts": {
                    child.efootprint_id: {"value": 2, "unit": "dimensionless", "label": "no label"}
                },
                "edge_device_counts": {
                    device.efootprint_id: {"value": 3, "unit": "dimensionless", "label": "no label"}
                },
            },
            parent,
            update_system_data=True,
        )

        assert parent.modeling_obj.sub_group_counts[child.modeling_obj].value.magnitude == 2
        assert parent.modeling_obj.edge_device_counts[device.modeling_obj].value.magnitude == 3

    def test_edit_rejects_unknown_ids_in_explainable_object_dicts(self, minimal_model_web):
        parent = minimal_model_web.add_new_efootprint_object_to_system(
            create_efootprint_obj_from_parsed_data({"name": "Parent"}, minimal_model_web, "EdgeDeviceGroup")
        )

        with pytest.raises(ValueError, match="Unknown modeling object id 'missing-id'"):
            edit_object_from_parsed_data(
                {
                    "sub_group_counts": {
                        "missing-id": {"value": 1, "unit": "dimensionless", "label": "no label"}
                    }
                },
                parent,
            )


class TestApplyMetadata:
    """Tests for _apply_metadata helper and its integration into create/edit paths."""

    def _make_explainable_obj(self, value="test"):
        from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
        obj = ExplainableObject(value, label="test label")
        return obj

    # --- _apply_metadata unit tests ---

    def test_sets_source_from_available_sources_by_id(self, minimal_model_web):
        obj = self._make_explainable_obj()
        sentinel = Sources.USER_DATA
        parsed = {"value": "x", "source": {"id": sentinel.id, "name": sentinel.name, "link": sentinel.link}}
        _apply_metadata(obj, parsed, minimal_model_web.available_sources, {})
        assert obj.source is sentinel

    def test_mints_new_source_when_id_unknown(self, minimal_model_web):
        obj = self._make_explainable_obj()
        parsed = {"value": "x", "source": {"id": "totally-unknown", "name": "Custom", "link": "https://ex.com"}}
        _apply_metadata(obj, parsed, minimal_model_web.available_sources, {})
        assert isinstance(obj.source, Source)
        assert obj.source.name == "Custom"
        assert obj.source.link == "https://ex.com"

    def test_minted_source_uses_submitted_id(self, minimal_model_web):
        """Minted Source must adopt the client-submitted id, not generate a fresh uuid."""
        obj = self._make_explainable_obj()
        parsed = {"value": "x", "source": {"id": "client-generated-abc", "name": "Custom", "link": ""}}
        _apply_metadata(obj, parsed, minimal_model_web.available_sources, {})
        assert obj.source.id == "client-generated-abc"

    def test_pending_sources_dedups_within_submission(self, minimal_model_web):
        """Two fields submitting the same unknown id resolve to the same Source instance."""
        obj1 = self._make_explainable_obj()
        obj2 = self._make_explainable_obj()
        pending = {}
        parsed = {"value": "x", "source": {"id": "shared-new-id", "name": "Shared", "link": "https://ex.com"}}
        _apply_metadata(obj1, parsed, minimal_model_web.available_sources, pending)
        _apply_metadata(obj2, parsed, minimal_model_web.available_sources, pending)
        assert obj1.source is obj2.source

    def test_mints_new_source_when_no_id_but_name_provided(self, minimal_model_web):
        obj = self._make_explainable_obj()
        parsed = {"value": "x", "source": {"id": None, "name": "Custom No Id", "link": "https://ex.com"}}
        _apply_metadata(obj, parsed, minimal_model_web.available_sources, {})
        assert isinstance(obj.source, Source)
        assert obj.source.name == "Custom No Id"
        assert obj.source.link == "https://ex.com"

    def test_defaults_to_user_data_when_no_source_in_parsed(self, minimal_model_web):
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x"}, minimal_model_web.available_sources, {})
        assert obj.source is Sources.USER_DATA

    def test_sets_confidence_from_parsed(self, minimal_model_web):
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x", "confidence": "medium"}, minimal_model_web.available_sources, {})
        assert obj.confidence == "medium"

    def test_confidence_none_when_absent(self, minimal_model_web):
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x"}, minimal_model_web.available_sources, {})
        assert obj.confidence is None

    def test_honors_explicitly_submitted_confidence_even_when_value_changed(self, minimal_model_web):
        """Client clears __confidence on value change; but if user sets it again before Save, server must honor it."""
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x", "confidence": "high"}, minimal_model_web.available_sources, {})
        assert obj.confidence == "high"

    def test_carries_comment(self, minimal_model_web):
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x", "comment": "my note", "confidence": "low"}, minimal_model_web.available_sources, {})
        assert obj.comment == "my note"
        assert obj.confidence == "low"

    def test_sets_comment_to_none_when_empty(self, minimal_model_web):
        obj = self._make_explainable_obj()
        _apply_metadata(obj, {"value": "x", "comment": ""}, minimal_model_web.available_sources, {})
        assert obj.comment is None

    # --- create path integration ---

    def test_create_applies_metadata_from_parsed_data(self, minimal_model_web):
        existing_source = minimal_model_web.available_sources[0]
        parsed = {
            "name": "Test Storage",
            "storage_capacity": {
                "value": 2.0, "unit": "TB_stored", "label": "no label",
                "confidence": "high",
                "comment": "benchmarked",
                "source": {"id": existing_source.id, "name": existing_source.name, "link": existing_source.link},
            },
        }
        new_obj = create_efootprint_obj_from_parsed_data(parsed, minimal_model_web, "Storage")
        assert new_obj.storage_capacity.confidence == "high"
        assert new_obj.storage_capacity.comment == "benchmarked"
        assert new_obj.storage_capacity.source is existing_source

    # --- edit path integration ---

    def test_edit_applies_metadata_and_source_identity(self, minimal_model_web):
        server_web = minimal_model_web.get_web_objects_from_efootprint_type("Server")[0]
        existing_source = minimal_model_web.available_sources[0]
        parsed = {
            "compute": {
                "value": str(server_web.modeling_obj.compute.magnitude),
                "unit": f"{server_web.modeling_obj.compute.value.units:~P}",
                "label": "no label",
                "confidence": "medium",
                "comment": "from audit",
                "source": {"id": existing_source.id, "name": existing_source.name, "link": existing_source.link},
            },
        }
        edit_object_from_parsed_data(parsed, server_web)
        assert server_web.modeling_obj.compute.confidence == "medium"
        assert server_web.modeling_obj.compute.comment == "from audit"
        assert server_web.modeling_obj.compute.source is existing_source

    def test_edit_clears_confidence_when_value_changes_and_no_confidence_submitted(self, minimal_model_web):
        server_web = minimal_model_web.get_web_objects_from_efootprint_type("Server")[0]
        server_web.modeling_obj.compute.confidence = "high"
        server_web.modeling_obj.compute.comment = "my note"
        parsed = {
            "compute": {
                "value": "999",
                "unit": f"{server_web.modeling_obj.compute.value.units:~P}",
                "label": "no label",
                "comment": "my note",
            },
        }
        edit_object_from_parsed_data(parsed, server_web)
        assert server_web.modeling_obj.compute.confidence is None
        assert server_web.modeling_obj.compute.comment == "my note"

    def test_edit_honors_confidence_when_value_changes_and_confidence_submitted(self, minimal_model_web):
        server_web = minimal_model_web.get_web_objects_from_efootprint_type("Server")[0]
        parsed = {
            "compute": {
                "value": "999",
                "unit": f"{server_web.modeling_obj.compute.value.units:~P}",
                "label": "no label",
                "confidence": "medium",
            },
        }
        edit_object_from_parsed_data(parsed, server_web)
        assert server_web.modeling_obj.compute.confidence == "medium"

    def test_edit_metadata_only_change_is_persisted(self, minimal_model_web):
        """Changing only confidence (no value change) should still be pushed."""
        server_web = minimal_model_web.get_web_objects_from_efootprint_type("Server")[0]
        current_magnitude = str(server_web.modeling_obj.compute.magnitude)
        current_units = f"{server_web.modeling_obj.compute.value.units:~P}"
        parsed = {
            "compute": {
                "value": current_magnitude,
                "unit": current_units,
                "label": "no label",
                "confidence": "low",
            },
        }
        edit_object_from_parsed_data(parsed, server_web)
        assert server_web.modeling_obj.compute.confidence == "low"
