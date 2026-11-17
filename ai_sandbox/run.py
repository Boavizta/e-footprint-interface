"""Run cases x models x repetitions, validate, build, compute, export, and record everything.

Usage (from the interface repo root):
    poetry run python -m ai_sandbox.run --cases 01 --models claude-haiku-5-5 --reps 1
    poetry run python -m ai_sandbox.run                      # all cases, DEFAULT_MODELS, 1 rep
    poetry run python -m ai_sandbox.run --replay runs/<run_dir>   # re-validate recorded outputs, no API call
    poetry run python -m ai_sandbox.run --dry-run cases/_handwritten_01_recipe_app.json   # pipeline check without an LLM
    poetry run python -m ai_sandbox.run --scope web_edge --cases 03 04 --models zai-glm-5-3-flash --effort low

--scope picks the prompt and the builder: web (default) is the production bootstrap, web_edge its Web + edge
instructions and schema, built by the sandbox's edge_dsl_hw.py. Without --cases, the cases of that scope run.

Each run writes ai_sandbox/runs/<timestamp>/<case>__<model>__r<rep>.json plus the exported model
<...>.e-f.json when the build succeeds. summary.md, summary.html and runs/index.html are produced by report.py.
A call whose output fails to parse, validate, build or compute is retried with the error (--retries, default 1);
the record holds the last attempt at top level and every attempt's outcome under "attempts".
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from . import edge_dsl
from . import edge_dsl_hw
from . import providers
from . import report
from model_builder.application.ai_bootstrap import dsl, service
from model_builder.application.ai_bootstrap.dsl import ModelSpec, parse_json

SANDBOX = Path(__file__).parent
CASES_DIR = SANDBOX / "cases"
RUNS_DIR = SANDBOX / "runs"


@dataclass(frozen=True)
class Scope:
    system_prompt: str
    validate: object  # data -> (spec, ignored fields)
    build: object     # answer text -> GeneratedModel


def _production(name: str, build) -> Scope:
    """A production scope's instructions and schema, with the given builder."""
    return Scope(service.system_prompt(name),
                 lambda data: dsl.validate_tolerating_extras(data, service.SCOPES[name].schema), build)


SCOPES = {
    "web": _production("web", lambda text: service.build_answer(text, "web")),
    # The edge builder is still the sandbox's until production builds the edge sections.
    "web_edge": _production("web_edge", edge_dsl_hw.build_answer),
}
DEVICE_TOTAL_TOLERANCE = 0.2  # "about 1,500 buildings", "around 40 sensors"


# --- Checks ----------------------------------------------------------------------------------

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
    edge_functions = getattr(spec, "edge_functions", [])
    edge_deployments = getattr(spec, "edge_deployments", [])
    edge_servers = {job_server.get(call.job) for f in edge_functions for call in f.server_calls} - {None}
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
        elif key == "devices_must_include":
            results[key] = set(expected) <= {p.device for p in spec.usage_patterns}
        elif key == "countries_must_include":
            results[key] = set(expected) <= {p.country.upper() for p in spec.usage_patterns + edge_deployments}
        elif key == "requires_edge_usage_pattern":
            results[key] = bool(edge_deployments)
        elif key == "requires_edge_server_call":
            results[key] = any(f.server_calls for f in edge_functions)
        elif key == "requires_server_shared_by_web_and_edge":
            results[key] = bool(edge_servers & set(server_journeys))
        elif key == "requires_device_group":
            results[key] = bool(getattr(spec, "edge_device_groups", [])) == expected
        elif key == "device_totals":
            results.update({device_total_key(pattern): False for pattern in expected})  # set from the built system
        else:
            raise ValueError(f"Unknown check {key}")
    results["all_journeys_have_usage_pattern"] = {j.name for j in spec.journeys} <= pattern_journeys
    return results


def device_total_key(pattern: str) -> str:
    return f"device_total_{pattern.split('|')[0]}"


def device_total_checks(totals: dict[str, float], expected: dict[str, float]) -> dict[str, bool]:
    """Per expected device ("a|b" matches a device name containing a or b), the devices in service at the start
    sum to the expected total within DEVICE_TOTAL_TOLERANCE."""
    results = {}
    for pattern, target in expected.items():
        words = pattern.lower().split("|")
        found = sum(n for name, n in totals.items() if any(w in name.lower() for w in words))
        results[device_total_key(pattern)] = abs(found - target) <= DEVICE_TOTAL_TOLERANCE * target
    return results


