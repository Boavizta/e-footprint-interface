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

from model_builder.adapters.views.sankey_views import _build_sankey_payload, _expand_skipped_columns
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
        "phase_split": "on",
        "category_split": "on",
        "object_split": "on",
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

    def test_card_id_increments_across_calls(self, sankey_client):
        r1 = sankey_client.get("/model_builder/sankey-form/")
        r2 = sankey_client.get("/model_builder/sankey-form/")
        id1 = re.search(r'name="card_id" value="(\d+)"', r1.content.decode()).group(1)
        id2 = re.search(r'name="card_id" value="(\d+)"', r2.content.decode()).group(1)
        assert id1 != id2

    def test_skip_column_chips_show_only_columns_with_present_classes(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # minimal_system has no edge objects — columns containing only edge classes should not appear
        # But columns with mixed classes (e.g. column 2 = UsagePattern + EdgeUsagePattern) should appear
        # if at least one class is present
        assert "Usage patterns" in content
        assert "Usage journeys" in content

    def test_exclude_chips_show_only_present_classes(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # EdgeDevice and EdgeStorage not in minimal_system
        assert "EdgeDevice" not in content
        assert "EdgeStorage" not in content

    def test_exclude_chips_present_for_server_via_serverbase(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # ServerBase chip should appear because Server (subclass) is in system
        assert 'data-class="ServerBase"' in content

    def test_default_skipped_column_has_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # Column 2 (Usage patterns) is a default skipped column
        assert 'name="skipped_columns" value="2"' in content

    def test_non_default_skipped_column_has_no_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # Column 3 (Usage journeys) is not a default skipped column
        assert 'name="skipped_columns" value="3"' not in content

    def test_skip_column_chips_use_column_index_as_data_class(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert 'data-class="2"' in content  # Usage patterns column

    def test_form_contains_card_id_input(self, sankey_client):
        r = sankey_client.get("/model_builder/sankey-form/")
        assert 'name="card_id"' in r.content.decode()


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
            "x_center": 0.5,
        }]

        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        content = response.content.decode()

        assert "padding-left: 30px;" in content
        assert "padding-right: 260px;" in content
        assert "100% - 290px" in content


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
    def test_skip_phase_true_when_checkbox_absent(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {k: v for k, v in default_post.items() if k != "phase_split"}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skip_phase_footprint_split"] is True

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_phase_false_when_checkbox_present(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["skip_phase_footprint_split"] is False

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_category_true_when_checkbox_absent(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {k: v for k, v in default_post.items() if k != "category_split"}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skip_object_category_footprint_split"] is True

    @patch("model_builder.adapters.views.sankey_views.ImpactRepartitionSankey")
    def test_skip_object_false_when_checkbox_present(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert mock_cls.call_args.kwargs["skip_object_footprint_split"] is False

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
    def test_skipped_columns_expanded_to_classes(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "skipped_columns": ["2", "6"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        skipped = mock_cls.call_args.kwargs["skipped_impact_repartition_classes"]
        assert "UsagePattern" in skipped
        assert "EdgeUsagePattern" in skipped
        assert "JobBase" in skipped
        assert "RecurrentEdgeComponentNeed" in skipped

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
    def test_skipped_classes_none_when_no_columns(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {k: v for k, v in default_post.items() if k not in ("skipped_columns",)}
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
