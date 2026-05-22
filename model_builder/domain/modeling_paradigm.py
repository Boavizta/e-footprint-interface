"""Edge-vs-web paradigm classification.

The set is maintained by hand because `efootprint` does not currently expose a
programmatic "is this an edge class?" predicate. A consistency test guards
against drift when new edge classes are added to
`EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING` without being added here.

Only concrete efootprint classes are listed: callers (`paradigm_for`,
`ModelWeb.has_edge_objects`) classify and enumerate via `class_as_simple_str`,
which always returns a concrete class name.
"""

EDGE_EFOOTPRINT_CLASS_NAMES: frozenset[str] = frozenset({
    "EdgeUsagePattern", "EdgeUsageJourney", "EdgeFunction",
    "EdgeDevice", "EdgeDeviceGroup",
    "EdgeComputer", "EdgeComputerCPUComponent", "EdgeComputerRAMComponent",
    "EdgeAppliance", "EdgeApplianceComponent",
    "EdgeComponent", "EdgeCPUComponent", "EdgeRAMComponent",
    "EdgeStorage", "EdgeWorkloadComponent",
    "RecurrentServerNeed",
    "RecurrentEdgeProcess", "RecurrentEdgeWorkload",
    "RecurrentEdgeDeviceNeed", "RecurrentEdgeComponentNeed",
    "RecurrentEdgeStorageNeed",
})


def paradigm_for(efootprint_class_name: str) -> str:
    """Return "edge" or "web" for a given efootprint class name."""
    return "edge" if efootprint_class_name in EDGE_EFOOTPRINT_CLASS_NAMES else "web"
