"""Domain exceptions for e-footprint interface.

These exceptions represent domain-level errors that can occur during
system operations, independent of the web framework.
"""
from efootprint.logger import logger


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
