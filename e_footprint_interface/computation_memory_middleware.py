"""Memory diagnostics and recoverable enforcement for model-builder computations."""

import base64
import json
import os
import uuid
from time import perf_counter, process_time

from django.urls import Resolver404, resolve
from efootprint.abstract_modeling_classes.reactive_core import observe_computations
from efootprint.logger import logger
import psutil
import zstandard as zstd

from e_footprint_interface import runtime_memory
from model_builder.adapters.views.exception_handling import render_exception_modal
from model_builder.domain.exceptions import ComputationMemoryLimitExceeded
from model_builder.domain.model_hydration_observer import observe_model_hydrations


SAMPLE_EVERY_SLOTS = 16
NEAR_LIMIT_WINDOW_BYTES = 256 * runtime_memory.MIB
HIGH_WATER_BAND_BYTES = 128 * runtime_memory.MIB
LARGE_SAMPLE_JUMP_BYTES = 128 * runtime_memory.MIB
FLOAT32_BYTES = 4


def _safe_route(request) -> str:
    match = getattr(request, "resolver_match", None)
    if match is None:
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return "model_builder/<unresolved>"
    return match.route or "model_builder/<root>"


def _emit_monitor_error(
    *, log, phase: str, route: str, method: str, mode: str, error: Exception, request_id=None
) -> None:
    record = {
        "event": "monitor_error",
        "phase": phase,
        "request_id": request_id,
        "route": route,
        "method": method,
        "mode": mode,
        "pid": os.getpid(),
        "error_type": type(error).__name__,
    }
    try:
        log.error("computation_memory %s", json.dumps(record, sort_keys=True, separators=(",", ":")))
    except Exception:
        pass


