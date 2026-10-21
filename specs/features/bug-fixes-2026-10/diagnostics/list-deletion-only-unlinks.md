# Confirmed delete of a list/dict-held object only unlinks it: `_delete` relies on the accordion-children cascade, and `check_can_delete` ignores direct references whenever a removal container exists

- **Status:** CONFIRMED
- **Confidence:** high. Code trace on `dev` at `9dc54426`. Every case was reproduced through the real
  `ask-delete-object` and `delete-object` views (Django client and session), with the persisted session read back
  afterwards. Patterns and journeys were built through the real `add-object`, `link-dict-entry` and
  `link-list-entry` views. Two scratch prototypes, applied by monkeypatch with no product edit, each kept
  `pytest tests --ignore=tests/e2e` green (1049 passed). Probes are in
  `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/s1/`:
  - `test_s1_reconcile.py`: the user's case and the UI steps;
  - `test_s1_probe.py`: shapes built in the library;
  - `test_s1_sweep.py` with `sweep_out.txt` (today), `sweep_block_out.txt` (settled fix) and `sweep_fix_out.txt`
    (rejected delete-everywhere);
  - `s1_block_plugin.py` (settled fix) and `s1_fix_plugin.py` (rejected delete-everywhere);
  - `rel_scan.py`.
- **Reported:** smell sweep S1 and S7 (`smell-sweep.md`).
  - **S1:** list/dict deletion unlinks the object and relies on the accordion-children cascade to delete it. Nothing
    checks that the object is gone. `check_can_delete` skips the direct-reference block whenever a list/dict
    container exists. The three reported survivors are a `UsageJourney` in a 2-journey `UsagePattern`, an
    `EdgeUsageJourney` in a 2-journey `EdgeUsagePattern`, and a custom `EdgeDevice` CPU referenced by a component need.
  - **S7:** `UsagePatternWebBaseClass` fakes empty containers through three overrides, and this is the root of
    S1(a)/(b).
  - **User challenge (2026-10-21):** "when I try to delete a usage journey that has at least one usage pattern
    pointing to it, I get: This UsageJourney is referenced by Daily analyst sessions, Usage pattern 2. To delete it,
    first delete or reorient these usage patterns."
  - **Verdict:** S1 holds in full. The user's modal is real, and it is what the sole-member rule produces. It is not
    a rule that blocks whenever a pattern references the journey (see "Current rule").
  - S7 is only half right. The overrides are why the cascade never fires for journeys. But they correctly encode
    "patterns reference journeys and do not own them". The defect is in the deletion use case.

## Root cause

**Library model.** `UsagePattern.usage_journeys` is a weighted dict
(`e-footprint/efootprint/core/usage/usage_pattern.py:43-52`). `EdgeUsagePattern.edge_usage_journeys` is a
non-empty, duplicate-free list (`e-footprint/efootprint/core/usage/edge/edge_usage_pattern.py:73-90`). One pattern
can hold several journeys, and one journey can be held by several patterns. Before plural patterns (library
`2df074ac`, interface `2190a8e1`, 2026-09-02), a pattern had a single `usage_journey: UsageJourney` direct
reference. Any referencing pattern then blocked the journey's deletion. The library deletes an object only when
nothing holds it: `ModelingObject.self_delete` raises `PermissionError` while `modeling_obj_containers` is not
empty (`e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:678-681`, containers at `:459-465`).

**Current rule for journeys** (`model_builder/application/use_cases/delete_object.py:75-149`). The patterns
holding a journey are its dict or list containers, so they are removal targets (`:61-73`,
`modeling_object_web.py:383-409`). Then:
1. The **sole-member block** (`:92-103`) runs only over removal targets. For each container whose class declares
   `required_non_empty_relationships` (`usage_pattern_web.py:15`, `edge_usage_pattern_web.py:15`), it blocks when
   the journey is in that relationship and `len(relationship) == 1`. It names **only** those patterns. This
   implements `specs/architecture/forms-and-relationships.html:180-181` ("blocked when it is the sole member of a
   required pattern relationship"). It was added with plural patterns.
2. The **direct-reference block** (`:106-118`) is skipped whenever any removal target exists
   (`and not list_or_dict_containers`). It never fires for a journey that a pattern holds.
3. Otherwise the modal offers "Yes, delete".

Weights play no part. The rule counts dict membership (`len`, `:97`), and journey weights are strictly positive
anyway (`field_ui_config.json:301-311`). The number of patterns holding the journey also plays no part. Only
"sole member of at least one holding pattern" matters. Both blocks render the same "referenced by … reorient
these usage patterns" copy (`htmx_presenter.py:360-374`), so they look the same to the user.

**The user's case, reproduced** (`test_s1_reconcile.py`, iot_industrial; "Daily analyst sessions" is that shipped
example's `UsagePattern` `Daily-analyst-sessions`, `iot_industrial.json:48-49`, holding only
`Analyst-reviews-sensor-data`):

