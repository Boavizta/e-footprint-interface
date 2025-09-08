from datetime import datetime
from typing import List

import numpy as np
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject, SourceHourlyValues
from efootprint.core.country import Country
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.constants.units import u
from pint import Quantity

from model_builder.efootprint_extensions.timeseries_form import TimeseriesForm


class EdgeUsagePatternFromForm(EdgeUsagePattern, TimeseriesForm):
    default_values = {
            "start_date": SourceObject("2025-01-01"),
            "modeling_duration_value": SourceValue(3 * u.dimensionless),
            "modeling_duration_unit": SourceObject("year"),
            "initial_edge_usage_journey_volume": SourceValue(10000 * u.dimensionless),
            "initial_edge_usage_journey_volume_timespan": SourceObject("month"),
            "net_growth_rate_in_percentage": SourceValue(0 * u.dimensionless),
            "net_growth_rate_timespan": SourceObject("year")
        }

    list_values ={
            "initial_edge_usage_journey_volume_timespan": [
                SourceObject("day"), SourceObject("month"), SourceObject("year")],
            "modeling_duration_unit": [SourceObject("month"), SourceObject("year")]
        }

    conditional_list_values = {
            "net_growth_rate_timespan": {
                "depends_on": "initial_edge_usage_journey_volume_timespan",
                "conditional_list_values": {
                    SourceObject("day"): [SourceObject("month"), SourceObject("year")],
                    SourceObject("month"): [SourceObject("month"), SourceObject("year")],
                    SourceObject("year"): [SourceObject("year")]
                }
            }
        }

    def __init__(self, name: str, edge_usage_journey: EdgeUsageJourney, country: Country,
                 start_date: SourceObject, modeling_duration_value: SourceValue,
                 modeling_duration_unit: SourceObject, initial_edge_usage_journey_volume: SourceValue,
                 initial_edge_usage_journey_volume_timespan: SourceObject,
                 net_growth_rate_in_percentage: SourceValue, net_growth_rate_timespan: SourceObject):
        super().__init__(
            name=name, edge_usage_journey=edge_usage_journey, country=country,
            hourly_edge_usage_journey_starts=SourceHourlyValues(
                Quantity(np.array([0], dtype=np.float32), u.dimensionless),
            start_date=datetime.strptime(start_date.value, "%Y-%m-%d")))

        self.initial_edge_usage_journey_volume = initial_edge_usage_journey_volume.set_label(
            f"initial edge usage journey volume")
        self.initial_edge_usage_journey_volume_timespan = initial_edge_usage_journey_volume_timespan.set_label(
            f"initial edge usage journey volume timespan")

        TimeseriesForm.__init__(
            self, start_date, modeling_duration_value, modeling_duration_unit,
            net_growth_rate_in_percentage, net_growth_rate_timespan)

    @property
    def calculated_attributes(self) -> List[str]:
        return (TimeseriesForm.calculated_attributes.__get__(self, TimeseriesForm)
                + ["hourly_edge_usage_journey_starts"] + super().calculated_attributes)

    def update_hourly_edge_usage_journey_starts(self):
        self.hourly_edge_usage_journey_starts = self.generate_hourly_starts()
