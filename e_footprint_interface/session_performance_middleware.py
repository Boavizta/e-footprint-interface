"""Middleware for monitoring session save performance.

This middleware runs in all environments (including production) to provide
visibility into session save times, which can be a significant performance bottleneck.
"""
import json
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
        if hasattr(request, 'session'):
            original_save = request.session.save


            def timed_save(*args, **kwargs):
                # Compute payload size and measure overhead
                size_start = time.time()
                try:
                    payload = json.dumps(dict(request.session))
                    size_mb = len(payload.encode("utf-8")) / (1024 * 1024)
                    size_overhead_ms = (time.time() - size_start) * 1000
                except Exception:
                    size_mb = None
                    size_overhead_ms = None

                start = time.time()
                result = original_save(*args, **kwargs)
                elapsed_ms = (time.time() - start) * 1000

                if size_mb is not None:
                    logger.info(
                        f"Session DB write took {elapsed_ms:.1f}ms, "
                        f"payload size: {size_mb:.2f}MB (size computation: {size_overhead_ms:.1f}ms)"
                    )
                else:
                    logger.info(f"Session DB write took {elapsed_ms:.1f}ms")
                return result

            request.session.save = timed_save

        return self.get_response(request)
