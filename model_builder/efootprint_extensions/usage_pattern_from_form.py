from datetime import datetime
from typing import List

import numpy as np
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject, SourceHourlyValues
from efootprint.core.country import Country
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.constants.units import u
from pint import Quantity

from model_builder.efootprint_extensions.timeseries_form import TimeseriesForm


class UsagePatternFromForm(UsagePattern, TimeseriesForm):
    default_values = {
            "start_date": SourceObject("2025-01-01"),
            "modeling_duration_value": SourceValue(3 * u.dimensionless),
            "modeling_duration_unit": SourceObject("year"),
            "initial_usage_journey_volume": SourceValue(10000 * u.dimensionless),
            "initial_usage_journey_volume_timespan": SourceObject("month"),
            "net_growth_rate_in_percentage": SourceValue(0 * u.dimensionless),
            "net_growth_rate_timespan": SourceObject("year")
        }

    list_values ={
            "initial_usage_journey_volume_timespan": [
                SourceObject("day"), SourceObject("month"), SourceObject("year")],
            "modeling_duration_unit": [SourceObject("month"), SourceObject("year")]
        }

    conditional_list_values = {
            "net_growth_rate_timespan": {
                "depends_on": "initial_usage_journey_volume_timespan",
                "conditional_list_values": {
                    SourceObject("day"): [SourceObject("month"), SourceObject("year")],
                    SourceObject("month"): [SourceObject("month"), SourceObject("year")],
                    SourceObject("year"): [SourceObject("year")]
                }
            }
        }

    def __init__(self, name: str, usage_journey: UsageJourney, devices: List[Device],
                 network: Network, country: Country, start_date: SourceObject, modeling_duration_value: SourceValue,
                 modeling_duration_unit: SourceObject, initial_usage_journey_volume: SourceValue,
                 initial_usage_journey_volume_timespan: SourceObject,
                 net_growth_rate_in_percentage: SourceValue, net_growth_rate_timespan: SourceObject):
        super().__init__(
            name=name, usage_journey=usage_journey, devices=devices, network=network, country=country,
            hourly_usage_journey_starts=SourceHourlyValues(Quantity(np.array([0], dtype=np.float32), u.dimensionless),
            start_date=datetime.strptime(start_date.value, "%Y-%m-%d")))

        self.initial_usage_journey_volume = initial_usage_journey_volume.set_label(f"initial usage journey volume")
        self.initial_usage_journey_volume_timespan = initial_usage_journey_volume_timespan.set_label(
            f"initial usage journey volume timespan")

        TimeseriesForm.__init__(
            self, start_date, modeling_duration_value, modeling_duration_unit,
            net_growth_rate_in_percentage, net_growth_rate_timespan)

    @property
    def calculated_attributes(self) -> List[str]:
        return (TimeseriesForm.calculated_attributes.__get__(self, TimeseriesForm) + ["hourly_usage_journey_starts"] +
                super().calculated_attributes)

    def update_hourly_usage_journey_starts(self):
        self.hourly_usage_journey_starts = self.generate_hourly_starts()
