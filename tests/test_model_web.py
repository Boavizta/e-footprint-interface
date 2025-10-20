import unittest
from unittest.mock import MagicMock

import ciso8601
import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u
from pint import Quantity

from model_builder.web_core.model_web import ModelWeb


class TestModelWeb(unittest.TestCase):
    def setUp(self):
        self.model_web = ModelWeb.__new__(ModelWeb)

        self.model_web.system = MagicMock()
        self.model_web.system.total_energy_footprints = {
            "Servers": {"value": [100, 200], "start_date": "2023-01-01 00:00"},
            "Storage": {"value": [300, 400], "start_date": "2023-01-01 00:00"},
            "Devices": {"value": [500, 600], "start_date": "2023-01-02 00:00"},
            "Network": {"value": [700, 800], "start_date": "2023-01-01 00:00"},
            "EdgeComputers": {"value": [100, 200], "start_date": "2023-01-01 00:00"},
            "EdgeStorage": {"value": [50, 60], "start_date": "2023-01-01 00:00"}
        }
        self.model_web.system.total_fabrication_footprints = {
            "Servers": {"value": [900, 1000], "start_date": "2023-01-01 00:00"},
            "Storage": {"value": [1100, 1200], "start_date": "2023-01-01 00:00"},
            "Devices": {"value": [1300, 1400], "start_date": "2023-01-02 00:00"},
            "Network": EmptyExplainableObject(),
            "EdgeComputers": {"value": [1500, 1600], "start_date": "2023-01-01 00:00"},
            "EdgeStorage": {"value": [1700, 1800], "start_date": "2023-01-01 00:00"}
        }

        for footprint_dict in [
            self.model_web.system.total_energy_footprints, self.model_web.system.total_fabrication_footprints]:
            for key, data in footprint_dict.items():
                if not isinstance(data, EmptyExplainableObject):
                    footprint_dict[key] = ExplainableHourlyQuantities(
                        Quantity(np.array(data["value"]), u.kg),
                        start_date=pytz.utc.localize(ciso8601.parse_datetime(data["start_date"])), label="test")

    def test_system_emissions(self):
        emissions = self.model_web.system_emissions

        self.assertListEqual(emissions["dates"], ["2023-01-01", "2023-01-02"])
        self.assertListEqual(emissions["values"]["Servers_and_storage_energy"], [1, 0])
        self.assertListEqual(emissions["values"]["Devices_energy"], [0, 1.1])
        self.assertListEqual(emissions["values"]["Network_energy"], [1.5, 0])
        self.assertListEqual(emissions["values"]["Servers_and_storage_fabrication"], [4.2, 0])
        self.assertListEqual(emissions["values"]["Devices_fabrication"], [0, 2.7])
        self.assertListEqual(emissions["values"]["Edge_devices_and_storage_energy"], [0.41, 0])
        self.assertListEqual(emissions["values"]["Edge_devices_and_storage_fabrication"], [6.6, 0])

if __name__ == '__main__':
    unittest.main()
