"""Run cases x models x repetitions, validate, build, compute, export, and record everything.

Usage (from the interface repo root):
    poetry run python ai_sandbox/run.py --cases 01 --models claude-haiku-5-5 --reps 1
    poetry run python ai_sandbox/run.py                      # all cases, DEFAULT_MODELS, 1 rep
    poetry run python ai_sandbox/run.py --replay runs/<run_dir>   # re-validate recorded outputs, no API call
    poetry run python ai_sandbox/run.py --dry-run cases/_handwritten_03.json   # pipeline check without an LLM

Each run writes ai_sandbox/runs/<timestamp>/<case>__<model>__r<rep>.json plus the exported model
<...>.e-f.json when the build succeeds. summary.md, summary.html and runs/index.html are produced by report.py.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pydantic import ValidationError  # noqa: E402

import providers  # noqa: E402
import report  # noqa: E402
from dsl import ModelSpec, build_system  # noqa: E402

SANDBOX = Path(__file__).parent
CASES_DIR = SANDBOX / "cases"
RUNS_DIR = SANDBOX / "runs"
SYSTEM_PROMPT = (SANDBOX / "prompts" / "system_prompt.md").read_text()


# --- Parsing and checks ----------------------------------------------------------------------

def parse_json(text: str) -> tuple[dict | None, bool, str | None]:
    """Returns (data, first_attempt_ok, error). Repairs only by stripping a code fence or surrounding prose."""
    try:
        return json.loads(text), True, None
    except json.JSONDecodeError as first_error:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0)), False, f"repaired: {first_error}"
            except json.JSONDecodeError:
                pass
        return None, False, str(first_error)


def validate_tolerating_extras(data: dict) -> tuple[ModelSpec, list[str]]:
    """Strict validation, except that unknown fields are stripped and reported instead of failing the run."""
    try:
        return ModelSpec.model_validate(data), []
    except ValidationError as error:
        extras = [e["loc"] for e in error.errors() if e["type"] == "extra_forbidden"]
        if not extras or len(extras) != len(error.errors()):
            raise
    for loc in extras:
        node = data
        for key in loc[:-1]:
            node = node[key]
        del node[loc[-1]]
    return ModelSpec.model_validate(data), [".".join(str(k) for k in loc) for loc in extras]


def structural_checks(spec: ModelSpec, checks: dict) -> dict[str, bool]:
    results = {}
    server_journeys: dict[str, set] = {}
    job_server = {j.name: j.server for j in spec.jobs}
    for journey in spec.journeys:
        for step in journey.steps:
            for job in step.jobs:
                if job_server.get(job):
                    server_journeys.setdefault(job_server[job], set()).add(journey.name)
    pattern_journeys = {p.journey for p in spec.usage_patterns}
    low_volume = any(
        (p.volume.per == "year" and p.volume.value <= 400) or (p.volume.per == "month" and p.volume.value <= 5000)
        for p in spec.usage_patterns)
    for key, expected in checks.items():
        if key == "min_journeys":
            results[key] = len(spec.journeys) >= expected
        elif key == "requires_genai_api":
            results[key] = bool(spec.genai_apis) and any(j.genai_api for j in spec.jobs)
        elif key == "requires_gpu_server":
            results[key] = any(s.kind == "gpu" for s in spec.servers)
        elif key == "requires_server_shared_by_journeys":
            results[key] = any(len(v) >= 2 for v in server_journeys.values())
        elif key == "requires_low_volume_journey":
            results[key] = low_volume
        elif key == "requires_edge_deployment":
            results[key] = bool(spec.edge_deployments)
        elif key == "requires_edge_server_call":
            results[key] = any(f.server_calls for f in spec.edge_functions)
        elif key == "devices_must_include":
            results[key] = set(expected) <= {p.device for p in spec.usage_patterns}
        elif key == "countries_must_include":
            results[key] = set(expected) <= {p.country.upper() for p in spec.usage_patterns} | {
                d.country.upper() for d in spec.edge_deployments}
        else:
            raise ValueError(f"Unknown check {key}")
    results["all_journeys_have_usage_pattern"] = {j.name for j in spec.journeys} <= pattern_journeys
    return results


def evaluate(data: dict, case: dict, export_path: Path | None) -> dict:
    """Validate -> build -> compute -> export -> reload. Each stage records ok/error."""
    from efootprint.api_utils.json_to_system import json_to_system
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.constants.units import u

    result = {"schema_ok": False, "build_ok": False, "compute_ok": False, "export_ok": False}
    try:
        spec, extra_fields = validate_tolerating_extras(data)
        result["schema_ok"] = True
        if extra_fields:
            result["extra_fields_ignored"] = extra_fields
    except ValidationError as error:
        result["schema_error"] = str(error)[:2000]
        return result
    result["checks"] = structural_checks(spec, case.get("checks", {}))
    result["counts"] = {
        "servers": len(spec.servers), "genai_apis": len(spec.genai_apis), "jobs": len(spec.jobs),
        "journeys": len(spec.journeys), "steps": sum(len(j.steps) for j in spec.journeys),
        "usage_patterns": len(spec.usage_patterns), "edge_devices": len(spec.edge_devices),
        "edge_functions": len(spec.edge_functions), "edge_deployments": len(spec.edge_deployments),
        "comments": sum(len(obj.comments) for section in (
            spec.servers, spec.genai_apis, spec.jobs, spec.usage_patterns, spec.edge_devices, spec.edge_functions,
            spec.edge_deployments, [st for jo in spec.journeys for st in jo.steps]) for obj in section),
        "open_questions": len(spec.open_questions)}
    try:
        start = time.perf_counter()
        system, resolutions = build_system(spec)
        result["build_ok"] = True
        result["catalog_resolutions"] = [res.as_dict() for res in resolutions]
        total = system.total_footprint.sum()
        result["compute_ok"] = True
        result["total_kg_co2e_over_horizon"] = round(float(total.value.to(u.kg).magnitude), 1)
        result["use_by_category_kg"] = {
            k: round(float(v.value.to(u.kg).magnitude), 1) for k, v in system.total_use_footprint_sum_over_period.items()}
        result["manufacturing_by_category_kg"] = {
            k: round(float(v.value.to(u.kg).magnitude), 1)
            for k, v in system.total_manufacturing_footprint_sum_over_period.items()}
        result["compute_s"] = round(time.perf_counter() - start, 2)
        if export_path:
            system_to_json(system, output_filepath=str(export_path), save_computed_state=False)
            json_to_system(json.loads(export_path.read_text()))
            result["export_ok"] = True
            result["export_path"] = str(export_path)
    except Exception as error:  # noqa: BLE001 - we want every failure recorded, not raised
        stage = "export" if result["compute_ok"] else "compute" if result["build_ok"] else "build"
        result[f"{stage}_error"] = f"{type(error).__name__}: {error}"[:2000]
        result[f"{stage}_traceback"] = traceback.format_exc()[-3000:]
    return result


# --- Orchestration --------------------------------------------------------------------------

def load_cases(selectors: list[str] | None) -> list[dict]:
    cases = [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("*.json")) if not p.name.startswith("_")]
    if selectors:
        cases = [c for c in cases if any(c["id"].startswith(s) for s in selectors)]
    return cases


def run_one(case: dict, model: str, rep: int, effort: str | None, run_dir: Path) -> dict:
    stem = f"{case['id']}__{model}__r{rep}"
    record = {"case": case["id"], "model": model, "rep": rep, "effort": effort,
              "timestamp": datetime.now().isoformat(timespec="seconds"),
              "system_prompt_chars": len(SYSTEM_PROMPT), "user_prompt": case["user_prompt"]}
    try:
        completion = providers.complete(model, SYSTEM_PROMPT, case["user_prompt"], effort)
    except Exception as error:  # noqa: BLE001
        record["api_error"] = f"{type(error).__name__}: {error}"[:2000]
        (run_dir / f"{stem}.json").write_text(json.dumps(record, indent=2))
        return record
    record.update({
        "raw_output": completion.text, "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens, "cached_input_tokens": completion.cached_input_tokens,
        "cache_write_tokens": completion.cache_write_tokens, "reasoning_tokens": completion.reasoning_tokens,
        "latency_s": round(completion.latency_s, 2), "cost_usd": round(completion.cost_usd(model), 6),
        "stop_reason": completion.stop_reason, "request_params": completion.request_params})
    data, first_ok, parse_error = parse_json(completion.text)
    record.update({"json_first_attempt_ok": first_ok, "json_ok": data is not None, "json_error": parse_error})
    if data is not None:
        record.update(evaluate(data, case, run_dir / f"{stem}.e-f.json"))
    (run_dir / f"{stem}.json").write_text(json.dumps(record, indent=2))
    return record


def replay(run_dir: Path):
    cases = {c["id"]: c for c in load_cases(None)}
    for path in sorted(run_dir.glob("*__r*.json")):
        if path.name.endswith(".e-f.json"):
            continue
        record = json.loads(path.read_text())
        if "raw_output" not in record:
            continue
        data, first_ok, parse_error = parse_json(record["raw_output"])
        record.update({"json_first_attempt_ok": first_ok, "json_ok": data is not None, "json_error": parse_error})
        if data is not None:
            record.update(evaluate(data, cases[record["case"]], path.with_suffix(".e-f.json")))
        path.write_text(json.dumps(record, indent=2))
        print(path.name, summary_line(record))
    report.write_summary(run_dir)


def summary_line(r: dict) -> str:
    if "api_error" in r:
        return f"API ERROR {r['api_error'][:120]}"
    stages = " ".join(f"{k[:-3]}={'ok' if r.get(k) else 'FAIL'}" for k in ("json_ok", "schema_ok", "build_ok", "compute_ok", "export_ok"))
    checks = r.get("checks", {})
    passed = sum(1 for v in checks.values() if v)
    return (f"{stages} checks={passed}/{len(checks)} out_tok={r.get('output_tokens')} "
            f"cost=${r.get('cost_usd', 0):.4f} {r.get('latency_s')}s total={r.get('total_kg_co2e_over_horizon')}kg")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*", help="case id prefixes, e.g. 01 03")
    parser.add_argument("--models", nargs="*", default=providers.DEFAULT_MODELS)
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--effort", default=None, help="low|medium|high; omitted = provider default")
    parser.add_argument("--replay", help="existing run dir to re-evaluate without API calls")
    parser.add_argument("--dry-run", help="a hand-written DSL json file to push through evaluate()")
    parser.add_argument("--max-cost-usd", type=float, default=3.0, help="stop launching new calls past this total")
    args = parser.parse_args()

    if args.replay:
        return replay(Path(args.replay))
    if args.dry_run:
        path = Path(args.dry_run)
        case = {"id": path.stem, "checks": {}}
        for c in load_cases(None):
            if c["id"][:2] in path.stem:
                case = c
        out = RUNS_DIR / "dry_run"
        out.mkdir(parents=True, exist_ok=True)
        result = evaluate(json.loads(path.read_text()), case, out / f"{path.stem}.e-f.json")
        print(json.dumps({k: v for k, v in result.items() if "traceback" not in k}, indent=2))
        return

    providers.load_dotenv()
    cases = load_cases(args.cases)
    run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps(
        {"cases": [c["id"] for c in cases], "models": args.models, "reps": args.reps, "effort": args.effort,
         "system_prompt": SYSTEM_PROMPT}, indent=2))
    total_cost = 0.0
    for case, model, rep in itertools.product(cases, args.models, range(1, args.reps + 1)):
        if total_cost >= args.max_cost_usd:
            print(f"Budget {args.max_cost_usd} USD reached, stopping.")
            break
        record = run_one(case, model, rep, args.effort, run_dir)
        total_cost += record.get("cost_usd", 0)
        print(f"{case['id']:32} {model:24} r{rep}  {summary_line(record)}")
    print(f"\nRun dir: {run_dir}\nTotal cost: ${total_cost:.4f}")
    report.write_summary(run_dir)


if __name__ == "__main__":
    main()