def evaluate(data: dict, case: dict, export_path: Path | None, scope: Scope = SCOPES["web"]) -> dict:
    """Validate -> build -> compute -> export -> reload. Each stage records ok/error."""
    from efootprint.api_utils.json_to_system import json_to_system
    from efootprint.api_utils.system_to_json import system_to_json
    from efootprint.constants.units import u

    result = {"schema_ok": False, "build_ok": False, "compute_ok": False, "export_ok": False}
    try:
        spec, extra_fields = scope.validate(data)
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
        "usage_patterns": len(spec.usage_patterns),
        **{section: len(getattr(spec, section, [])) for section in EDGE_SECTIONS},
        "comments": sum(len(obj.comments) for section in (
            spec.servers, spec.genai_apis, spec.jobs, spec.usage_patterns, [st for jo in spec.journeys for st in jo.steps],
            *(getattr(spec, section, []) for section in EDGE_SECTIONS if section != "edge_journeys"))
            for obj in section)}
    try:
        start = time.perf_counter()
        generated = scope.build(json.dumps(data))
        system, resolutions = generated.system, generated.resolutions
        result["build_ok"] = True
        if system.edge_usage_patterns:
            result["device_totals"] = {k: round(v) for k, v in edge_dsl.device_totals(system).items()}
            result["checks"].update(device_total_checks(result["device_totals"], case.get("checks", {}).get("device_totals", {})))
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

EDGE_SECTIONS = ("edge_devices", "edge_device_groups", "edge_functions", "edge_journeys", "edge_deployments")


def load_cases(selectors: list[str] | None, scope: str | None = None) -> list[dict]:
    """The cases named by id prefix, or without selectors every case of the scope (a case's scope defaults to web)."""
    cases = [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("*.json")) if not p.name.startswith("_")]
    if selectors:
        return [c for c in cases if any(c["id"].startswith(s) for s in selectors)]
    return [c for c in cases if scope is None or c.get("scope", "web") == scope]


RETRY_PROMPT = """{user_prompt}

---
Your previous answer was:
{previous_output}

It failed with this error:
{error}

Return the corrected complete JSON object."""
SUMMED_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens", "reasoning_tokens",
               "latency_s", "cost_usd")


def model_error(result: dict) -> str | None:
    """The error to send back for a retry: a model mistake at parse, schema, build or compute. Export is ours."""
    for stage, key in (("json_ok", "json_error"), ("schema_ok", "schema_error"), ("build_ok", "build_error"),
                       ("compute_ok", "compute_error")):
        if not result.get(stage):
            return re.sub(r"\n\s+For further information visit \S+", "", result.get(key) or f"{stage[:-3]} failed")
    return None


def attempt(case: dict, model: str, prompt: str, effort: str | None, export_path: Path, scope: Scope) -> dict:
    completion = providers.complete(model, scope.system_prompt, prompt, effort)
    cost = completion.cost_usd(model)
    result = {
        "raw_output": completion.text, "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens, "cached_input_tokens": completion.cached_input_tokens,
        "cache_write_tokens": completion.cache_write_tokens, "reasoning_tokens": completion.reasoning_tokens,
        "latency_s": round(completion.latency_s, 2), "cost_usd": round(cost, 6) if cost is not None else None,
        "stop_reason": completion.stop_reason, "request_params": completion.request_params}
    data, first_ok, parse_error = parse_json(completion.text)
    result.update({"json_first_attempt_ok": first_ok, "json_ok": data is not None, "json_error": parse_error})
    if data is not None:
        result.update(evaluate(data, case, export_path, scope))
    return result


