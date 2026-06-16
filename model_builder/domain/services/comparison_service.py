"""Thin adapter shaping the library ``SystemComparison`` for the comparison dashboard.

The comparison *computation* is the library's domain truth (constitution §1.3): this service calls
``system_a.compare_to(system_b)`` and re-implements **rendering only** — it shapes the resulting
``SystemComparison`` into the view model the dashboard template needs: the KPI-strip values, the
Chart.js JSON for the three §4.2 chart variants (paired bars, cumulative overlay, diverging
decomposition), and the assumptions-diff table rows. No modeling logic, no attribution claims, no
Django imports — it lives in ``domain/`` and stays usable from a plain ``System`` pair.

Magnitude honesty (§4.3) is enforced here, not in styling: the paired bars and the cumulative overlay
each carry a single shared y-axis unit and one legend for both models; model identity is a constant
colour pair. The decomposition is grouped to the §4.2 display categories (Servers + Storage merged)
but only by relabelling — every per-(category, phase) delta still appears exactly once, so the bars
sum to the headline Δ by construction (the library guarantees the underlying rows do).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# Constant model-identity colours, shared across every chart (the KPI cards' left border, both chart
# series, the cumulative curves). Model A is the cool blue, model B the warm amber — the same pairing
# the §4.2 mockup uses. Usage is the saturated tone, fabrication the lighter tint of the same hue, so
# one capsule legend (Usage / Fabrication × A / B) reads across both models.
MODEL_A_COLOR = "#4878a8"
MODEL_A_COLOR_LIGHT = "#9db9d8"
MODEL_B_COLOR = "#e09f3e"
MODEL_B_COLOR_LIGHT = "#f0cf94"

LOWER_COLOR = "#2e7d32"   # B emits less than A (a reduction) — green
HIGHER_COLOR = "#c62828"  # B emits more than A (an increase) — red

# The §4.2 decomposition collapses the six library hardware categories to the four display rows of the
# mockup, merging Servers + Storage into one "Servers & storage" line. Relabelling only — the
# underlying per-(category, phase) deltas are summed per display group, so the bars still total Δ.
DISPLAY_CATEGORY_LABELS = {
    "Servers": "Servers & storage",
    "Storage": "Servers & storage",
    "ExternalAPIs": "External APIs",
    "Network": "Network",
    "Devices": "User devices",
    "EdgeDevices": "Edge devices",
}
# Display order for the decomposition rows (largest, most-expected movers first).
DISPLAY_CATEGORY_ORDER = ["Servers & storage", "External APIs", "Network", "Edge devices", "User devices"]
PHASE_LABELS = {"energy": "usage", "fabrication": "fabrication"}


@dataclass
class KpiCard:
    """One model's headline figures for the KPI strip (``*_display`` are pre-formatted strings)."""
    name: str
    total_kg: float
    usage_kg: float
    fabrication_kg: float
    period_label: str
    total_display: str = ""
    usage_display: str = ""
    fabrication_display: str = ""


@dataclass
class KpiDelta:
    """The headline difference card (second model minus first)."""
    absolute_kg: float
    relative: Optional[float]
    usage_kg: float
    fabrication_kg: float
    absolute_display: str = ""
    relative_display: str = ""
    usage_display: str = ""
    fabrication_display: str = ""
    # "lower" when B emits less than A (a reduction, green), "higher" otherwise (red), "" when equal.
    direction: str = ""


@dataclass
class DecompositionBar:
    """One diverging bar of the "what explains the difference" chart."""
    label: str
    delta_kg: float
    delta_display: str = ""
    # "lower" (B reduces this category, green) or "higher" (B increases it, red).
    direction: str = ""


@dataclass
class DiffRow:
    """A changed input attribute between the paired objects."""
    object_label: str
    attribute: str
    value_a: Optional[str]
    value_b: Optional[str]


@dataclass
class DiffUnmatched:
    """An object present in only one model."""
    object_label: str


@dataclass
class ComparisonView:
    """The full view model the §4.2 dashboard renders."""
    card_a: KpiCard
    card_b: KpiCard
    delta: KpiDelta
    decomposition: List[DecompositionBar]
    decomposition_chart: Dict
    paired_chart: Dict
    cumulative_chart: Dict
    diff_changed: List[DiffRow]
    diff_only_in_a: List[DiffUnmatched]
    diff_only_in_b: List[DiffUnmatched]
    colors: Dict[str, str] = field(default_factory=lambda: {
        "model_a": MODEL_A_COLOR, "model_b": MODEL_B_COLOR,
        "lower": LOWER_COLOR, "higher": HIGHER_COLOR})


