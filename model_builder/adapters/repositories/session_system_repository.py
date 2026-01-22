"""Session-based implementation of ISystemRepository.

This implementation stores system data in Django sessions, which is the
current production storage mechanism for the application.
"""
import os
from typing import Dict, Any, Optional

from django.contrib.sessions.backends.base import SessionBase
from efootprint.logger import logger

from e_footprint_interface.json_payload_utils import compute_json_size
from model_builder.domain.exceptions import PayloadSizeLimitExceeded
from model_builder.domain.interfaces import ISystemRepository


class SessionSystemRepository(ISystemRepository):
    """Session-based implementation of system repository.

    This class wraps Django's session mechanism to provide a clean interface
    for storing and retrieving system data. It implements ISystemRepository,
    allowing the business logic to remain decoupled from Django.

    Usage:
        repository = SessionSystemRepository(request.session)
        data = repository.get_system_data()
        repository.save_system_data(modified_data)
    """

    SYSTEM_DATA_KEY = "system_data"
    MAX_PAYLOAD_SIZE_MB = float(os.environ.get("MAX_PAYLOAD_SIZE_MB", 30.0))

    def __init__(self, session: SessionBase):
        """Initialize with a Django session.

        Args:
            session: The Django session object (typically request.session)
        """
        self._session = session

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve the current system data from the session.

        Returns:
            The system data dictionary, or None if no data exists.
        """
        return self._session.get(self.SYSTEM_DATA_KEY)

    def save_system_data(self, data: Dict[str, Any]) -> None:
        """Persist the system data to the session.

        Args:
            data: The system data dictionary to save.

        Raises:
            PayloadSizeLimitExceeded: If the data exceeds MAX_PAYLOAD_SIZE_MB.
        """
        size_result = compute_json_size(data)
        logger.info(
            f"System data JSON size: {size_result.size_mb:.2f} MB "
            f"(computation took {size_result.computation_time_ms:.1f} ms)"
        )

        if size_result.size_mb > self.MAX_PAYLOAD_SIZE_MB:
            raise PayloadSizeLimitExceeded(size_result.size_mb, self.MAX_PAYLOAD_SIZE_MB)

        self._session[self.SYSTEM_DATA_KEY] = data
        self._session.modified = True

    def has_system_data(self) -> bool:
        """Check if system data exists in the session.

        Returns:
            True if system data exists, False otherwise.
        """
        return self.SYSTEM_DATA_KEY in self._session

    def clear(self) -> None:
        """Clear system data from the session."""
        self._session.pop(self.SYSTEM_DATA_KEY, None)
        self._session.modified = True

    @property
    def session(self) -> SessionBase:
        """Access the underlying session (for backwards compatibility during migration).

        This property allows gradual migration of code that still needs
        direct session access. It should be used sparingly and eventually removed.
        """
        return self._session
