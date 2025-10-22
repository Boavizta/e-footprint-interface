import numpy as np
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from pint import Quantity
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.constants.units import u


class RecurrentEdgeWorkloadFromForm(RecurrentEdgeWorkload):
    default_values = {
        "constant_workload": SourceValue(1 * u.dimensionless)
    }
    def __init__(self, name: str, edge_device: EdgeAppliance, constant_workload: ExplainableQuantity):
        # Initialize with a labeled zero array for recurrent_workload
        initial_recurrent_workload = ExplainableRecurrentQuantities(
            Quantity(np.array([0] * 168, dtype=np.float32), u.dimensionless),
            label="initial recurrent workload")

        super().__init__(
            name,
            edge_device,
            recurrent_workload=initial_recurrent_workload
        )
        self.constant_workload = constant_workload.set_label(f"{self.name} constant workload")

    @property
    def calculated_attributes(self):
        return ["recurrent_workload"] + super().calculated_attributes

    def update_recurrent_workload(self):
        recurrent_workload = ExplainableRecurrentQuantities(
            Quantity(np.array([self.constant_workload.magnitude] * 168, dtype=np.float32),
                     self.constant_workload.unit),
            left_parent=self.constant_workload, operator="expanded from")

        self.recurrent_workload = recurrent_workload.set_label(f"{self.name} recurrent workload")
