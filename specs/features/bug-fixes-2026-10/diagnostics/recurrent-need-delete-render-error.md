# Deleting a recurrent need shows an error and leaves its card: the card wrapper reads detached contextual containers as live parents

- **Status:** CONFIRMED
- **Confidence:** high. Reproduced locally through the real view on the shipped Industrial IoT example, for both the reported server need and the reported edge process. The exception, frame and `None` object were identified by instrumentation. A monkeypatched fix makes all three need deletions return 200 with the right out-of-band (OOB) card swap, and the full non-E2E suite still passes with it (1049 passed).
- **Reported:** GitHub Boavizta/e-footprint-interface#151 (Clémence Knaebel, 2026-10-01, deployed app, one-model workspace). After "Yes, delete" on a recurrent server need, a modal shows `'NoneType' object has no attribute 'efootprint_class'`. The object is deleted (it is gone after a reload), but the canvas keeps showing it. This was reproduced 3/3: a new need without a job, a new need with a job, and an imported need ("Fleet telemetry"). A 2026-10-02 comment widened the report to an edge need on the "Industrial IoT" example ("Measure temperature and vibration", a `RecurrentEdgeProcess`, in edge function "Sensor records and uploads readings"). **Hypothesis held, with a refinement:** the failure does happen in the interface after deletion, inside `HtmxPresenter.present_deleted_object`. It is not in a `delete_side_effects` hook, the use case or the library. The faulty code is not presenter logic, though. It is the domain wrapper property `ModelingObjectWeb.list_containers_and_attr_name_in_list_container`, which the card templates call while the presenter renders the surviving parent card.

## Root cause

**Request path.** `delete_object` runs the use case, then the presenter (`e-footprint-interface/model_builder/adapters/views/views_deletion.py:47`, `:51`). A need is a list child of its `EdgeFunction`, so `_delete` takes the list branch. It edits the function's list through `EditService.edit_with_cascade_cleanup`, which deletes the orphaned need in the library, then returns `was_list_deletion=True` with the edited function (`e-footprint-interface/model_builder/application/use_cases/delete_object.py:180-219`). The only OOB region is `results_buttons`, so the presenter takes the list-deletion branch. That branch re-renders the top-level ancestor card of each edited container in the same request, on the same in-memory model (`e-footprint-interface/model_builder/adapters/presenters/htmx_presenter.py:318-326`, rendering at `:276-283`).

**Library state at that point (by design).** When the library unlinks a relationship, it detaches the `ContextualModelingObjectAttribute` wrapper (`set_modeling_obj_container(None, None)`). The wrapper stays in the referenced object's `contextual_modeling_obj_containers`. It was appended at construction (`e-footprint/efootprint/abstract_modeling_classes/contextual_modeling_object_attribute.py:17`) and detaching only nulls its container (`e-footprint/efootprint/abstract_modeling_classes/object_linked_to_modeling_obj.py:65-81`). This detaching happens in two places:
- `self_delete` detaches all of the deleted object's forward links (`e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:693-699`). The deleted need's `edge_device` wrapper stays on the shared `EdgeComputer`.
- A list replacement detaches the old entries (`e-footprint/efootprint/abstract_modeling_classes/list_linked_to_modeling_obj.py:74-97`). The surviving sibling need gets a detached entry from the function's old list.

Every library reader treats detached entries as absent:
- `modeling_obj_containers` (`e-footprint/efootprint/abstract_modeling_classes/modeling_object.py:459-465`)
- `nb_of_occurrences_per_container` (`:806-808`)
- typed reverse relationships (`e-footprint/efootprint/abstract_modeling_classes/reactive_core/reverse_relationships.py:81-84`)

Dict keys are pruned outright (`e-footprint/efootprint/abstract_modeling_classes/explainable_object_dict.py:401-414`). A fresh deserialization creates no detached entries, which is why a page reload "fixes" the canvas.

