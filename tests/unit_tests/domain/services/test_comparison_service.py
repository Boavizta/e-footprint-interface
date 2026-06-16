"""Unit tests for the ComparisonService dashboard adapter (model-comparison Task 4).

The library ``SystemComparison`` is the domain truth; these tests pin the *shaping* this thin adapter
does on top of it. We feed a hand-built comparison stub with the exact attribute shape the library
exposes (totals, per-(category, phase) decomposition, an aligned hourly time-series, the input diff)
so the assertions are about the view model — not about recomputing footprints.

The load-bearing invariants checked here: the decomposition bars sum to the headline Δ, the KPI cards'
usage+fabrication split each total their model, the paired/cumulative chart payloads carry one shared
unit and the constant model-identity colour pair (magnitude honesty), and the diff shows only
differences, id-first.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from model_builder.domain.services.comparison_service import (
    ComparisonService, MODEL_A_COLOR, MODEL_A_COLOR_LIGHT, MODEL_B_COLOR, MODEL_B_COLOR_LIGHT)


def _delta(before, after):
    absolute = after - before
    relative = None if before == 0 else absolute / before
    return SimpleNamespace(before=before, after=after, absolute=absolute, relative=relative)


def _row(category, phase, before, after):
    return SimpleNamespace(category=category, phase=phase, delta=_delta(before, after))


def _system(name, total, n_hours, start):
    """A System stub exposing ``name`` and the model's own (unaligned) ``total_footprint`` axis.

    The adapter reads ``total_footprint.start_date`` + length to learn the model's calendar coverage
    (so it can blank years the model does not cover); the values themselves sum to the model's total.
    """
    footprint = SimpleNamespace(start_date=start, value=_hourly_summing_to(total, n_hours))
    return SimpleNamespace(name=name, total_footprint=footprint)


def _hourly_summing_to(total, n_hours):
    """An n-hour series whose values sum to ``total`` — mirrors the library guarantee that the hourly
    footprint integrates to the period total (so the cumulative curve ends at it)."""
    if n_hours == 0:
        return np.zeros(0, dtype="float32")
    return np.full(n_hours, total / n_hours, dtype="float32")


def build_comparison(*, hours_a=None, hours_b=None, start_a=None, start_b=None,
                     changed=(), only_in_a=(), only_in_b=()):
    """A SystemComparison stub with the same attribute surface as the library object.

    ``decomposition`` is a fixed, deliberately mixed set of (category, phase) rows: a reduction in
    servers usage, an increase in edge fabrication, several unchanged rows, so the sum is a non-trivial
    Δ. The hourly time-series is *derived from* the decomposition totals (spread over the requested
    span), reproducing the library's own consistency between the per-category totals and the hourly
    series — so the cumulative curve ends at each model's total, as in production.
    """
    start_a = start_a or datetime(2025, 1, 1, tzinfo=timezone.utc)
    start_b = start_b or datetime(2025, 1, 1, tzinfo=timezone.utc)

    decomposition = [
        _row("Servers", "energy", before=1590.0, after=930.0),       # −660 reduction
        _row("Storage", "energy", before=0.0, after=0.0),            # unchanged
        _row("Servers", "fabrication", before=540.0, after=240.0),   # −300 reduction
        _row("Storage", "fabrication", before=10.0, after=10.0),     # unchanged
        _row("Network", "energy", before=330.0, after=90.0),         # −240 reduction
        _row("Network", "fabrication", before=0.0, after=0.0),
        _row("Devices", "energy", before=400.0, after=400.0),        # unchanged
        _row("Devices", "fabrication", before=1000.0, after=1000.0), # unchanged
        _row("ExternalAPIs", "energy", before=0.0, after=0.0),
        _row("ExternalAPIs", "fabrication", before=0.0, after=0.0),
        _row("EdgeDevices", "energy", before=0.0, after=0.0),
        _row("EdgeDevices", "fabrication", before=0.0, after=90.0),  # +90 increase, new in B
    ]
    total_a = sum(row.delta.before for row in decomposition)
    total_b = sum(row.delta.after for row in decomposition)

    # Each model's own (unaligned) span; default a single 24h day for both.
    n_a = hours_a if hours_a is not None else 24
    n_b = hours_b if hours_b is not None else 24

    # The library aligns both onto one calendar axis starting at the earliest start, zero-padding the
    # gaps — reproduce that so the shared time-series is realistic.
    axis_start = min(start_a, start_b)
    offset_a = int((start_a - axis_start).total_seconds() // 3600)
    offset_b = int((start_b - axis_start).total_seconds() // 3600)
    length = max(offset_a + n_a, offset_b + n_b)
    series_a = np.zeros(length, dtype="float32")
    series_b = np.zeros(length, dtype="float32")
    series_a[offset_a:offset_a + n_a] = _hourly_summing_to(total_a, n_a)
    series_b[offset_b:offset_b + n_b] = _hourly_summing_to(total_b, n_b)
    time_series = SimpleNamespace(start_date=axis_start, values_a=series_a, values_b=series_b)

    input_diff = SimpleNamespace(
        changed=[SimpleNamespace(
            object_class=c["object_class"], attribute=c["attribute"],
            value_a=c["value_a"], value_b=c["value_b"],
            object_name_a=c.get("object_name_a", ""), object_name_b=c.get("object_name_b", ""),
            source_a=None, source_b=None, confidence_a=None, confidence_b=None) for c in changed],
        only_in_a=[SimpleNamespace(object_class=o["object_class"], object_name=o["object_name"],
                                   object_id=o.get("object_id", "")) for o in only_in_a],
        only_in_b=[SimpleNamespace(object_class=o["object_class"], object_name=o["object_name"],
                                   object_id=o.get("object_id", "")) for o in only_in_b])

    return SimpleNamespace(
        system_a=_system("Streaming app", total_a, n_a, start_a),
        system_b=_system("Streaming app — edge caching", total_b, n_b, start_b),
        total_a=total_a, total_b=total_b,
        total_delta=_delta(total_a, total_b),
        decomposition=decomposition,
        time_series=time_series,
        input_diff=input_diff)


@pytest.fixture
def view():
    comparison = build_comparison(
        changed=[{"object_class": "Job", "attribute": "data_transferred",
                  "value_a": "800 megabyte", "value_b": "250 megabyte"}],
        only_in_b=[{"object_class": "EdgeDevice", "object_name": "Edge cache node"}])
    return ComparisonService().build_from_comparison(comparison)


class TestKpiStrip:
    def test_cards_carry_each_model_name_total_and_period(self, view):
        assert view.card_a.name == "Streaming app"
        assert view.card_b.name == "Streaming app — edge caching"
        assert view.card_a.total_kg == pytest.approx(540 + 10 + 1590 + 330 + 400 + 1000)
        assert view.card_a.period_label == "2025"

    def test_card_usage_plus_fabrication_equals_total(self, view):
        assert view.card_a.usage_kg + view.card_a.fabrication_kg == pytest.approx(view.card_a.total_kg)
        assert view.card_b.usage_kg + view.card_b.fabrication_kg == pytest.approx(view.card_b.total_kg)

    def test_delta_is_b_minus_a_with_relative_and_phase_split(self, view):
        assert view.delta.absolute_kg == pytest.approx(view.card_b.total_kg - view.card_a.total_kg)
        assert view.delta.relative == pytest.approx(view.delta.absolute_kg / view.card_a.total_kg)
        assert view.delta.usage_kg + view.delta.fabrication_kg == pytest.approx(view.delta.absolute_kg)


class TestDecomposition:
    def test_bars_sum_to_the_headline_delta(self, view):
        """The hard requirement: the diverging bars sum to the headline Δ (zero-delta rows dropped)."""
        assert sum(bar.delta_kg for bar in view.decomposition) == pytest.approx(view.delta.absolute_kg)

    def test_drops_unchanged_rows_and_merges_servers_and_storage(self, view):
        labels = [bar.label for bar in view.decomposition]
        # Servers + Storage usage are merged under one display label; unchanged rows are absent.
        assert "Servers & storage usage" in labels
        assert "Servers & storage fabrication" in labels
        assert "Network usage" in labels
        assert "Edge devices fabrication" in labels
        assert "User devices usage" not in labels  # unchanged → not a bar

    def test_servers_and_storage_usage_bar_sums_its_member_categories(self, view):
        bar = next(b for b in view.decomposition if b.label == "Servers & storage usage")
        assert bar.delta_kg == pytest.approx(930.0 - 1590.0)  # Servers usage moved, Storage usage flat


class TestPairedChart:
    def test_four_series_two_per_model_on_a_shared_axis(self, view):
        datasets = view.paired_chart["datasets"]
        assert len(datasets) == 4
        assert [d["stack"] for d in datasets] == ["A", "A", "B", "B"]

    def test_model_identity_is_the_constant_colour_pair(self, view):
        datasets = view.paired_chart["datasets"]
        assert datasets[0]["backgroundColor"] == MODEL_A_COLOR        # A usage
        assert datasets[1]["backgroundColor"] == MODEL_A_COLOR_LIGHT  # A fabrication
        assert datasets[2]["backgroundColor"] == MODEL_B_COLOR        # B usage
        assert datasets[3]["backgroundColor"] == MODEL_B_COLOR_LIGHT  # B fabrication

    def test_per_year_stacked_total_reconstructs_each_model_total(self, view):
        datasets = view.paired_chart["datasets"]
        a_total = sum((datasets[0]["data"][i] or 0) + (datasets[1]["data"][i] or 0)
                      for i in range(len(view.paired_chart["labels"])))
        assert a_total == pytest.approx(view.card_a.total_kg)

    def test_non_overlapping_years_are_blank_not_zero(self):
        """Model A covers into 2026; B stays in 2025 — the 2026 bucket must be null for B (§6)."""
        comparison = build_comparison(
            hours_a=24 * 400,                   # ~13 months from 2025-01-01 → spans 2025 + 2026
            hours_b=24 * 30,                    # ~1 month → 2025 only
            start_a=datetime(2025, 1, 1, tzinfo=timezone.utc),
            start_b=datetime(2025, 1, 1, tzinfo=timezone.utc))
        view = ComparisonService().build_from_comparison(comparison)
        labels = view.paired_chart["labels"]
        b_usage = view.paired_chart["datasets"][2]["data"]
        a_usage = view.paired_chart["datasets"][0]["data"]
        assert "2026" in labels
        # The 2026 bucket has no B data (B is one month in 2025) → blank, not a zero bar.
        assert b_usage[labels.index("2026")] is None
        # A does cover 2026, so its 2026 bucket is a real (possibly zero) value, not null.
        assert a_usage[labels.index("2026")] is not None


class TestCumulativeChart:
    def test_two_curves_end_at_each_model_total_on_a_shared_axis(self, view):
        datasets = view.cumulative_chart["datasets"]
        assert len(datasets) == 2
        assert datasets[0]["data"][-1] == pytest.approx(view.card_a.total_kg)
        assert datasets[1]["data"][-1] == pytest.approx(view.card_b.total_kg)

    def test_curves_carry_the_model_identity_colours(self, view):
        datasets = view.cumulative_chart["datasets"]
        assert datasets[0]["borderColor"] == MODEL_A_COLOR
        assert datasets[1]["borderColor"] == MODEL_B_COLOR


class TestAssumptionsDiff:
    def test_changed_rows_show_both_values_only(self, view):
        assert len(view.diff_changed) == 1
        row = view.diff_changed[0]
        assert row.object_label == "Job"
        assert row.attribute == "data_transferred"
        assert (row.value_a, row.value_b) == ("800 megabyte", "250 megabyte")

    def test_only_in_b_objects_are_listed_with_label(self, view):
        assert view.diff_only_in_a == []
        assert len(view.diff_only_in_b) == 1
        assert view.diff_only_in_b[0].object_label == "Edge cache node (EdgeDevice)"

    def test_identical_inputs_produce_no_rows(self):
        view = ComparisonService().build_from_comparison(build_comparison())
        assert view.diff_changed == []
        assert view.diff_only_in_a == []
        assert view.diff_only_in_b == []
