"""Registry of ``{ui:token}`` placeholders used in interface-side descriptions.

Tokens reference UI elements (buttons, panels). Each entry carries a human
``display`` (rendered into help text) and an optional CSS ``selector`` (used
later by the guided tour). Library-side strings must not use ``{ui:...}``.
"""

UI_TOKENS: dict[str, dict[str, str]] = {
    "infra_panel_add_button": {
        "display": "the Add button in the Infrastructure section",
        "selector": "#add_server",
    },
    "jobs_panel_add_button": {
        "display": "the Add button in the Jobs section",
        "selector": "#add_job",
    },
    "usage_journeys_panel_add_button": {
        "display": "the Add button in the Usage journeys section",
        "selector": "#add_usagejourney",
    },
    "usage_patterns_panel_add_button": {
        "display": "the Add button in the Usage patterns section",
        "selector": "#add_usagepattern",
    },
}