def run_one(case: dict, model: str, rep: int, effort: str | None, retries: int, run_dir: Path, scope_name: str) -> dict:
    scope = SCOPES[scope_name]
    stem = f"{case['id']}__{model}__r{rep}"
    record = {"case": case["id"], "model": model, "rep": rep, "effort": effort, "scope": scope_name,
              "timestamp": datetime.now().isoformat(timespec="seconds"),
              "system_prompt_chars": len(scope.system_prompt), "user_prompt": case["user_prompt"]}
    attempts, prompt = [], case["user_prompt"]
    try:
        for _ in range(retries + 1):
            result = attempt(case, model, prompt, effort, run_dir / f"{stem}.e-f.json", scope)
            attempts.append(result)
            error = model_error(result)
            if error is None:
                break
            result["retry_error"] = error
            prompt = RETRY_PROMPT.format(user_prompt=case["user_prompt"], previous_output=result["raw_output"], error=error)
    except Exception as error:  # noqa: BLE001
        record["api_error"] = f"{type(error).__name__}: {error}"[:2000]
    if attempts:
        record.update(attempts[-1])
        for key in SUMMED_KEYS:
            values = [a[key] for a in attempts if a.get(key) is not None]
            record[key] = round(sum(values), 6) if len(values) == len(attempts) else None
        record["first_try_ok"] = bool(attempts[0].get("export_ok"))
        record["attempts"] = [{k: v for k, v in a.items() if k != "request_params"} for a in attempts[:-1]]
    (run_dir / f"{stem}.json").write_text(json.dumps(record, indent=2))
    return record


def replay(run_dir: Path):
    cases = {c["id"]: c for c in load_cases(None)}
    config = json.loads((run_dir / "config.json").read_text()) if (run_dir / "config.json").exists() else {}
    for path in sorted(run_dir.glob("*__r*.json")):
        if path.name.endswith(".e-f.json"):
            continue
        record = json.loads(path.read_text())
        if "raw_output" not in record or record["case"] not in cases:
            continue
        data, first_ok, parse_error = parse_json(record["raw_output"])
        record.update({"json_first_attempt_ok": first_ok, "json_ok": data is not None, "json_error": parse_error})
        if data is not None:
            scope = SCOPES[record.get("scope", config.get("scope", "web"))]
            record.update(evaluate(data, cases[record["case"]], path.with_suffix(".e-f.json"), scope))
        path.write_text(json.dumps(record, indent=2))
        print(path.name, summary_line(record))
    report.write_summary(run_dir)


def summary_line(r: dict) -> str:
    if "api_error" in r:
        return f"API ERROR {r['api_error'][:120]}"
    stages = " ".join(f"{k[:-3]}={'ok' if r.get(k) else 'FAIL'}" for k in ("json_ok", "schema_ok", "build_ok", "compute_ok", "export_ok"))
    stages += f" tries={len(r.get('attempts', [])) + 1}"
    checks = r.get("checks", {})
    passed = sum(1 for v in checks.values() if v)
    return (f"{stages} checks={passed}/{len(checks)} out_tok={r.get('output_tokens')} "
            f"cost={r.get('cost_usd')} USD {r.get('latency_s')}s total={r.get('total_kg_co2e_over_horizon')}kg")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*", help="case id prefixes, e.g. 01 02; default: every case of the scope")
    parser.add_argument("--scope", choices=sorted(SCOPES), default="web", help="prompt and builder (default web)")
    parser.add_argument("--models", nargs="*", default=providers.DEFAULT_MODELS)
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--effort", default=None, help="low|medium|high; omitted = provider default")
    parser.add_argument("--retries", type=int, default=1, help="extra calls with the error when an output fails")
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
        result = evaluate(json.loads(path.read_text()), case, out / f"{path.stem}.e-f.json", SCOPES[args.scope])
        print(json.dumps({k: v for k, v in result.items() if "traceback" not in k}, indent=2))
        return

    providers.load_dotenv()
    cases = load_cases(args.cases, args.scope)
    run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps(
        {"cases": [c["id"] for c in cases], "models": args.models, "reps": args.reps, "effort": args.effort,
         "retries": args.retries, "scope": args.scope,
         "system_prompt": SCOPES[args.scope].system_prompt}, indent=2))
    total_cost = 0.0
    unknown_cost = False
    for case, model, rep in itertools.product(cases, args.models, range(1, args.reps + 1)):
        if total_cost >= args.max_cost_usd:
            print(f"Budget {args.max_cost_usd} USD reached, stopping.")
            break
        record = run_one(case, model, rep, args.effort, args.retries, run_dir, args.scope)
        cost = record.get("cost_usd")
        if cost is None:
            unknown_cost = True
        else:
            total_cost += cost
        print(f"{case['id']:32} {model:24} r{rep}  {summary_line(record)}")
        if unknown_cost:
            print("Call cost unavailable; stopping because the budget cannot be checked.")
            break
    cost_label = "Known cost subtotal (incomplete)" if unknown_cost else "Total cost"
    print(f"\nRun dir: {run_dir}\n{cost_label}: ${total_cost:.4f}")
    report.write_summary(run_dir)


if __name__ == "__main__":
    main()