class ComputationMemoryMonitor:
    """Observe reactive completions and trip once when enforce mode reaches its limit."""

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
        self.attribution_request = attribution_request
        self.attribution_matrix_cached = None
        self._measure_overhead = method == "PROFILE"
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
        self._process = psutil.Process(os.getpid())
        self._last_working_set_bytes: int | None = None
        self._logged_high_water_band = -1
        self._would_abort_emitted = False
        self._limit_exceeded = False
        self._abort_emitted = False
        self._finished = False
        self._sample_and_emit("start")

    @staticmethod
    def _hourly_value_count(hourly_values) -> int | None:
        form_inputs = getattr(hourly_values, "form_inputs", None)
        if form_inputs is not None:
            days_per_unit = {"day": 1, "month": 30, "year": 365}
            try:
                return int(
                    float(form_inputs["modeling_duration_value"])
                    * days_per_unit[form_inputs["modeling_duration_unit"]]
                    * 24
                )
            except (KeyError, TypeError, ValueError):
                return None

        compressed_data = getattr(hourly_values, "json_compressed_value_data", None)
        if compressed_data is not None:
            try:
                compressed_prefix = base64.b64decode(compressed_data["compressed_values"][:24])
                byte_count = zstd.frame_content_size(compressed_prefix)
            except (KeyError, TypeError, ValueError, zstd.ZstdError):
                return None
            if byte_count in {zstd.CONTENTSIZE_ERROR, zstd.CONTENTSIZE_UNKNOWN} or byte_count % FLOAT32_BYTES:
                return None
            return byte_count // FLOAT32_BYTES

        try:
            return len(hourly_values)
        except (TypeError, ValueError):
            return None

    def model_hydrated(self, model_web) -> None:
        usage_patterns = model_web.usage_patterns
        edge_usage_patterns = model_web.edge_usage_patterns
        self.usage_pattern_count = len(usage_patterns) + len(edge_usage_patterns)
        pattern_hours = [
            self._hourly_value_count(pattern.modeling_obj.hourly_usage_journey_starts) for pattern in usage_patterns
        ]
        pattern_hours.extend(
            self._hourly_value_count(pattern.modeling_obj.hourly_edge_usage_journey_starts)
            for pattern in edge_usage_patterns
        )
        self.modeled_hours = (
            max(pattern_hours, default=0) if all(hours is not None for hours in pattern_hours) else None
        )

    def __call__(self, slot) -> None:
        if not self._measure_overhead:
            self._observe_slot(slot)
            return

        callback_started_at = perf_counter()
        try:
            self._observe_slot(slot)
        finally:
            callback_ms = 1000 * (perf_counter() - callback_started_at)
            self.callback_wall_ms += callback_ms
            self.max_callback_ms = max(self.max_callback_ms, callback_ms)

    def _observe_slot(self, slot) -> None:
        self.completed_slots += 1
        if self.attribution_request and slot.diagnostic_name.endswith(
            (".impact_repartition_rows", ".impact_repartition_matrix")
        ):
            self.attribution_matrix_cached = False
        if self._should_sample():
            self._sample_progress(slot.diagnostic_name)

    def _should_sample(self) -> bool:
        if self._limit_exceeded or (self.mode == "observe" and self._would_abort_emitted):
            return self.completed_slots % SAMPLE_EVERY_SLOTS == 0
        if self._last_working_set_bytes is not None:
            limit = runtime_memory.COMPUTATION_MEMORY_LIMIT_BYTES
            if limit is not None and self._last_working_set_bytes >= limit - NEAR_LIMIT_WINDOW_BYTES:
                return True
        return self.completed_slots % SAMPLE_EVERY_SLOTS == 0

    def _track_working_set(self, working_set: int | None) -> None:
        if working_set is not None:
            self.peak_working_set_bytes = max(self.peak_working_set_bytes, working_set)

    def _read_working_set(self) -> int | None:
        started_at = perf_counter() if self._measure_overhead else None
        working_set = runtime_memory.read_cgroup_working_set_bytes()
        if started_at is not None:
            self.memory_read_ms += 1000 * (perf_counter() - started_at)
        self.sample_count += 1
        self._track_working_set(working_set)
        return working_set

    def _read_snapshot(self, *, count_sample: bool) -> runtime_memory.MemorySnapshot:
        started_at = perf_counter() if self._measure_overhead else None
        snapshot = runtime_memory.read_memory_snapshot(self._process)
        if started_at is not None:
            self.memory_read_ms += 1000 * (perf_counter() - started_at)
        if count_sample:
            self.sample_count += 1
        self._track_working_set(snapshot.working_set_bytes)
        return snapshot

    def _sample_progress(self, diagnostic_name: str) -> None:
        working_set = self._read_working_set()
        jump = 0
        if working_set is not None and self._last_working_set_bytes is not None:
            jump = max(0, working_set - self._last_working_set_bytes)
            self.largest_sample_jump_bytes = max(self.largest_sample_jump_bytes, jump)
        self._last_working_set_bytes = working_set

        high_water_band = working_set // HIGH_WATER_BAND_BYTES if working_set is not None else -1
        crossed_band = high_water_band > self._logged_high_water_band
        large_jump = jump >= LARGE_SAMPLE_JUMP_BYTES
        limit = runtime_memory.COMPUTATION_MEMORY_LIMIT_BYTES
        would_abort = (
            self.mode == "observe"
            and not self._would_abort_emitted
            and limit is not None
            and working_set is not None
            and working_set >= limit
        )
        must_abort = (
            self.mode == "enforce"
            and not self._limit_exceeded
            and limit is not None
            and working_set is not None
            and working_set >= limit
        )
        if crossed_band or large_jump or would_abort or must_abort:
            self._logged_high_water_band = max(self._logged_high_water_band, high_water_band)
            extras = {"sample_jump_mb": round(jump / runtime_memory.MIB, 1)}
            if large_jump:
                extras["slot"] = diagnostic_name
            if would_abort:
                self._would_abort_emitted = True
            if must_abort:
                # Latch before logging or raising. Rollback computations may re-enter this callback
                # while the working set is still high and must not trip the request a second time.
                self._limit_exceeded = True
                try:
                    self._emit("abort", self._read_snapshot(count_sample=False), **extras)
                    self._abort_emitted = True
                finally:
                    # A diagnostic snapshot or logger failure must never cancel the safety trip.
                    raise ComputationMemoryLimitExceeded(
                        working_set_bytes=working_set,
                        limit_bytes=limit,
                        capacity_bytes=runtime_memory.CGROUP_CAPACITY_BYTES,
                    )
            event = "would_abort" if would_abort else "progress"
            self._emit(event, self._read_snapshot(count_sample=False), **extras)

    def _sample_and_emit(self, event: str) -> None:
        snapshot = self._read_snapshot(count_sample=True)
        self._last_working_set_bytes = snapshot.working_set_bytes
        if snapshot.working_set_bytes is not None:
            self._logged_high_water_band = snapshot.working_set_bytes // HIGH_WATER_BAND_BYTES
        self._emit(event, snapshot)

    def finish(self, status: str) -> None:
        if self._finished:
            return
        self._finished = True
        if self._limit_exceeded:
            status = "abort"
        if status == "complete" and self.attribution_request and self.attribution_matrix_cached is None:
            self.attribution_matrix_cached = True
        if status != "abort" or not self._abort_emitted:
            self._sample_and_emit(status)

    def _emit(self, event: str, snapshot: runtime_memory.MemorySnapshot, **extras) -> None:
        record = {
            "event": event,
            "request_id": self.request_id,
            "route": self.route,
            "method": self.method,
            "mode": self.mode,
            "pid": os.getpid(),
            "limit_mb": (
                runtime_memory.COMPUTATION_MEMORY_LIMIT_BYTES / runtime_memory.MIB
                if runtime_memory.COMPUTATION_MEMORY_LIMIT_BYTES is not None
                else None
            ),
            "elapsed_ms": round(1000 * (perf_counter() - self.started_at), 1),
            "cpu_ms": round(1000 * (process_time() - self.cpu_started_at), 1),
            "completed_slots": self.completed_slots,
            "sample_count": self.sample_count,
            "usage_pattern_count": self.usage_pattern_count,
            "modeled_hours": self.modeled_hours,
            "attribution_matrix_cached": self.attribution_matrix_cached,
            "peak_working_set_mb": round(self.peak_working_set_bytes / runtime_memory.MIB, 1),
            "largest_sample_jump_mb": round(self.largest_sample_jump_bytes / runtime_memory.MIB, 1),
            **snapshot.as_mebibytes(),
            **extras,
        }
        started_at = perf_counter() if self._measure_overhead else None
        self.log.info("computation_memory %s", json.dumps(record, sort_keys=True, separators=(",", ":")))
        if started_at is not None:
            self.logging_ms += 1000 * (perf_counter() - started_at)


