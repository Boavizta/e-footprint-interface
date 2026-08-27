import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import ciso8601
import numpy as np
import pytz
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u
from pint import Quantity

from model_builder.domain.entities.web_core.model_web import ModelWeb, _log_runtime_stage


class TestRuntimeStageLogging:
    @patch("model_builder.domain.entities.web_core.model_web.getpid", return_value=42)
    @patch("model_builder.domain.entities.web_core.model_web.process_time", return_value=1.25)
    @patch("model_builder.domain.entities.web_core.model_web.perf_counter", return_value=2.5)
    @patch("model_builder.domain.entities.web_core.model_web._gc_stats_snapshot")
    @patch("model_builder.domain.entities.web_core.model_web.logger.info")
    def test_logs_wall_cpu_pid_and_per_generation_gc_deltas(
            self, logger_info, gc_stats_snapshot, _perf_counter, _process_time, _getpid):
        gc_stats_snapshot.return_value = ((12, 130, 0), (4, 20, 0), (2, 38214, 1))

        _log_runtime_stage(
            "Serialized system data",
            wall_started_at=2.0,
            cpu_started_at=1.0,
            gc_before=((8, 10, 0), (3, 20, 0), (1, 0, 0)),
        )

        logger_info.assert_called_once_with(
            "Serialized system data in 500.0 ms "
            "(CPU 250.0 ms, pid=42, GC collections/collected/uncollectable: "
            "g0=4/120/0, g1=1/0/0, g2=1/38214/1)."
        )


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

    def test_system_emissions_returns_empty_result_when_no_hourly_quantities(self):
        empty_model_web = ModelWeb.__new__(ModelWeb)
        empty_model_web._system_emissions = None
        empty_model_web.system = MagicMock()
        empty_model_web.system.total_energy_footprints = {
            "Servers": EmptyExplainableObject(),
            "Storage": EmptyExplainableObject(),
            "ExternalAPIs": EmptyExplainableObject(),
            "Devices": EmptyExplainableObject(),
            "Network": EmptyExplainableObject(),
            "EdgeDevices": EmptyExplainableObject(),
        }
        empty_model_web.system.total_fabrication_footprints = {
            "Servers": EmptyExplainableObject(),
            "Storage": EmptyExplainableObject(),
            "ExternalAPIs": EmptyExplainableObject(),
            "Devices": EmptyExplainableObject(),
            "Network": EmptyExplainableObject(),
            "EdgeDevices": EmptyExplainableObject(),
        }

        emissions = empty_model_web.system_emissions

        self.assertListEqual(emissions["dates"], [])
        self.assertEqual(emissions["display_unit"], "kg")
        for key in [
            "Servers_and_storage_energy", "ExternalAPIs_energy", "Edge_devices_energy", "Devices_energy",
            "Network_energy", "Servers_and_storage_fabrication", "ExternalAPIs_fabrication",
            "Edge_devices_fabrication", "Devices_fabrication",
        ]:
            self.assertListEqual(emissions["values"][key], [])

    def test_root_edge_device_groups_returns_only_groups_without_parents(self):
        root_group = SimpleNamespace(modeling_obj=SimpleNamespace(parent_groups=[]))
        nested_group = SimpleNamespace(modeling_obj=SimpleNamespace(parent_groups=["parent"]))
        self.model_web.get_web_objects_from_efootprint_type = MagicMock(return_value=[root_group, nested_group])

        result = self.model_web.root_edge_device_groups

        self.assertEqual([root_group], result)
        self.model_web.get_web_objects_from_efootprint_type.assert_called_with("EdgeDeviceGroup")

    def test_ungrouped_edge_devices_returns_only_devices_without_parents(self):
        ungrouped_device = SimpleNamespace(modeling_obj=SimpleNamespace(parent_groups=[]))
        grouped_device = SimpleNamespace(modeling_obj=SimpleNamespace(parent_groups=["group"]))
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


