"""Service for calculating system emissions.

This service aggregates energy and fabrication footprints into daily emissions
timeseries for visualization.
"""
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Any, Protocol, runtime_checkable

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities

from model_builder.domain.entities.web_core.model_web_utils import (
    determine_global_time_bounds, get_reindexed_array_from_dict, to_rounded_daily_values
)


@runtime_checkable
class SystemWithFootprints(Protocol):
    """Protocol for objects that have energy and fabrication footprints."""
    @property
    def total_energy_footprints(self) -> Dict: ...
    @property
    def total_fabrication_footprints(self) -> Dict: ...


@dataclass
class EmissionsResult:
    """Result of emissions calculation."""
    dates: List[str]
    values: Dict[str, List[float]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"dates": self.dates, "values": self.values}


class EmissionsCalculationService:
    """Service for calculating system emissions timeseries.

    This service aggregates energy and fabrication footprints from
    servers, storage, edge devices, devices, and network into daily
    emissions values suitable for charting.
    """

    def calculate_daily_emissions(self, system: SystemWithFootprints) -> EmissionsResult:
        """Calculate daily emissions timeseries for the system.

        Args:
            system: The efootprint System to calculate emissions for

        Returns:
            EmissionsResult with dates and categorized emissions values

        Raises:
            ValueError: If no ExplainableHourlyQuantities are found
        """
        energy = system.total_energy_footprints
        fab = system.total_fabrication_footprints

        ehqs = [q for q in list(energy.values()) + list(fab.values()) if isinstance(q, ExplainableHourlyQuantities)]

        if not ehqs:
            raise ValueError("No ExplainableHourlyQuantities found.")

        global_start, total_hours = determine_global_time_bounds(ehqs)

        dates = [
            (global_start + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(math.ceil(total_hours / 24))
        ]

        values = {
            "Servers_and_storage_energy": to_rounded_daily_values(
                get_reindexed_array_from_dict("Servers", energy, global_start, total_hours)
                + get_reindexed_array_from_dict("Storage", energy, global_start, total_hours)
            ),
            "Edge_devices_energy": to_rounded_daily_values(
                get_reindexed_array_from_dict("EdgeDevices", energy, global_start, total_hours)
            ),
            "Devices_energy": to_rounded_daily_values(
                get_reindexed_array_from_dict("Devices", energy, global_start, total_hours)
            ),
            "Network_energy": to_rounded_daily_values(
                get_reindexed_array_from_dict("Network", energy, global_start, total_hours)
            ),
            "Servers_and_storage_fabrication": to_rounded_daily_values(
                get_reindexed_array_from_dict("Servers", fab, global_start, total_hours)
                + get_reindexed_array_from_dict("Storage", fab, global_start, total_hours)
            ),
            "Edge_devices_fabrication": to_rounded_daily_values(
                get_reindexed_array_from_dict("EdgeDevices", fab, global_start, total_hours)
            ),
            "Devices_fabrication": to_rounded_daily_values(
                get_reindexed_array_from_dict("Devices", fab, global_start, total_hours)
            ),
        }

        return EmissionsResult(dates=dates, values=values)
