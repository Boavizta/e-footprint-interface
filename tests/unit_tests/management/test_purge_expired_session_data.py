"""Database tests for physical removal of expired cache and session rows."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier, Lock
from unittest.mock import patch

import pytest
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.management.commands.purge_expired_session_data import PurgeResult, purge_expired_session_data


@pytest.fixture(scope="module", autouse=True)
def database_cache_table(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        if "django_cache" not in connection.introspection.table_names():
            call_command("createcachetable", "django_cache", verbosity=0)


@pytest.fixture(autouse=True)
def clean_rows(db):
    caches["postgres"].clear()
    Session.objects.all().delete()


def _cache_row_count() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM django_cache")
        return cursor.fetchone()[0]


class AtomicRows:
    """Barrier-controlled stand-in for an atomic conditional database delete."""

    def __init__(self, count: int):
        self._count = count
        self._barrier = Barrier(2)
        self._lock = Lock()

    def delete_once(self) -> int:
        self._barrier.wait(timeout=5)
        with self._lock:
            deleted = self._count
            self._count = 0
            return deleted


class AtomicSessionQuery:
    def __init__(self, rows: AtomicRows):
        self._rows = rows

    def delete(self):
        deleted = self._rows.delete_once()
        return deleted, {"sessions.Session": deleted}


@pytest.mark.django_db
def test_purge_removes_only_expired_cache_and_session_rows():
    cache = caches["postgres"]
    cache.set("expired-cache", "private payload", timeout=-1)
    cache.set("live-cache", "keep", timeout=3600)
    Session.objects.create(
        session_key="expired-session",
        session_data="private session payload",
        expire_date=timezone.now() - timedelta(seconds=1),
    )
    Session.objects.create(
        session_key="live-session",
        session_data="keep",
        expire_date=timezone.now() + timedelta(hours=1),
    )

    result = purge_expired_session_data()

    assert result.cache_rows == 1
    assert result.session_rows == 1
    assert _cache_row_count() == 1
    assert cache.get("live-cache") == "keep"
    assert list(Session.objects.values_list("session_key", flat=True)) == ["live-session"]


@pytest.mark.django_db
def test_repeated_cleanup_is_idempotent():
    caches["postgres"].set("expired-cache", "payload", timeout=-1)
    Session.objects.create(
        session_key="expired-session",
        session_data="payload",
        expire_date=timezone.now() - timedelta(seconds=1),
    )

    first = purge_expired_session_data()
    second = purge_expired_session_data()

    assert (first.cache_rows, first.session_rows) == (1, 1)
    assert (second.cache_rows, second.session_rows) == (0, 0)


def test_overlapping_cleanup_reports_each_atomic_deletion_exactly_once():
    cache_rows = AtomicRows(3)
    session_rows = AtomicRows(2)

    def delete_cache_rows(_backend, _now):
        return cache_rows.delete_once()

    def filter_sessions(**_kwargs):
        return AtomicSessionQuery(session_rows)

    with (
        patch.object(CacheBackend, "delete_expired_postgres", autospec=True, side_effect=delete_cache_rows),
        patch.object(Session.objects, "filter", side_effect=filter_sessions),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = [executor.submit(purge_expired_session_data) for _ in range(2)]
        results = [future.result(timeout=5) for future in futures]

    assert sum(result.cache_rows for result in results) == 3
    assert sum(result.session_rows for result in results) == 2
    assert all(result.duration_ms >= 0 for result in results)


@pytest.mark.django_db
def test_purge_removes_a_session_that_expired_earlier_in_the_current_second():
    now = timezone.now().replace(microsecond=900_000)
    Session.objects.create(
        session_key="same-second-expired-session",
        session_data="payload",
        expire_date=now - timedelta(microseconds=400_000),
    )

    with patch("model_builder.management.commands.purge_expired_session_data.timezone.now", return_value=now):
        result = purge_expired_session_data()

    assert result.session_rows == 1
    assert not Session.objects.filter(session_key="same-second-expired-session").exists()


@pytest.mark.django_db
def test_command_reports_counts_and_duration_without_identifiers_or_payloads():
    caches["postgres"].set("secret-cache-key", "secret payload", timeout=-1)
    Session.objects.create(
        session_key="secret-session-key",
        session_data="secret session payload",
        expire_date=timezone.now() - timedelta(seconds=1),
    )
    stdout = StringIO()

    call_command("purge_expired_session_data", stdout=stdout)

    output = stdout.getvalue()
    assert "cache_rows=1 session_rows=1 duration_ms=" in output
    assert "secret" not in output


def test_repeat_mode_purges_immediately_then_waits_for_the_configured_interval():
    result = PurgeResult(cache_rows=0, session_rows=0, duration_ms=1.0)
    with (
        patch(
            "model_builder.management.commands.purge_expired_session_data.purge_expired_session_data",
            return_value=result,
        ) as purge,
        patch(
            "model_builder.management.commands.purge_expired_session_data.time.sleep",
            side_effect=KeyboardInterrupt,
        ) as sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        call_command("purge_expired_session_data", repeat_interval=3600, stdout=StringIO())

    purge.assert_called_once_with()
    sleep.assert_called_once_with(3600)
