from datetime import datetime, timedelta
from typing import List

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject, SourceHourlyValues
from efootprint.core.country import Country
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.constants.units import u
from pint import Quantity

from model_builder.efootprint_extensions.explainable_start_date import ExplainableStartDate


class UsagePatternFromForm(UsagePattern):
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
            name, usage_journey, devices, network, country,
            SourceHourlyValues(Quantity(np.array([0], dtype=np.float32), u.dimensionless),
                start_date=datetime.strptime(start_date.value, "%Y-%m-%d")))

        self.start_date = start_date.set_label(f"{self.name} start date")
        self.modeling_duration_value = modeling_duration_value.set_label(f"{self.name} modeling duration value")
        self.modeling_duration_unit = modeling_duration_unit.set_label(f"{self.name} modeling duration unit")
        self.initial_usage_journey_volume = initial_usage_journey_volume.set_label(
            f"{self.name} initial usage journey volume")
        self.initial_usage_journey_volume_timespan = initial_usage_journey_volume_timespan.set_label(
            f"{self.name} initial usage journey volume timespan")
        self.net_growth_rate_in_percentage = net_growth_rate_in_percentage.set_label(
            f"{self.name} net growth rate in percentage")
        self.net_growth_rate_timespan = net_growth_rate_timespan.set_label(f"{self.name} net growth rate timespan")
        self.daily_growth_rate = EmptyExplainableObject()
        self.first_daily_usage_journey_volume = EmptyExplainableObject()
        self.modeling_duration = EmptyExplainableObject()
        self.local_timezone_start_date = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return (["daily_growth_rate", "first_daily_usage_journey_volume", "modeling_duration",
                 "local_timezone_start_date", "hourly_usage_journey_starts"] + super().calculated_attributes)

    @staticmethod
    def _timestamp_sourceobject_to_explainable_quantity(timestamp_sourceobject: SourceObject):
        unit_day_mapping = {"day": 1, "month": 30, "year": 365}
        timespan_unit = timestamp_sourceobject.value.lower()
        timespan = ExplainableQuantity(
            unit_day_mapping[timespan_unit] * u.day, label=f"1 {timespan_unit}"
        ).generate_explainable_object_with_logical_dependency(timestamp_sourceobject)

        return timespan

    def update_daily_growth_rate(self):
        timespan = self._timestamp_sourceobject_to_explainable_quantity(self.net_growth_rate_timespan)

        daily_rate = (1 + self.net_growth_rate_in_percentage.to(u.dimensionless).magnitude / 100
                      ) ** (1 / timespan.to(u.day).magnitude)

        self.daily_growth_rate = ExplainableQuantity(
            daily_rate * u.dimensionless, left_parent=self.net_growth_rate_in_percentage, right_parent=timespan,
            operator="converted to daily growth rate given timespan").set_label(f"{self.name} daily growth rate")

    def update_first_daily_usage_journey_volume(self):
        timespan = self._timestamp_sourceobject_to_explainable_quantity(self.initial_usage_journey_volume_timespan)
        timespan_in_days = timespan.to(u.day).magnitude
        if self.daily_growth_rate.magnitude == 1:
            exponential_daily_growth_sum_over_timespan_value = timespan_in_days
        else:
            exponential_daily_growth_sum_over_timespan_value = (
                (self.daily_growth_rate.magnitude ** timespan_in_days - 1) / (self.daily_growth_rate.magnitude - 1))
        exponential_daily_growth_sum_over_timespan = ExplainableQuantity(
            exponential_daily_growth_sum_over_timespan_value * u.dimensionless,
            left_parent=self.daily_growth_rate, right_parent=timespan,
            operator="daily geometric sum over")

        init_vol = self.initial_usage_journey_volume / exponential_daily_growth_sum_over_timespan

        self.first_daily_usage_journey_volume = init_vol.to(u.dimensionless).set_label(
            f"{self.name} initial daily usage journey volume")

    def update_modeling_duration(self):
        modeling_duration = ExplainableQuantity(
            self.modeling_duration_value.to(u.dimensionless).magnitude * u(self.modeling_duration_unit.value),
            left_parent=self.modeling_duration_value, right_parent=self.modeling_duration_unit,
            operator="combined and converted to modeling duration")

        self.modeling_duration = modeling_duration.set_label(f"{self.name} modeling duration")

    def update_local_timezone_start_date(self):
        utc_start_date = datetime.strptime(self.start_date.value, "%Y-%m-%d")

        utc_tz = pytz.timezone('UTC')
        time_diff = self.country.timezone.value.utcoffset(utc_start_date) - utc_tz.utcoffset(utc_start_date)
        time_diff_in_hours = int(time_diff.total_seconds() / 3600)

        local_start_date = utc_start_date + timedelta(hours=time_diff_in_hours)

        self.local_timezone_start_date = ExplainableStartDate(
            local_start_date, left_parent=self.start_date, right_parent=self.country.timezone,
            operator="converted to local timezone",
            label=f"{self.name} local timezone {self.country.timezone} start date")

    def update_hourly_usage_journey_starts(self):
        num_days = int(self.modeling_duration.to(u.day).magnitude)
        days = np.arange(num_days)

        # Compute the daily usage journeys (daily constant value) with exponential growth.
        # Each day, the volume grows by daily_rate from the previous day.
        daily_values = (
            self.first_daily_usage_journey_volume.to(u.dimensionless).magnitude * self.daily_growth_rate.magnitude ** days)

        # Since the exponential growth is computed daily,
        # each day’s hourly value remains constant (daily value divided equally among 24 hours).
        hourly_values = np.repeat(daily_values / 24, 24).astype(np.float32)

        self.hourly_usage_journey_starts = ExplainableHourlyQuantities(
            Quantity(hourly_values, u.dimensionless), start_date=self.local_timezone_start_date.value,
            left_parent=self.first_daily_usage_journey_volume, right_parent=self.daily_growth_rate,
            operator="exponentially growing with daily rate"
        ).generate_explainable_object_with_logical_dependency(
            self.local_timezone_start_date
        ).generate_explainable_object_with_logical_dependency(
            self.modeling_duration
        ).set_label(
            f"{self.name} hourly usage journey starts")
