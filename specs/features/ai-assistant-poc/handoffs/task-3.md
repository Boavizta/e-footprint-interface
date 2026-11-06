# Task 3 — Edit path
Repositories and implementation ranges: e-footprint-interface `2a5a7862..270e560f`.

## Review pointers
- `ai_sandbox/edit.py` `apply_edits` processes `changed` in section order (servers, APIs, jobs, journeys with
  their steps, patterns) with each entry either built and registered or edited in place, then `removed` in the
  reverse order; the plan's "sets after all adds" ordering is not kept because no set depends on a later add.
- Fields the DSL describes but cannot change (`kind`, a job's `server`/`genai_api`, a pattern's `journey`,
  `device`, `network`, `country`) are accepted when they repeat the read-back value and refused otherwise, since
  small models echo the whole object.
- A step dropped from a journey's re-listed `steps` is deleted through the delete use case (the form path's
  cascade cleanup does the same); a job dropped from a step's `jobs` is only detached.
- The component template already rendered `ai_feedback.applied` from task 1, so it is untouched.

## Design decisions
- Verified in a shell on the built handwritten case: `ModelingUpdate` with the provider and instance-type
  `SourceObject` pair on a `BoaviztaCloudServer` and on an `EcoLogitsGenAIExternalAPI`;
  `to_weighted_explainable_object_dict` on an existing step after a delete and an add in the same request; passing
  a journey's live weight `ExplainableQuantity` objects into the new `uj_steps` dict re-attaches them to the journey.
- `_volume_timeseries` takes a `horizon` (start date and duration) so an edit keeps the current form inputs; a
  non-form series keeps its start date and its length rounded to whole years, growth 0.
- When only `cloud_provider` changes, the current instance name is snapped to the new provider's catalog instead of
  re-sizing on default cores and RAM.

## Resolved concern after rebase onto main
- Removing a job and then its server or API in the same `ModelWeb` originally crashed because detached contextual
  wrappers remained in the target's reverse links. The interface filter added during review is now obsolete:
  `main` uses efootprint 27.0.1, which unregisters wrappers when detached. The filter is removed; the same-model
  deletion regression test remains. See [IMPL-DECISION-02](../plan.html#impl-decision-02).
