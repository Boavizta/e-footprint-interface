# Step 4 — Mechanical track: package, registry, resolver, tests, nav

**Status:** Done (2026-05-21). All sub-steps 4.1, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11 landed in the e-footprint library; `mkdocs build --strict` is clean locally; full pytest suite passes.

This document covers the **mechanical** half of Step 4. The companion `step-04-content.md` covers the prose authorship of the ten mkdocs pages (web_vs_edge, three how-to, four FAQ, two sub-bucket indexes), which is co-authored with the user in dedicated interactive sessions and tracked outside `tasks.md`.

The two tracks ship independently but cross-reference each other:
- Mechanical depends on prose for: nav add-side entries to reference real files; `doc_path` existence test; `mkdocs build --strict` passing.
- Prose depends on mechanical for: the `{doc:}` resolver and topic registry (so placeholders render); the `extra.interface_base_url` Jinja value (so the "Try this interactively" line works); the modeling-template authoring scripts (so How-to Python code blocks can mirror them).

In practice: mechanical scaffolding (4.6, 4.10) can land first as foundation; nav add-side (4.1) and tests (4.9) land after the prose pages they reference exist.

**Repo:** e-footprint (library only).

**Draws from:** `04-efootprint-docs-overhaul.md`, `01-single-source-of-truth.md` (placeholder syntax, `{doc:}` handling), `05-maintainability-and-build.md` (template load/compute checks).

**Depends on:** Step 2 (placeholder utility `efootprint/utils/placeholder_resolver.py`, upgraded `generate_object_reference.py`, `param_descriptions` content on all classes).

**Note on library CI.** There is no library CI workflow yet (Step 1's CI deliverable hasn't landed). `mkdocs build --strict` is documented and run by hand for now; wiring it into CI is deferred to whichever step (Step 1 or Step 7) actually introduces the workflow.

---

## Deliverables overview

1. `efootprint/modeling_templates/` Python package shipped with PyPI distribution: three how-to template JSONs, typed registry, public API.
2. Python constructor scripts (re-runnable) that regenerate each how-to template JSON via `system_to_json`.
3. `{doc:topic}` resolver wired into `generate_object_reference.py`, backed by a small topic→filename registry.
4. `tests/test_modeling_templates.py` covering load, compute, metadata schema, and `doc_path` cross-references.
5. `tests/test_descriptions.py` extended with `{doc:}` resolution checks.
6. `mkdocs.yml` updates: delete two dead entries; add `web_vs_edge`, two sub-bucket index entries, `extra.interface_base_url`.
7. Stub deletions: `design_deep_dive.md`, `evolution_across_time.md`.
8. `mkdocs build --strict` documented as a manual pre-merge check in `CONTRIBUTING.md`. No CI wiring in this step.

---

## Sub-step 4.1 — Stub triage and mkdocs nav update

### Delete (independent — can land first)

- `docs_sources/mkdocs_sourcefiles/design_deep_dive.md`
- `docs_sources/mkdocs_sourcefiles/evolution_across_time.md`

Remove both lines from `mkdocs.yml`:
- Under `Explanation:` — drop `e-footprint design choices deep dive: design_deep_dive.md`.
- Under `How-to guides:` — drop `How to model the evolution of a system across time: evolution_across_time.md`.

### Add to nav (depends on prose track files existing)

- Under `Explanation:` after `methodology.md` — `Web vs edge modeling: web_vs_edge.md`.
- Two new sub-bucket landing pages in the Reference section:

```yaml
  - Hardware:
      - ...
      - Edge: hardware_edge_index.md
        - Edge device: ...
  - Usage:
      - ...
      - Edge: usage_edge_index.md
        - Edge usage pattern: ...
```

(Exact placement to confirm against the generated nav — these become the landing pages for the existing `Edge:` sub-nav groups.)

- FAQ entries already in nav; the prose track fills in the stub files.

No restructure beyond these add/remove operations. Diátaxis bucket order is preserved.

---

## Sub-step 4.6 — `efootprint.modeling_templates` package

New Python sub-package shipped with the PyPI distribution.

### Layout

```
efootprint/modeling_templates/
├── __init__.py                       # public API
├── how_to/
│   ├── __init__.py
│   ├── machine_learning_workflow.json
│   └── registry.py
```

### Public API (`efootprint/modeling_templates/__init__.py`)

