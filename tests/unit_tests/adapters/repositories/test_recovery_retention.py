"""Tests for session-scoped recovery retention and expiry-only slot updates."""

from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection

from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.recovery_retention import (
    APPROVED_RECOVERY_RETENTION_SECONDS,
    DEFAULT_RECOVERY_RETENTION_SECONDS,
    MAX_RECOVERY_RETENTION_SECONDS,
    RECOVERY_RETENTION_SESSION_KEY,
    get_recovery_retention_seconds,
    recovery_retention_choices,
    set_recovery_retention,
)
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex


class DictSession(dict):
    def __init__(self):
        super().__init__()
        self.session_key = "session-key"
        self.modified = False

    def save(self):
        pass


@pytest.fixture
def database_cache_table(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        if "django_cache" not in connection.introspection.table_names():
            call_command("createcachetable", "django_cache", verbosity=0)


def test_approved_choices_are_exactly_hours_then_one_through_fourteen_days():
    assert APPROVED_RECOVERY_RETENTION_SECONDS == (
        3600,
        10800,
        21600,
        43200,
        *(days * 86400 for days in range(1, 15)),
    )
    assert recovery_retention_choices() == APPROVED_RECOVERY_RETENTION_SECONDS


def test_choices_are_capped_by_cookie_age_and_policy_maximum():
    assert recovery_retention_choices(3 * 86400)[-1] == 3 * 86400
    assert recovery_retention_choices(30 * 86400)[-1] == MAX_RECOVERY_RETENTION_SECONDS
    with pytest.raises(ImproperlyConfigured):
        recovery_retention_choices(3599)


def test_absent_or_corrupt_session_value_uses_twelve_hour_default():
    session = DictSession()
    assert get_recovery_retention_seconds(session) == DEFAULT_RECOVERY_RETENTION_SECONDS

    for corrupt_value in (True, "43200", 12.5, 0, 15 * 86400, None):
        session[RECOVERY_RETENTION_SESSION_KEY] = corrupt_value
        assert get_recovery_retention_seconds(session) == DEFAULT_RECOVERY_RETENTION_SECONDS


def test_default_respects_a_shorter_cookie_cap_using_an_approved_choice():
    assert get_recovery_retention_seconds(DictSession(), session_cookie_age=6 * 3600) == 6 * 3600


def test_empty_workspace_stores_preference_without_touching_a_cache():
    session = DictSession()
    with patch.object(CacheBackend, "touch_postgres", autospec=True) as touch:
        results = set_recovery_retention(session, 3600)

    assert results == {}
    assert session[RECOVERY_RETENTION_SESSION_KEY] == 3600
    assert session.modified is True
    touch.assert_not_called()


def test_invalid_preference_is_rejected_without_mutation():
    session = DictSession()
    with pytest.raises(ValueError):
        set_recovery_retention(session, 2 * 3600)
    assert RECOVERY_RETENTION_SESSION_KEY not in session


def test_each_saved_slot_is_touched_once_without_loading_or_rewriting_payloads():
    session = DictSession()
    index = WorkspaceIndex(session)
    index.set_slot_size(0, 100)
    index.set_slot_size(1, 200)

    with (
        patch.object(CacheBackend, "touch_postgres", autospec=True, side_effect=[True, False]) as touch,
        patch.object(CacheBackend, "get", autospec=True, side_effect=AssertionError("must not hydrate")),
        patch.object(CacheBackend, "set", autospec=True, side_effect=AssertionError("must not rewrite")),
    ):
        results = set_recovery_retention(session, 6 * 3600)

    assert results == {0: True, 1: False}
    assert session[RECOVERY_RETENTION_SESSION_KEY] == 6 * 3600
    assert [args.args[1:] for args in touch.call_args_list] == [
        ("system_data:session-key:0", 6 * 3600),
        ("system_data:session-key:1", 6 * 3600),
    ]


def test_partial_disappearance_does_not_rollback_success_or_preference():
    session = DictSession()
    index = WorkspaceIndex(session)
    index.set_slot_size(0, 100)
    index.set_slot_size(1, 200)

    with patch.object(CacheBackend, "touch_postgres", autospec=True, side_effect=[True, False]):
        results = set_recovery_retention(session, 3 * 3600)

    assert results == {0: True, 1: False}
    assert get_recovery_retention_seconds(session) == 3 * 3600


@pytest.mark.django_db
def test_expired_database_row_is_reported_missing_and_is_not_revived(database_cache_table):
    session = DictSession()
    index = WorkspaceIndex(session)
    index.set_slot_size(0, 100)
    index.set_slot_size(1, 200)
    cache = caches["postgres"]
    cache.set("system_data:session-key:0", {"payload": "live"}, timeout=3600)
    cache.set("system_data:session-key:1", {"payload": "expired"}, timeout=-1)

    results = set_recovery_retention(session, 12 * 3600)

    assert results == {0: True, 1: False}
    assert cache.get("system_data:session-key:0") == {"payload": "live"}
    assert cache.get("system_data:session-key:1") is None
