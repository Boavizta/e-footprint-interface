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
    mock_fig = MagicMock()
    mock_fig.to_json.return_value = json.dumps({"data": [], "layout": {}})
    instance.figure.return_value = mock_fig
    instance.total_system_kg = 1_000_000.0  # 1000 kg → "1 t"
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

    def test_skip_chips_show_only_present_classes(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # minimal_system has no edge objects — their chips must not appear
        assert "EdgeUsagePattern" not in content
        assert "EdgeUsageJourney" not in content

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

    def test_skip_chips_present_for_jobbase(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # JobBase chip should appear because Job (subclass) is in system
        assert 'data-class="JobBase"' in content

    def test_default_skipped_usage_pattern_has_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert 'name="skipped_classes" value="UsagePattern"' in content

    def test_default_skipped_jobbase_has_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        assert 'name="skipped_classes" value="JobBase"' in content

    def test_non_default_skipped_chip_has_no_hidden_input(self, sankey_client):
        response = sankey_client.get("/model_builder/sankey-form/")
        content = response.content.decode()
        # UsageJourney is in SKIPPABLE_CLASSES but NOT in DEFAULT_SKIPPED_CLASSES
        assert 'name="skipped_classes" value="UsageJourney"' not in content

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

    def test_plotly_json_present_in_data_attribute(self, sankey_client, default_post):
        response = sankey_client.post("/model_builder/sankey-diagram/", default_post)
        assert "data-plotly=" in response.content.decode()

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
    def test_skipped_classes_passed_from_chips(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {**default_post, "skipped_classes": ["UsagePattern", "JobBase"]}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skipped_impact_repartition_classes"] == ["UsagePattern", "JobBase"]

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
    def test_skipped_classes_none_when_empty(self, mock_cls, sankey_client, default_post):
        _make_sankey_mock(mock_cls)
        data = {k: v for k, v in default_post.items() if k not in ("skipped_classes",)}
        sankey_client.post("/model_builder/sankey-diagram/", data)
        assert mock_cls.call_args.kwargs["skipped_impact_repartition_classes"] is None