```python
from efootprint.modeling_templates.how_to.registry import HOW_TO_TEMPLATES, HowToTemplate
from efootprint.api_utils.json_to_system import json_to_system
from pathlib import Path
import json

def list_how_to_templates() -> list["HowToTemplate"]:
    """Return the registered how-to templates with their metadata."""
    return list(HOW_TO_TEMPLATES)

def get_template(template_id: str) -> "HowToTemplate":
    for tpl in HOW_TO_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    raise KeyError(template_id)

def load_template_system(template_id: str):
    tpl = get_template(template_id)
    with open(tpl.json_path) as f:
        return json_to_system(json.load(f))
```

### Registry shape (`how_to/registry.py`)

```python
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent

@dataclass(frozen=True)
class HowToTemplate:
    id: str
    name: str
    description: str
    doc_path: str         # path under docs_sources/mkdocs_sourcefiles, e.g. "database_modeling.md"
    json_path: Path       # absolute path to the JSON file
    category: str = "how_to"

HOW_TO_TEMPLATES: tuple[HowToTemplate, ...] = (
    HowToTemplate(
        id="machine_learning_workflow",
        name="Machine learning workflow",
        description="Training on a GPUServer plus recurrent inference jobs.",
        doc_path="machine_learning_workflow.md",
        json_path=HERE / "machine_learning_workflow.json",
    ),
)
```

### Packaging

