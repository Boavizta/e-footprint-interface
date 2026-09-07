"""Session-scoped policy for Postgres recovery-copy retention."""

from typing import Dict, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sessions.backends.base import SessionBase

from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex

SYSTEM_DATA_CACHE_NAMESPACE = "system_data"
RECOVERY_RETENTION_SESSION_KEY = "recovery_retention_seconds"
DEFAULT_RECOVERY_RETENTION_SECONDS = 12 * 60 * 60
MAX_RECOVERY_RETENTION_SECONDS = 14 * 24 * 60 * 60
APPROVED_RECOVERY_RETENTION_SECONDS = (
    1 * 60 * 60,
    3 * 60 * 60,
    6 * 60 * 60,
    12 * 60 * 60,
    *(days * 24 * 60 * 60 for days in range(1, 15)),
)


def recovery_retention_choices(
    session_cookie_age: int | None = None,
) -> Tuple[int, ...]:
    """Return the closed retention allowlist capped by the session-cookie lifetime."""
    cookie_age = settings.SESSION_COOKIE_AGE if session_cookie_age is None else session_cookie_age
    cap = min(cookie_age, MAX_RECOVERY_RETENTION_SECONDS)
    choices = tuple(seconds for seconds in APPROVED_RECOVERY_RETENTION_SECONDS if seconds <= cap)
    if not choices:
        raise ImproperlyConfigured("SESSION_COOKIE_AGE must be at least one hour.")
    return choices


def get_recovery_retention_seconds(
    session: SessionBase,
    session_cookie_age: int | None = None,
) -> int:
    """Read a valid preference, defaulting to the longest allowed value up to 12 hours."""
    choices = recovery_retention_choices(session_cookie_age)
    default = max(seconds for seconds in choices if seconds <= DEFAULT_RECOVERY_RETENTION_SECONDS)
    value = session.get(RECOVERY_RETENTION_SESSION_KEY, default)
    if isinstance(value, bool) or not isinstance(value, int) or value not in choices:
        return default
    return value


def set_recovery_retention(session: SessionBase, seconds: int) -> Dict[int, bool]:
    """Persist a valid preference and touch each saved slot's Postgres recovery expiry.

    The preference is committed before touches so a concurrently expired slot cannot roll back the
    user's choice. The returned mapping makes each slot's outcome observable to the caller.
    """
    choices = recovery_retention_choices()
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds not in choices:
        raise ValueError("Recovery retention must be one of the configured choices.")

    session[RECOVERY_RETENTION_SESSION_KEY] = seconds
    session.modified = True

    index = WorkspaceIndex(session)
    saved_slots = index.slot_sizes()
    results: Dict[int, bool] = {}
    cache_backend = CacheBackend()
    session_key = session.session_key
    for slot in index.slots():
        if slot in saved_slots:
            if not session_key:
                results[slot] = False
                continue
            cache_key = f"{SYSTEM_DATA_CACHE_NAMESPACE}:{session_key}:{slot}"
            results[slot] = cache_backend.touch_postgres(cache_key, seconds)
    return results
