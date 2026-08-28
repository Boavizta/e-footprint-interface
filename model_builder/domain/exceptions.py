"""Domain exceptions for e-footprint interface.

These exceptions represent domain-level errors that can occur during
system operations, independent of the web framework.
"""

from efootprint.logger import logger


class SessionExpiredError(Exception):
    """Raised when the user's session has expired and model data is no longer available."""

    pass


class PayloadSizeLimitExceeded(Exception):
    """Raised when the system data exceeds the maximum allowed size for storage.

    This exception is raised by the repository layer when attempting to save
    data that exceeds the configured size limit. It carries context about
    the current size and limit for user-friendly error messages.
    """

    def __init__(self, current_size_mb: float, limit_mb: float):
        self.current_size_mb = current_size_mb
        self.limit_mb = limit_mb
        logger.error(f"Payload size limit exceeded: {current_size_mb:.1f} MB (limit: {limit_mb} MB)")
        message = (
            f"Your model has become too large to be saved on this shared instance "
            f"(current size: {current_size_mb:.1f} MB, limit: {limit_mb} MB).\n\n"
            f"To continue working with large models, please consider:\n"
            f"- Hosting your own instance of e-footprint-interface and updating the MAX_PAYLOAD_SIZE_MB env variable, "
            f"or\n"
            f"- Contacting vincent.villet@publicissapient.com for assistance\n\n"
            f"Your recent changes have NOT been saved."
        )
        super().__init__(message)


class ComputationMemoryLimitExceeded(Exception):
    """Raised when a reactive calculation reaches the safe container memory limit."""

    safe_message = (
        "This calculation was stopped before it exhausted the memory available on this instance. "
        "Your saved model is still available. Reduce the model complexity or modeling timespan, "
        "split the model, or use an instance with more memory, then try again."
    )

    def __init__(self, *, working_set_bytes: int, limit_bytes: int, capacity_bytes: int | None):
        self.working_set_bytes = working_set_bytes
        self.limit_bytes = limit_bytes
        self.capacity_bytes = capacity_bytes
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        # ModelingUpdate annotates Exception.args while rolling a rejected edit back. Keep the
        # presentation deliberately stable and free of internal calculation details.
        return self.safe_message
