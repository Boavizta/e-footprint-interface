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


class TestAvailableSources:
    """Tests for ModelWeb.available_sources property."""

    def test_sentinels_always_present(self, minimal_model_web):
        from efootprint.abstract_modeling_classes.source_objects import Sources
        sources = minimal_model_web.available_sources
        source_ids = [s.id for s in sources]
        assert Sources.USER_DATA.id in source_ids
        assert Sources.HYPOTHESIS.id in source_ids

    def test_returns_deduplicated_sources(self, minimal_model_web):
        sources = minimal_model_web.available_sources
        ids = [s.id for s in sources]
        assert len(ids) == len(set(ids))

    def test_sorted_by_name(self, minimal_model_web):
        sources = minimal_model_web.available_sources
        names = [s.name for s in sources]
        assert names == sorted(names)

    def test_sentinel_is_same_python_instance(self, minimal_model_web):
        from efootprint.abstract_modeling_classes.source_objects import Sources
        sources = minimal_model_web.available_sources
        user_data = next(s for s in sources if s.id == Sources.USER_DATA.id)
        assert user_data is Sources.USER_DATA

    def test_available_sources_includes_sources_from_explainable_object_dict(self, minimal_model_web):
        from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

        custom_source = Source("Dict Element Source", "https://dict.example.com")

        target_obj = None
        for obj in minimal_model_web.flat_efootprint_objs_dict.values():
            for attr_val in obj.__dict__.values():
                if isinstance(attr_val, ExplainableObjectDict) and len(attr_val) > 0:
                    target_obj = obj
                    target_eod = attr_val
                    break
            if target_obj:
                break

        assert target_obj is not None, "No non-empty ExplainableObjectDict found in minimal model"
        next(iter(target_eod.values())).source = custom_source

        assert custom_source.id in [s.id for s in minimal_model_web.available_sources]
