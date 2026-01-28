"""Middleware for monitoring session save performance.

This middleware runs in all environments (including production) to provide
visibility into session save times, which can be a significant performance bottleneck.

Note: JSON payload size computation and limit enforcement is handled by
SessionSystemRepository.save_system_data(). This middleware only times
the actual database write.
"""
import time
from efootprint.logger import logger


class SessionPerformanceMiddleware:
    """Middleware that logs session save timing.

    This should be placed AFTER SessionMiddleware in MIDDLEWARE list so that
    the session is already initialized when this middleware runs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Wrap session.save to measure its timing
        if hasattr(request, "session"):
            original_save = request.session.save

            def timed_save(*args, **kwargs):
                start = time.perf_counter()
                result = original_save(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(f"Session DB write took {elapsed_ms:.1f} ms")
                return result

            request.session.save = timed_save

        return self.get_response(request)
