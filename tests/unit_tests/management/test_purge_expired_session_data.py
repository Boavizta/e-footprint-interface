"""Database tests for physical removal of expired cache and session rows."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

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
def test_repeated_or_overlapping_cleanup_is_idempotent():
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