Instrumentation after deleting `Upload-sensor-readings` found these detached entries: one on `Factory-sensor` (EdgeComputer) and two on `Sensor-data-server` (from the cascaded jobs). After deleting `Measure-temperature-and-vibration`, it found detached entries on `Factory-sensor`, its CPU, RAM and storage components, and the sibling `Keep-recent-readings-on-the-sensor`.

**The crash.** Rendering the `EdgeUsageJourney` card reaches the surviving sibling need's default `links_to`. For each direct modeling-object attribute (`edge_device`), it computes `mirrored_cards` (`e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py:359-368`). That calls `list_containers_and_attr_name_in_list_container` (`:415`). This property iterates the raw `contextual_modeling_obj_containers` (`:378-380`, `:386`), takes `container = contextual_container.modeling_obj_container`, which is **`None` for the detached wrapper** (`:388`), and dereferences `container.efootprint_class` at **`modeling_object_web.py:389`**. That raises the `AttributeError` above.

Traceback chain: `views_deletion.py:51` → `htmx_presenter.py:326` → `htmx_presenter.py:281` (`render_to_string` of the top parent card) → template → `modeling_object_web.py:366` → `:415` → `:389`.

The dict sibling property is already safe: `dict_container` returns `None` when the wrapper is detached (`e-footprint/efootprint/abstract_modeling_classes/contextual_modeling_object_attribute.py:92-101`, read at `modeling_object_web.py:402-404`).

`@render_exception_modal_if_error` turns the exception into the reported modal. The modal's `remove #<id>` hyperscript cannot remove the card either, because its selector never matches a nested card (see Flags, Report 3). So the stale card stays.

**Scope.** The crash needs two conditions in one request: (a) a mutation detaches a wrapper that points to object S, and (b) the response computes `mirrored_cards` (through `list_containers…`) on S or on an object holding the detached entry.

A sweep deleted every deletable object of the three introductory examples through the real view. It failed only for `RecurrentServerNeed` and both `RecurrentEdgeProcess` objects of `iot_industrial.json`. Everything else returned 200:
- `Job`s and steps: `JobWeb.links_to` uses `web_id` and never calls `mirrored_cards` (`e-footprint-interface/model_builder/domain/entities/web_core/usage/job_web.py:32-38`).
- Edge components: their web classes override `list_containers_and_attr_name_in_list_container` (for example `e-footprint-interface/model_builder/domain/entities/web_builders/hardware/edge/edge_computer_cpu_component.py:6`).
- Usage patterns: they take the non-list branch with no card render.

Other edge needs that use the default `links_to` follow the same mechanism (`RecurrentEdgeDeviceNeed`, `RecurrentEdgeWorkload`, and other `RecurrentEdgeDeviceNeedBaseWeb` and `ResourceNeedBaseWeb` subclasses). A need whose function has no surviving sibling sharing its targets would not crash.

The bug is **not deletion-only**. Relinking a server need's `edge_device` to another device (library `ModelingUpdate`) and then rendering the top parent card in the same `ModelWeb` raises the same error. So an edit response that re-renders cards after a direct-attribute relink is exposed too. This was confirmed at render level; the full edit form path was not exercised.

**Why tests miss it.**
- Integration deletion tests stop at the use case (`e-footprint-interface/tests/fixtures/use_case_helpers.py:26-28`) and never render.
- The only view-level deletion test deletes a `UsagePattern`, which takes the non-list path (`e-footprint-interface/tests/unit_tests/adapters/views/test_views_deletion.py:7-24`).
- The unit test for the property uses stubs with live containers only (`e-footprint-interface/tests/unit_tests/domain/entities/web_abstract_modeling_classes/test_modeling_object_web.py:308-334`).

## Fix approach

Make `ModelingObjectWeb.efootprint_contextual_modeling_obj_containers` (`modeling_object_web.py:378-380`) return only the entries whose `modeling_obj_container is not None`. This applies the library's own reading rule in the one place that feeds both container properties (it is used only at `:386` and `:401`). A one-line filter here fixes the list path and makes the dict path's implicit guard explicit.