class TestToJsonHoldsOnlyReferencedSources:
    """ModelWeb.to_json persists only sources a serialized value references, so pure
    computed-attribute provenance (EcoLogits / Boavizta getters attach a source to a *computed*
    value) never reaches the saved Sources block or the row-editor dropdown built from it."""

    @staticmethod
    def _simple_model_web():
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.constants.countries import Countries
        from efootprint.core.hardware.device import Device
        from efootprint.core.hardware.network import Network
        from efootprint.core.hardware.server import Server
        from efootprint.core.hardware.storage import Storage
        from efootprint.core.system import System
        from efootprint.core.usage.job import Job
        from efootprint.core.usage.usage_journey import UsageJourney
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep
        from efootprint.core.usage.usage_pattern import UsagePattern
        from model_builder.adapters.repositories import InMemorySystemRepository
        from tests.fixtures.system_builders import create_hourly_usage

        storage = Storage.from_defaults("Storage")
        server = Server.from_defaults("Server", storage=storage)
        job = Job.from_defaults("Job", server=server)
        uj = UsageJourney("Journey", uj_steps=[UsageJourneyStep.from_defaults("Step", jobs=[job])])
        usage_pattern = UsagePattern(
            "UP", usage_journey=uj, devices=[Device.from_defaults("Device")],
            network=Network.from_defaults("Network"), country=Countries.FRANCE(),
            hourly_usage_journey_starts=create_hourly_usage())
        system = System("System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
        # Inputs-only so the loaded ModelWeb recomputes its whole cone on first read below.
        return ModelWeb(InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False)))

    def test_source_inventory_does_not_pull_computed_slots(self):
        from efootprint.abstract_modeling_classes.reactive_core import computed_slots

        model_web = self._simple_model_web()

        def peeked_slots():
            return {
                (id(obj), attr_name): descriptor.peek(obj)
                for obj in model_web.flat_efootprint_objs_dict.values()
                for attr_name, descriptor in computed_slots(obj.efootprint_class).items()
            }

        before = peeked_slots()
        assert any(value is None for value in before.values())

        _ = model_web.web_explainable_quantities_sources

        after = peeked_slots()
        assert after.keys() == before.keys()
        assert all(after[key] is value for key, value in before.items())

    def test_source_on_a_computed_slot_is_not_persisted_or_offered(self):
        from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
        from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
        from efootprint.abstract_modeling_classes.reactive_core import computed_slots, serialized_slots
        from efootprint.abstract_modeling_classes.source_objects import Sources
        from model_builder.adapters.views.source_table_row_editor_context import _available_sources_from_json

        model_web = self._simple_model_web()
        raw_system = next(iter(model_web.response_objs["System"].values()))
        _ = raw_system.total_footprint  # local compute, materializes the computed slots

        # A named source on an *input* is referenced by a serialized value → it must be kept.
        input_source = Source("named input provenance", "https://example.com/input")
        # A source on a *bare* (non-serialized) computed slot is referenced by nothing serialized → it
        # must be dropped (stand-in for the EcoLogits / Boavizta computed-attribute provenance).
        computed_source = Source("synthetic computed provenance", "https://example.com/computed")
        input_tagged = computed_tagged = False
        for obj in model_web.flat_efootprint_objs_dict.values():
            if not input_tagged:
                for attr_val in get_instance_attributes(obj, ExplainableObject).values():
                    attr_val.source = input_source
                    input_tagged = True
                    break
            if not computed_tagged:
                serialized = set(serialized_slots(obj.efootprint_class))
                for attr_name, descriptor in computed_slots(obj.efootprint_class).items():
                    if attr_name in serialized:
                        continue
                    peeked = descriptor.peek(obj)
                    if isinstance(peeked, ExplainableObject):
                        peeked.source = computed_source
                        computed_tagged = True
                        break
            if input_tagged and computed_tagged:
                break
        assert input_tagged and computed_tagged, "Could not tag both an input and a bare computed slot"

        sources_block = model_web.to_json(save_computed_state=True).get("Sources", {})
        block_names = {payload["name"] for payload in sources_block.values()}
        assert input_source.name in block_names
        assert computed_source.name not in block_names

        dropdown_names = {source.name for source in _available_sources_from_json(sources_block)}
        assert input_source.name in dropdown_names
        assert computed_source.name not in dropdown_names
        assert Sources.USER_DATA.name in dropdown_names and Sources.HYPOTHESIS.name in dropdown_names


