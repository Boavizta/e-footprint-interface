from datetime import datetime, timedelta
from typing import List
import re

import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u
from pint import Quantity

from model_builder.efootprint_extensions.explainable_start_date import ExplainableStartDate


class TimeseriesForm:
    def __init__(self, start_date: SourceObject, modeling_duration_value: SourceValue,
                 modeling_duration_unit: SourceObject, net_growth_rate_in_percentage: SourceValue,
                 net_growth_rate_timespan: SourceObject) -> None:
        self.start_date = start_date.set_label(f"start date")
        self.modeling_duration_value = modeling_duration_value.set_label(f"modeling duration value")
        self.modeling_duration_unit = modeling_duration_unit.set_label(f"modeling duration unit")
        self.net_growth_rate_in_percentage = net_growth_rate_in_percentage.set_label(f"net growth rate in percentage")
        self.net_growth_rate_timespan = net_growth_rate_timespan.set_label(f"net growth rate timespan")
        self.daily_growth_rate = EmptyExplainableObject()
        self.first_daily_volume = EmptyExplainableObject()
        self.modeling_duration = EmptyExplainableObject()
        self.local_timezone_start_date = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return ["daily_growth_rate", "first_daily_volume", "modeling_duration", "local_timezone_start_date"]

    @property
    def volume_type(self):
        pattern = r"initial_(.*?)_volume"
        for attr_name in self.__dict__:
            match = re.search(pattern, attr_name)
            if match:
                return match.group(1)
        raise AttributeError(f"No attribute matching {pattern}")

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
            operator="converted to daily growth rate given timespan").set_label(f"daily growth rate")

    def update_first_daily_volume(self):
        timespan = self._timestamp_sourceobject_to_explainable_quantity(
            getattr(self, f"initial_{self.volume_type}_volume_timespan"))
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

        init_vol = getattr(self, f"initial_{self.volume_type}_volume") / exponential_daily_growth_sum_over_timespan

        self.first_daily_volume = init_vol.to(u.dimensionless).set_label(
            f"initial daily {self.volume_type} volume")

    def update_modeling_duration(self):
        modeling_duration = ExplainableQuantity(
            self.modeling_duration_value.to(u.dimensionless).magnitude * u(self.modeling_duration_unit.value),
            left_parent=self.modeling_duration_value, right_parent=self.modeling_duration_unit,
            operator="combined and converted to modeling duration")

        self.modeling_duration = modeling_duration.set_label(f"modeling duration")

    def update_local_timezone_start_date(self):
        utc_start_date = datetime.strptime(self.start_date.value, "%Y-%m-%d")

        utc_tz = pytz.timezone('UTC')
        time_diff = self.country.timezone.value.utcoffset(utc_start_date) - utc_tz.utcoffset(utc_start_date)
        time_diff_in_hours = int(time_diff.total_seconds() / 3600)

        local_start_date = utc_start_date + timedelta(hours=time_diff_in_hours)

        self.local_timezone_start_date = ExplainableStartDate(
            local_start_date, left_parent=self.start_date, right_parent=self.country.timezone,
            operator="converted to local timezone",
            label=f"local timezone {self.country.timezone} start date")

    def generate_hourly_starts(self):
        num_days = int(self.modeling_duration.to(u.day).magnitude)
        days = np.arange(num_days)

        # Compute the daily {self.volume_type}s (daily constant value) with exponential growth.
        # Each day, the volume grows by daily_rate from the previous day.
        daily_values = (
            self.first_daily_volume.to(u.dimensionless).magnitude * self.daily_growth_rate.magnitude ** days)

        # Since the exponential growth is computed daily,
        # each day’s hourly value remains constant (daily value divided equally among 24 hours).
        hourly_values = np.repeat(daily_values / 24, 24).astype(np.float32)

        return ExplainableHourlyQuantities(
            Quantity(hourly_values, u.occurrence), start_date=self.local_timezone_start_date.value,
            left_parent=self.first_daily_volume, right_parent=self.daily_growth_rate,
            operator="exponentially growing with daily rate"
        ).generate_explainable_object_with_logical_dependency(
            self.local_timezone_start_date
        ).generate_explainable_object_with_logical_dependency(
            self.modeling_duration
        ).set_label(f"hourly {self.volume_type} starts")