Verified by monkeypatch:
- deleting `Upload-sensor-readings`, `Measure-temperature-and-vibration` and `Keep-recent-readings-on-the-sensor` returns 200 with the top-parent OOB swap, and the deleted id is absent from the body;
- the edit/relink render probe renders;
- `poetry run pytest tests --ignore=tests/e2e -n 4` passes (1049).

This is not "papering over" (constitution §3.1). A detached wrapper has no parent, the library's public `modeling_obj_containers` excludes it, and the interface reads the raw list only because it needs `attr_name_in_mod_obj_container`.

Rejected alternatives:
- **Guard in the presenter** (re-hydrate `ModelWeb` before rendering, or catch and fall back to a canvas OOB): this costs an extra deserialization per delete, or hides the fault. The edit path stays exposed.
- **Filter only at `:388` in the list property**: this works, but leaves the dict property depending on a library internal (`dict_container` returning `None`) and leaves the raw read available to future callers. Filtering at the single source is equally small.
- **Library prunes detached wrappers from `_value.contextual_modeling_obj_containers` on unlink**, as dict keys already are: this is cross-repository, needs a PyPI release before the interface ships, and changes core link bookkeeping on the hot mutation path. Wrappers can be detached and then re-attached, so pruning would need re-registration there. Not needed for this bug. It is an optional library follow-up only if the per-request accumulation of detached wrappers ever matters.
- **Override `links_to` in need web classes the way `JobWeb` does**: this handles one symptom per class and leaves `mirrored_cards` broken for any other caller.

## Files to touch

- `e-footprint-interface/model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`: in `efootprint_contextual_modeling_obj_containers` (`:378-380`), skip contextual containers whose `modeling_obj_container` is `None`.
- `e-footprint-interface/tests/unit_tests/adapters/views/test_views_deletion.py`: add a view-level regression (below).
- `e-footprint-interface/tests/unit_tests/domain/entities/web_abstract_modeling_classes/test_modeling_object_web.py`: extend the list and dict container tests with a detached entry (`modeling_obj_container=None`) that must be ignored.
- `e-footprint-interface/CHANGELOG.md`: add a `## [Unreleased]` fix entry.

## Tests

- **View regression** (`tests/unit_tests/adapters/views/test_views_deletion.py`, Django client plus session, like the existing test there). Load `model_builder/domain/reference_data/modeling_examples/introductory/iot_industrial.json` into the session. Parametrize over `Upload-sensor-readings` (`RecurrentServerNeed`) and `Measure-temperature-and-vibration` (`RecurrentEdgeProcess`). POST `/model_builder/delete-object/<id>/` and assert:
  - status 200 and no exception modal;
  - the body contains the `outerHTML` OOB swap of the `EdgeUsageJourney` top-parent card;
  - the deleted need's id is absent from the body, and its sibling need is still present;
  - the session system data no longer contains the need.

  Run it under `RAISE_EXCEPTIONS` unset: the decorator then returns the modal, and the test asserts it is absent. Before the fix it fails with the reported `AttributeError` (reproduced by the scratch test).
- **Domain unit**: `list_containers_and_attr_name_in_list_container` and `dict_containers_and_attr_name_in_dict_container` ignore a contextual entry whose `modeling_obj_container` is `None`, and `mirrored_cards` on such an object returns `[self]` or its live mirrors without raising.
- **Optional**: an integration-level assertion that, after `DeleteObjectUseCase.execute` on a need, `mirrored_cards` of the shared edge device and of the sibling need resolve on the same `ModelWeb`. This covers the use case → domain boundary without Django.
- **E2E is not required.** The behavior is fully server-rendered, and the view test covers the response.

## Acceptance criteria

