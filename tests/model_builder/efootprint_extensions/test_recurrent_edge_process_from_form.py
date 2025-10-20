import unittest
from copy import copy
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_computer import EdgeComputer

from model_builder.efootprint_extensions.recurrent_edge_process_from_form import RecurrentEdgeProcessFromForm


class TestRecurrentEdgeProcessFromForm(unittest.TestCase):
    def setUp(self):
        self.constant_compute = SourceValue(2 * u.cpu_core, label="Test compute")
        self.constant_ram = SourceValue(4 * u.GB, label="Test RAM")
        self.constant_storage = SourceValue(200 * u.GB, label="Test storage")
        self.edge_device = MagicMock(spec=EdgeComputer)
        self.edge_device.id = "edge-device-1"

        self.edge_process = RecurrentEdgeProcessFromForm(
            name="test_edge_process",
            edge_device=self.edge_device,
            constant_compute_needed=self.constant_compute,
            constant_ram_needed=self.constant_ram,
            constant_storage_needed=self.constant_storage
        )

        self.edge_process.trigger_modeling_updates = False

    def test_initialization(self):
        """Test that the edge process is initialized correctly with constant values."""
        self.assertEqual(self.edge_process.name, "test_edge_process")
        self.assertEqual(self.edge_process.constant_compute_needed.magnitude, 2)
        self.assertEqual(self.edge_process.constant_ram_needed.magnitude, 4)
        self.assertEqual(self.edge_process.constant_storage_needed.magnitude, 200)

        # Check that labels are set correctly
        self.assertIn("test_edge_process constant compute needed", self.edge_process.constant_compute_needed.label)
        self.assertIn("test_edge_process constant ram needed", self.edge_process.constant_ram_needed.label)
        self.assertIn("test_edge_process constant storage needed", self.edge_process.constant_storage_needed.label)

    def test_initial_recurrent_values_are_zero(self):
        """Test that initial recurrent values are arrays of zeros."""
        # Check that recurrent values are initialized as zero arrays
        self.assertTrue(np.allclose(self.edge_process.recurrent_compute_needed.magnitude, np.zeros(168)))
        self.assertTrue(np.allclose(self.edge_process.recurrent_ram_needed.magnitude, np.zeros(168)))
        self.assertTrue(np.allclose(self.edge_process.recurrent_storage_needed.magnitude, np.zeros(168)))

    def test_update_recurrent_compute_needed(self):
        """Test that update_recurrent_compute_needed sets all hours to constant value."""
        self.edge_process.update_recurrent_compute_needed()

        expected_array = np.array([2.0] * 168, dtype=np.float32)
        actual_array = self.edge_process.recurrent_compute_needed.magnitude

        self.assertTrue(np.allclose(actual_array, expected_array))
        self.assertEqual(self.edge_process.recurrent_compute_needed.unit, u.cpu_core)
        self.assertEqual(self.edge_process.recurrent_compute_needed.label, "test_edge_process recurrent compute needed")

    def test_update_recurrent_ram_needed(self):
        """Test that update_recurrent_ram_needed sets all hours to constant value."""
        self.edge_process.update_recurrent_ram_needed()

        expected_array = np.array([4.0] * 168, dtype=np.float32)
        actual_array = self.edge_process.recurrent_ram_needed.magnitude

        self.assertTrue(np.allclose(actual_array, expected_array))
        self.assertEqual(self.edge_process.recurrent_ram_needed.unit, u.GB)
        self.assertEqual(self.edge_process.recurrent_ram_needed.label, "test_edge_process recurrent RAM needed")

    def test_update_recurrent_storage_needed(self):
        """Test that update_recurrent_storage_needed sets first hour to constant, rest to zero."""
        self.edge_process.update_recurrent_storage_needed()

        expected_array = np.array([200.0] + [0.0] * 166 + [-200.0], dtype=np.float32)
        actual_array = self.edge_process.recurrent_storage_needed.magnitude

        self.assertTrue(np.allclose(actual_array, expected_array))
        self.assertEqual(len(self.edge_process.recurrent_storage_needed.magnitude), 168)
        self.assertEqual(self.edge_process.recurrent_storage_needed.unit, u.GB)
        self.assertEqual(self.edge_process.recurrent_storage_needed.label, "test_edge_process recurrent storage needed")

    def test_units_consistency(self):
        """Test that units are preserved correctly in recurrent updates."""
        # Test with different units for RAM
        ram_in_mb = SourceValue(4000 * u.MB, label="Test RAM in MB")
        edge_process_mb = RecurrentEdgeProcessFromForm(
            name="test_mb",
            edge_device=self.edge_device,
            constant_compute_needed=copy(self.constant_compute),
            constant_ram_needed=ram_in_mb,
            constant_storage_needed=copy(self.constant_storage)
        )

        edge_process_mb.update_recurrent_ram_needed()
        self.assertEqual(edge_process_mb.recurrent_ram_needed.unit, u.MB)
        self.assertTrue(np.allclose(edge_process_mb.recurrent_ram_needed.magnitude, np.array([4000.0] * 168)))

    def test_logical_dependencies(self):
        """Test that recurrent values have logical dependencies on constant values."""
        self.edge_process.update_recurrent_compute_needed()
        self.edge_process.update_recurrent_ram_needed()
        self.edge_process.update_recurrent_storage_needed()

        # Check that the explainable objects have dependencies
        self.assertIn(self.constant_compute, self.edge_process.recurrent_compute_needed.direct_ancestors_with_id)
        self.assertIn(self.constant_ram, self.edge_process.recurrent_ram_needed.direct_ancestors_with_id)
        self.assertIn(self.constant_storage, self.edge_process.recurrent_storage_needed.direct_ancestors_with_id)

    def test_to_json(self):
        """Test JSON serialization includes constant resource attributes."""
        result_json = self.edge_process.to_json()

        # Should include the constant resource attributes
        self.assertIn("constant_compute_needed", result_json)
        self.assertIn("constant_ram_needed", result_json)
        self.assertIn("constant_storage_needed", result_json)

        # Check values are correct
        self.assertEqual(result_json["constant_compute_needed"]["value"], 2.0)
        self.assertEqual(result_json["constant_ram_needed"]["value"], 4.0)
        self.assertEqual(result_json["constant_storage_needed"]["value"], 200.0)


if __name__ == "__main__":
    unittest.main()
