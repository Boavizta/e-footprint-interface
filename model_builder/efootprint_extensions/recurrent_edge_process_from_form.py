import numpy as np
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge_computer import EdgeComputer
from pint import Quantity
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.units import u


class RecurrentEdgeProcessFromForm(RecurrentEdgeProcess):
    default_values = {
        "constant_compute_needed": SourceValue(1 * u.cpu_core),
        "constant_ram_needed": SourceValue(1 * u.GB_ram),
        "constant_storage_needed": SourceValue(1 * u.GB)
    }
    def __init__(
        self, name:str, edge_device: EdgeComputer, constant_compute_needed: ExplainableQuantity,
        constant_ram_needed: ExplainableQuantity, constant_storage_needed: ExplainableQuantity):
        super().__init__(
            name,
            edge_device,
            recurrent_compute_needed=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.cpu_core)),
            recurrent_ram_needed=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB_ram)),
            recurrent_storage_needed=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB))
        )
        self.constant_compute_needed = constant_compute_needed.set_label(f"{self.name} constant compute needed")
        self.constant_ram_needed = constant_ram_needed.set_label(f"{self.name} constant ram needed")
        self.constant_storage_needed = constant_storage_needed.set_label(f"{self.name} constant storage needed")

    @property
    def calculated_attributes(self):
        return (["recurrent_compute_needed", "recurrent_ram_needed", "recurrent_storage_needed"]
                + super().calculated_attributes)

    def update_recurrent_compute_needed(self):
        recurrent_compute_needed = ExplainableRecurrentQuantities(
            Quantity(np.array([self.constant_compute_needed.magnitude] * 168, dtype=np.float32),
                     self.constant_compute_needed.unit),
            left_parent=self.constant_compute_needed, operator="expanded from")

        self.recurrent_compute_needed = recurrent_compute_needed.set_label(f"{self.name} recurrent compute needed")

    def update_recurrent_ram_needed(self):
        recurrent_ram_needed = ExplainableRecurrentQuantities(
            Quantity(np.array([self.constant_ram_needed.magnitude] * 168, dtype=np.float32),
                     self.constant_ram_needed.unit),
        left_parent=self.constant_ram_needed, operator="expanded from")

        self.recurrent_ram_needed = recurrent_ram_needed.set_label(f"{self.name} recurrent RAM needed")

    def update_recurrent_storage_needed(self):
        recurrent_storage_needed = ExplainableRecurrentQuantities(
            Quantity(np.array(
                # At the beginning of the canonical week, the storage is set to the constant storage needed,
                # then reset at the end only to be brought back the next week
                [self.constant_storage_needed.magnitude] + [0] * 166 + [-self.constant_storage_needed.magnitude],
                dtype=np.float32),
                self.constant_storage_needed.unit),
            left_parent=self.constant_storage_needed, operator="expanded from")

        self.recurrent_storage_needed = recurrent_storage_needed.set_label(f"{self.name} recurrent storage needed")