class ComparisonService:
    """Shapes a library ``SystemComparison`` into the dashboard view model. Stateless."""

    def build(self, model_a, model_b) -> ComparisonView:
        """Compare two ``ModelWeb``s and return the dashboard view model.

        ``model_a``/``model_b`` are interface ``ModelWeb`` wrappers; the comparison runs against their
        underlying library ``System``s (``.system.modeling_obj``), keeping the computation in the
        library and this service a pure shaper.
        """
        system_a = model_a.system.modeling_obj
        system_b = model_b.system.modeling_obj
        comparison = system_a.compare_to(system_b)
        return self.build_from_comparison(comparison)

    def build_from_comparison(self, comparison) -> ComparisonView:
        """Shape an already-computed ``SystemComparison`` (the unit-testable seam)."""
        card_a = self._kpi_card(comparison.system_a, comparison.total_a, comparison.decomposition, is_model_a=True)
        card_b = self._kpi_card(comparison.system_b, comparison.total_b, comparison.decomposition, is_model_a=False)
        delta = self._kpi_delta(comparison)
        decomposition = self._decomposition_bars(comparison.decomposition)
        paired_chart = self._paired_chart(comparison)
        cumulative_chart = self._cumulative_chart(comparison)
        diff_changed, diff_only_a, diff_only_b = self._diff(comparison.input_diff)
        # One shared display unit across the whole KPI strip + decomposition, so the magnitudes read
        # against each other (magnitude honesty) — picked from the larger of the two totals.
        self._format_displays(card_a, card_b, delta, decomposition)
        decomposition_chart = self._decomposition_chart(decomposition)
        return ComparisonView(
            card_a=card_a, card_b=card_b, delta=delta, decomposition=decomposition,
            decomposition_chart=decomposition_chart,
            paired_chart=paired_chart, cumulative_chart=cumulative_chart,
            diff_changed=diff_changed, diff_only_in_a=diff_only_a, diff_only_in_b=diff_only_b)

    def _decomposition_chart(self, bars) -> Dict:
        """A horizontal diverging bar chart: one bar per non-zero category × phase, signed.

        Reductions (B < A) are green and point left, increases red and point right; the bars sum to
        the headline Δ (the zero-delta rows are the only ones dropped). One value axis (kg).
        """
        return {
            "labels": [bar.label for bar in bars],
            "datasets": [{
                "label": "Δ by category and phase",
                "data": [bar.delta_kg for bar in bars],
                "backgroundColor": [LOWER_COLOR if bar.delta_kg < 0 else HIGHER_COLOR for bar in bars],
            }],
        }

    @staticmethod
    def _format_displays(card_a, card_b, delta, decomposition):
        from efootprint.constants.units import u
        from efootprint.utils.display import (
            best_display_unit, human_readable_unit, format_display_number, format_quantity_for_display)

        # One shared unit for the whole strip, picked from the larger total so every figure reads against
        # it (magnitude honesty). Sig-fig rounding goes through the library's public
        # ``format_quantity_for_display`` — converting its result back to the shared unit is safe because
        # sig-fig rounding is scale-invariant, so the shared unit is preserved across the round-trip.
        unit = best_display_unit(max(card_a.total_kg, card_b.total_kg) * u.kg)
        unit_str = human_readable_unit(unit)

        def fmt(kg, signed=False):
            magnitude = format_quantity_for_display((kg * u.kg).to(unit), 3).to(unit).magnitude
            sign = "+" if signed and magnitude > 0 else ""
            return f"{sign}{format_display_number(magnitude)} {unit_str}"

        for card in (card_a, card_b):
            card.total_display = fmt(card.total_kg)
            card.usage_display = fmt(card.usage_kg)
            card.fabrication_display = fmt(card.fabrication_kg)

        delta.absolute_display = fmt(delta.absolute_kg, signed=True)
        delta.usage_display = fmt(delta.usage_kg, signed=True)
        delta.fabrication_display = fmt(delta.fabrication_kg, signed=True)
        delta.relative_display = (
            "" if delta.relative is None else f"{'+' if delta.relative > 0 else ''}{round(delta.relative * 100)} %")
        delta.direction = "lower" if delta.absolute_kg < 0 else ("higher" if delta.absolute_kg > 0 else "")

        for bar in decomposition:
            bar.delta_display = fmt(bar.delta_kg, signed=True)
            bar.direction = "lower" if bar.delta_kg < 0 else "higher"

    # --- KPI strip -----------------------------------------------------------------------------

    def _kpi_card(self, system, total_kg, decomposition, is_model_a) -> KpiCard:
        # ``decomposition`` carries each system's own subtotals on the Delta (``before`` = A,
        # ``after`` = B), so derive both cards from it rather than re-summing the library dicts.
        usage_kg, fab_kg = self._usage_fabrication_split(decomposition, is_model_a)
        return KpiCard(
            name=system.name,
            total_kg=total_kg,
            usage_kg=usage_kg,
            fabrication_kg=fab_kg,
            period_label=self._period_label(system))

    @staticmethod
    def _usage_fabrication_split(decomposition, is_model_a):
        """(usage, fabrication) subtotals for one model, summed from the decomposition rows."""
        usage = sum((row.delta.before if is_model_a else row.delta.after)
                    for row in decomposition if row.phase == "energy")
        fab = sum((row.delta.before if is_model_a else row.delta.after)
                  for row in decomposition if row.phase == "fabrication")
        return usage, fab

    def _kpi_delta(self, comparison) -> KpiDelta:
        decomposition = comparison.decomposition
        usage_delta = sum(row.delta.absolute for row in decomposition if row.phase == "energy")
        fab_delta = sum(row.delta.absolute for row in decomposition if row.phase == "fabrication")
        return KpiDelta(
            absolute_kg=comparison.total_delta.absolute,
            relative=comparison.total_delta.relative,
            usage_kg=usage_delta,
            fabrication_kg=fab_delta)

    @staticmethod
    def _period_label(system) -> str:
        """The model's modeling period as ``YYYY–YYYY`` (or a single year) from its footprint axis."""
        footprint = system.total_footprint
        start = footprint.start_date
        hours = len(footprint.value)
        end = start
        if hours:
            from datetime import timedelta
            end = start + timedelta(hours=hours - 1)
        if start.year == end.year:
            return str(start.year)
        return f"{start.year}–{end.year}"

    # --- decomposition (diverging bars) --------------------------------------------------------

    def _decomposition_bars(self, decomposition) -> List[DecompositionBar]:
        """Diverging bars per §4.2 display category × phase, dropping zero-delta rows.

        Merges Servers + Storage by label, sums each display group, and keeps only non-zero movers
        (a row with no change is "no change", not a zero bar). The dropped rows are exactly the
        zero-delta ones, so the displayed bars still sum to the headline Δ.
        """
        grouped: Dict[str, float] = {}
        for row in decomposition:
            label = f"{DISPLAY_CATEGORY_LABELS[row.category]} {PHASE_LABELS[row.phase]}"
            grouped[label] = grouped.get(label, 0.0) + row.delta.absolute

        bars = [DecompositionBar(label=label, delta_kg=delta) for label, delta in grouped.items()
                if abs(delta) > _ZERO_KG]
        bars.sort(key=lambda bar: self._decomposition_sort_key(bar.label))
        return bars

    @staticmethod
    def _decomposition_sort_key(label):
        category = next((c for c in DISPLAY_CATEGORY_ORDER if label.startswith(c)), label)
        order = DISPLAY_CATEGORY_ORDER.index(category) if category in DISPLAY_CATEGORY_ORDER else len(
            DISPLAY_CATEGORY_ORDER)
        # usage before fabrication within a category
        return order, 0 if label.endswith("usage") else 1

    # --- time-series charts --------------------------------------------------------------------

    def _paired_chart(self, comparison) -> Dict:
        """Per-year paired bars: model A | model B per year, dark = usage, light = fabrication.

        Both models bucket onto one shared yearly calendar axis (the union of their periods); a year
        outside a model's own modeling period is left blank (``null``), not a zero bar (§4.2 / §6).
        The usage / fabrication split is *exact per year*: the library's per-phase aligned series
        (``usage_*`` / ``fabrication_*``) are summed per calendar year, never a single full-period
        ratio applied to every year — so the dark / light segmentation reads truthfully even when a
        model's mix shifts across years. One y-axis (kg), one legend over the four series, model
        identity by the constant colour pair — the magnitude-honesty rule.
        """
        time_series = comparison.time_series
        years = self._shared_year_axis(comparison)
        years_a = self._model_years(comparison.system_a)
        years_b = self._model_years(comparison.system_b)

        usage_a = _yearly_totals(time_series.start_date, time_series.usage_a, years, years_a)
        fabrication_a = _yearly_totals(time_series.start_date, time_series.fabrication_a, years, years_a)
        usage_b = _yearly_totals(time_series.start_date, time_series.usage_b, years, years_b)
        fabrication_b = _yearly_totals(time_series.start_date, time_series.fabrication_b, years, years_b)

        return {
            "labels": [str(year) for year in years],
            "datasets": [
                _bar_dataset(f"{comparison.system_a.name} usage", usage_a, MODEL_A_COLOR, stack="A"),
                _bar_dataset(f"{comparison.system_a.name} fabrication", fabrication_a, MODEL_A_COLOR_LIGHT, stack="A"),
                _bar_dataset(f"{comparison.system_b.name} usage", usage_b, MODEL_B_COLOR, stack="B"),
                _bar_dataset(f"{comparison.system_b.name} fabrication", fabrication_b, MODEL_B_COLOR_LIGHT, stack="B"),
            ],
        }

    def _cumulative_chart(self, comparison) -> Dict:
        """Two cumulative curves on a shared axis; the area between them is the avoided/added gap.

        The end gap equals the headline Δ (each curve ends at its model's period total). A curve is
        flat across years before its model's period starts and is not drawn past its end (``null``),
        so the gap reads honestly when the two periods differ. Both share one y-axis.
        """
        time_series = comparison.time_series
        years = self._shared_year_axis(comparison)
        cum_a = _yearly_cumulative(time_series.start_date, time_series.values_a, years,
                                   self._model_years(comparison.system_a))
        cum_b = _yearly_cumulative(time_series.start_date, time_series.values_b, years,
                                   self._model_years(comparison.system_b))
        return {
            "labels": [str(year) for year in years],
            "datasets": [
                _line_dataset(comparison.system_a.name, cum_a, MODEL_A_COLOR),
                _line_dataset(comparison.system_b.name, cum_b, MODEL_B_COLOR),
            ],
        }

    def _shared_year_axis(self, comparison) -> List[int]:
        """The union of both models' calendar years — the shared axis both charts bucket onto."""
        years_a = self._model_years(comparison.system_a)
        years_b = self._model_years(comparison.system_b)
        if not years_a and not years_b:
            return []
        return list(range(min(years_a + years_b), max(years_a + years_b) + 1))

    @staticmethod
    def _model_years(system) -> List[int]:
        """The calendar years a model's own (unaligned) footprint axis spans."""
        from datetime import timedelta
        footprint = system.total_footprint
        hours = len(footprint.value)
        if hours == 0:
            return []
        start = footprint.start_date
        end = start + timedelta(hours=hours - 1)
        return list(range(start.year, end.year + 1))

    # --- assumptions diff ----------------------------------------------------------------------

    def _diff(self, input_diff):
        changed = [
            DiffRow(object_label=row.object_class, attribute=row.attribute,
                    value_a=row.value_a, value_b=row.value_b)
            for row in input_diff.changed]
        only_a = [DiffUnmatched(object_label=f"{obj.object_name} ({obj.object_class})")
                  for obj in input_diff.only_in_a]
        only_b = [DiffUnmatched(object_label=f"{obj.object_name} ({obj.object_class})")
                  for obj in input_diff.only_in_b]
        return changed, only_a, only_b