| Step (real views) | Delete `Analyst-reviews-sensor-data` |
|---|---|
| R0: shipped example | BLOCKED: "referenced by Daily analyst sessions" (sole member) |
| R1: add "Usage pattern 2" (creation preselects the first journey, `usage_pattern_web_base_class.py:72-78`) | BLOCKED: "referenced by **Daily analyst sessions, Usage pattern 2**", the user's exact message. It is the sole member of both. |
| R2: create "UJ two" and add it to Daily analyst sessions only | BLOCKED: "referenced by **Usage pattern 2**". Daily analyst sessions still references it but is not named. |
| R3: also add "UJ two" to Usage pattern 2 | **"Yes, delete"**. After confirming, the journey survives, removed from both patterns. |
| "UJ two" in R2 (held by Daily analyst sessions with another journey) | **"Yes, delete"** → survives, unlinked |
| Edge: create "EUJ two", add it to "Factory sensors starting up" | "Yes, delete" on `Sensor-working-week` → survives, unlinked |

R2 shows that "blocked whenever a pattern references it" is not the rule. A referencing pattern that is not left
empty is silently left out of the blocker list.

**Reachable in the UI: yes, in two common steps.**
1. Create a second (edge) usage journey.
2. Add it to the pattern, through the pattern's journey field (`dict_count` / `select_multiple`) or through the
   journey panel's "Add to pattern".

Deleting either journey of that pattern then offers "Yes, delete". The journey is only unlinked. Its card
disappears through the modal hyperscript (`delete_card_modal.html:9-10`) and comes back on reload, while the
pattern's results have changed. After Task 3 drops the hyperscript, the card would stay in place under a
"deleted" toast. The user hits the blocking modal only because each of their patterns holds a single journey.

**Mechanism of the silent survival.**
- `_delete`'s container branch (`delete_object.py:180-219`) rewrites each container without the object and
  returns. The only deletion is `EditService`'s orphan cleanup. It diffs the first mirrored card's
  `accordion_children` and needs `gets_deleted_if_unique_mod_obj_container_gets_deleted`
  (`model_builder/domain/services/edit_service.py:44-69`).
- Journeys fail both conditions: `UsagePatternWebBaseClass.accordion_children` is `[]`
  (`usage_pattern_web_base_class.py:57-60`), and `JourneyBaseWeb` sets the flag to `False` (`journey_base_web.py:7`).
- The orphan is serialized again, because `ModelWeb.to_json` writes everything left in `flat_efootprint_objs_dict`
  (`model_web.py:146-151`).
- A custom `EdgeDevice` component referenced by a `RecurrentEdgeComponentNeed.edge_component`
  (`e-footprint/efootprint/core/usage/edge/recurrent_edge_component_need.py:50-53`) keeps one container. The cleanup
  skips it (`edit_service.py:67`), and step 2 above never warned. The component is dropped from `device.components`
  but stays the need's component, hidden from the device card (`test_s1_probe.py` case c).
- `Device/Default-laptop` (UI-unreachable) survives, and its pattern is left with `devices=[]` (case d).

**S7, the `UsagePatternWebBaseClass` overrides.**
- `renders_relationship_children_as_nested_cards = False` (`:19`, consumed at `modeling_object_web.py:419,424`)
  keeps journey cards top-level with root ids. Load-bearing.
- `modeling_obj_containers -> []` (`:47-50`) hides the invisible `System` from the direct-reference block and from
  the blocking-noun lookup (`htmx_presenter.py:363`). It was added in `1731c6ca` "so that usage patterns become
  deletable again". `pre_delete` unlinks the System (`:100-105`).
- `list_containers_and_attr_name_in_list_container -> [], None` (`:52-55`) keeps patterns off the container
  branch. Without it, the System would be edited and re-rendered as a card (`htmx_presenter.py:321`), and patterns
  would get `_in_` web ids.