class _TelemetryBoundary:
    """Fail open on telemetry defects while preserving the intentional capacity exception."""

    def __init__(self, monitor: ComputationMemoryMonitor):
        self.monitor = monitor
        self.failed = False

    @property
    def request_id(self) -> str:
        return self.monitor.request_id

    def _run(self, phase: str, callback, *args) -> None:
        if self.failed:
            return
        try:
            callback(*args)
        except ComputationMemoryLimitExceeded:
            raise
        except Exception as error:
            self.failed = True
            _emit_monitor_error(
                log=self.monitor.log,
                phase=phase,
                route=self.monitor.route,
                method=self.monitor.method,
                mode=self.monitor.mode,
                error=error,
                request_id=self.monitor.request_id,
            )

    def model_hydrated(self, model_web) -> None:
        self._run("model_hydrated", self.monitor.model_hydrated, model_web)

    def __call__(self, slot) -> None:
        self._run("computation_callback", self.monitor, slot)

    def finish(self, status: str) -> None:
        self._run("finish", self.monitor.finish, status)


class ComputationMemoryMiddleware:
    """Install diagnostics before any model-builder view can hydrate its ``ModelWeb``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.startswith("/model_builder/") or runtime_memory.COMPUTATION_MEMORY_GUARD_MODE == "off":
            return self.get_response(request)

        mode = runtime_memory.COMPUTATION_MEMORY_GUARD_MODE
        route = "model_builder/<monitor-setup>"
        try:
            route = _safe_route(request)
            monitor = ComputationMemoryMonitor(
                route=route,
                method=request.method,
                mode=mode,
                attribution_request=route.endswith("sankey-diagram/"),
            )
        except Exception as error:
            _emit_monitor_error(
                log=logger,
                phase="setup",
                route=route,
                method=request.method,
                mode=mode,
                error=error,
            )
            return self.get_response(request)

        telemetry = _TelemetryBoundary(monitor)
        request.META["efootprint.memory_request_id"] = monitor.request_id
        request._efootprint_memory_monitor = telemetry
        try:
            with observe_model_hydrations(telemetry.model_hydrated), observe_computations(telemetry):
                response = self.get_response(request)
        except ComputationMemoryLimitExceeded as error:
            telemetry.finish("abort")
            return render_exception_modal(request, error)
        except Exception:
            try:
                telemetry.finish("abort")
            except Exception as error:
                _emit_monitor_error(
                    log=monitor.log,
                    phase="finish",
                    route=monitor.route,
                    method=monitor.method,
                    mode=monitor.mode,
                    error=error,
                    request_id=monitor.request_id,
                )
            raise
        telemetry.finish("abort" if response.status_code >= 500 else "complete")
        return response

    def process_exception(self, request, exception):
        monitor = getattr(request, "_efootprint_memory_monitor", None)
        if monitor is not None:
            try:
                monitor.finish("abort")
            except Exception:
                pass
        if isinstance(exception, ComputationMemoryLimitExceeded):
            return render_exception_modal(request, exception)
        return None
