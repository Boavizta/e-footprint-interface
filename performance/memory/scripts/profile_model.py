"""Measure memory across representative e-footprint calculation stages.

Run this inside the production image. The source model is mounted separately so
large or sensitive fixtures do not become repository test data.
"""

import argparse
import gc
import json
import os
import platform
import sys
import threading
import time
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path

import psutil


MIB = 1024 * 1024
SAMPLE_INTERVAL_SECONDS = 0.005
CGROUP_CURRENT_PATHS = (Path("/sys/fs/cgroup/memory.current"), Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"))
CGROUP_PEAK_PATHS = (Path("/sys/fs/cgroup/memory.peak"), Path("/sys/fs/cgroup/memory/memory.max_usage_in_bytes"))
CGROUP_LIMIT_PATHS = (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
CGROUP_STAT_PATHS = (Path("/sys/fs/cgroup/memory.stat"), Path("/sys/fs/cgroup/memory/memory.stat"))
PROFILE_STARTED_AT = time.perf_counter()

if Path("/app/model_builder").is_dir():
    sys.path.insert(0, "/app")


def _read_first_integer(paths):
    for path in paths:
        try:
            raw_value = path.read_text().strip()
            if raw_value != "max":
                value = int(raw_value)
                if value < 1 << 60:
                    return value
        except (OSError, ValueError):
            continue
    return None


def _smaps_rollup_mb():
    values = {}
    try:
        for line in Path(f"/proc/{os.getpid()}/smaps_rollup").read_text().splitlines():
            key, separator, remainder = line.partition(":")
            if separator and key in {"Rss", "Pss", "Private_Clean", "Private_Dirty"}:
                values[key] = int(remainder.split()[0]) / 1024
    except (OSError, ValueError):
        return {}
    values["Uss"] = values.get("Private_Clean", 0) + values.get("Private_Dirty", 0)
    return {key.lower() + "_mb": round(value, 1) for key, value in values.items()}


def _read_inactive_file_bytes():
    for path in CGROUP_STAT_PATHS:
        try:
            values = dict(line.split() for line in path.read_text().splitlines())
            key = "inactive_file" if "inactive_file" in values else "total_inactive_file"
            return int(values[key])
        except (KeyError, OSError, ValueError):
            continue
    return None


class MemorySampler:
    def __init__(self):
        self.process = psutil.Process()
        self.stage = "startup"
        self.stage_peaks = {}
        self.milestones = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _current(self):
        process_rss_mb = self.process.memory_info().rss / MIB
        cgroup_current_bytes = _read_first_integer(CGROUP_CURRENT_PATHS)
        inactive_file_bytes = _read_inactive_file_bytes()
        cgroup_current_mb = cgroup_current_bytes / MIB if cgroup_current_bytes is not None else None
        inactive_file_mb = inactive_file_bytes / MIB if inactive_file_bytes is not None else None
        working_set_mb = (
            max(0, cgroup_current_bytes - inactive_file_bytes) / MIB
            if cgroup_current_bytes is not None and inactive_file_bytes is not None
            else None
        )
        return {
            "process_rss_mb": process_rss_mb,
            "cgroup_current_mb": cgroup_current_mb,
            "cgroup_inactive_file_mb": inactive_file_mb,
            "cgroup_working_set_mb": working_set_mb,
        }

    def _sample(self):
        while not self._stop.is_set():
            current = self._current()
            peak = self.stage_peaks.setdefault(self.stage, {})
            for metric, value in current.items():
                if value is not None:
                    peak[metric] = max(peak.get(metric, 0), value)
            time.sleep(SAMPLE_INTERVAL_SECONDS)

    def start(self):
        self._thread.start()

    def begin(self, stage):
        self.stage = stage

    def snapshot(self, stage, event):
        current = self._current()
        self.stage_peaks.setdefault(stage, {key: value or 0 for key, value in current.items()})
        milestone = {
            "stage": stage,
            "event": event,
            "elapsed_seconds": round(time.perf_counter() - PROFILE_STARTED_AT, 3),
            **{key: round(value, 1) if value is not None else None for key, value in current.items()},
            **_smaps_rollup_mb(),
        }
        self.milestones.append(milestone)
        print("MILESTONE " + json.dumps(milestone, sort_keys=True), flush=True)

    def stop(self):
        self._stop.set()
        self._thread.join()


def add_usage_patterns(data, target_count):
    patterns = data["EdgeUsagePattern"]
    if target_count < len(patterns):
        raise ValueError(f"Model already has {len(patterns)} usage patterns; requested {target_count}")
    original = next(iter(patterns.values()))
    system = next(iter(data["System"].values()))
    for index in range(len(patterns), target_count):
        pattern = deepcopy(original)
        pattern_id = f"memory-profile-pattern-{index + 1}"
        pattern["id"] = pattern_id
        pattern["name"] = f"Memory profile usage pattern {index + 1}"
        patterns[pattern_id] = pattern
        system["edge_usage_patterns"].append(pattern_id)


def build_sankey(model_web):
    from efootprint.utils.impact_repartition.sankey import ImpactRepartitionSankey
    from model_builder.adapters.views.sankey_views import (
        ANALYSE_BY_CHIPS,
        DEFAULT_ACTIVE_COLUMNS,
        _build_sankey_payload,
        _expand_skipped_columns,
    )

    inactive = [
        chip_id
        for chip_id, _, _ in ANALYSE_BY_CHIPS
        if chip_id not in DEFAULT_ACTIVE_COLUMNS and chip_id not in ("phase", "category")
    ]
    sankey = ImpactRepartitionSankey(
        model_web.system.modeling_obj,
        skipped_impact_repartition_classes=_expand_skipped_columns(inactive),
        display_column_information=False,
    )
    payload, _ = _build_sankey_payload(sankey)
    return sankey, payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--patterns", type=int, default=2)
    parser.add_argument(
        "--scenario",
        choices=("hydrate", "results", "cold-sankey", "warm-sankey", "results-then-sankey"),
        required=True,
    )
    parser.add_argument(
        "--disable-gc-during-calculation",
        action="store_true",
        help="Match production Gunicorn, which disables automatic cyclic GC while handling a request.",
    )
    parser.add_argument(
        "--monitor-mode",
        choices=("off", "noop", "observe"),
        default="off",
        help="Install no observer, a no-op observer, or the observation-only request monitor.",
    )
    args = parser.parse_args()

    sampler = MemorySampler()
    sampler.start()
    started_at = time.perf_counter()
    sampler.snapshot("startup", "before_app_imports")
    sampler.begin("imports")

    from efootprint import __version__ as efootprint_version
    from efootprint.abstract_modeling_classes.reactive_core import observe_computations
    from e_footprint_interface.computation_memory_middleware import ComputationMemoryMonitor
    from model_builder.adapters.repositories import InMemorySystemRepository
    from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
    from model_builder.domain.entities.web_core.model_web import ModelWeb

    sampler.snapshot("imports", "after_app_imports")
    sampler.begin("input")
    data = json.loads(args.model.read_text())
    add_usage_patterns(data, args.patterns)
    data = SessionSystemRepository.upgrade_system_data(data)
    sampler.snapshot("input", "after_input_upgrade")

    if args.disable_gc_during_calculation:
        gc.disable()
    noop_callback_count = 0
    monitor = None
    calculation_elapsed_seconds = 0.0

    def noop_callback(_slot):
        nonlocal noop_callback_count
        noop_callback_count += 1

    observer_scope = nullcontext()
    if args.monitor_mode == "noop":
        observer_scope = observe_computations(noop_callback)
    elif args.monitor_mode == "observe":
        monitor = ComputationMemoryMonitor(
            route=f"profile/{args.scenario}",
            method="PROFILE",
            usage_pattern_count=args.patterns,
            attribution_request="sankey" in args.scenario,
        )
        observer_scope = observe_computations(monitor)

    with observer_scope:
        sampler.begin("hydrate")
        model_web = ModelWeb(InMemorySystemRepository(), data)
        sampler.snapshot("hydrate", "after_hydration")

        result = sankey = payload = None
        if args.scenario in {"results", "results-then-sankey"}:
            sampler.begin("results")
            calculation_started_at = time.perf_counter()
            result = model_web.system_emissions
            calculation_elapsed_seconds += time.perf_counter() - calculation_started_at
            sampler.snapshot("results", "after_results")

        if args.scenario == "results-then-sankey":
            sampler.begin("between_requests_gc")
            del model_web, result
            result = None
            gc.collect()
            sampler.snapshot("between_requests_gc", "after_first_request_gc")
            sampler.begin("rehydrate")
            model_web = ModelWeb(InMemorySystemRepository(), deepcopy(data))
            sampler.snapshot("rehydrate", "after_second_hydration")

        if args.scenario in {"cold-sankey", "warm-sankey", "results-then-sankey"}:
            sampler.begin("cold_sankey")
            calculation_started_at = time.perf_counter()
            sankey, payload = build_sankey(model_web)
            matrix = model_web.system.modeling_obj.impact_repartition_matrix
            calculation_elapsed_seconds += time.perf_counter() - calculation_started_at
            sampler.snapshot("cold_sankey", "after_cold_sankey")
            print(
                f"MATRIX rows={len(matrix)}; SANKEY nodes={len(payload['nodes'])} links={len(payload['links'])}",
                flush=True,
            )

        if args.scenario == "warm-sankey":
            del sankey, payload
            sampler.begin("warm_sankey")
            calculation_started_at = time.perf_counter()
            sankey, payload = build_sankey(model_web)
            calculation_elapsed_seconds += time.perf_counter() - calculation_started_at
            sampler.snapshot("warm_sankey", "after_warm_sankey")

    if monitor is not None:
        monitor.finish("complete")

    sampler.begin("post_gc")
    del model_web, data, result, sankey, payload
    collected = gc.collect()
    gc.enable()
    sampler.snapshot("post_gc", "after_delete_and_full_gc")
    sampler.stop()

    cgroup_peak = _read_first_integer(CGROUP_PEAK_PATHS)
    cgroup_limit = _read_first_integer(CGROUP_LIMIT_PATHS)
    document = {
        "schema_version": 1,
        "scenario": args.scenario,
        "monitor_mode": args.monitor_mode,
        "observer_callback_count": monitor.completed_slots if monitor is not None else noop_callback_count,
        "observer_sample_count": monitor.sample_count if monitor is not None else 0,
        "observer_callback_wall_ms": round(monitor.callback_wall_ms, 3) if monitor is not None else 0,
        "observer_max_callback_ms": round(monitor.max_callback_ms, 3) if monitor is not None else 0,
        "observer_memory_read_ms": round(monitor.memory_read_ms, 3) if monitor is not None else 0,
        "observer_logging_ms": round(monitor.logging_ms, 3) if monitor is not None else 0,
        "observer_largest_sample_jump_mb": (
            round(monitor.largest_sample_jump_bytes / MIB, 1) if monitor is not None else 0
        ),
        "calculation_elapsed_seconds": round(calculation_elapsed_seconds, 3),
        "usage_patterns": args.patterns,
        "source_model": args.model.name,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "efootprint": efootprint_version,
            "pid": os.getpid(),
            "cgroup_limit_mb": round(cgroup_limit / MIB, 1) if cgroup_limit else None,
            "automatic_gc_during_calculation": not args.disable_gc_during_calculation,
        },
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "gc_collected": collected,
        "cgroup_peak_mb": round(cgroup_peak / MIB, 1) if cgroup_peak else None,
        "sampled_working_set_peak_mb": round(
            max((values.get("cgroup_working_set_mb", 0) for values in sampler.stage_peaks.values()), default=0), 1
        ),
        "stage_peaks": {
            stage: {metric: round(value, 1) for metric, value in values.items()}
            for stage, values in sampler.stage_peaks.items()
        },
        "milestones": sampler.milestones,
    }
    print("RESULT " + json.dumps(document, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