_ZERO_KG = 1e-9


def _bar_dataset(label, data, color, stack) -> Dict:
    return {"label": label, "data": data, "backgroundColor": color, "stack": stack}


def _line_dataset(label, data, color) -> Dict:
    return {"label": label, "data": data, "borderColor": color, "backgroundColor": color}


def _sum_by_year(start_date: datetime, hourly_values) -> Dict[int, float]:
    """Sum the (aligned) hourly kg series into per-calendar-year totals."""
    from datetime import timedelta
    by_year: Dict[int, float] = {}
    for hour_offset, value in enumerate(hourly_values):
        year = (start_date + timedelta(hours=hour_offset)).year
        by_year[year] = by_year.get(year, 0.0) + float(value)
    return by_year


def _yearly_totals(start_date, hourly_values, axis_years, model_years):
    """Per-year totals on the shared ``axis_years``; ``None`` for years outside ``model_years``.

    A year a model does not cover is blank (``None``), distinct from a covered year that happens to
    be zero — the §6 "leave non-overlapping buckets blank" rule. ``model_years`` is the model's own
    (unaligned) coverage; the aligned ``hourly_values`` are summed by their own calendar year.
    """
    by_year = _sum_by_year(start_date, hourly_values)
    covered = set(model_years)
    return [by_year.get(year, 0.0) if year in covered else None for year in axis_years]


def _yearly_cumulative(start_date, hourly_values, axis_years, model_years):
    """Cumulative kg sampled at each year's end on the shared axis; ``None`` outside coverage.

    Before the model's period the curve has not started (``None``); within it the running sum is
    carried so the final point equals the model's period total.
    """
    by_year = _sum_by_year(start_date, hourly_values)
    covered = set(model_years)
    cumulative: List[Optional[float]] = []
    running = 0.0
    for year in axis_years:
        if year not in covered:
            cumulative.append(None)
            continue
        running += by_year.get(year, 0.0)
        cumulative.append(running)
    return cumulative
