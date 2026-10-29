"""Browsable HTML for a run dir (summary.html) and across runs (runs/index.html).

Each record shows a structure tree rendered from the DSL JSON the model wrote (what it said, not the
effective values after library defaults), structural warnings, the record's numbers, and an
"Open in interface" link to the DEBUG-only ``/dev/load-file/`` route of a locally running interface.
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.parse import urlencode

INTERFACE_URL = os.environ.get("EFOOTPRINT_INTERFACE_URL", "http://localhost:8000").rstrip("/")

STAGES = ("json_ok", "schema_ok", "build_ok", "compute_ok", "export_ok")

CSS = """
body{font:14px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1400px;padding:16px;color:#222;background:#fff}
h1{font-size:20px}h2{font-size:17px;margin-top:32px}h3{font-size:15px;margin:0}
table{border-collapse:collapse;font-size:13px}th,td{border:1px solid #ddd;padding:3px 7px;text-align:left;vertical-align:top}
th{background:#f3f3f3;cursor:pointer;white-space:nowrap}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.ok{color:#1a7f37}.fail{color:#c62828;font-weight:600}.muted{color:#777}.warn{color:#b26a00}
.controls{display:flex;gap:16px;align-items:center;margin:12px 0}
section.record{border:1px solid #ddd;border-radius:6px;padding:12px 16px;margin:16px 0}
section.record header{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;margin-bottom:8px}
.cols{display:grid;grid-template-columns:3fr 2fr;gap:24px}@media(max-width:900px){.cols{grid-template-columns:1fr}}
ul.tree,ul.tree ul{list-style:none;margin:0;padding-left:18px;border-left:1px dotted #bbb}ul.tree{padding-left:0;border:none}
ul.tree li{margin:2px 0}.kind{display:inline-block;min-width:60px;margin-right:6px;color:#555;font-size:11px;text-transform:uppercase;letter-spacing:.03em}
.asm{display:block;color:#777;font-size:12px;margin-left:66px}.stats dt{font-weight:600;margin-top:8px}.stats dd{margin:2px 0 0 0}
.badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:12px;background:#eee;margin-right:4px}
.badge.fail{background:#fde0e0}.badge.ok{background:#e3f3e8}a.open{font-weight:600}
pre{background:#f7f7f7;padding:8px;overflow:auto;font-size:12px;max-height:600px}ul.warnings{color:#b26a00;padding-left:18px}
.hidden{display:none}
"""

JS = """
const caseSel=document.getElementById('f-case'),modelSel=document.getElementById('f-model');
function applyFilters(){const c=caseSel.value,m=modelSel.value;
 document.querySelectorAll('[data-case]').forEach(el=>{el.classList.toggle('hidden',(c&&el.dataset.case!==c)||(m&&el.dataset.model!==m));});}
caseSel.onchange=modelSel.onchange=applyFilters;
document.querySelectorAll('table.sortable th').forEach((th,i)=>th.onclick=()=>{
 const tb=th.closest('table').tBodies[0],rows=[...tb.rows],asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
 const val=r=>{const t=r.cells[i].innerText.trim(),n=parseFloat(t.replace(/[^0-9.\\-]/g,''));return t!==''&&!isNaN(n)&&/^[-0-9.$%\\/ ]+$/.test(t)?n:t.toLowerCase();};
 rows.sort((a,b)=>{const x=val(a),y=val(b);return (x<y?-1:x>y?1:0)*(asc?1:-1);});rows.forEach(r=>tb.appendChild(r));});
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def stem(record: dict) -> str:
    return f"{record['case']}__{record['model']}__r{record['rep']}"


def open_link(record: dict) -> str:
    if not record.get("export_ok") or not record.get("export_path"):
        return ""
    url = f"{INTERFACE_URL}/dev/load-file/?{urlencode({'path': record['export_path']})}"
    return f'<a class="open" href="{esc(url)}" target="efootprint">Open in interface ↗</a>'


# --- Structure tree ------------------------------------------------------------------------------

def _names(items) -> set[str]:
    return {i.get("name") for i in items if isinstance(i, dict) and i.get("name")}


def _comments(obj: dict) -> str:
    comments = obj.get("comments") if isinstance(obj.get("comments"), dict) else {}
    return "".join(f'<span class="asm">{esc(field.replace("_", " "))}: {esc(text)}</span>' for field, text in comments.items())


def _volume(v) -> str:
    return f"{v.get('value')}/{v.get('per')}" if isinstance(v, dict) else esc(v)


def structural_warnings(data: dict) -> list[str]:
    """Dangling references and orphans in the DSL. Both are what a reader checks first."""
    servers, apis, jobs = _names(data.get("servers", [])), _names(data.get("genai_apis", [])), _names(data.get("jobs", []))
    journeys = _names(data.get("journeys", []))
    warnings, used_jobs, used_servers, used_apis, used_journeys = [], set(), set(), set(), set()
    for job in data.get("jobs", []):
        if job.get("server") and job.get("genai_api"):
            warnings.append(f"job '{job['name']}' targets both a server and a GenAI API")
        if not job.get("server") and not job.get("genai_api"):
            warnings.append(f"job '{job['name']}' targets neither a server nor a GenAI API")
        if job.get("server") and job["server"] not in servers:
            warnings.append(f"job '{job['name']}' → unknown server '{job['server']}'")
        if job.get("genai_api") and job["genai_api"] not in apis:
            warnings.append(f"job '{job['name']}' → unknown GenAI API '{job['genai_api']}'")
        used_servers.add(job.get("server")), used_apis.add(job.get("genai_api"))
    for journey in data.get("journeys", []):
        for step in journey.get("steps", []):
            for job in step.get("jobs", []):
                if job not in jobs:
                    warnings.append(f"step '{step.get('name')}' → unknown job '{job}'")
                used_jobs.add(job)
    for up in data.get("usage_patterns", []):
        if up.get("journey") not in journeys:
            warnings.append(f"usage pattern '{up.get('name')}' → unknown journey '{up.get('journey')}'")
        used_journeys.add(up.get("journey"))
    for label, declared, used in (("server", servers, used_servers), ("GenAI API", apis, used_apis), ("job", jobs, used_jobs),
                                  ("journey", journeys, used_journeys)):
        for name in sorted(declared - used):
            warnings.append(f"unused {label} '{name}'")
    return warnings


def render_tree(data: dict) -> str:
    jobs = {j["name"]: j for j in data.get("jobs", []) if isinstance(j, dict) and j.get("name")}
    journeys = {j["name"]: j for j in data.get("journeys", []) if isinstance(j, dict) and j.get("name")}

    def job_li(name: str) -> str:
        job = jobs.get(name)
        if job is None:
            return f'<li><span class="kind">job</span><span class="fail">{esc(name)} (unknown)</span></li>'
        target = (f'→ <span class="kind">GenAI</span>{esc(job["genai_api"])}' if job.get("genai_api")
                  else f'→ <span class="kind">server</span>{esc(job.get("server"))}')
        nums = ", ".join(f"{k.replace('_', ' ')}={job[k]}" for k in ("data_transferred_kb", "data_stored_kb", "request_duration_s",
                                                                     "cpu_cores", "gpus", "ram_mb", "output_tokens") if job.get(k) is not None)
        return (f'<li><span class="kind">job</span>{esc(name)} {target} <span class="muted">{esc(nums)}</span>'
                f'{_comments(job)}</li>')

    def journey_ul(name: str) -> str:
        journey = journeys.get(name)
        if journey is None:
            return f'<ul><li><span class="kind">journey</span><span class="fail">{esc(name)} (unknown)</span></li></ul>'
        steps = "".join(
            f'<li><span class="kind">step</span>{esc(s.get("name"))}'
            + (f' <span class="muted">{s["user_time_spent_min"]} min</span>' if s.get("user_time_spent_min") is not None else "")
            + "<ul>" + "".join(job_li(j) for j in s.get("jobs", [])) + "</ul></li>" for s in journey.get("steps", []))
        return f'<ul><li><span class="kind">journey</span>{esc(name)}<ul>{steps}</ul></li></ul>'

    parts = [f'<ul class="tree"><li><strong>{esc(data.get("system_name", "(no system name)"))}</strong></li>']
    for up in data.get("usage_patterns", []):
        growth = f", +{up['growth_pct_per_year']}%/yr" if up.get("growth_pct_per_year") else ""
        parts.append(
            f'<li><span class="kind">usage</span>{esc(up.get("name"))} <span class="muted">{esc(up.get("device"))} · '
            f'{esc(up.get("network"))} · {esc(up.get("country"))} · {_volume(up.get("volume"))}{growth}</span>'
            f'{_comments(up)}{journey_ul(up.get("journey"))}</li>')
    for s in data.get("servers", []):
        specs = ", ".join(f"{k.replace('_', ' ')}={s[k]}" for k in ("cores", "ram_gb", "gpus", "storage_gb", "cloud_provider",
                                                                     "instance_type", "carbon_intensity_g_per_kwh") if s.get(k) is not None)
        parts.append(f'<li><span class="kind">{esc(s.get("kind", "cpu"))} server</span>{esc(s.get("name"))} '
                     f'<span class="muted">{esc(specs)}</span>{_comments(s)}</li>')
    for api in data.get("genai_apis", []):
        parts.append(f'<li><span class="kind">GenAI</span>{esc(api.get("name"))} <span class="muted">{esc(api.get("provider"))}/'
                     f'{esc(api.get("model_name") or "<unstated>")}</span>{_comments(api)}</li>')
    parts.append("</ul>")
    return "".join(parts)


def preview_block(record: dict) -> str:
    raw = record.get("raw_output")
    if not raw:
        return '<p class="muted">no output</p>'
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return f'<p class="fail">unparseable JSON</p><pre>{esc(raw[:4000])}</pre>'
    if not isinstance(data, dict):
        return f"<pre>{esc(json.dumps(data, indent=1)[:4000])}</pre>"
    try:
        tree, warnings = render_tree(data), structural_warnings(data)
    except (AttributeError, TypeError, KeyError) as error:  # malformed DSL (schema failures): show the raw JSON instead
        return (f'<p class="fail">tree not renderable ({type(error).__name__}: {esc(error)})</p>'
                f"<pre>{esc(json.dumps(data, indent=1)[:6000])}</pre>")
    warnings_html = ("<ul class=\"warnings\">" + "".join(f"<li>{esc(w)}</li>" for w in warnings) + "</ul>") if warnings else ""
    questions = data.get("open_questions") or []
    questions_html = ("<p><strong>Open questions</strong></p><ul>" + "".join(f"<li>{esc(q)}</li>" for q in questions) + "</ul>"
                      if questions else "")
    return tree + warnings_html + questions_html


# --- Record and run pages ------------------------------------------------------------------------

def _kv_list(d: dict, fmt=lambda v: v) -> str:
    return ", ".join(f"{k}={fmt(v)}" for k, v in d.items() if v) or "–"


def stats_block(record: dict, case: dict) -> str:
    parts = ['<dl class="stats">']
    for key in ("api_error", "json_error", "schema_error", "build_error", "compute_error", "export_error"):
        if record.get(key):
            parts.append(f'<dt class="fail">{key}</dt><dd><pre>{esc(record[key][:1500])}</pre></dd>')
    for n, earlier in enumerate(record.get("attempts", []), start=1):
        parts.append(f'<dt class="warn">Attempt {n} failed, retried with</dt><dd><pre>{esc(earlier.get("retry_error", "")[:1500])}</pre>'
                     f'<details><summary>attempt {n} output</summary><pre>{esc((earlier.get("raw_output") or "")[:20000])}</pre></details></dd>')
    if record.get("counts"):
        parts.append(f"<dt>Counts</dt><dd>{esc(_kv_list(record['counts']))}</dd>")
    if record.get("total_kg_co2e_over_horizon") is not None:
        parts.append(f"<dt>Total over horizon</dt><dd>{record['total_kg_co2e_over_horizon']} kg CO2e</dd>")
        parts.append(f"<dt>Use by category (kg)</dt><dd>{esc(_kv_list(record.get('use_by_category_kg', {})))}</dd>")
        parts.append(f"<dt>Manufacturing by category (kg)</dt><dd>{esc(_kv_list(record.get('manufacturing_by_category_kg', {})))}</dd>")
    if record.get("checks"):
        parts.append("<dt>Checks</dt><dd>" + " ".join(
            f'<span class="badge {"ok" if v else "fail"}">{esc(k)}</span>' for k, v in record["checks"].items()) + "</dd>")
    if record.get("catalog_resolutions"):
        parts.append("<dt>Catalog resolutions</dt><dd><ul>" + "".join(
            f'<li class="{"" if c.get("how") == "exact" else "warn"}">{esc(c.get("kind"))}: {esc(c.get("requested"))} → '
            f'{esc(c.get("resolved"))} ({esc(c.get("how"))})</li>' for c in record["catalog_resolutions"]) + "</ul></dd>")
    parts.append(f"<dt>Cost</dt><dd>{record.get('input_tokens')} in / {record.get('output_tokens')} out"
                 f"{' / ' + str(record['reasoning_tokens']) + ' reasoning' if record.get('reasoning_tokens') else ''} tokens, "
                 f"{record.get('latency_s')} s, ${record.get('cost_usd', 0):.4f}, stop={esc(record.get('stop_reason'))}</dd>")
    if case.get("facts_if_asked"):
        parts.append("<dt>Facts the user could have given</dt><dd><details><summary>show</summary><ul>" + "".join(
            f"<li><strong>{esc(k)}</strong>: {esc(v)}</li>" for k, v in case["facts_if_asked"].items()) + "</ul></details></dd>")
    if case.get("expected_properties"):
        parts.append("<dt>Expected properties (expert rubric)</dt><dd><ul>" + "".join(
            f"<li>☐ {esc(e)}</li>" for e in case["expected_properties"]) + "</ul></dd>")
    parts.append("</dl>")
    return "".join(parts)


def record_section(record: dict, case: dict, siblings: list[dict]) -> str:
    index = siblings.index(record)
    prev_rec, next_rec = siblings[index - 1] if index > 0 else None, siblings[index + 1] if index + 1 < len(siblings) else None
    nav = " ".join(filter(None, [
        f'<a href="#rec-{esc(stem(prev_rec))}">← {esc(prev_rec["model"])} r{prev_rec["rep"]}</a>' if prev_rec else "",
        f'<span class="muted">{index + 1}/{len(siblings)} for this case</span>',
        f'<a href="#rec-{esc(stem(next_rec))}">{esc(next_rec["model"])} r{next_rec["rep"]} →</a>' if next_rec else ""]))
    badges = "".join(f'<span class="badge {"ok" if record.get(s) else "fail"}">{s[:-3]}</span>' for s in STAGES)
    if "api_error" in record:
        badges = '<span class="badge fail">API error</span>'
    raw = record.get("raw_output")
    raw_html = f"<details><summary>raw model output</summary><pre>{esc(raw[:20000])}</pre></details>" if raw else ""
    return (f'<section class="record" id="rec-{esc(stem(record))}" data-case="{esc(record["case"])}" data-model="{esc(record["model"])}">'
            f'<header><h3>{esc(record["case"])} / {esc(record["model"])} / r{record["rep"]}</h3>{badges}{open_link(record)}{nav}</header>'
            f'<div class="cols"><div>{preview_block(record)}</div><div>{stats_block(record, case)}</div></div>{raw_html}</section>')


def overview_table(records: list[dict]) -> str:
    head = ("<thead><tr><th>case</th><th>model</th><th>rep</th>" + "".join(f"<th>{s[:-3]}</th>" for s in STAGES)
            + '<th class="num">tries</th><th>checks</th><th class="num">in tok</th><th class="num">out tok</th><th class="num">reasoning</th>'
            '<th class="num">latency s</th><th class="num">cost USD</th><th class="num">total kg</th><th>open</th></tr></thead>')
    rows = []
    for r in records:
        checks = r.get("checks", {})
        checks_str = f"{sum(1 for v in checks.values() if v)}/{len(checks)}" if checks else "–"
        if "api_error" in r:
            stages = f'<td colspan="{len(STAGES)}" class="fail">API error: {esc(r["api_error"][:80])}</td>'
        else:
            stages = "".join(f'<td class="{"ok" if r.get(s) else "fail"}">{"✓" if r.get(s) else "✗"}'
                             f'{"" if s != "json_ok" or r.get("json_first_attempt_ok") else " (repaired)"}</td>' for s in STAGES)
        rows.append(f'<tr data-case="{esc(r["case"])}" data-model="{esc(r["model"])}"><td><a href="#rec-{esc(stem(r))}">{esc(r["case"])}</a></td>'
                    f'<td>{esc(r["model"])}</td><td>{r["rep"]}</td>{stages}<td class="num">{len(r.get("attempts", [])) + 1}</td><td>{checks_str}</td>'
                    f'<td class="num">{r.get("input_tokens", "")}</td><td class="num">{r.get("output_tokens", "")}</td>'
                    f'<td class="num">{r.get("reasoning_tokens") or ""}</td><td class="num">{r.get("latency_s", "")}</td>'
                    f'<td class="num">{r.get("cost_usd", 0):.4f}</td><td class="num">{r.get("total_kg_co2e_over_horizon", "")}</td>'
                    f'<td>{open_link(r)}</td></tr>')
    return f'<table class="sortable">{head}<tbody>{"".join(rows)}</tbody></table>'


def per_model_table(records: list[dict]) -> str:
    by_model: dict[str, list] = {}
    for r in records:
        by_model.setdefault(r["model"], []).append(r)
    rows = []
    for model, rs in by_model.items():
        n = len(rs)
        exported = sum(1 for r in rs if r.get("export_ok"))
        checks_total = sum(len(r.get("checks", {})) for r in rs)
        checks_passed = sum(sum(1 for v in r.get("checks", {}).values() if v) for r in rs)
        first_try = sum(1 for r in rs if r.get("first_try_ok", r.get("export_ok")))
        rows.append(f'<tr><td>{esc(model)}</td><td class="num">{n}</td><td class="num">{first_try}/{n}</td><td class="num">{exported}/{n}</td>'
                    f'<td class="num">{checks_passed}/{checks_total}</td>'
                    f'<td class="num">{sum(r.get("output_tokens", 0) for r in rs) / n:.0f}</td>'
                    f'<td class="num">{sum(r.get("latency_s", 0) for r in rs) / n:.1f}</td>'
                    f'<td class="num">{sum(r.get("cost_usd", 0) for r in rs) / n:.4f}</td></tr>')
    return ('<table class="sortable"><thead><tr><th>model</th><th class="num">runs</th><th class="num">ok first try</th><th class="num">export ok</th>'
            '<th class="num">checks passed</th><th class="num">mean out tok</th><th class="num">mean latency s</th>'
            f'<th class="num">mean cost USD</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')


def _page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>'
            f"<body>{body}</body></html>")


def write_html(run_dir: Path, records: list[dict], cases: dict[str, dict]) -> Path:
    config = json.loads((run_dir / "config.json").read_text()) if (run_dir / "config.json").exists() else {}
    options = lambda key: "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in sorted({r[key] for r in records}))  # noqa: E731
    by_case: dict[str, list[dict]] = {}
    for r in records:
        by_case.setdefault(r["case"], []).append(r)
    sections = "".join(f"<h2>{esc(case_id)} <span class=\"muted\">{esc(cases.get(case_id, {}).get('title', ''))}</span></h2>"
                       + "".join(record_section(r, cases.get(case_id, {}), rs) for r in rs) for case_id, rs in by_case.items())
    body = (
        f'<p><a href="../index.html">← all runs</a></p><h1>Run {esc(run_dir.name)}</h1>'
        f'<p class="muted">models: {esc(", ".join(config.get("models", [])))} · reps: {esc(config.get("reps", ""))} · '
        f'effort: {esc(config.get("effort") or "provider default")} · total cost: ${sum(r.get("cost_usd", 0) for r in records):.4f}</p>'
        f'<p class="muted">Trees show the structure the model wrote, not the effective values after library defaults filled the gaps. '
        f'When a number looks off, open the model in the interface (needs a local interface running with DEBUG at {esc(INTERFACE_URL)}).</p>'
        f'<div class="controls"><label>case <select id="f-case"><option value="">all</option>{options("case")}</select></label>'
        f'<label>model <select id="f-model"><option value="">all</option>{options("model")}</select></label>'
        f'<span class="muted">click a column header to sort</span></div>'
        f"{overview_table(records)}<h2>Per model</h2>{per_model_table(records)}{sections}<script>{JS}</script>")
    out = run_dir / "summary.html"
    out.write_text(_page(f"Run {run_dir.name}", body))
    return out


def write_index(runs_dir: Path) -> Path:
    """One table across every run dir holding a config.json, newest first, linking to each summary.html."""
    rows = []
    for run_dir in sorted((p for p in runs_dir.iterdir() if (p / "config.json").exists()), reverse=True):
        config = json.loads((run_dir / "config.json").read_text())
        records = [json.loads(p.read_text()) for p in run_dir.glob("*__r*.json") if not p.name.endswith(".e-f.json")]
        exported = sum(1 for r in records if r.get("export_ok"))
        link = f'<a href="{esc(run_dir.name)}/summary.html">{esc(run_dir.name)}</a>' if (run_dir / "summary.html").exists() else esc(run_dir.name)
        rows.append(f"<tr><td>{link}</td><td>{esc(', '.join(config.get('cases', [])))}</td><td>{esc(', '.join(config.get('models', [])))}</td>"
                    f"<td class=\"num\">{esc(config.get('reps', ''))}</td><td>{esc(config.get('effort') or 'default')}</td>"
                    f'<td class="num">{len(records)}</td><td class="num">{exported}/{len(records)}</td>'
                    f'<td class="num">{sum(r.get("cost_usd", 0) for r in records):.4f}</td></tr>')
    body = ("<h1>AI sandbox runs</h1><table><thead><tr><th>run</th><th>cases</th><th>models</th><th class=\"num\">reps</th>"
            "<th>effort</th><th class=\"num\">records</th><th class=\"num\">exported</th><th class=\"num\">cost USD</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")
    out = runs_dir / "index.html"
    out.write_text(_page("AI sandbox runs", body))
    return out
