"""Request-scoped notification after a ``ModelWeb`` has hydrated successfully."""

from contextlib import contextmanager
from contextvars import ContextVar


_observer: ContextVar = ContextVar("model_hydration_observer", default=None)


@contextmanager
def observe_model_hydrations(callback):
    token = _observer.set(callback)
    try:
        yield
    finally:
        _observer.reset(token)


def report_model_hydrated(model_web) -> None:
    callback = _observer.get()
    if callback is not None:
        callback(model_web)
