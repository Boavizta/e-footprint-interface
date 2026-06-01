"""Unit tests for the guided-tour step copy (Step 6 Task 3).

The tour carries map/order copy only; these guard that both flavors resolve, that placeholders
are expanded server-side (no raw {kind:target} reaches JS), and that the blank flavor adds the
"create a usage journey" first-action suggestion.
"""
import re

from model_builder.adapters.ui_config.tour_steps import build_tour_steps

_PLACEHOLDER_RE = re.compile(r"\{[a-z]+:[^}]+\}")
_TOUR_TARGETS = {"usage-journeys", "infrastructure", "usage-patterns", "results", "help-menu"}


def _targets(steps):
    return {re.search(r'data-tour-target="([^"]+)"', step["target"]).group(1) for step in steps}


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


def test_help_step_resolves_a_help_drawer_link():
    help_steps = [s for s in build_tour_steps(is_blank=False) if "open_help_class" in s]
    assert len(help_steps) == 1
    assert help_steps[0]["open_help_class"] == "UsageJourney"
    # The {class:UsageJourney} placeholder resolved into an open-help-drawer button.
    assert 'data-action="open-help-drawer"' in help_steps[0]["body"]
