"""Service for validating system modeling completeness.

This service checks that the system has all required components
for impact computation.
"""
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


@dataclass
class ValidationError:
    """Represents a validation error."""
    message: str
    affected_objects: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of system validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)

    def raise_if_invalid(self):
        """Raise ValueError with combined error messages if validation failed."""
        if not self.is_valid:
            messages = [error.message for error in self.errors]
            raise ValueError("\n\n".join(messages))


class SystemValidationService:
    """Service for validating system modeling completeness.

    This service checks that the system has all required components
    for impact computation, without any Django dependencies.
    """

    def validate_for_computation(self, model_web: "ModelWeb") -> ValidationResult:
        """Validate that the system is complete enough for impact computation.

        Args:
            model_web: The ModelWeb instance to validate

        Returns:
            ValidationResult with is_valid flag and any errors found
        """
        errors = []

        # Check for at least one usage pattern
        usage_pattern_error = self._check_usage_patterns(model_web)
        if usage_pattern_error:
            errors.append(usage_pattern_error)

        # Check usage journeys have steps
        uj_error = self._check_usage_journey_steps(model_web)
        if uj_error:
            errors.append(uj_error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _check_usage_patterns(self, model_web: "ModelWeb") -> ValidationError | None:
        """Check that at least one usage pattern exists."""
        system = model_web.system
        total_patterns = len(system.usage_patterns) + len(system.edge_usage_patterns)
        if total_patterns == 0:
            return ValidationError(
                message=(
                    "No impact could be computed because the modeling is incomplete. "
                    "Please make sure you have at least one usage pattern or one edge usage pattern."
                )
            )
        return None

    def _check_usage_journey_steps(self, model_web: "ModelWeb") -> ValidationError | None:
        """Check that usage journeys linked to patterns have at least one step."""
        journeys_without_steps = []
        for usage_journey in model_web.usage_journeys:
            if len(usage_journey.usage_patterns) > 0 and len(usage_journey.uj_steps) == 0:
                journeys_without_steps.append(usage_journey.name)

        if journeys_without_steps:
            return ValidationError(
                message=(
                    f"The following usage journey(s) have no usage journey step: {journeys_without_steps}. "
                    f"Please add at least one step in each of the above usage journey(s), "
                    f"so that the model can be computed.\n\n"
                    "(Alternatively, if they are work in progress, you can delete the usage patterns "
                    "pointing to them: in that way the usage journeys will be ignored in the computation.)"
                ),
                affected_objects=journeys_without_steps
            )
        return None
