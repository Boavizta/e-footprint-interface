"""Utilities for JSON payload size computation with timing.

This module provides functions to compute JSON payload sizes with performance measurement,
used by both the session repository (for size limit enforcement) and the performance middleware.
"""
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict

import orjson

# orjson hard-caps nesting at 254 levels; the stdlib encoder's depth instead
# follows sys.getrecursionlimit() (each JSON level costs ~3 Python frames). We
# raise the limit only for the rare deep-payload fallback, enough to measure
# models nested a few thousand levels. Going higher is pointless: on Python
# 3.12+ a separate C-stack guard (Py_C_RECURSION_LIMIT, independent of this
# limit) caps real depth around ~10k and raises a clean, catchable
# RecursionError beyond it — so there is no segfault risk, just a hard ceiling.
_DEEP_PAYLOAD_RECURSION_LIMIT = 20_000


@dataclass
class JsonSizeResult:
    """Result of a JSON size computation."""
    size_bytes: int
    size_mb: float
    computation_time_ms: float


def compute_json_size(data: Dict[str, Any]) -> JsonSizeResult:
    """Compute the JSON payload size of a dictionary with timing.

    Args:
        data: The dictionary to serialize and measure.

    Returns:
        JsonSizeResult containing size in bytes, size in MB, and computation time in milliseconds.
    """
    start = time.perf_counter()
    size_bytes = _serialized_size_bytes(data)
    computation_time_ms = (time.perf_counter() - start) * 1000

    return JsonSizeResult(
        size_bytes=size_bytes,
        size_mb=size_bytes / (1024 * 1024),
        computation_time_ms=computation_time_ms
    )


def _serialized_size_bytes(data: Dict[str, Any]) -> int:
    """Return the byte length of the JSON serialization of ``data``.

    Uses orjson for speed, but orjson hard-caps nesting at 254 levels and raises
    ``TypeError: Recursion limit reached`` beyond that. Deeply nested calculation
    explanations (e.g. ``explain_nested_tuples`` from summing many objects in one
    step) can exceed it, so fall back to the stdlib ``json`` encoder, whose nesting
    limit follows the interpreter recursion limit, for those payloads. A payload
    deeper than the runtime's C-stack guard allows raises RecursionError, which
    the import flow surfaces as an invalid-model error.
    """
    try:
        return len(orjson.dumps(data))
    except TypeError as orjson_error:
        if "recursion limit" not in str(orjson_error).lower():
            raise
        previous_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(previous_limit, _DEEP_PAYLOAD_RECURSION_LIMIT))
        try:
            return len(json.dumps(data).encode("utf-8"))
        finally:
            sys.setrecursionlimit(previous_limit)