Add `efootprint.modeling_templates` to the package list in `pyproject.toml`. JSON files ship with the wheel via `include = ["efootprint/modeling_templates/how_to/*.json"]` (or whatever Poetry's current packaging convention is in this repo — check `pyproject.toml`).

### Why a `dataclass` over a dict registry

Type safety, IDE auto-complete in the interface (Step 6 imports this), and easier extension when categories beyond `how_to` get factored into the library (currently only `how_to` is library-owned; `introductory` and `other` stay interface-owned).

---

## Sub-step 4.7 — Authoring scripts (Python constructors)

Each how-to JSON is regenerated from a Python constructor. **Locked-in decision: Python constructor + `system_to_json` is the canonical authoring path.** Interface export is not the authoring route for library how-to templates (the library can't depend on the interface).

### Layout

```
efootprint/modeling_templates/how_to/_authoring/
├── __init__.py
└── machine_learning_workflow.py
```

Each module exposes a `build_system() -> System` function and a `if __name__ == "__main__":` block that writes the JSON next to itself in `how_to/`:

```python
from efootprint.api_utils.system_to_json import save_system_to_json
from efootprint.core.system import System
# ... imports of needed core objects

def build_system() -> System:
    # construct the model
    ...
    return System(...)

if __name__ == "__main__":
    from pathlib import Path
    target = Path(__file__).parents[1] / "database_modeling.json"
    save_system_to_json(build_system(), target)
```

(Use whatever the actual `system_to_json` API is in the current repo — check `efootprint/api_utils/system_to_json.py`.)

### Why a `_authoring/` sub-package, not `tests/`

- The scripts ship with the package because users can run them as worked examples (`python -m efootprint.modeling_templates.how_to._authoring.machine_learning_workflow`).
- Underscore-prefix signals "internal authoring tool" without hiding it.
- Keeps `tests/` focused on testing.

### Re-running

The test in sub-step 4.9 loads the JSON via `json_to_system` and compares it round-trip to `build_system()` serialized — if they diverge, the JSON is regenerated by running the authoring script. CI does **not** auto-regenerate; the test fails and the author re-runs the script locally and commits the new JSON.

### Coordination with the prose track

Each how-to template is paired with its How-to page in the prose track. The page's "Python construction" code block is hand-copied from the authoring script. Both sides can be drafted in either order; reconciliation happens at commit time.

---

## Sub-step 4.8 — Mkdocs `extra.interface_base_url` config

Add to `mkdocs.yml`:

```yaml
extra:
  interface_base_url: https://app.e-footprint.com   # or whichever production URL is canonical
```

How-to pages reference it via mkdocs's `{{ config.extra.interface_base_url }}` Jinja syntax in the "Try this interactively" line. Single config point; URL changes propagate to all three How-to pages with one edit.

(If the production interface URL is not yet stable, leave a placeholder + a TODO comment; the deep-link mechanism still works in a build.)

---

## Sub-step 4.9 — Tests

### `tests/test_modeling_templates.py`

Parametrized over `HOW_TO_TEMPLATES`:

**Test 1 — JSON exists and loads.** `tpl.json_path` is a file; `json.load(open(tpl.json_path))` succeeds.

**Test 2 — Round-trips via `json_to_system`.** Loading the JSON produces a `System` instance without raising.

**Test 3 — Computes emissions.** After load, accessing `system.total_footprint` (or the standard end-to-end emissions property — check the actual API) returns a non-empty `ExplainableObject`. No errors during recompute.

**Test 4 — Round-trip is stable.** `build_system()` from the authoring script, serialized via `system_to_json`, byte-equals (or structure-equals modulo source ordering) the committed JSON. If this fails, the test message tells the author to re-run the authoring script.

**Test 5 — Metadata schema.** Every field on `HowToTemplate` is non-empty; `category == "how_to"`; `id` is unique across the tuple.

**Test 6 — `doc_path` exists.** `docs_sources/mkdocs_sourcefiles/<doc_path>` exists as a file. **Depends on the prose track having landed the matching How-to pages.**

**Test 7 — How-to → template reverse check.** For each of the three How-to source files, the file content contains a reference to its matching template (either via the `extra.interface_base_url` link or via an explicit template id in a comment). This catches drift where a How-to page exists but doesn't actually back its template. **Depends on the prose track.**

### Why test 4 is structure-equal, not byte-equal

JSON serialization may not be deterministic across runs (e.g. dict key ordering for sources). Use a tolerant comparator: parse both, sort the `Sources` block by id, and compare. If the repo already standardizes on sorted JSON output, byte-equal works; otherwise structure-equal.

---

## Sub-step 4.10 — `{doc:topic}` resolver and registry

Step 2 ships the parser. This step wires the `doc` handler.

### Topic registry

Small Python module: `docs_sources/doc_utils/doc_topic_registry.py`:

```python
DOC_TOPICS: dict[str, str] = {
    "methodology": "methodology.md",
    "web_vs_edge": "web_vs_edge.md",
    "database_modeling": "database_modeling.md",
    "machine_learning_workflow": "machine_learning_workflow.md",
    "server_to_server_interaction": "server_to_server_interaction.md",
    "best_practices": "best_practices.md",
    "build_process": "build_process.md",
    "measurement_tools": "measurement_tools.md",
    "only_CO2": "only_CO2.md",
    "efootprint_scope": "efootprint_scope.md",
    "why_efootprint": "why_efootprint.md",
    "get_started": "get_started.md",
    "explanation_overview": "explanation_overview.md",
    "tutorial": "tutorial.md",
    "object_reference": "object_reference.md",
}
```

Keys are stable topic ids used in placeholder strings; values are the mkdocs source filenames.

### Handler in `generate_object_reference.py`

```python
from docs_sources.doc_utils.doc_topic_registry import DOC_TOPICS

def doc_handler(target: str) -> str:
    if target not in DOC_TOPICS:
        raise ValueError(f"Unknown doc topic: {target}")
    return f"[{target}]({DOC_TOPICS[target]})"   # mkdocs resolves relative links
```

Register in the handlers dict alongside `class`/`param`/`calc` (from Step 2).

### Test coverage (added to `tests/test_descriptions.py`)

- Every `{doc:X}` placeholder appearing in any library description string has `X` in `DOC_TOPICS`.
- Every value in `DOC_TOPICS` points at an existing file in `docs_sources/mkdocs_sourcefiles/`.
- Every key in `DOC_TOPICS` matches `[a-z_]+` (no accidental whitespace, etc.).

This extends the Step 2 test rather than duplicating logic.

**Ordering:** this is foundation for the prose track (placeholders won't resolve without it). Land early.

---

## Sub-step 4.11 — Manual `mkdocs build --strict` check (documented)

There is no library CI workflow yet, so this step does **not** wire `mkdocs build --strict` into any automation. It documents the manual command and leaves the CI wiring for the step that first introduces the workflow (Step 1 if/when its CI deliverable lands, or Step 7 as the gap-check fallback).

### What to document

Add a short "Documentation checks before merging" section to `CONTRIBUTING.md` (or, if a more specific home exists, `RELEASE_PROCESS.md`):

```
Before merging documentation changes, run the reference generator and a
strict mkdocs build locally:

    poetry run python docs_sources/doc_utils/main.py
    poetry run mkdocs build --strict

The first command regenerates the per-class reference pages from current
class metadata and copies the prose pages into the mkdocs build directory.
The second builds the full mkdocs site with warnings promoted to errors
(broken links, missing files, etc.) and must exit zero.
```

Generated reference files are committed to the repo per the current convention; running the generator before the strict build ensures the committed files reflect current class metadata. A drift check (committed reference files == freshly generated) is deferred to Step 7.

### Why manual for now

- No CI workflow exists to extend.
- The content authorship for this step lands in a controlled set of files; running the strict build by hand before merging is a reasonable interim check.
- When CI is introduced (Step 1 deliverable or Step 7), the two commands above migrate verbatim into the workflow.

---

## Files to change

### Library code

1. `efootprint/modeling_templates/__init__.py` — **new** (sub-step 4.6).
2. `efootprint/modeling_templates/how_to/__init__.py` — **new**.
3. `efootprint/modeling_templates/how_to/registry.py` — **new** (sub-step 4.6).
4. `efootprint/modeling_templates/how_to/machine_learning_workflow.json` — **new**.
5. `efootprint/modeling_templates/how_to/_authoring/__init__.py` — **new**.
6. `efootprint/modeling_templates/how_to/_authoring/machine_learning_workflow.py` — **new**.
7. `pyproject.toml` — add `efootprint.modeling_templates` and its submodules to the package list; include `*.json` files (sub-step 4.6).

### Docs tooling

12. `docs_sources/doc_utils/doc_topic_registry.py` — **new** (sub-step 4.10).
13. `docs_sources/doc_utils/generate_object_reference.py` — register the `doc` handler (sub-step 4.10).

### mkdocs nav and config

14. `docs_sources/mkdocs_sourcefiles/design_deep_dive.md` — **delete** (sub-step 4.1).
15. `docs_sources/mkdocs_sourcefiles/evolution_across_time.md` — **delete** (sub-step 4.1).
16. `mkdocs.yml` — remove two nav entries; add `web_vs_edge`, two sub-bucket index entries, `extra.interface_base_url` (sub-steps 4.1, 4.8).

### Tests

17. `tests/test_modeling_templates.py` — **new** (sub-step 4.9).
18. `tests/test_descriptions.py` — extend with `{doc:}` resolution checks (sub-step 4.10). Modifies the file Step 2 lands.

### Documentation tooling guidance

19. `CONTRIBUTING.md` (or `RELEASE_PROCESS.md` if more appropriate) — add a "Documentation checks before merging" section with the two manual commands (sub-step 4.11). No CI workflow is created or modified by this step.

### Owned by the prose track (listed for completeness)

See `step-04-content.md`:

- `docs_sources/mkdocs_sourcefiles/web_vs_edge.md` — new.
- `docs_sources/mkdocs_sourcefiles/database_modeling.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/machine_learning_workflow.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/server_to_server_interaction.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/best_practices.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/build_process.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/measurement_tools.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/only_CO2.md` — rewrite.
- `docs_sources/mkdocs_sourcefiles/hardware_edge_index.md` — new.
- `docs_sources/mkdocs_sourcefiles/usage_edge_index.md` — new.

---

## Implementation order

```
4.10 ({doc:} resolver + registry)     ── foundation for prose; land early
4.1  delete-side (stubs + nav drops)
4.6  (modeling_templates package skeleton)
4.7  (authoring scripts + JSONs)
4.8  (mkdocs extra.interface_base_url)
[prose track lands its pages — see step-04-content.md]
4.1  add-side (web_vs_edge + two sub-bucket index nav entries)
4.9  (template tests — tests 6, 7 need prose pages to exist)
4.11 (CONTRIBUTING.md note)
```

Recommended sequence for the coding agent:

1. **4.10** first — the resolver and registry unblock validation of any new `{doc:}` placeholders the prose track wants to write.
2. **4.1 delete-side** — drop the two dead stubs and their `mkdocs.yml` entries.
3. **4.6 + 4.7** — package skeleton, then one authoring script + one JSON at a time. Coordinate with the prose track when finalizing each how-to page's Python code block (the prose mirrors the authoring script).
4. **4.8** — drop in the `extra.interface_base_url`.
5. **Prose track lands its pages** (out of this file's scope; see `step-04-content.md`).
6. **4.1 add-side** — wire `web_vs_edge.md` and the two sub-bucket index files into `mkdocs.yml` now that they exist.
7. **4.9** — graduate the tests; tests 6 and 7 now have files to point at.
8. **4.11** — add the "Documentation checks before merging" section to `CONTRIBUTING.md` once `mkdocs build --strict` runs clean locally; no workflow file is created.

---

## Tests at a glance

| Layer | New / extended | What it covers |
|---|---|---|
| Unit | `tests/test_modeling_templates.py` (new) | Template load, compute, metadata schema, doc_path existence, How-to → template reverse cross-check, round-trip stability |
| Unit | `tests/test_descriptions.py` (extended in 4.10) | `{doc:}` target validation, registry consistency |
| Manual | `mkdocs build --strict` (documented in `CONTRIBUTING.md`) | Broken links across the whole site, including new `{doc:}`-resolved links. Run by hand before merging docs changes; CI wiring deferred. |

---

## Cross-cutting concerns

- **Migrations:** None. No JSON schema change on the library side; the new template JSONs ride the current schema version. `version_upgrade_handlers.py` is untouched.
- **Constitution:** Touches §1.4 (doc-as-code SSOT) by feeding the reference generator richer content from Step 2's metadata. No amendment needed — this is exactly the realization the constitution anticipates.
- **Architecture:** New `efootprint/modeling_templates/` sub-package sits alongside `core/`, `api_utils/`, `builders/`. It imports from `api_utils/` (`json_to_system`) and indirectly from `core/`. **Update `specs/architecture.md`** with a one-line mention under the package listing once the package lands.

---

## Risks

- **Risk: Template JSON drift from authoring scripts.** Authors edit the JSON directly (hand-tweaking a value), forget to update the script. **Mitigation:** test 4 in sub-step 4.9 asserts round-trip stability; the author cannot land an inconsistent pair without test failure.
- **Risk: a broken `{doc:}` or `{class:}` link slips into `main` because `mkdocs build --strict` is manual, not enforced.** **Mitigation:** the Step 2 `test_descriptions` already catches `{class:}`/`{param:}`/`{calc:}` issues at unit test time, well before mkdocs sees them, and sub-step 4.10's tests close the `{doc:}` gap. The `--strict` build is then a last-line check rather than the primary one; running it by hand before merging docs changes is sufficient until library CI lands.
- **Risk: Interface base URL not yet finalized.** **Mitigation:** ship a placeholder in `mkdocs.yml`; update when the production URL stabilizes. No technical blocker.
- **Risk: Mechanical and prose tracks land out of order, leaving a window where `mkdocs build --strict` fails.** **Mitigation:** the implementation order above sequences nav add-side and tests 6/7 after the prose pages exist. Until then, the mechanical work is mergeable independently because the failing nav entries simply aren't added yet.

---

## Decisions and scoping

### Locked-in decisions

- **`default_system_data.json` stays as the blank baseline.** Not migrated into the introductory templates and not deleted. Step 6 builds `ecommerce.json`, `ai_chatbot.json`, `iot_industrial.json` fresh.
- **How-to template authoring path: Python constructor + `system_to_json`.** Each how-to JSON has a re-runnable Python authoring script under `_authoring/`. Interface export is not used for library how-to templates.
- **Try-this-interactively URL: single base URL in mkdocs `extra`.** `extra.interface_base_url` resolves the deep-link target on each How-to page.
- **`{doc:topic}` resolution lives in this step.** A topic→filename registry in `docs_sources/doc_utils/doc_topic_registry.py`, consumed by the reference generator and validated in `tests/test_descriptions.py`.
- **Hand-written sub-bucket `index.md` files** for Hardware/Edge and Usage/Edge, not generator-injected (the prose track owns the file content; this track owns the nav entry).
- **Hand-copy Python snippets** in How-to pages, not build-time codegen from JSON. Upgrade only if drift becomes a real problem.
- **Prose authorship is its own track** in `step-04-content.md`. Co-authored interactively with the user; not broken into `tasks.md` units.

### What's out of scope (deferred)

- **Introductory templates** (`ecommerce.json`, `ai_chatbot.json`, `iot_industrial.json`) — Step 6.
- **`other/` category templates** — Step 6 (folder scaffold only).
- **Interface-side template browser merging library and interface registries** — Step 6 sub-phase B.
- **Tag vocabulary** (`showcases:edge`, etc.) — deferred until tags are actually used. Locked-in: "lean closed enum validated in CI, but defer until tags are actually used."
- **A dedicated How-to for web vs edge overall** — `web_vs_edge.md` (Explanation) is enough on its own; if a How-to is later justified, it lands as a follow-up.
- **Reference generator drift check** (committed generated files match current class metadata) — Step 7 graduation.

### Open questions for review

1. **Test 4 strictness (round-trip equality).** Byte-equal versus structure-equal JSON comparison. Recommend structure-equal (sort-tolerant on sources/dicts) to avoid spurious test failures from non-deterministic serialization ordering. Confirm during implementation by inspecting `system_to_json` output for determinism.
2. **`mkdocs.yml` nav placement of sub-bucket indexes.** Both `Hardware → Edge` and `Usage → Edge` are currently sub-trees, not landing pages. Promoting them to have a landing page may slightly change the nav rendering. Confirm the chosen mkdocs theme renders the `<section>: <index.md>` form cleanly before finalising the nav edit.
3. **Authoring scripts as importable vs main-only.** Worth exposing `build_system()` for users who want to study or fork the model in Python without round-tripping JSON? Lean yes (free with the proposed structure); confirm no naming conflict with the registry module.
