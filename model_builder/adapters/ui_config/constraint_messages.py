"""Messages for creation constraint changes: toast notifications and disabled-button tooltips."""

CONSTRAINT_MESSAGES = {
    "JobWeb": {
        "unlocked": "You can now add jobs",
        "locked": "Job creation is no longer available",
        "tooltip": "Add a server or external API in the Infrastructure section first.",
    },
    "UsagePatternWeb": {
        "unlocked": "You can now add usage patterns",
        "locked": "Usage pattern creation is no longer available",
        "tooltip": "Add a usage journey in the Usage journeys section first.",
    },
    "EdgeUsagePatternWeb": {
        "unlocked": "You can now add edge usage patterns",
        "locked": "Edge usage pattern creation is no longer available",
        "tooltip": "Add an edge usage journey in the Usage journeys section first.",
    },
    "RecurrentServerNeedWeb": {
        "unlocked": "You can now add recurrent server needs",
        "locked": "Recurrent server need creation is no longer available",
        "tooltip": "Add an edge device in the Infrastructure section first.",
    },
    "RecurrentEdgeDeviceNeedBaseWeb": {
        "unlocked": "You can now add recurrent edge device needs",
        "locked": "Recurrent edge device need creation is no longer available",
        "tooltip": "Add an edge device in the Infrastructure section first.",
    },
    "__results__": {
        "unlocked": "Your model is complete — results are now available",
        "locked": "Results are no longer available",
        "tooltip": "Complete your model to access results",
    },
}