class TestExportSerialization:
    def test_cache_persistence_stays_lazy_but_export_materializes_every_serialized_slot(self, minimal_model_web):
        """Ordinary edit persistence peeks, while explicit export computes a complete snapshot."""
        from efootprint.abstract_modeling_classes.reactive_core import serialized_slots

        raw_system = next(iter(minimal_model_web.response_objs["System"].values()))
        total_descriptor = serialized_slots(type(raw_system))["total_footprint"]
        assert total_descriptor.peek(raw_system) is None

        minimal_model_web.persist_to_cache()

        assert total_descriptor.peek(raw_system) is None
        persisted = minimal_model_web.repository.get_system_data()
        assert "total_footprint" not in persisted["System"][raw_system.id]

        exported = minimal_model_web.export_json()

        assert "calculation_graph" in exported
        assert [raw_system.id, "total_footprint", None] in exported["calculation_graph"]["nodes"]
        assert exported["calculation_graph"]["edges"]
        for obj in minimal_model_web.flat_efootprint_objs_dict.values():
            for attr_name, descriptor in serialized_slots(obj.efootprint_class).items():
                assert descriptor.peek(obj) is not None, f"{obj.name}.{attr_name} was not materialized"
                assert attr_name in exported[obj.class_as_simple_str][obj.id]


class TestGetEfootprintObjectsFromEfootprintType:
    """Tests for ModelWeb.get_efootprint_objects_from_efootprint_type catalog/system deduplication."""

    def _model_web_with_france(self):
        from efootprint.api_utils.system_to_json import system_to_json
        from efootprint.constants.countries import Countries
        from efootprint.core.hardware.device import Device
        from efootprint.core.hardware.network import Network
        from efootprint.core.hardware.server import Server
        from efootprint.core.hardware.storage import Storage
        from efootprint.core.system import System
        from efootprint.core.usage.job import Job
        from efootprint.core.usage.usage_journey import UsageJourney
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep
        from efootprint.core.usage.usage_pattern import UsagePattern
        from model_builder.adapters.repositories import InMemorySystemRepository
        from tests.fixtures.system_builders import create_hourly_usage

        storage = Storage.from_defaults("Storage")
        server = Server.from_defaults("Server", storage=storage)
        job = Job.from_defaults("Job", server=server)
        uj = UsageJourney("Journey", uj_steps=[UsageJourneyStep.from_defaults("Step", jobs=[job])])
        usage_pattern = UsagePattern(
            "UP", usage_journey=uj, devices=[Device.from_defaults("Device")],
            network=Network.from_defaults("Network"), country=Countries.FRANCE(),
            hourly_usage_journey_starts=create_hourly_usage())
        system = System("System", usage_patterns=[usage_pattern], edge_usage_patterns=[])
        repository = InMemorySystemRepository(initial_data=system_to_json(system, save_computed_state=False))
        return ModelWeb(repository)

    def test_existing_country_shadows_same_named_catalog_default(self):
        # A system country named "France" (with a system-generated id, not the catalog id) must shadow the catalog
        # "France": the option list offers it once, and selecting it reuses the existing object instead of
        # materializing a duplicate on submit.
        model_web = self._model_web_with_france()
        existing_france = next(c for c in model_web.response_objs["Country"].values() if c.name == "France")

        countries = model_web.get_efootprint_objects_from_efootprint_type("Country")

        frances = [c for c in countries if c.name == "France"]
        assert len(frances) == 1
        assert frances[0].id == existing_france.id

        before = set(model_web.flat_efootprint_objs_dict)
        resolved = model_web.get_efootprint_object_from_efootprint_id(frances[0].id, "Country")
        assert resolved.id == existing_france.id
        assert set(model_web.flat_efootprint_objs_dict) == before
