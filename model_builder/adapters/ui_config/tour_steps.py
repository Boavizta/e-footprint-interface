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
"""
from model_builder.adapters.ui_config.efootprint_description_provider import EFOOTPRINT_DESCRIPTION_PROVIDER


def _sel(target: str) -> str:
    return f'[data-tour-target="{target}"]'


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
        "target": _sel("usage-journeys"),
        "title": "Help is always one click away",
        "body": "The {class:UsageJourney} help links beside each add button, the field tooltips and the "
                "info icons explain every concept — we just opened the help panel so you can see. Explore "
                "it now; the tour stays open.",
        "open_help_class": "UsageJourney",
    },
    {
        "target": _sel("help-menu"),
        "title": "Replay this any time",
        "body": "The Help menu replays this tour, re-opens the templates, or jumps to the documentation.",
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
        resolved.append(resolved_step)
    return resolved


def build_tour_steps(is_blank: bool) -> list[dict]:
    """Resolve the tour steps for the given flavor, placeholders expanded to HTML."""
    steps = list(_SHARED_STEPS)
    if is_blank:
        steps = steps + [_BLANK_FIRST_ACTION_STEP]
    return _resolve(steps)
