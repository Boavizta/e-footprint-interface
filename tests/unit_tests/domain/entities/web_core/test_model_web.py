import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace

import ciso8601
import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u
from pint import Quantity

from model_builder.domain.entities.web_core.model_web import ModelWeb


class TestModelWeb(unittest.TestCase):
    def setUp(self):
        self.model_web = ModelWeb.__new__(ModelWeb)
        self.model_web._system_emissions = None

        self.model_web.system = MagicMock()
        self.model_web.system.total_energy_footprints = {
            "Servers": {"value": [100, 200], "start_date": "2023-01-01 00:00"},
            "Storage": {"value": [300, 400], "start_date": "2023-01-01 00:00"},
            "ExternalAPIs": {"value": [100, 300], "start_date": "2023-01-01 00:00"},
            "Devices": {"value": [500, 600], "start_date": "2023-01-02 00:00"},
            "Network": {"value": [700, 800], "start_date": "2023-01-01 00:00"},
            "EdgeDevices": {"value": [100, 200], "start_date": "2023-01-01 00:00"},
        }
        self.model_web.system.total_fabrication_footprints = {
            "Servers": {"value": [900, 1000], "start_date": "2023-01-01 00:00"},
            "Storage": {"value": [1100, 1200], "start_date": "2023-01-01 00:00"},
            "ExternalAPIs": {"value": [500, 700], "start_date": "2023-01-01 00:00"},
            "Devices": {"value": [1300, 1400], "start_date": "2023-01-02 00:00"},
            "Network": EmptyExplainableObject(),
            "EdgeDevices": {"value": [1500, 1600], "start_date": "2023-01-01 00:00"},
        }

        for footprint_dict in [
            self.model_web.system.total_energy_footprints, self.model_web.system.total_fabrication_footprints]:
            for key, data in footprint_dict.items():
                if not isinstance(data, EmptyExplainableObject):
                    footprint_dict[key] = ExplainableHourlyQuantities(
                        Quantity(np.array(data["value"]), u.kg),
                        start_date=pytz.utc.localize(ciso8601.parse_datetime(data["start_date"])), label="test")

        self.model_web.system.total_footprint = ExplainableHourlyQuantities(
            Quantity(np.array([7900, 7600]), u.kg),
            start_date=pytz.utc.localize(ciso8601.parse_datetime("2023-01-01 00:00")),
            label="total",
        )

    def test_system_emissions(self):
        emissions = self.model_web.system_emissions

        self.assertListEqual(emissions["dates"], ["2023-01-01", "2023-01-02"])
        self.assertEqual(emissions["display_unit"], "t")
        self.assertListEqual(emissions["values"]["Servers_and_storage_energy"], [1, 0])
        self.assertListEqual(emissions["values"]["Devices_energy"], [0, 1.1])
        self.assertListEqual(emissions["values"]["ExternalAPIs_energy"], [0.4, 0])
        self.assertListEqual(emissions["values"]["Network_energy"], [1.5, 0])
        self.assertListEqual(emissions["values"]["Servers_and_storage_fabrication"], [4.2, 0])
        self.assertListEqual(emissions["values"]["ExternalAPIs_fabrication"], [1.2, 0])
        self.assertListEqual(emissions["values"]["Devices_fabrication"], [0, 2.7])
        self.assertListEqual(emissions["values"]["Edge_devices_energy"], [0.3, 0])
        self.assertListEqual(emissions["values"]["Edge_devices_fabrication"], [3.1, 0])

    def test_root_edge_device_groups_returns_only_groups_without_parents(self):
        root_group = SimpleNamespace(modeling_obj=SimpleNamespace(_find_parent_groups=lambda: []))
        nested_group = SimpleNamespace(modeling_obj=SimpleNamespace(_find_parent_groups=lambda: ["parent"]))
        self.model_web.get_web_objects_from_efootprint_type = MagicMock(return_value=[root_group, nested_group])

        result = self.model_web.root_edge_device_groups

        self.assertEqual([root_group], result)
        self.model_web.get_web_objects_from_efootprint_type.assert_called_with("EdgeDeviceGroup")

    def test_ungrouped_edge_devices_returns_only_devices_without_parents(self):
        ungrouped_device = SimpleNamespace(modeling_obj=SimpleNamespace(_find_parent_groups=lambda: []))
        grouped_device = SimpleNamespace(modeling_obj=SimpleNamespace(_find_parent_groups=lambda: ["group"]))
        self.model_web.get_web_objects_from_efootprint_type = MagicMock(return_value=[ungrouped_device, grouped_device])

        result = self.model_web.ungrouped_edge_devices

        self.assertEqual([ungrouped_device], result)
        self.model_web.get_web_objects_from_efootprint_type.assert_called_with("EdgeDevice")

if __name__ == '__main__':
    unittest.main()
