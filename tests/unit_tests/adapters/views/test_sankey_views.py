"""Unit tests for sankey_views.py.

Covers:
1. sankey_form(): card_id uniqueness, chip list filtering, default pre-selections
2. sankey_diagram(): response structure, title, column header labels, parameter mapping
"""
import json
import re
from unittest.mock import MagicMock, patch

import pytest
from efootprint.core.lifecycle_phases import LifeCyclePhases

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.sankey_views import (
    _build_sankey_payload, _expand_skipped_columns, DEFAULT_ACTIVE_COLUMNS,
)
from tests.fixtures.system_builders import create_hourly_usage


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _setup_session(client, system_data: dict) -> None:
    session = client.session
    session["system_data"] = system_data
    session.save()


def _make_sankey_mock(mock_cls):
    """Configure a mocked ImpactRepartitionSankey to return minimal valid data."""
    instance = MagicMock()
    mock_cls.return_value = instance
    instance.build.return_value = None
    instance.total_system_kg = 1_000_000.0  # 1000 kg → "1 t"
    instance.node_labels = ["Test System", "Usage"]
    instance.full_node_labels = ["Test System", "Usage"]
    instance.link_sources = [0]
    instance.link_targets = [1]
    instance.link_values = [1.0]
    instance.node_total_kg = [1_000_000.0, 1_000_000.0]
    instance.aggregated_node_members = {}
    instance._node_columns = {0: 1, 1: 2}
    instance._spacer_nodes = set()
    instance._category_node_indices = set()
    instance._leaf_node_indices = set()
    instance._breakdown_node_indices = set()
    instance._compute_node_colors.return_value = ["rgba(100,100,100,0.8)", "rgba(80,120,180,0.8)"]
    instance.get_column_information.return_value = []
    instance.get_column_metadata.return_value = []
    return instance


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sankey_client(client, minimal_system_data):
    _setup_session(client, minimal_system_data)
    return client


@pytest.fixture
def default_post():
    return {
        "card_id": "1",
        "lifecycle_phase_filter": "",
        "aggregation_threshold_percent": "1.0",
        "active_columns": list(DEFAULT_ACTIVE_COLUMNS),
        "display_column_headers": "on",
        "node_label_max_length": "15",
    }


