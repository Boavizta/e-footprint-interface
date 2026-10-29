# Task 3 — Edit path
Written 2026-10-29 against e-footprint-interface `0899c3c4` (efootprint from PyPI in the venv).
Plan: [1.4 edit](../plan.html#edit) with accepted [PLAN-UPDATE-01](../plan.html#plan-update-01).
Task: [tasks.md](../tasks.md#task-3--edit-path).
Status: under review. The plan's cut line: dropping this task leaves tasks 1 and 2 shippable.

## Start here
- The view's non-empty branch — `model_builder/adapters/views/views_ai_assistant.py` (task 1) — replace `AssistantError("Editing is not available in this build.")` with the plan's 1.4 else branch: `system_to_dsl`, `complete(model, EDIT_PROMPT, ...)`, `parse_json`, `apply_edits`, `model_web.persist_to_cache()`, `feedback["applied"]`, `feedback["note"]`.
- `system_to_dsl` and the `*_FIELDS` tables, per-kind builders, seedable `_Shared` — `ai_sandbox/edit.py` and `ai_sandbox/dsl.py` (task 2) — `apply_edits` builds its name lookups from the same walk and adds objects through the same builders.
- `ModelingObject.__setattr__` — library, `efootprint/abstract_modeling_classes/modeling_object.py` in site-packages — every assignment recomputes and validates; this is the only validator.
- `ModelWeb.add_new_efootprint_object_to_system` — `model_builder/domain/entities/web_core/model_web.py:311` — registers a created object and one level of its modeling-object attributes (storage, devices, network, country) in the response dicts.
- `UsagePatternWebBaseClass.pre_add_to_system` — `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py:96` — appends a new pattern to `system.usage_patterns`; call it (or do the same append) before registering.
- `DeleteObjectUseCase.check_can_delete` and `_delete` — `model_builder/application/use_cases/delete_object.py:75` and `:158` — removals; `execute` (line 151) persists and must not be used. Construct with `input_catalog` from `model_builder.adapters.presenters.simplified_inputs` as `views_deletion.py:21` does.
- `to_weighted_explainable_object_dict` — library, `efootprint/abstract_modeling_classes/explainable_object_dict.py:27`, signature `(input_value, weight_label=None)` — rebuilds a step's `jobs` or a journey's `uj_steps` from a list with repeats giving the weight.
- `ModelingUpdate` — library, `efootprint/abstract_modeling_classes/modeling_update.py:18`, `ModelingUpdate(changes_list)` with `[[attribute, new_value], ...]` — one batch for a provider and instance-type pair.
- `ModelWeb.persist_to_cache` — `model_web.py:187` — the single write of the path.

## Change along the code path
1. `ai_sandbox/prompts/edit_prompt.md`: the addendum appended to the generation prompt. It states the answer shape of the plan's 1.4 snippet (`changed` by section, `removed` by name, `note`), the rules (match by name within a section; a known name with fields sets those fields; an unknown name is a complete new object; a journey's `steps` and a step's `jobs` re-list all children; no renames, no nulls; change only what is asked) and that the current model follows as JSON.
2. `edit.py`: `apply_edits(answer, model_web) -> list[str]` returning the human lines for the feedback ("set Browsing.volume to 5,200,000 per month", "added job Push notification on API server", "removed job Photo upload"). Order of work: new servers and APIs, new jobs, changed and new journeys and steps, new usage patterns, field sets, removals. Everything mutates `model_web.system.modeling_obj` and the objects reachable from it; nothing is persisted here.
   - Lookups by name from the library walk of task 2; two objects with the same name in a section → `ValueError` naming them.
   - New object: validate the section's pydantic class (`JobSpec.model_validate(obj)` and so on), build with the task 2 builder, seeded `_Shared` from the current devices, networks and countries, then `model_web.add_new_efootprint_object_to_system(obj)`; for a usage pattern also the `pre_add_to_system` append.
   - Table field: `setattr(obj, attr, SourceValue(value * unit, comment=comments.get(field)))`.
   - Volume or growth: new `_volume_timeseries(VolumeSpec, growth, comment)` assigned to `up.hourly_occurrences`, the omitted half read from the current `form_inputs` (growth 0 when the current series is not a form one).
   - Server sizing (`cores`, `ram_gb`, `cloud_provider`, `instance_type`) on a `BoaviztaCloudServer`: merge with current, `resolve_cloud_instance`, then `ModelingUpdate([[server.provider, SourceObject(provider)], [server.instance_type, SourceObject(instance)]])`. GenAI `provider`/`model_name` on an `EcoLogitsGenAIExternalAPI` the same way with `resolve_genai`. Any other server or API class → refuse with the plan's "not supported by the assistant in this experiment; change it by hand".
   - Re-list children: `step.jobs = to_weighted_explainable_object_dict([job objects by name])`, `journey.uj_steps = to_weighted_explainable_object_dict([...])`; new steps in a journey are built first with `build_step`.
   - Remove: `use_case = DeleteObjectUseCase(model_web, input_catalog)`; `check_can_delete(obj.id)`; if blocked, raise with `blocking_containers`; else `_delete(DeleteObjectInput(obj.id))`.
   - Not expressible (`device`, `network`, `country`, `kind`, renames, `null` values, a `server`/`genai_api` change on a job): raise with the plan's message.
3. View: the plan's else branch; `EDIT_PROMPT = SYSTEM_PROMPT + "\n\n" + edit_prompt.md`; the user message is `Current model:\n{json.dumps(current, indent=1)}\n\nRequest: {prompt}`. On any exception the handler of task 1 already re-hydrates `ModelWeb(repository)` for the render, discarding the in-memory mutations.
4. Template: render `ai_feedback.applied` as a list under the note (task 1 left the slot).
5. `ai_sandbox/README.md`: one paragraph under "How it works": the interface's flagged assistant imports this folder; `edit.py` and the edit addendum.

Visible result: after "double the volume of the browsing usage pattern", the builder re-renders with that one value doubled and the feedback lists the change; a bad answer leaves the canvas as it was with the error text.

## Earlier tasks
Task 1: the view skeleton, `AssistantError`, `feedback` dict, the re-hydration on failure, the template slot, `parse_json`/`validate_tolerating_extras` in `dsl.py`. Task 2: the tables, per-kind builders with lookups, seedable `_Shared`, `system_to_dsl` and its walk, which `apply_edits` reuses for its lookups (factor the walk into a helper returning the name maps if `system_to_dsl` does not already expose it).

## Reuse
- Builders of task 2 for every add; do not write a second DSL-to-library mapping.
- `DeleteObjectUseCase` internals for removals; do not reimplement container unlinking.
- Test fixture pattern from task 1 (fake `complete`, Django client, `settings.AI_ASSISTANT_ENABLED = True`) and the handwritten case loaded through the generate path or directly through `load_system_into_session` with the exported JSON.

## Invariants and traps
- One persist, at the end, only on success. `check_can_delete` builds a preview `ModelWeb` when simplified inputs are selected; that preview is not the live one and is harmless.
- `_delete` on a job that is in steps goes through `EditService.edit_with_cascade_cleanup` on each container; a job removed and re-listed in the same request must be re-listed after the removal, or simply refused; keep the order above and let the library raise on an inconsistency.
- Objects created by the builders carry fresh ids; `add_new_efootprint_object_to_system` is what makes them visible to the canvas and to `to_json`. A `Storage` created with a new server, and any new `Device`, `Network` or `Country`, is registered through the one-level attribute follow; seed `_Shared` from the current model so defaults are reused, not duplicated.
- Assistant-set values carry `Sources.HYPOTHESIS` as the library default for `SourceValue` without a source, and the DSL comment; user-set sources and comments on other fields are untouched because the live objects are edited.
- The view must not import `run.py`; the prompt files are read at import time like `SYSTEM_PROMPT`.
- Constitution: the library validates every assignment; no computation in the adapter; the failure is rendered.

## Validation
- Row 2 in `tests/integration/test_ai_assistant.py`: generate the handwritten case with the task 1 fake, then hand-set a server's `lifespan` with a comment through `ModelWeb` and `persist_to_cache` (outside the DSL vocabulary); fake answer with one changed volume (doubled), one new job on "API server" re-listed in the "Open feed" step, and `removed: {"jobs": ["Photo upload"]}`. Assert: volume form input doubled, the new job present in the step's `jobs`, "Photo upload" absent from the system and from "Upload photo", lifespan value and comment intact, every surviving id unchanged, and `applied` lines rendered.
- Failure case: a fake answer naming an unknown job; the session payload is equal before and after and the error names the job.
- `poetry run pytest tests --ignore=tests/e2e`. Manual on the dev server with a real model on an example: one set, one add, one removal.

## Out of scope
Spending guardrails, conversation memory, edge objects, device/network/country edits, renames (all out of the spec's scope or deliberately refused).

## Unverified
- `ModelingUpdate` with two `SourceObject` attribute changes on a `BoaviztaCloudServer` (the plan marks it "to confirm"); settle in a shell on the built handwritten case before writing the server-sizing branch, and refuse sizing edits with a clear message if the batch does not behave.
- `to_weighted_explainable_object_dict` assignment on an existing step's `jobs` after jobs were deleted and added in the same request; the plan verified the helper on a fresh step only.