- `mirrored_cards -> [self]` (`:42-45`) is **redundant**, because the base already returns `[self]` here
  (`modeling_object_web.py:429-430`).
- `accordion_children -> []` (`:57-60`) keeps a pattern's delete modal from announcing that its journeys will be
  deleted (`delete_object.py:121-123`). It also stops `EditService` from deleting a journey that a pattern edit
  removes. `JourneyBaseWeb`'s flag also stops the forward cascade on pattern delete (`modeling_object_web.py:578-583`).
  Unlinking and pattern deletion keep reusable journeys alive, which is correct.

## Reproduction
- `tests/unit_tests/application/use_cases/test_delete_object.py::TestDeleteObjectUseCase::test_referenced_object_is_blocked_naming_every_holder_and_never_only_unlinked`
  — use case (`check_can_delete`, then a forced `execute`); fails on `dev@6a1c10ea`. Parametrized over programmatic
  systems. The asserted tuple is (`can_delete`, sorted blocking names, "object gone or repository
  unchanged after the forced delete").
- Assertion failures (`--runxfail`):
  - `[journey_in_two_journey_pattern]`: `(True, [], False) == (False, ['Pattern'], True)`.
  - `[edge_journey_in_two_journey_edge_pattern]`: `(True, [], False) == (False, ['Edge pattern'], True)`.
  - `[journey_in_two_patterns]` (R2 shape: sole member of "Sole pattern", one of two in "Shared pattern"):
    `(False, ['Sole pattern'], False) == (False, ['Shared pattern', 'Sole pattern'], True)`.
  - `[edge_component_referenced_by_need]`: `(True, [], False) == (False, ['CPU need'], True)`.
  - In every case the forced delete returns normally and the object stays in the saved model, only unlinked.
- Watch (values from the recorded run; `[edge_component_referenced_by_need]` in brackets):
  - `self._container_removal_targets(web_obj, web_class)` at `model_builder/application/use_cases/delete_object.py:89`
    → dict containers `['Pattern']` (`usage_journeys`); edge: list containers `['Edge pattern']`; two patterns:
    `['Shared pattern', 'Sole pattern']` [list containers `['Device']` (`components`)].
  - `blocking_required_containers` at `delete_object.py:99` → `[]`; two patterns: `['Sole pattern']` only.
  - `web_obj.modeling_obj_containers and not list_or_dict_containers` at `delete_object.py:106` → `False`, with
    containers `['Pattern']` [`['Device', 'CPU need']`]: the direct-reference block is skipped.
  - `removed_children` at `model_builder/domain/services/edit_service.py:59` → `[]`, because the pattern's
    `accordion_children` is `[]` [`[CPU]`, but `len(child.modeling_obj_containers) == 1` at `:67`, so it is not
    deleted].
  - `input_data.object_id in self.model_web.flat_efootprint_objs_dict` at `delete_object.py:212` (`_delete`'s
    list/dict branch, `:180` → `True`) → `True`; remaining containers `[]` [`['CPU need']`].
- Debug recipe: break at the test's `data_after = repository.get_system_data()` line, after the forced `execute`.
  Unmasked run: `poetry run pytest --runxfail "tests/unit_tests/application/use_cases/test_delete_object.py::TestDeleteObjectUseCase::test_referenced_object_is_blocked_naming_every_holder_and_never_only_unlinked"`.
- Discrimination: passes (4/4, whole file 10/10) with the settled-fix prototype `s1_block_plugin.py` applied via
  `-p` and no other prototype (Tasks 4, 6 and 8 are not needed for these shapes). The rejected delete-everywhere
  prototype `s1_fix_plugin.py` passes only the component case and fails the three journey cases on the blocking
  names.

## Fix approach

**Settled (2026-10-21): a pattern's reference blocks deleting the journey.** This generalizes
what the user sees: a journey can be deleted only once no pattern holds it. The modal names every holding
pattern, and the existing membership × ("Used in usage patterns", `field_ui_config.json:301-311`;
`list_membership_section.html:11-14` for edge journeys) is the way to detach first. The rule is consistent with:
- every other reference in the app (a server referenced by jobs, a network, a country or an external API are all
  blocked, "Blocked, explained", `specs/design/journeys/build-a-model.html:504`);
- journey deletion before plural patterns;
- "never silent" (`build-a-model.html:470`): deleting a journey would otherwise silently change other patterns'
  results.

It is also the leaner change. Steps:
1. **Removal targets are ownership containers only.** In `_container_removal_targets` (`delete_object.py:61-73`),
   keep only containers with `renders_relationship_children_as_nested_cards`, the existing flag whose documented
   meaning is "reference, not rendered ownership" (`forms-and-relationships.html:168-176`). Journeys (and
   `Device` in `UsagePattern.devices`) then have no removal target. The default direct-reference block names all
   holding patterns, as the library's `self_delete` precondition would. The sole-member block (`:92-103`) becomes
   dead for deletion, because `required_non_empty_relationships` is declared only on the two pattern wrappers.
   Delete it. The attribute stays, for the membership sections' last-member guard (`modeling_object_web.py:236,271`).
2. **Block residual references** (`:105-118`). Compute
   `residual = [c for c in web_obj.modeling_obj_containers if c.efootprint_id not in removal_ids]`. Apply the
   existing rule (`can_delete` hook, else block naming them) whenever `residual` is not empty, and drop
   `not list_or_dict_containers`. This blocks case c, naming the need. Paths that work today are unchanged:
   - with no removal target, `residual` is every container;
   - for `handles_own_dict_memberships` classes, parent groups stay residual;
   - patterns keep `[]`.
3. **"Gone or error" in `_delete`** (`:158-235`). One tail for both branches. After unlinking, if the object is still
   in `flat_efootprint_objs_dict`, run `pre_delete` and `web_obj.self_delete()`. The library raises
   `PermissionError` on any residual reference, so the view shows the error modal and nothing is persisted
   (`:151-156`). Call `delete_side_effects()` once, at the end. With steps 1 and 2 this tail is only a backstop.
   Every list/dict deletion left is an owned nested child that the cascade already deletes, so it is the invariant,
   not a second path.
4. **S7, folded.** Remove the redundant `mirrored_cards` override. Reword the remaining comments: "the System is
   never a removal or blocking container; `pre_delete` unlinks it"; "patterns reference journeys, they never own
   them".

Task 3's OOB-delete condition stays as written. List deletions now target only nested cards, which the top-parent
re-render covers. Prototyped in `s1_block_plugin.py`: the suite stays green, and the sweep is in
`sweep_block_out.txt`.

**Rejected:**
- *Delete everywhere,* i.e. keep patterns as removal targets plus the sole-member block, and let the tail delete
  the unlinked journey. It keeps the inconsistency the user's case exposes: some referencing patterns block, while
  others are silently changed (R2). It would also need Task 3's OOB delete widened to list deletions with a root
  card, and a confirmation listing the patterns that lose the journey. Prototyped in `s1_fix_plugin.py`.
- *Copy-only fix.* It leaves case c inconsistent and keeps a half-delete.
- *Flip `JourneyBaseWeb`'s flag or the pattern's `accordion_children`.* Pattern edits, unlinks and pattern deletes
  would then delete reusable journeys.
- *Cascade-delete the need in case c.* This is settled below as block.
- *A generic "System is never a container" filter in `efootprint_contextual_modeling_obj_containers`.* It is wider
  than this bug and gives no behavior gain. Leave it to S4 if wanted.

## Files to touch
- `e-footprint-interface/model_builder/application/use_cases/delete_object.py`:
  - ownership-only removal targets (`:61-73`);
  - remove the sole-member block (`:92-103`);
  - residual-reference block (`:105-118`);
  - single deletion tail with one `delete_side_effects` call (`:177-235`).
- `e-footprint-interface/model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py`: remove the
  `mirrored_cards` override (`:42-45`) and reword the comments at `:47-60`.
- `e-footprint-interface/specs/architecture/forms-and-relationships.html:168-181` ("Required pattern-to-journey
  relationships"). Replace the sole-member sentence (`:180-181`) with: "Deleting a journey is blocked while any
  pattern holds it, naming every holding pattern; remove it from those patterns through its membership section
  first." Add one line: a container that does not nest a child
  (`renders_relationship_children_as_nested_cards = False`) is a reference, not a removal target, so it blocks the
  child's deletion. `required_non_empty_relationships` now only guards last-member removal in the widgets and the
  membership sections.
- `e-footprint-interface/CHANGELOG.md`: `## [Unreleased]` fix entry. Deleting a journey held by a pattern is now
  blocked instead of silently unlinking it. A custom edge component referenced by a need is blocked.

## Tests
- `tests/unit_tests/application/use_cases/test_delete_object.py::TestDeleteObjectUseCase::test_referenced_object_is_blocked_naming_every_holder_and_never_only_unlinked`
  is the task's only test: remove its expected-failure marker. It covers the journey and edge-journey blocks, every holding pattern named, the need-referenced component, and "deleted or model unchanged" for a forced
  delete.
- Existing coverage that must keep passing (not new tests): the E2E unused-journey deletions
  (`tests/e2e/objects/test_usage_journeys.py::test_delete_usage_journey`, `test_full_journey.py:143-165`) and the
  existing deletion suites (patterns, grouped edge devices, jobs, steps, needs).
- The earlier list (unit, integration and view cases, the `Device` in `UsagePattern.devices` case) is subsumed by
  the reproduction and the existing suites.

## Acceptance criteria
- A journey or edge journey held by any pattern shows the blocking modal naming every holding pattern. It is never
  offered "Yes, delete". Once removed from all patterns through the membership ×, it deletes with its unshared
  steps or functions.
- A custom edge device component that a component need references shows the blocking modal naming that need, and
  the model is unchanged. Without such a need, it is still deleted.
- No confirmed delete returns 200 while the object stays in the saved model. It deletes, or it shows the error
  modal with the session unchanged.
- The four shipped examples (`sweep_out.txt` → `sweep_block_out.txt`): today 6 objects survive a confirmed delete.
  - `Device/Default-laptop` in all four examples. It is UI-unreachable (S11) and becomes blocked, like Network and
    Country.
  - `Factory-sensor-CPU`/`-RAM` (Task 8) become blocked.
  - None survive afterwards. The remaining `ERROR`/`ASK_EXC` rows belong to Tasks 4 and 6.
- Pattern, job, step, edge function, need, server and edge-group deletions behave as before.

## Risks and side effects
- **Behavior change.** Users who relied on "Yes, delete" to drop a journey from a multi-journey pattern now get the
  blocking modal, and must use the membership × first: one more click per pattern. The modal does not say where
  the × is. Copy is deferred (see Decisions).
- The blocking noun comes from `modeling_obj_containers[0]` (S12). For case c it reads "reorient these edge
  devices" while it names the need. Deferred.
- Sessions that already hold an orphan from case c keep it. After Task 8, `EdgeComponentWeb.mirrored_cards`
  assumes a device container (`edge-component-delete-silent-noop.md`, risk at `:109`), so such an orphan could
  fail to render where it is placed. No migration: the orphan is user-made, rare, and no longer produced.
- Journeys orphaned by the current bug are already plain top-level journeys held by no pattern. They stay deletable
  normally.

## Flags
- **Order:** after Tasks 3, 4, 6 and 8 in the same run.
  - **Task 8 (hard):** without it, an edge appliance's built-in component reaches the tail and raises (error
    modal instead of the blocking modal).
  - **Task 6 (soft):** same property family; its panels make more blocked cases reachable.
  - **Task 3 (soft):** its OOB-delete rule is unchanged, but both tasks touch `delete_object.py`'s return paths.
  - **Task 4 (soft).**
- **Shared files:**
  - `delete_object.py`: Tasks 3, 6 and 8 tests;
  - `test_views_deletion.py`: Tasks 3, 4 and 8;
  - `test_delete_object.py`: Tasks 6 and 8;
  - `CHANGELOG.md`: all tasks.
- **Invariants:** constitution §1.3 (the library's `self_delete` precondition decides) and §3.1 (no silent
  half-delete). `build-a-model.html:470` "never silent".
- **FULL review surface:** an application use case, plus a relationship-semantics doc change.
- No migration, serialization or library change.

## Decisions
- 2026-10-21: a custom edge device component referenced by a need is **blocked, naming the need**. It does not
  cascade-delete the need.
- 2026-10-21: copy fixes are **deferred** to a copy backlog with smell-sweep S12. This covers the blocking noun
  ("reorient these edge devices" for case c) and the journey confirmation or blocking wording (where to unlink, or
  which patterns are affected).
- 2026-10-21: deleting a usage journey or edge usage journey is **blocked while any pattern holds it**, naming
  every holding pattern. Detaching goes through the membership section's ×. Delete-everywhere is rejected. The
  fix:
  - only nesting containers are removal targets;
  - the sole-member block is deleted;
  - references left after removal block the delete;
  - a "gone or error" tail is added to `_delete`.

  Task 3's OOB-delete rule stays as written. `forms-and-relationships.html:168-181` is updated to the new rule.
