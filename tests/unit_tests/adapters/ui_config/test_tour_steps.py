"""Unit tests for the guided-tour step copy.

The tour carries map/order copy only; these guard that both flavors resolve, that placeholders
are expanded server-side (no raw {kind:target} reaches JS), and that the blank flavor adds the
"create a usage journey" first-action suggestion.
"""
import re

from model_builder.adapters.ui_config.tour_steps import build_tour_steps

_PLACEHOLDER_RE = re.compile(r"\{[a-z]+:[^}]+\}")
_TOUR_TARGETS = {"usage-journeys", "infrastructure", "edge-modeling", "usage-patterns", "results",
                 "comparison", "help-menu"}


def _targets(steps):
    # The help step anchors on the "?" help button, not a data-tour-target column — skip it here.
    return {m.group(1) for step in steps if (m := re.search(r'data-tour-target="([^"]+)"', step["target"]))}


def test_loaded_flavor_has_no_first_action_suggestion():
    loaded = build_tour_steps(is_blank=False)
    assert loaded
    assert all("create a usage journey" not in step["body"] for step in loaded)


def test_blank_flavor_adds_the_create_a_usage_journey_suggestion():
    blank = build_tour_steps(is_blank=True)
    assert "create a usage journey" in blank[-1]["body"]
    # The blank flavor is the shared steps plus exactly one extra suggestion step.
    assert len(blank) == len(build_tour_steps(is_blank=False)) + 1


def test_every_step_targets_a_known_tour_anchor():
    for is_blank in (False, True):
        assert _targets(build_tour_steps(is_blank=is_blank)) <= _TOUR_TARGETS


def test_placeholders_are_resolved_server_side():
    for is_blank in (False, True):
        for step in build_tour_steps(is_blank=is_blank):
            assert not _PLACEHOLDER_RE.search(step["body"]), step["body"]


def test_help_step_opens_drawer_and_anchors_on_the_help_button():
    help_steps = [s for s in build_tour_steps(is_blank=False) if "open_help_class" in s]
    assert len(help_steps) == 1
    assert help_steps[0]["open_help_class"] == "UsageJourney"
    # It anchors on the "?" help button beside the add-usage-journey button (not the column,
    # which resizes when the drawer opens), and the body no longer hard-links UsageJourney.
    assert help_steps[0]["target"] == '[data-action="open-help-drawer"][data-help-class="UsageJourney"]'
    assert 'data-action="open-help-drawer"' not in help_steps[0]["body"]
    # It carries a phone-only body (tour.js shows it instead of opening the full-screen drawer),
    # resolved server-side like every other body so no raw placeholder reaches JS.
    assert "mobile_body" in help_steps[0]
    assert not _PLACEHOLDER_RE.search(help_steps[0]["mobile_body"])


def test_edge_modeling_step_anchors_on_the_toggle_and_links_to_the_deep_dive():
    edge_steps = [s for s in build_tour_steps(is_blank=False)
                  if 'data-tour-target="edge-modeling"' in s["target"]]
    assert len(edge_steps) == 1
    step = edge_steps[0]
    # The toolbar collapses into the burger below lg, so the step carries a mobile fallback.
    assert step["mobile_target"] == ".navbar-toggler"
    # The {doc:web_vs_edge} placeholder is resolved server-side into a web-vs-edge deep-link.
    assert "web_vs_edge" in step["body"]
    assert "<a href=" in step["body"]


def test_comparison_step_anchors_on_the_tab_strip_with_a_mobile_fallback():
    comparison_steps = [s for s in build_tour_steps(is_blank=False)
                        if 'data-tour-target="comparison"' in s["target"]]
    assert len(comparison_steps) == 1
    step = comparison_steps[0]
    # The tab strip is hidden below lg (it lives in the burger there), so the step carries a fallback.
    assert step["mobile_target"] == ".navbar-toggler"
    assert "Compare" in step["title"]


def test_help_menu_step_closes_the_drawer():
    steps = build_tour_steps(is_blank=False)
    close_steps = [s for s in steps if s.get("close_help")]
    assert len(close_steps) == 1
    # It is the toolbar Help-menu step, reached right after the drawer-opening help step.
    assert 'data-tour-target="help-menu"' in close_steps[0]["target"]
