import unittest
from datetime import datetime
from unittest.mock import MagicMock

import ciso8601
import numpy as np
import pytz

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.logger import logger

from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm

class TestUsagePatternFromForm(unittest.TestCase):
    def setUp(self):
        self.mock_usage_journey = MagicMock(spec=UsageJourney, id="usage-journey-id")
        self.mock_devices = [MagicMock(spec=Device, id="device-id"), MagicMock(spec=Device, id="device-id2")]
        self.mock_network = MagicMock(spec=Network, id = "network-id")
        self.mock_country = MagicMock(spec=Country, id = "FR-id")
        self.mock_country.timezone = SourceObject(pytz.timezone('Europe/Paris'))

        self.monthly_source = SourceObject("month", label="Monthly timespan")
        self.yearly_source = SourceObject("year", label="Yearly timespan")

        self.start_date_val = SourceObject("2025-01-01", label="Start date")
        self.modeling_duration_val = SourceValue(2 * u.dimensionless, label="modeling duration")
        self.modeling_duration_unit = SourceObject("month", label="modeling duration unit")
        self.initial_usage_val = SourceValue(1000.0 * u.dimensionless, label="initial usage journeys")
        self.growth_rate_val = SourceValue(20 * u.dimensionless, label="20% growth rate")

        # Instantiate the usage pattern
        self.usage_pattern = UsagePatternFromForm(
            name="test_usage_pattern_from_form",
            usage_journey=self.mock_usage_journey,
            devices=self.mock_devices,
            network=self.mock_network,
            country=self.mock_country,
            start_date=self.start_date_val,
            modeling_duration_value=self.modeling_duration_val,
            modeling_duration_unit=self.modeling_duration_unit,
            initial_usage_journey_volume=self.initial_usage_val,
            initial_usage_journey_volume_timespan=self.monthly_source,
            net_growth_rate_in_percentage=self.growth_rate_val,
            net_growth_rate_timespan=self.yearly_source
        )

        # Prevent automatic recomputations
        self.usage_pattern.trigger_modeling_updates = False

    def test_calculated_attributes(self):
        """Check that the newly introduced attributes are in calculated_attributes."""
        attrs = self.usage_pattern.calculated_attributes
        # "first_daily_usage_journey_volume", "daily_growth_rate", "hourly_usage_journey_starts" + parent's
        self.assertIn("first_daily_volume", attrs)
        self.assertIn("daily_growth_rate", attrs)
        self.assertIn("hourly_usage_journey_starts", attrs)
        # Also check one of the parent's attributes:
        self.assertIn("devices_energy", attrs)

    def test_update_daily_growth_rate_yearly_20_percent(self):
        """
        For a 20% net growth over 1 year, the daily growth factor is:
        (1 + 0.20)^(1 / 365.25...) ~ 1.00050
        """
        self.usage_pattern.update_daily_growth_rate()
        daily_rate = self.usage_pattern.daily_growth_rate.to(u.dimensionless).magnitude

        # Approx (1.2)^(1/365) ~ 1.0005
        expected = 1.0005
        self.assertAlmostEqual(daily_rate, expected, places=4)

    def test_update_daily_growth_rate_monthly_30_percent(self):
        """
        If net_growth_rate is 30% for 'monthly', daily rate is (1.3)^(1/30.437...) ~ ...
        """
        self.usage_pattern.net_growth_rate_in_percentage = SourceValue(30 * u.dimensionless)
        self.usage_pattern.net_growth_rate_timespan = SourceObject("month")
        self.usage_pattern.update_daily_growth_rate()

        daily_rate = self.usage_pattern.daily_growth_rate.magnitude
        # If we assume 1 month ~ 30 days => daily_rate = 1.3^(1/30)
        expected = 1.00878
        self.assertAlmostEqual(daily_rate, expected, places=5)

    def test_update_first_daily_volume_monthly_no_growth_rate(self):
        """
        If initial usage is 1000 journeys per 'monthly' timespan and there is no growth,
        we should see (approximately) 1000 / (1 month in days) journeys per day.
        Pint usually interprets 1 * month as ~30.437 days, so we check accordingly.
        """
        self.usage_pattern.daily_growth_rate = SourceValue(1 * u.dimensionless)
        self.usage_pattern.update_first_daily_volume()
        val_per_day = self.usage_pattern.first_daily_volume.to(u.dimensionless).magnitude

        # 1 month ~ 30 days => 1000 / 30 ~ 33.33 journeys/day
        self.assertAlmostEqual(val_per_day, 1000.0 / 30, places=2)

    def test_update_first_daily_volume_yearly_no_growth_rate(self):
        """
        If initial usage is 1000 journeys per 'yearly' timespan and there is no growth,
        we should see 1000 / (1 year in days) journeys per day.
        """
        # We'll switch to "year" to check
        self.usage_pattern.initial_usage_journey_volume_timespan = SourceObject("year")
        self.usage_pattern.daily_growth_rate = SourceValue(1 * u.dimensionless)
        self.usage_pattern.update_first_daily_volume()

        val_per_day = self.usage_pattern.first_daily_volume.to(u.dimensionless).magnitude
        self.assertAlmostEqual(val_per_day, 1000.0 / 365, places=3)

    def test_sum_over_first_month_is_very_close_to_initial_usage_journey_volume_input(self):
        self.usage_pattern.net_growth_rate_timespan = SourceObject("month")
        self.usage_pattern.update_daily_growth_rate()
        self.usage_pattern.update_first_daily_volume()
        self.usage_pattern.update_modeling_duration()
        self.usage_pattern.update_local_timezone_start_date()
        self.usage_pattern.update_hourly_usage_journey_starts()

        nb_visits_over_first_30_days = sum(self.usage_pattern.hourly_usage_journey_starts.value_as_float_list[:30*24])

        self.assertAlmostEqual(
            nb_visits_over_first_30_days, self.usage_pattern.initial_usage_journey_volume.magnitude, places=1)

    def test_update_modeling_duration(self):
        """
        If modeling duration is 2 months, we should see 2 * 30.437 days.
        """
        self.usage_pattern.update_modeling_duration()
        modeling_duration = self.usage_pattern.modeling_duration.to(u.day).magnitude

        # 2 months ~ 60.874 days
        self.assertAlmostEqual(modeling_duration, 2 * 30.437, places=2)

    def test_update_local_timezone_start_date(self):
        self.usage_pattern.update_local_timezone_start_date()
        self.assertEqual(datetime(2025, 1, 1, 1), self.usage_pattern.local_timezone_start_date.value)

    def test_update_hourly_usage_journey_starts_no_growth_2_days(self):
        """
        If daily usage is constant over 2 days, we want to see that the resulting
        hourly_usage_journey_starts is just the daily volume / 24 repeated for 48 hours.
        """
        # Set up no growth
        self.usage_pattern.net_growth_rate_in_percentage = SourceValue(0.0 * u.dimensionless)
        self.usage_pattern.net_growth_rate_timespan = SourceObject("year")  # any timespan => 0% means no growth
        self.usage_pattern.update_daily_growth_rate()

        # Set an initial volume of 240 journeys per day
        self.usage_pattern.initial_usage_journey_volume = SourceValue(240.0 * u.dimensionless)
        self.usage_pattern.initial_usage_journey_volume_timespan = SourceObject("day")
        self.usage_pattern.update_first_daily_volume()

        # We only want a 2-day modeling duration => 48 hours
        self.usage_pattern.modeling_duration = SourceValue(2.0 * u.day)
        self.usage_pattern.local_timezone_start_date = SourceObject(datetime(2025, 1, 1))

        self.usage_pattern.update_hourly_usage_journey_starts()

        # We expect 48 hours * (240 / 24) = 48 * 10 = 480 total journeys, each hour = 10 journeys
        hourly_values = self.usage_pattern.hourly_usage_journey_starts.value

        self.assertEqual(len(hourly_values), 48)
        # Check that all values are 10
        self.assertTrue(np.allclose(hourly_values, 10.0))

        # Check the index starts at the specified start_date and spans 48 hours
        expected_start = ciso8601.parse_datetime(self.start_date_val.value)
        self.assertEqual(self.usage_pattern.hourly_usage_journey_starts.start_date, expected_start)

    def test_update_hourly_usage_journey_starts_growth_scenario(self):
        """
        If daily growth rate is e.g. 1.0005 (20% yearly growth),
        then day0 = initial_daily_usage, day1 = 1.0005 * day0, day2 = 1.0005^2 * day0, ...
        We'll check a 2-day scenario for easy verification.
        """
        self.usage_pattern.initial_usage_journey_volume_timespan = SourceObject("day")
        self.usage_pattern.initial_usage_journey_volume = SourceValue(200.0 * u.dimensionless)
        self.usage_pattern.update_first_daily_volume()

        # Let’s say net_growth_rate is 20% for 'yearly' => daily growth = 1.0005
        self.usage_pattern.net_growth_rate_in_percentage = SourceValue(20 * u.dimensionless)
        self.usage_pattern.net_growth_rate_timespan = SourceObject("year")
        self.usage_pattern.update_daily_growth_rate()

        self.usage_pattern.modeling_duration = SourceValue(2.0 * u.day)
        self.usage_pattern.local_timezone_start_date = SourceObject(datetime(2025, 1, 1))
        self.usage_pattern.update_hourly_usage_journey_starts()

        hourly_df = self.usage_pattern.hourly_usage_journey_starts.value
        self.assertEqual(len(hourly_df), 48)

        # Day0 daily usage = 200 => hourly => 200/24 ~ 8.3333
        # Day1 daily usage = 1.0005 * 200 = 200.1 => hourly => 200.1/24 ~ 8.3375
        day0_hours = hourly_df[:24]
        day1_hours = hourly_df[24:]

        # Check day0 hours are all about 8.333
        self.assertTrue(np.allclose(day0_hours, 200.0 / 24, atol=1e-3))
        # Check day1 hours are all about 8.3375
        self.assertFalse(np.allclose(day1_hours, 200.0 / 24, atol=1e-3))
        self.assertTrue(np.allclose(day1_hours, 200.1 / 24, atol=1e-3))

    def test_variations_on_inputs_update_computations(self):
        self.usage_pattern.update_daily_growth_rate()
        self.usage_pattern.update_first_daily_volume()
        self.usage_pattern.update_modeling_duration()
        self.usage_pattern.update_local_timezone_start_date()
        self.usage_pattern.update_hourly_usage_journey_starts()
        self.usage_pattern.trigger_modeling_updates = True

        new_values = [
            ("net_growth_rate_timespan", SourceObject("month")),
            ("net_growth_rate_timespan", SourceObject("year")),
            ("initial_usage_journey_volume", SourceValue(100.0 * u.dimensionless)),
            ("initial_usage_journey_volume_timespan", SourceObject("year")),
            ("net_growth_rate_in_percentage", SourceValue(30 * u.dimensionless)),
            ("modeling_duration_value", SourceValue(1.0 * u.dimensionless)),
            ("modeling_duration_unit", SourceObject("year")),
            ("start_date", SourceObject("2025-01-02"))
        ]

        current_hourly_usage_journey_starts = self.usage_pattern.hourly_usage_journey_starts
        for input_attr_name, new_value in new_values:
            logger.warning(
                f"Updating {input_attr_name} from {getattr(self.usage_pattern, input_attr_name)} to {new_value}")
            setattr(self.usage_pattern, input_attr_name, new_value)
            if len(current_hourly_usage_journey_starts) == len(self.usage_pattern.hourly_usage_journey_starts):
                self.assertNotEqual(self.usage_pattern.hourly_usage_journey_starts, current_hourly_usage_journey_starts)
            current_hourly_usage_journey_starts = self.usage_pattern.hourly_usage_journey_starts

    def test_to_json(self):
        expected_json_without_id = {
            'name': 'test_usage_pattern_from_form',
            'country': 'FR-id',
            'devices': ['device-id', 'device-id2'],
            'modeling_duration_value': {
                'label': 'modeling duration value from e-footprint hypothesis',
                'source': {'link': None, 'name': 'e-footprint hypothesis'},
                'unit': 'dimensionless',
                'value': 2.0},
            "modeling_duration_unit": {
                "label": "modeling duration unit from e-footprint hypothesis",
                "source": {"link": None, "name": "e-footprint hypothesis"},
                "value": "month"
            },
            'net_growth_rate_in_percentage': {
                'label': 'net growth rate in percentage from e-footprint hypothesis',
                'source': {'link': None, 'name': 'e-footprint hypothesis'},
                'unit': 'dimensionless',
                'value': 20},
            'net_growth_rate_timespan': {
                'label': 'net growth rate timespan from e-footprint hypothesis',
                'source': {'link': None, 'name': 'e-footprint hypothesis'},
                'value': 'year'},
            "initial_usage_journey_volume": {
                "label": "initial usage journey volume from e-footprint hypothesis",
                "source": {"link": None, "name": "e-footprint hypothesis"},
                "unit": "dimensionless",
                "value": 1000.0
            },
            "initial_usage_journey_volume_timespan": {
                "label": "initial usage journey volume timespan from e-footprint hypothesis",
                "source": {"link": None, "name": "e-footprint hypothesis"},
                "value": "month"
            },
            'network': 'network-id',
            'start_date': {
                'label': 'start date from e-footprint hypothesis',
                'source': {'link': None, 'name': 'e-footprint hypothesis'},
                'value': '2025-01-01'},
            'usage_journey': 'usage-journey-id'}
        result_json = self.usage_pattern.to_json()
        result_json.pop("id")
        self.maxDiff = None
        self.assertDictEqual(expected_json_without_id, result_json)


if __name__ == "__main__":
    unittest.main()
