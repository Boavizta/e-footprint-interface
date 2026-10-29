"""Build summary.md and summary.html for a run dir, and refresh runs/index.html.

The Markdown is the grep-able record; the HTML (report_html.py) is the browsing view with structure trees
and "Open in interface" links.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import report_html  # noqa: E402


def load_records(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(run_dir.glob("*__r*.json")) if not p.name.endswith(".e-f.json")]


def load_cases() -> dict[str, dict]:
    cases_dir = Path(__file__).parent / "cases"
    return {c["id"]: c for c in (json.loads(p.read_text()) for p in cases_dir.glob("0*.json"))}


def write_summary(run_dir: Path):
    records = load_records(run_dir)
    cases = load_cases()
    lines = [f"# Run {run_dir.name}", "",
             "| case | model | rep | json | schema | build | compute | export | tries | checks | in tok | out tok | reasoning | latency s | cost USD | total kg CO2e |",
             "|---|---|---|---|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    by_model: dict[str, list] = {}
    for r in records:
        ok = lambda k: "✅" if r.get(k) else "❌"  # noqa: E731
        checks = r.get("checks", {})
        checks_str = f"{sum(1 for v in checks.values() if v)}/{len(checks)}" if checks else "-"
        if "api_error" in r:
            lines.append(f"| {r['case']} | {r['model']} | {r['rep']} | API error: {r['api_error'][:80]} | | | | | | | | | | | | |")
            continue
        lines.append(
            f"| {r['case']} | {r['model']} | {r['rep']} | {ok('json_ok')}{'' if r.get('json_first_attempt_ok') else ' (repaired)'} "
            f"| {ok('schema_ok')} | {ok('build_ok')} | {ok('compute_ok')} | {ok('export_ok')} | {len(r.get('attempts', [])) + 1} | {checks_str} "
            f"| {r.get('input_tokens')} | {r.get('output_tokens')} | {r.get('reasoning_tokens') or ''} "
            f"| {r.get('latency_s')} | {r.get('cost_usd', 0):.4f} | {r.get('total_kg_co2e_over_horizon', '')} |")
        by_model.setdefault(r["model"], []).append(r)
    lines += ["", "## Per model", "", "| model | runs | ok first try | export ok | checks passed | mean out tok | mean latency s | mean cost USD |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for model, rs in by_model.items():
        n = len(rs)
        exported = sum(1 for r in rs if r.get("export_ok"))
        checks_total = sum(len(r.get("checks", {})) for r in rs)
        checks_passed = sum(sum(1 for v in r.get("checks", {}).values() if v) for r in rs)
        first_try = sum(1 for r in rs if r.get("first_try_ok", r.get("export_ok")))
        lines.append(f"| {model} | {n} | {first_try}/{n} | {exported}/{n} | {checks_passed}/{checks_total} "
                     f"| {sum(r.get('output_tokens', 0) for r in rs) / n:.0f} | {sum(r.get('latency_s', 0) for r in rs) / n:.1f} "
                     f"| {sum(r.get('cost_usd', 0) for r in rs) / n:.4f} |")
    lines += ["", "## Details", ""]
    for r in records:
        lines += [f"### {r['case']} / {r['model']} / r{r['rep']}", ""]
        for key in ("api_error", "json_error", "schema_error", "build_error", "compute_error", "export_error"):
            if r.get(key):
                lines += [f"- **{key}**: `{r[key][:600]}`"]
        for n, earlier in enumerate(r.get("attempts", []), start=1):
            lines += [f"- **attempt {n} failed, retried with**: `{earlier.get('retry_error', '')[:600]}`"]
        if r.get("checks"):
            lines += ["- checks: " + ", ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in r["checks"].items())]
        if r.get("catalog_resolutions"):
            lines += ["- catalog resolutions: " + "; ".join(
                f"{c['kind']} {c['requested']} → {c['resolved']} ({c['how']})" for c in r["catalog_resolutions"])]
        if r.get("counts"):
            lines += ["- counts: " + ", ".join(f"{k}={v}" for k, v in r["counts"].items() if v)]
        if r.get("use_by_category_kg"):
            lines += ["- use kg: " + ", ".join(f"{k}={v}" for k, v in r["use_by_category_kg"].items() if v),
                      "- manufacturing kg: " + ", ".join(f"{k}={v}" for k, v in r["manufacturing_by_category_kg"].items() if v)]
        if r.get("raw_output"):
            try:
                pretty = json.dumps(json.loads(r["raw_output"]), indent=1)
            except json.JSONDecodeError:
                pretty = r["raw_output"]
            case = cases.get(r["case"], {})
            if case.get("facts_if_asked"):
                lines += ["- facts the user could have given:"] + [
                    f"  - **{k}**: {v}" for k, v in case["facts_if_asked"].items()]
            if case.get("expected_properties"):
                lines += ["- expected properties (expert rubric):"] + [f"  - [ ] {e}" for e in case["expected_properties"]]
            lines += ["", "<details><summary>model output</summary>", "", "```json", pretty[:12000], "```", "", "</details>", ""]
    (run_dir / "summary.md").write_text("\n".join(lines))
    html_path = report_html.write_html(run_dir, records, cases)
    index_path = report_html.write_index(run_dir.parent)
    print(f"Wrote {run_dir / 'summary.md'}, {html_path} and {index_path}")


if __name__ == "__main__":
    write_summary(Path(sys.argv[1]))
