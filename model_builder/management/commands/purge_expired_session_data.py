"""Physically delete expired database-cache and Django-session rows."""

import time
from dataclasses import dataclass

from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from model_builder.adapters.repositories.cache_backend import CacheBackend


@dataclass(frozen=True)
class PurgeResult:
    """Aggregate, non-sensitive outcome of one purge pass."""

    cache_rows: int
    session_rows: int
    duration_ms: float


def purge_expired_session_data() -> PurgeResult:
    """Delete expired rows once; concurrent invocations are safe and idempotent."""
    started = time.perf_counter()
    now = timezone.now()
    cache_rows = CacheBackend().delete_expired_postgres(now)
    session_rows, _details = Session.objects.filter(expire_date__lt=now).delete()
    duration_ms = (time.perf_counter() - started) * 1000
    return PurgeResult(cache_rows=cache_rows, session_rows=session_rows, duration_ms=duration_ms)


class Command(BaseCommand):
    """Run one purge pass or an immediate-and-repeating supervised loop."""

    help = "Delete expired recovery-cache and Django-session rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repeat-interval",
            type=int,
            help="Repeat forever at this interval in seconds after an immediate first purge.",
        )

    def handle(self, *args, **options):
        repeat_interval = options["repeat_interval"]
        if repeat_interval is not None and repeat_interval < 1:
            raise CommandError("--repeat-interval must be at least one second.")

        while True:
            result = purge_expired_session_data()
            self.stdout.write(
                "Expired session-data purge: "
                f"cache_rows={result.cache_rows} session_rows={result.session_rows} "
                f"duration_ms={result.duration_ms:.1f}"
            )
            if repeat_interval is None:
                return
            time.sleep(repeat_interval)