# ---------------------------------------------------------------------------
# TestSankeyForm
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSankeyForm:

    def test_returns_200(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        assert response.status_code == 200

    def test_card_id_updates_across_calls(self, sankey_client):
        r1 = sankey_client.get("/model_builder/sankey-form/")
        r2 = sankey_client.get("/model_builder/sankey-form/")
        id1 = re.search(r'name="card_id" value="([0-9a-f]{8})"', r1.content.decode()).group(1)
        id2 = re.search(r'name="card_id" value="([0-9a-f]{8})"', r2.content.decode()).group(1)
        assert id1 != id2

    def test_analyse_by_chips_show_only_columns_with_present_classes(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # Phase and Category are always present (virtual chips)
        assert "Phase" in content
        assert "Category" in content
        # Columns with at least one present class should appear
        assert "Usage patterns" in content
        assert "Usage journeys" in content

    def test_exclude_chips_show_only_present_classes(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert "EdgeDevice" not in content
        assert "EdgeStorage" not in content

    def test_exclude_chips_present_for_server_via_serverbase(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert 'data-class="ServerBase"' in content

    def test_default_active_column_has_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # "phase" is active by default
        assert 'name="active_columns" value="phase"' in content
        # Column 3 (Usage journeys) is active by default
        assert 'name="active_columns" value="3"' in content

    def test_non_default_active_column_has_no_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # Column 2 (Usage patterns) is NOT active by default
        assert 'name="active_columns" value="2"' not in content

    def test_analyse_by_chips_use_chip_id_as_data_class(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert 'data-class="phase"' in content
        assert 'data-class="category"' in content
        assert 'data-class="3"' in content

    def test_form_contains_card_id_input(self, sankey_client):
        r = sankey_client.get("/model_builder/sankey-form/")
        assert 'name="card_id"' in r.content.decode()


@pytest.mark.django_db
class TestSankeyCards:

    def test_returns_default_card_when_no_saved_cards(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-cards/")
        assert response.status_code == 200
        assert response.content.decode().count('class="sankey-card"') == 1

    def test_restores_saved_cards_with_saved_settings(self, client, minimal_system_data):
        system_data = {
            **minimal_system_data,
            "interface_config": {
                "sankey_diagrams": [{
                    "id": "deadbeef",
                    "lifecycle_phase_filter": "Manufacturing",
                    "aggregation_threshold_percent": 2.5,
                    "active_columns": ["phase", "category", "3"],
                    "excluded_types": ["Device"],
                    "display_column_headers": False,
                    "node_label_max_length": 31,
                }]
            },
        }
        _setup_session(client, system_data)

        response = client.get("/model_builder/sankey-cards/")
        content = response.content.decode()

        assert 'value="deadbeef"' in content
        assert 'option value="Manufacturing" selected' in content
        assert 'name="aggregation_threshold_percent" min="0" max="10" step="0.5" value="2.5"' in content
        assert 'name="node_label_max_length" value="31"' in content
        assert 'name="excluded_types" value="Device"' in content

    def test_delete_endpoint_removes_saved_card(self, client, minimal_system_data):
        system_data = {
            **minimal_system_data,
            "interface_config": {
                "sankey_diagrams": [
                    {"id": "deadbeef", "active_columns": ["phase"], "excluded_types": []},
                    {"id": "cafebabe", "active_columns": ["phase"], "excluded_types": []},
                ]
            },
        }
        _setup_session(client, system_data)

        response = client.post("/model_builder/sankey-delete-card/", {"card_id": "deadbeef"})

        assert response.status_code == 200
        repository = SessionSystemRepository(client.session)
        saved_data = repository.get_system_data()
        assert saved_data["interface_config"]["sankey_diagrams"] == [
            {"id": "cafebabe", "active_columns": ["phase"], "excluded_types": []}
        ]


# ---------------------------------------------------------------------------
# TestSankeyDiagram — response structure
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSankeyDiagramStructure:

    def test_returns_200(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert response.status_code == 200

    def test_diagram_area_id_matches_card_id(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert 'id="sankey-diagram-area-1"' in response.content.decode()

    def test_sankey_payload_present_in_data_attribute(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert "data-sankey=" in response.content.decode()

    def test_title_contains_system_name(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert "Test System" in response.content.decode()

    def test_title_contains_co2_unit(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        content = response.content.decode()
        assert "CO" in content  # CO₂eq or CO2eq

    def test_column_headers_absent_without_flag(self, sankey_client, default_post):
        data = {k: v for k, v in default_post.items() if k != "display_column_headers"}
        response = sankey_client.post("/model_builder/sankey-diagram/", data)
        assert "column-header-tag" not in response.content.decode()

    def test_column_headers_present_with_flag(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        content = response.content.decode()
        # With column headers on, we should see column header tags if there are columns
        assert "sankey-plot-1" in content

    def test_raw_class_names_not_in_column_headers(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        content = response.content.decode()
        # The column header area should use UI labels, not raw efootprint class names
        assert "ServerBase" not in content

    def test_manufacturing_subtitle_when_filter_manufacturing(self, sankey_client, default_post):
        data = {**default_post, "lifecycle_phase_filter": "Manufacturing"}
        response = sankey_client.post("/model_builder/sankey-diagram/", data)
        assert "Manufacturing only" in response.content.decode()

    def test_all_phases_subtitle_when_no_filter(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert "All phases" in response.content.decode()

    def test_different_card_id_in_response(self, sankey_client, default_post):
        data = {**default_post, "card_id": "42"}
        response = sankey_client.post("/model_builder/sankey-diagram/", data)
        assert 'id="sankey-diagram-area-42"' in response.content.decode()

    def test_diagram_persists_card_settings(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)

        assert response.status_code == 200
        repository = SessionSystemRepository(sankey_client.session)
        saved_data = repository.get_system_data()
        assert saved_data["interface_config"]["sankey_diagrams"] == [{
            "id": "1",
            "lifecycle_phase_filter": "",
            "aggregation_threshold_percent": 1.0,
            "active_columns": sorted(DEFAULT_ACTIVE_COLUMNS),
            "excluded_types": [],
            "display_column_headers": True,
            "node_label_max_length": 15,
        }]

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_column_headers_use_same_dynamic_padding_as_chart(self, mock_cls, sankey_client, default_post):
        instance = _make_sankey_mock(mock_cls)
        instance.node_labels = ["System", "Very long rightmost equipment label for alignment"]
        instance.full_node_labels = instance.node_labels
        instance.get_column_information.return_value = [{
            "column_index": 1,
            "column_type": "manual_split",
            "description": "Lifecycle phase",
            "class_names": [],
            "x_left": 0.5,
        }]
        instance.get_column_header_x_shift_px.return_value = -10

        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        content = response.content.decode()

        assert "padding-left: 30px;" in content
        assert "padding-right: 260px;" in content
        assert "100% - 290px" in content
        assert "+ -10px" in content


# ---------------------------------------------------------------------------
# TestSankeyDiagramParameterMapping — patches ImpactRepartitionSankey constructor
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSankeyDiagramParameterMapping:

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_lifecycle_filter_none_when_all_phases(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", {**default_post, "lifecycle_phase_filter": ""})
        assert mock_cls.call_args.kwargs["lifecycle_phase_filter"] is None

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_lifecycle_filter_manufacturing(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", {**default_post, "lifecycle_phase_filter": "Manufacturing"})
        assert mock_cls.call_args.kwargs["lifecycle_phase_filter"] == LifeCyclePhases.MANUFACTURING

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_lifecycle_filter_usage(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", {**default_post, "lifecycle_phase_filter": "Usage"})
        assert mock_cls.call_args.kwargs["lifecycle_phase_filter"] == LifeCyclePhases.USAGE

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_phase_true_when_phase_not_in_active_columns(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "active_columns": ["1", "3", "4", "category", "7"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skip_phase_footprint_split"] is True

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_phase_false_when_phase_in_active_columns(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["skip_phase_footprint_split"] is False

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_category_true_when_category_not_in_active_columns(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "active_columns": ["phase", "1", "3", "4", "7"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skip_object_category_footprint_split"] is True

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_object_false_when_hardware_active(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["skip_object_footprint_split"] is False

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_object_true_when_hardware_and_component_breakdown_inactive(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "active_columns": [c for c in default_post["active_columns"] if c not in ["7", "8"]]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skip_object_footprint_split"] is True

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_aggregation_threshold_passed_as_float(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", {**default_post, "aggregation_threshold_percent": "3.5"})
        assert mock_cls.call_args.kwargs["aggregation_threshold_percent"] == pytest.approx(3.5)

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_excluded_types_passed_from_chips(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "excluded_types": ["Device", "Network"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["excluded_object_types"] == ["Device", "Network"]

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_inactive_columns_expanded_to_skipped_classes(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        # Default active_columns excludes columns 2, 5, 6 — those should be skipped
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        skipped = mock_cls.call_args.kwargs["skipped_impact_repartition_classes"]
        assert "UsagePattern" in skipped
        assert "EdgeUsagePattern" in skipped
        assert "RecurrentEdgeDeviceNeed" in skipped
        assert "JobBase" in skipped

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_display_column_information_always_false(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["display_column_information"] is False

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_node_label_max_length_passed(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", {**default_post, "node_label_max_length": "20"})
        assert mock_cls.call_args.kwargs["node_label_max_length"] == 20

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_excluded_types_none_when_empty(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["excluded_object_types"] is None

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skipped_classes_none_when_all_columns_active(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "active_columns": ["phase", "1", "2", "3", "4", "5", "6", "category", "7", "8"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skipped_impact_repartition_classes"] is None


class TestBuildSankeyPayload:

    def test_layout_padding_added_to_payload(self):
        sankey = MagicMock()
        sankey.build.return_value = None
        sankey.node_labels = ["Root", "Very long rightmost equipment label for layout"]
        sankey.full_node_labels = sankey.node_labels
        sankey.link_sources = [0]
        sankey.link_targets = [1]
        sankey.link_values = [1.0]
        sankey.node_total_kg = [1000.0, 1000.0]
        sankey.total_system_kg = 1000.0
        sankey.aggregated_node_members = {}
        sankey._node_columns = {0: 1, 1: 2}
        sankey._spacer_nodes = set()
        sankey._category_node_indices = set()
        sankey._leaf_node_indices = set()
        sankey._breakdown_node_indices = set()
        sankey._compute_node_colors.return_value = [
            "rgba(100,100,100,0.8)",
            "rgba(80,120,180,0.8)",
        ]

        payload, _ = _build_sankey_payload(sankey)

        assert payload["layout"] == {
            "left_padding_px": 30,
            "right_padding_px": 260,
            "horizontal_padding_px": 290,
        }

    def test_spacer_links_are_not_double_counted(self):
        sankey = MagicMock()
        sankey.build.return_value = None
        sankey.node_labels = ["Root", "", "Leaf"]
        sankey.full_node_labels = ["Root", "", "Leaf"]
        sankey.link_sources = [0, 1]
        sankey.link_targets = [1, 2]
        sankey.link_values = [1.0, 1.0]
        sankey.node_total_kg = [1000.0, 1000.0, 1000.0]
        sankey.total_system_kg = 1000.0
        sankey.aggregated_node_members = {}
        sankey._node_columns = {0: 1, 1: 2, 2: 3}
        sankey._spacer_nodes = {1}
        sankey._category_node_indices = set()
        sankey._leaf_node_indices = set()
        sankey._breakdown_node_indices = set()
        sankey._compute_node_colors.return_value = [
            "rgba(100,100,100,0.8)",
            "rgba(100,100,100,0.3)",
            "rgba(80,120,180,0.8)",
        ]

        payload, _ = _build_sankey_payload(sankey)

        assert payload["links"] == [{
            "source_key": "node-0",
            "target_key": "node-2",
            "source_name_key": "Root⁣0",
            "target_name_key": "Leaf⁣2",
            "value": 1.0,
            "value_kg": 1000.0,
            "color": "rgba(100,100,100,0.35)",
            "tooltip_html": "Root → Leaf<br>1.0 tonnes CO2eq (100.0%)",
        }]

    def test_category_nodes_use_object_category_ui_labels(self):
        sankey = MagicMock()
        sankey.build.return_value = None
        sankey.node_labels = ["EdgeDevices Usage", "Leaf"]
        sankey.full_node_labels = ["EdgeDevices Usage", "Leaf"]
        sankey.link_sources = [0]
        sankey.link_targets = [1]
        sankey.link_values = [1.0]
        sankey.node_total_kg = [1000.0, 1000.0]
        sankey.total_system_kg = 1000.0
        sankey.aggregated_node_members = {}
        sankey._node_columns = {0: 1, 1: 2}
        sankey._spacer_nodes = set()
        sankey._category_node_indices = {0}
        sankey._leaf_node_indices = {1}
        sankey._breakdown_node_indices = set()
        sankey._compute_node_colors.return_value = [
            "rgba(100,100,100,0.8)",
            "rgba(80,120,180,0.8)",
        ]

        payload, _ = _build_sankey_payload(sankey)

        assert payload["nodes"][0]["label"] == "Edge devices Usage"
        assert payload["nodes"][0]["full_name"] == "Edge devices Usage"
        assert payload["nodes"][0]["tooltip_html"] == "Edge devices Usage<br>1.0 tonnes CO2eq (100.0%)"
        assert payload["links"][0]["source_name_key"] == "Edge devices Usage⁣0"
        assert payload["links"][0]["tooltip_html"] == "Edge devices Usage → Leaf<br>1.0 tonnes CO2eq (100.0%)"


class TestSankeyColumnsGuard:
    """Guard test: if SANKEY_COLUMNS changes in e-footprint, this test fails and must be manually revalidated."""

    def test_sankey_columns_match_expected_structure(self):
        from efootprint.all_classes_in_order import SANKEY_COLUMNS

        actual = [[cls.__name__ for cls in col] for col in SANKEY_COLUMNS]
        expected = [
            ["System"],
            ["Country"],
            ["UsagePattern", "EdgeUsagePattern"],
            ["UsageJourney", "EdgeUsageJourney"],
            ["EdgeFunction", "UsageJourneyStep"],
            ["RecurrentEdgeDeviceNeed", "RecurrentServerNeed"],
            ["JobBase", "RecurrentEdgeComponentNeed"],
            ["Device", "EdgeDevice", "Network", "ExternalAPI", "ServerBase", "ExternalAPIServer", "Storage"],
        ]
        assert actual == expected, (
            "SANKEY_COLUMNS in e-footprint has changed. Update SANKEY_COLUMN_NAMES and "
            "SKIPPABLE_COLUMN_INDICES in sankey_views.py, then update this test."
        )

    def test_sankey_breakdown_only_classes_match_expected(self):
        from efootprint.all_classes_in_order import SANKEY_BREAKDOWN_ONLY_CLASSES

        actual = [cls.__name__ for cls in SANKEY_BREAKDOWN_ONLY_CLASSES]
        assert actual == ["EdgeComponent"], (
            "SANKEY_BREAKDOWN_ONLY_CLASSES in e-footprint has changed. Update SANKEY_COLUMN_NAMES "
            "and _BREAKDOWN_COLUMN_INDEX in sankey_views.py, then update this test."
        )


class TestExpandSkippedColumns:

    def test_expand_single_column(self):
        result = _expand_skipped_columns(["2"])
        assert "UsagePattern" in result
        assert "EdgeUsagePattern" in result

    def test_expand_multiple_columns(self):
        result = _expand_skipped_columns(["1", "6"])
        assert "Country" in result
        assert "JobBase" in result
        assert "RecurrentEdgeComponentNeed" in result

    def test_expand_breakdown_column(self):
        result = _expand_skipped_columns(["8"])
        assert "EdgeComponent" in result

    def test_expand_empty_returns_empty(self):
        assert _expand_skipped_columns([]) == []
