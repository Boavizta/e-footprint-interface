# Topic 5 — Maintainability and build

All the CI checks, tests, and build steps that keep the documentation,
the SSOT plumbing, and the modeling templates honest as both repos
evolve. Self-contained so the exploration can resume cold from this
file alone.

---

## Current state

### e-footprint (library)

- **No GitHub Actions CI workflow.** Only `dependabot.yml` and issue
  templates exist under `.github/`. Tests are run locally only.
- Comprehensive `pytest` suite: unit, integration, performance, and
  `test_notebooks.py`.
- `mkdocs` docs build is not automated.

### e-footprint-interface

- **GitHub Actions `ci.yml` on every push:**
  - `poetry install`
  - `pytest tests/unit_tests tests/integration` (Python unit + integration)
  - Playwright E2E tests against Chromium via
    `pytest tests/e2e --base-url http://localhost:8000`
- `test_ui_config.py` already validates that every `__init__` param
  across all web-mapped classes has a `label` entry in
  `FIELD_UI_CONFIG` — a structural guard that catches new classes
  being added without updating the UI config.
- `test_reference_data.py` validates that default JSON files match
  library-computed archetypes; the same file doubles as a
  regeneration script when run directly (`if __name__ == "__main__"`).
- This **run-as-script pattern** (test as guard, script as
  regenerator) is the house style for data files and should be
  reused for modeling template authoring/export.

---

## Checks to add — library side

A GitHub Actions workflow needs to be created for the library. It
should be written alongside the SSOT and modeling-template
implementation phases.

### 1. Python tests (already exists locally, needs CI)

Run the existing pytest suite on every push. Python version: 3.12+
(per library `CLAUDE.md`).

### 2. mkdocs build

`mkdocs build --strict` catches broken links, missing page references,
and nav entries pointing at non-existent files. Runs on every push.
Ensures `web_vs_edge.md` and all How-to stubs are real files before
they can be deep-linked from the interface.

### 3. SSOT description tests (new — from Topic 1)

One new test file, e.g. `tests/test_descriptions.py`. Checks run over
all concrete classes imported from `ALL_EFOOTPRINT_CLASSES`:

- Every concrete class has a non-empty docstring.
- `param_descriptions` is present and exactly covers `__init__`
  params minus `self` and `name`.
- Every `update_<attr>` method for each attribute in
  `calculated_attributes` has a non-empty docstring.
- Every `{kind:target}` placeholder in any description string
  (docstring, `param_descriptions` value, `disambiguation`,
  `interactions`, `pitfalls`) resolves via the handler registry
  defined in Topic 1. `ui` and `doc` kind placeholders are
  forbidden in library-side strings and trigger a failure.
- **Ban-word check:** strings that are intended to be
  context-free (class docstrings, `param_descriptions` values,
  `update_<attr>` docstrings) must not contain UI-specific words
  (`click`, `button`, `drag`, `select from the dropdown`) nor
  Python-specific words (`instantiate`, `import`, backticks). This
  is enforced as a **hard failure from day one**, not a warning —
  the tests are written alongside content, so there is no
  legacy to grandfather in.

These tests **drive content authorship**: they fail until the
description metadata is written, which is the point.

### 4. Modeling template tests (new — from Topic 4)

One new test file, e.g. `tests/test_modeling_templates.py`. Checks
for every entry in `efootprint.modeling_templates` how-to registry:

- The JSON file at the registered path exists.
- `json_to_system(json_path)` loads without error.
- The loaded `System` computes emissions without error (the
  standard pipeline runs to completion).
- Metadata schema: `name`, `description`, `category`, `doc_path`
  fields are present; `category` is `"how_to"`; `doc_path` points
  to a file that exists under `docs_sources/`.
- No `"description to be done"` string appears in any registered
  template's system JSON (catches stale auto-generated
  placeholder content).

### 5. Reference generator smoke test (new — from Topic 4)

Runs the upgraded `generate_object_reference.py` against the live
class set and asserts it exits without error and produces output
files. Does **not** assert prose quality (that is human work), but
does assert that:

- No `"description to be done"` string survives in any generated
  output file (once content is written — this check starts as a
  *count / warning* during the writing phase and becomes a hard
  failure when content is declared complete).
- Every `{kind:target}` placeholder in generated output was
  resolved (no raw placeholder strings in rendered pages).

---

## Checks to add — interface side

Extend the existing `ci.yml`. Add new test files following the
existing layer conventions in `tests/`.

### 1. `{ui:token}` placeholder resolution (new — from Topic 1)

The interface `DescriptionProvider` adapter resolves `{ui:token}`
placeholders by mapping tokens to UI element selectors. A new unit
test (`tests/unit_tests/adapters/test_description_provider.py` or
similar) asserts:

- Every `{ui:token}` that appears in any description string consumed
  by the interface has a registered handler entry.
- Every registered `{ui:token}` maps to a non-empty selector or
  display name.

### 2. `class_ui_config.json` completeness (extend `test_ui_config.py`)

`test_ui_config.py` already checks field-level completeness. Extend
it to check class-level:

- Every class name in `MODELING_OBJECT_CLASSES_DICT` either has an
  entry in `CLASS_UI_CONFIG` or is in an explicit exclusion list.
- Every key in `CLASS_UI_CONFIG` corresponds to a class name known
  to `MODELING_OBJECT_CLASSES_DICT` (catches stale entries from
  deleted classes).

