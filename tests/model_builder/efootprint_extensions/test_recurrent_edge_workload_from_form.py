import unittest
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.recurrent_edge_component_need import WorkloadOutOfBoundsError

from model_builder.efootprint_extensions.recurrent_edge_workload_from_form import RecurrentEdgeWorkloadFromForm


class TestRecurrentEdgeWorkloadFromForm(unittest.TestCase):
    def setUp(self):
        self.constant_workload = SourceValue(0.5 * u.dimensionless, label="Test workload")
        self.edge_device = MagicMock(spec=EdgeAppliance)
        self.edge_device.id = "edge-device-1"
        self.edge_device.appliance_component = MagicMock(spec=EdgeComponent)

        self.edge_workload = RecurrentEdgeWorkloadFromForm(
            name="test_edge_workload",
            edge_device=self.edge_device,
            constant_workload=self.constant_workload
        )

        self.edge_workload.trigger_modeling_updates = False

    def test_initialization(self):
        """Test that the edge workload is initialized correctly with constant value."""
        self.assertEqual(self.edge_workload.name, "test_edge_workload")
        self.assertEqual(self.edge_workload.constant_workload.magnitude, 0.5)

        # Check that label is set correctly
        self.assertIn("test_edge_workload constant workload", self.edge_workload.constant_workload.label)

    def test_initial_recurrent_workload_is_zero(self):
        """Test that initial recurrent workload is an array of zeros."""
        # Check that recurrent workload is initialized as zero array
        self.assertTrue(np.allclose(self.edge_workload.recurrent_workload.magnitude, np.zeros(168)))

    def test_update_recurrent_workload(self):
        """Test that update_recurrent_workload sets all hours to constant value."""
        self.edge_workload.update_recurrent_workload()

        expected_array = np.array([0.5] * 168, dtype=np.float32)
        actual_array = self.edge_workload.recurrent_workload.magnitude

        self.assertTrue(np.allclose(actual_array, expected_array))
        self.assertEqual(self.edge_workload.recurrent_workload.unit, u.dimensionless)
        self.assertEqual(self.edge_workload.recurrent_workload.label, "test_edge_workload recurrent workload")

    def test_workload_validation_within_bounds(self):
        """Test that workload values within 0-1 range are accepted."""
        # Test with 0
        workload_zero = SourceValue(0 * u.dimensionless, label="Zero workload")
        edge_workload_zero = RecurrentEdgeWorkloadFromForm(
            name="test_zero",
            edge_device=self.edge_device,
            constant_workload=workload_zero
        )
        edge_workload_zero.update_recurrent_workload()
        self.assertTrue(np.allclose(edge_workload_zero.recurrent_workload.magnitude, np.zeros(168)))

        # Test with 1
        workload_one = SourceValue(1 * u.dimensionless, label="Full workload")
        edge_workload_one = RecurrentEdgeWorkloadFromForm(
            name="test_one",
            edge_device=self.edge_device,
            constant_workload=workload_one
        )
        edge_workload_one.update_recurrent_workload()
        self.assertTrue(np.allclose(edge_workload_one.recurrent_workload.magnitude, np.ones(168)))

    def test_units_consistency(self):
        """Test that units are preserved correctly in recurrent updates."""
        self.edge_workload.update_recurrent_workload()
        self.assertEqual(self.edge_workload.recurrent_workload.unit, u.dimensionless)

    def test_logical_dependencies(self):
        """Test that recurrent workload has logical dependency on constant workload."""
        self.edge_workload.update_recurrent_workload()

        # Check that the explainable object has dependency
        self.assertIn(self.constant_workload, self.edge_workload.recurrent_workload.direct_ancestors_with_id)

    def test_to_json(self):
        """Test JSON serialization includes constant workload attribute."""
        result_json = self.edge_workload.to_json()

        # Should include the constant workload attribute
        self.assertIn("constant_workload", result_json)

        # Check value is correct
        self.assertEqual(result_json["constant_workload"]["value"], 0.5)

    def test_calculated_attributes(self):
        """Test that recurrent_workload is in calculated_attributes."""
        self.assertIn("recurrent_workload", self.edge_workload.calculated_attributes)


if __name__ == "__main__":
    unittest.main()
