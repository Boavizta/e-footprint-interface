import numpy as np
from pint import Quantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.constants.units import get_unit


@ExplainableRecurrentQuantities.register_subclass(lambda d: "constant_value" in d and "constant_unit" in d)
class ExplainableRecurrentQuantitiesFromConstant(ExplainableRecurrentQuantities):
    """
    ExplainableRecurrentQuantities generated from a single constant value repeated 168 times.

    Stores the constant value in JSON so it can be edited later.
    Computes the 168-element array lazily when .value is first accessed.
    """

    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None
        constant_value = d["constant_value"]
        constant_unit = get_unit(d["constant_unit"])

        return cls(
            constant_value=constant_value,
            constant_unit=constant_unit,
            label=d["label"],
            source=source
        )

    def __init__(self, constant_value: float, constant_unit, label: str = None,
                 left_parent=None, right_parent=None, operator: str = None, source: Source = None):
        """
        Initialize with a constant value that will be repeated 168 times.

        Args:
            constant_value: The constant numeric value
            constant_unit: The pint unit for this value
            label: Optional label
            source: Optional source information
        """
        self.constant_value = constant_value
        self.constant_unit = constant_unit

        # Don't compute value yet - will be computed lazily
        # Initialize parent with None value
        super(ExplainableRecurrentQuantities, self).__init__(
            value=None, label=label, left_parent=left_parent,
            right_parent=right_parent, operator=operator, source=source
        )

    @property
    def value(self):
        """Lazy computation of 168-element recurrent array from constant value."""
        if self._value is None:
            self._value = self._compute_recurrent_values()

        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value

    @value.deleter
    def value(self):
        self._value = None

    def _compute_recurrent_values(self) -> Quantity:
        """Generate 168-element array (7 days * 24 hours) with constant value."""
        recurrent_array = np.array([self.constant_value] * 168, dtype=np.float32)
        return Quantity(recurrent_array, self.constant_unit)

    def to_json(self, save_calculated_attributes=False):
        """Save both constant value and computed recurrent values to JSON."""
        # Ensure value is computed and cached
        if self._value is None:
            _ = self.value

        output_dict = {
            "constant_value": self.constant_value,
            "constant_unit": str(self.constant_unit),
            "recurring_values": str(self.magnitude.tolist()),
            "unit": str(self.unit),
        }

        # Add parent class metadata (label, source, etc.)
        output_dict.update(super(ExplainableRecurrentQuantities, self).to_json(save_calculated_attributes))

        return output_dict