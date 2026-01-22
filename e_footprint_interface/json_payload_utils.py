"""Utilities for JSON payload size computation with timing.

This module provides functions to compute JSON payload sizes with performance measurement,
used by both the session repository (for size limit enforcement) and the performance middleware.
"""
import json
import time
from dataclasses import dataclass
from typing import Any, Dict


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
    start = time.time()
    payload = json.dumps(data)
    size_bytes = len(payload.encode("utf-8"))
    computation_time_ms = (time.time() - start) * 1000

    return JsonSizeResult(
        size_bytes=size_bytes,
        size_mb=size_bytes / (1024 * 1024),
        computation_time_ms=computation_time_ms
    )