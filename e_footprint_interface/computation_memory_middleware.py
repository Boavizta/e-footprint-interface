"""Observation-only memory diagnostics for model-builder reactive computations."""

import json
import os
from time import perf_counter, process_time
import uuid

from django.urls import Resolver404, resolve
from efootprint.abstract_modeling_classes.reactive_core import observe_computations
from efootprint.logger import logger

from e_footprint_interface import runtime_memory


SAMPLE_EVERY_SLOTS = 16
NEAR_LIMIT_WINDOW_BYTES = 256 * runtime_memory.MIB
HIGH_WATER_BAND_BYTES = 128 * runtime_memory.MIB
LARGE_SAMPLE_JUMP_BYTES = 128 * runtime_memory.MIB


def _safe_route(request) -> str:
    match = getattr(request, "resolver_match", None)
    if match is None:
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return "model_builder/<unresolved>"
    return match.route or "model_builder/<root>"


class ComputationMemoryMonitor:
    """Count every reactive completion and sample memory without changing request behavior."""

    def __init__(
        self,
        *,
        route: str,
        method: str,
        mode: str = "observe",
        log=logger,
        usage_pattern_count: int | None = None,
        modeled_hours: int | None = None,
        attribution_request: bool = False,
    ):
        self.route = route
        self.method = method
        self.mode = runtime_memory.parse_guard_mode(mode)
        self.log = log
        self.request_id = uuid.uuid4().hex
        self.usage_pattern_count = usage_pattern_count
        self.modeled_hours = modeled_hours
        self.attribution_matrix_cached = True if attribution_request else None
        self.started_at = perf_counter()
        self.cpu_started_at = process_time()
        self.completed_slots = 0
        self.sample_count = 0
        self.callback_wall_ms = 0.0
        self.max_callback_ms = 0.0
        self.memory_read_ms = 0.0
        self.logging_ms = 0.0
        self.peak_working_set_bytes = 0
        self.largest_sample_jump_bytes = 0
        self._last_sample: runtime_memory.MemorySnapshot | None = None
        self._logged_high_water_band = -1
        self._sample_and_emit("start")

    def __call__(self, slot) -> None:
        callback_started_at = perf_counter()
        try:
            self.completed_slots += 1
            if slot.diagnostic_name.endswith(".impact_repartition_matrix"):
                self.attribution_matrix_cached = False
            if self._should_sample():
                self._sample_progress(slot.diagnostic_name)
        finally:
            callback_ms = 1000 * (perf_counter() - callback_started_at)
            self.callback_wall_ms += callback_ms
            self.max_callback_ms = max(self.max_callback_ms, callback_ms)

    def _should_sample(self) -> bool:
        if self._last_sample is not None and self._last_sample.working_set_bytes is not None:
            limit = runtime_memory.COMPUTATION_MEMORY_LIMIT_BYTES
            if limit is not None and self._last_sample.working_set_bytes >= limit - NEAR_LIMIT_WINDOW_BYTES:
                return True
        return self.completed_slots % SAMPLE_EVERY_SLOTS == 0

    def _read_snapshot(self) -> runtime_memory.MemorySnapshot:
        started_at = perf_counter()
        snapshot = runtime_memory.read_memory_snapshot()
        self.memory_read_ms += 1000 * (perf_counter() - started_at)
        self.sample_count += 1
        if snapshot.working_set_bytes is not None:
            self.peak_working_set_bytes = max(self.peak_working_set_bytes, snapshot.working_set_bytes)
        return snapshot

    def _sample_progress(self, diagnostic_name: str) -> None:
        snapshot = self._read_snapshot()
        jump = 0
        if (
            snapshot.working_set_bytes is not None
            and self._last_sample is not None
            and self._last_sample.working_set_bytes is not None
        ):
            jump = max(0, snapshot.working_set_bytes - self._last_sample.working_set_bytes)
            self.largest_sample_jump_bytes = max(self.largest_sample_jump_bytes, jump)
        self._last_sample = snapshot

        working_set = snapshot.working_set_bytes
        high_water_band = working_set // HIGH_WATER_BAND_BYTES if working_set is not None else -1
        crossed_band = high_water_band > self._logged_high_water_band
        large_jump = jump >= LARGE_SAMPLE_JUMP_BYTES
        if crossed_band or large_jump:
            self._logged_high_water_band = max(self._logged_high_water_band, high_water_band)
            extras = {"sample_jump_mb": round(jump / runtime_memory.MIB, 1)}
            if large_jump:
                extras["slot"] = diagnostic_name
            self._emit("progress", snapshot, **extras)

    def _sample_and_emit(self, event: str) -> None:
        snapshot = self._read_snapshot()
        self._last_sample = snapshot
        if snapshot.working_set_bytes is not None:
            self._logged_high_water_band = snapshot.working_set_bytes // HIGH_WATER_BAND_BYTES
        self._emit(event, snapshot)

    def finish(self, status: str) -> None:
        self._sample_and_emit(status)

    def _emit(self, event: str, snapshot: runtime_memory.MemorySnapshot, **extras) -> None:
        record = {
            "event": event,
            "request_id": self.request_id,
            "route": self.route,
            "method": self.method,
            "mode": self.mode,
            "pid": os.getpid(),
            "elapsed_ms": round(1000 * (perf_counter() - self.started_at), 1),
            "cpu_ms": round(1000 * (process_time() - self.cpu_started_at), 1),
            "completed_slots": self.completed_slots,
            "sample_count": self.sample_count,
            "usage_pattern_count": self.usage_pattern_count,
            "modeled_hours": self.modeled_hours,
            "attribution_matrix_cached": self.attribution_matrix_cached,
            "peak_working_set_mb": round(self.peak_working_set_bytes / runtime_memory.MIB, 1),
            "largest_sample_jump_mb": round(self.largest_sample_jump_bytes / runtime_memory.MIB, 1),
            "callback_wall_ms": round(self.callback_wall_ms, 3),
            "max_callback_ms": round(self.max_callback_ms, 3),
            "memory_read_ms": round(self.memory_read_ms, 3),
            "logging_ms": round(self.logging_ms, 3),
            **snapshot.as_mebibytes(),
            **extras,
        }
        started_at = perf_counter()
        self.log.info("computation_memory %s", json.dumps(record, sort_keys=True, separators=(",", ":")))
        self.logging_ms += 1000 * (perf_counter() - started_at)


class ComputationMemoryMiddleware:
    """Install diagnostics before any model-builder view can hydrate its ``ModelWeb``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.startswith("/model_builder/") or runtime_memory.COMPUTATION_MEMORY_GUARD_MODE == "off":
            return self.get_response(request)

        route = _safe_route(request)
        monitor = ComputationMemoryMonitor(
            route=route,
            method=request.method,
            mode=runtime_memory.COMPUTATION_MEMORY_GUARD_MODE,
            attribution_request=route.endswith("sankey-diagram/"),
        )
        request.META["efootprint.memory_request_id"] = monitor.request_id
        try:
            with observe_computations(monitor):
                response = self.get_response(request)
        except Exception:
            monitor.finish("abort")
            raise
        monitor.finish("complete")
        return response