This is the answer to the open question from Topic 1's index entry
("How is the interface's `class_ui_config.json` extension validated
against the e-footprint class set?").

### 3. Modeling template tests (new — from Topic 4)

One new test file, e.g.
`tests/unit_tests/domain/test_modeling_templates.py`. For every entry
in the interface-owned introductory and other registries:

- The JSON file exists at the registered path.
- `json_to_system(json_path)` → `ModelWeb` loads without error.
- `EmissionsCalculationService` runs to completion on the loaded
  model without error.
- Metadata schema: required fields present, valid category.

For the library-owned how-to templates (discovered via
`efootprint.modeling_templates.list_how_to_templates`): run the same
load + compute check in the interface context, to catch edge cases
where a system that loads in the library fails when wrapped by
`ModelWeb`. (The library's own template tests validate correctness;
this test validates interface compatibility.)

### 4. `can_create` predicate tests (new — from Topic 2)

The disabled-button UX refactor (Topic 2) introduces a predicate form
of `get_creation_prerequisites`. Tests in `tests/unit_tests/` assert:

- For each class that has prerequisites, `can_create(model)` returns
  `(False, non_empty_reason_string)` when the prerequisite is absent.
- For each such class, `can_create(model)` returns `(True, "")` when
  the prerequisite is present.
- The reason string is non-empty and does not trigger the ban-word
  list (same ban-words as library-side, minus Python-specific terms,
  plus UI-specific terms are now *allowed* since this is
  interface-side copy).

### 5. Edge toggle latch test (new — from Topic 3)

A unit test for the `ModelWeb` property/method that drives the
navbar toggle latch:

- A `ModelWeb` containing no edge objects returns
  `has_edge_objects == False`.
- A `ModelWeb` containing at least one edge object returns
  `has_edge_objects == True`.
- Confirm the latch logic uses this property (not a session flag or
  UI-only state).

---

## The run-as-script regeneration pattern

The interface already uses this pattern in `test_reference_data.py`
and `test_ui_config.py`: the same file acts as a pytest test (guard
that detects drift) and a regeneration script when run directly
(`python tests/... regeneration args`).

Use this pattern for modeling template authoring:

- A script under `tests/unit_tests/domain/` (or a standalone
  `scripts/` file) can be run directly to:
  1. Instantiate a scenario using Python e-footprint constructors.
  2. Call `system_to_json(system)` to produce the serialized snapshot.
  3. Write the output to the appropriate registry path.
- The matching test guard loads the JSON and runs the smoke checks
  above, catching drift if the library evolves and breaks a template.
- The same approach is used on the library side for how-to template
  authoring. Authoring via the interface (build a model interactively
  then export the session JSON) is also valid; the regeneration script
  is for programmatic authoring of precise scenarios.

---

## Phasing

These checks do not all need to land at once. They are distributed across the
seven implementation steps defined in `99-implementation-plan.md`.

| Implementation step | What lands |
|---|---|
| Step 1 (disabled UX) | Library GitHub Actions CI (existing pytest). `can_create` predicate tests on interface side. |
| Step 2 (SSOT metadata) | SSOT description tests (`tests/test_descriptions.py`) on library side. Hard-fail from day one. |
| Step 3 (SSOT in interface) | `{ui:token}` resolution test and `class_ui_config.json` completeness check on interface side. `DescriptionProvider` round-trip test. |
| Step 4 (docs overhaul) | `mkdocs build --strict` in library CI. Modeling template load/compute tests on library side. Cross-reference consistency check. |
| Step 5 (edge interface) | Edge toggle latch test. |
| Step 6 (templates + tour) | Template load/compute tests on interface side (introductory + other registries). Metadata schema validation. |
| Step 7 (build review) | Reference generator smoke test graduates from count/warn to hard failure on `"description to be done"` strings. Final gap-check across all checks. |

---

## Open questions

- **Library Python version in CI.** Library `CLAUDE.md` specifies
  Python 3.12+. Interface CI uses 3.10.12. The library workflow
  should use 3.12; they are independent and can differ.
- **Ban-word list finalization.** The list from Topic 1 is a starting
  point (`click`, `button`, `drag`, `select from the dropdown`,
  `instantiate`, `import`, backtick). Lock the final list when the
  first SSOT content is written; adjust based on what real content
  naturally wants to say.
- **mkdocs `--strict` flag vs warnings.** Some link-check failures
  may be expected during incremental content writing. Consider
  whether to run `--strict` only on the `main` branch and use a
  softer check on feature branches.
- **Interface CI: `manage.py test` vs `pytest`.** Current CI uses
  Django's test runner but `tests/CLAUDE.md` recommends pytest. This
  inconsistency is pre-existing and out of scope for this project,
  but should be resolved separately (probably: switch CI to
  `poetry run pytest`).
- ~~**Cypress vs Playwright.**~~ Resolved: CI updated to run
  Playwright E2E tests via `pytest tests/e2e`. Cypress steps removed.

---

## How this topic connects to the others

- **Topic 1 (SSOT).** The SSOT description tests (library) and the
  `{ui:token}` + `class_ui_config.json` checks (interface) are the
  enforcement layer that keeps Topic 1's contracts honest.
- **Topic 2 (interface onboarding).** The `can_create` predicate
  tests and edge toggle latch test guard the disabled-button UX and
  the edge toggle latch introduced in Topics 2 and 3.
- **Topic 3 (web vs edge).** Edge toggle latch test and the
  `web_vs_edge.md` mkdocs build check are this topic's direct
  deliverables for Topic 3.
- **Topic 4 (e-footprint docs overhaul).** Modeling template
  load/compute tests, metadata schema validation,
  cross-reference consistency checks, and the reference generator
  smoke test are all Topic 4's CI deliverables, landing in Phase 3
  and Phase 4 above.
