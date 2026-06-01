"""Interface-specific guided-tour copy (the "map + order + where help lives" tour).

This is the only place the tour's *words* live — ``tour.js`` carries none. Each
step pairs a stable ``data-tour-target`` selector with a short title/body. The
body may contain ``{kind:target}`` placeholders, resolved server-side through the
same ``EFOOTPRINT_DESCRIPTION_PROVIDER`` the rest of the UI uses
(``tour_steps.html`` renders the result as JSON for ``tour.js``).

The tour deliberately carries no domain-concept prose (spec §3 out-of-scope): it
points at the canvas columns and the existing help affordances, never re-explaining
what a usage journey or a server *is*. Two flavors share the same orientation steps:

- ``loaded`` — a template was just loaded; steps point at the real cards.
- ``blank`` — "Start from scratch"; the same steps anchor on the empty columns and
  a final step suggests the first concrete action (create a usage journey).

``data-tour-target`` selectors (set in the canvas partials, asserted present in E2E):

- ``usage-journeys`` — the usage-journey column (the recommended starting point)
- ``infrastructure`` — the servers / edge-devices column
- ``usage-patterns``  — the usage-patterns column
- ``results``         — the results bar at the bottom
- ``help-menu``       — the toolbar Help menu (replay tour, templates, docs)

The help step is the one exception: it anchors on the "?" help button beside the
"Add usage journey" button (``_HELP_BUTTON_SEL``) rather than a ``data-tour-target``
column, because the column resizes when the drawer opens and would break the highlight.

A step may carry an optional ``mobile_target`` selector: tour.js uses it when the primary
target isn't visible (e.g. the toolbar Help menu collapses into the burger below ``lg``).
"""
from model_builder.adapters.ui_config.efootprint_description_provider import EFOOTPRINT_DESCRIPTION_PROVIDER


def _sel(target: str) -> str:
    return f'[data-tour-target="{target}"]'


# The concrete "?" help affordance the help step points at — the one beside the
# "Add usage journey" button. Unique on the page (only UsageJourney's add button
# renders this class). tour.js opens the drawer for this same class on the step.
_HELP_BUTTON_SEL = '[data-action="open-help-drawer"][data-help-class="UsageJourney"]'


# Shared orientation steps (same content in both flavors). ``open_help_class`` on a
# step tells tour.js to open the help drawer for that class when the step is shown,
# so the user sees contextual help populated without leaving the tour.
_SHARED_STEPS = [
    {
        "target": _sel("usage-journeys"),
        "title": "Start in the middle: usage journeys",
        "body": "A usage journey is what a user actually does with your service. This column is your "
                "anchor — begin here, then build out the rest.",
    },
    {
        "target": _sel("infrastructure"),
        "title": "Then the infrastructure",
        "body": "Add the servers, external APIs and edge devices your journeys rely on.",
    },
    {
        "target": _sel("usage-patterns"),
        "title": "Then who uses it, and how much",
        "body": "Usage patterns describe how many people follow each journey over time.",
    },
    {
        "target": _sel("results"),
        "title": "Watch the results add up",
        "body": "Once the model is complete, its environmental footprint appears here.",
    },
    {
        "target": _HELP_BUTTON_SEL,
        "title": "Help is always one click away",
        "body": "Every add button has a help link beside it, like this one — we just opened it so you can "
                "see. Together with the field tooltips and info icons, they explain every concept. Explore "
                "it now; the tour stays open.",
        "open_help_class": "UsageJourney",
    },
    {
        "target": _sel("help-menu"),
        # On mobile the toolbar collapses into the burger, so the Help menu has no layout box
        # to anchor on; point at the burger (where the Help menu now lives) instead. tour.js
        # uses this only when the primary target isn't visible.
        "mobile_target": ".navbar-toggler",
        "title": "Replay this any time",
        "body": "The Help menu replays this tour, re-opens the templates, or jumps to the documentation.",
        # Close the help drawer we opened on the previous step before highlighting the toolbar.
        "close_help": True,
    },
]

# The blank flavor ends on a concrete first action (spec §6: "create a usage journey").
_BLANK_FIRST_ACTION_STEP = {
    "target": _sel("usage-journeys"),
    "title": "Your first step",
    "body": "Your model is empty. Suggested first step: create a usage journey — what a user does with "
            "your service.",
}


def _resolve(steps: list[dict]) -> list[dict]:
    resolved = []
    for step in steps:
        resolved_step = {"target": step["target"], "title": step["title"],
                         "body": str(EFOOTPRINT_DESCRIPTION_PROVIDER.resolve_text(step["body"]))}
        if "open_help_class" in step:
            resolved_step["open_help_class"] = step["open_help_class"]
        if "close_help" in step:
            resolved_step["close_help"] = step["close_help"]
        if "mobile_target" in step:
            resolved_step["mobile_target"] = step["mobile_target"]
        resolved.append(resolved_step)
    return resolved


def build_tour_steps(is_blank: bool) -> list[dict]:
    """Resolve the tour steps for the given flavor, placeholders expanded to HTML."""
    steps = list(_SHARED_STEPS)
    if is_blank:
        steps = steps + [_BLANK_FIRST_ACTION_STEP]
    return _resolve(steps)