- On a one-model workspace, deleting a `RecurrentServerNeed` or a `RecurrentEdgeProcess` (Industrial IoT example; new or imported needs, with or without jobs) shows no error modal. The canvas immediately re-renders the edge usage journey card without the deleted need, the sibling needs and their leader lines stay intact, and the deletion toast appears.
- A page reload shows the same canvas as the immediate post-delete render.
- Existing deletion behavior for jobs, steps, usage patterns and edge components is unchanged.

## Risks and side effects

- `check_can_delete`, `_container_removal_targets` and `mirrored_cards` stop seeing detached entries. On a freshly hydrated model there are none, so pre-mutation decisions are unchanged. After a mutation, only parentless entries are dropped, which matches the library's `modeling_obj_containers`.
- The same filter fixes the latent edit/relink render crash. No separate task is needed for it.
- Once the crash is gone, these nested-card deletions reach the client-side `remove #<id>` hyperscript, which never matches a nested card id. They will log Report 3's hyperscript "is null" console error, which the crash currently masks. No visible defect: the OOB swap already removes the card.

## Flags

- **Report 3 interaction (same batch):** there are no shared files. This fix touches only `modeling_object_web.py:378-380`; Report 3 touches `delete_card_modal.html:9-10` and `htmx_presenter.py:381`/`:401-402`. The tasks can ship in either order. Doing #151 first makes Report 3's error reproducible on every nested-child deletion. The diagnosis also found two facts Report 3's diagnostician should take as input:
  1. For nested children, the modal's selector is never valid. `ask_delete_object` wraps the object without its container (`e-footprint-interface/model_builder/domain/entities/web_core/model_web.py:288-290`), so `obj.web_id` is the root form `sys-<system>-RecurrentServerNeed-Upload-sensor-readings`. The DOM card id is `RecurrentServerNeed-Upload-sensor-readings_in_EdgeFunction-…_in_sys-…-EdgeUsageJourney-…` (`modeling_object_web.py:158-160`). So "is null" comes from a selector mismatch here, not only from a card the response already removed.
  2. For **root-card** deletions (for example a `UsagePattern`), the response contains no card removal. Its OOB targets are only `#btn-open-panel-result`, `#show-results-toolbar-btn` and `#workspace-storage-status` (via `htmx_presenter.py:331-335`). The hyperscript is therefore the only mechanism that removes root cards: it is not dead code. Report 3's proposed "server emits an OOB delete" fix must cover root cards before it drops the hyperscript.
- **Constitution:** §1.3 is respected; there is no modeling logic in the interface, only the library's existing "detached entry has no parent" rule. §3.1 does not apply; see Fix approach. §2.6 needs a changelog entry.
- **Cross-repository:** none required. The interface venv resolves `efootprint` 27.0.0 from the local checkout (`/Users/vinville/dev/e-footprint-full/e-footprint/efootprint/__init__.py`), the same version as the pinned PyPI dependency (`e-footprint-interface/pyproject.toml:43`). The relevant library code was read in that checkout.
- **Migration and serialization:** none. This is runtime wrapper logic only; saved JSON is untouched.
- **Local-only validation:** none needed. Reproduction and the fix check ran locally with the Django test client. Scratch evidence (not committed) is in `/private/tmp/claude-502/-Users-vinville-dev-e-footprint-full-e-footprint-interface/23796261-1031-4f35-ab98-3b287a617058/scratchpad/repro/`.
- **Unrelated observation (not diagnosed, not part of this task):** calling `DeleteObjectUseCase.check_can_delete` directly raised `KeyError` for EcoLogits external API servers, `EdgeStorage` and recurrent edge process component needs. The cause is `get_init_signature_params(container.efootprint_class)[attr_name]` at `modeling_object_web.py:390` meeting a non-constructor relationship attribute. It is unclear whether the UI exposes delete for these objects. Worth a separate check if delete buttons exist on them.

## Decisions

- None pending. The interface-side filter is recommended over a library prune (see Fix approach). The supervisor or user may still choose to schedule the library prune separately.
