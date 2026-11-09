# Task 2 — Install the fresh-start and generation lifecycle

Written 2026-11-09 against e-footprint-interface `1b2ea43740f76b1edcf7f345ed922582d2142bc4`; library reference `afc60887fa05c34d18d5969a45276bb08d3dace0`.
Plan: [Start](../plan.html#confirm-start), [input](../plan.html#input-panel), [installation](../plan.html#installation), [summary](../plan.html#report). Task: [2](../tasks.md#task-2--install-the-fresh-start-and-generation-lifecycle).
Status: approved for Run A on 2026-11-09.

## Start here

- `load_system_into_session`, `render_model_builder`, `reset_model` — [views.py](../../../../model_builder/adapters/views/views.py): extract preparation; retain existing callers and full-builder response triggers.
- `ai_assistant` — [current PoC view](../../../../model_builder/adapters/views/views_ai_assistant.py): replace with two POSTs, remove raw logging/error echo/edit behavior.
- `SessionWorkspaceRepository` — [session workspace](../../../../model_builder/adapters/repositories/session_workspace_repository.py); `distinctify_against_siblings` — [workspace_base.py](../../../../model_builder/adapters/repositories/workspace_base.py); `save_data`, `interface_config` — [session repository](../../../../model_builder/adapters/repositories/session_system_repository.py).
- `SystemImportService.import_system` — [import service](../../../../model_builder/domain/services/system_import_service.py); `validate_for_computation` — [completeness service](../../../../model_builder/domain/services/system_validation_service.py); `ModelWeb.persist_to_cache` — [model_web.py](../../../../model_builder/domain/entities/web_core/model_web.py).
- [Builder template](../../../../model_builder/templates/model_builder/model_builder_main.html), [panel shell](../../../../model_builder/templates/model_builder/side_panels/side_panel_structure.html), `closeAndEmptySidePanel` — [side_panel_utils.js](../../../../theme/static/scripts/side_panel_utils.js): response-only panel composition.

## Change along the code path

Replace the view module/route with `start_ai_bootstrap` and `generate_ai_bootstrap` and register the plan's POST URLs. Replace experimental settings/context with default-off `AI_BOOTSTRAP_ENABLED`, server Mistral key and one availability boolean using Task 1's shared helper; both views 404 when unavailable. Remove the old builder include as soon as its view/context disappear; delete the now-unused floating template in Task 4.

Start resolves `workspace.active_repository()`, assigns request-local `interface_config = {}`, loads scratch through `load_system_into_session(..., workspace=workspace)`, and renders input with `show_example_picker=False`. This writes only the active slot, resets view defaults and leaves Results empty. No pre-clear of backend state. Reference/comparison roles can change after removing/re-adding slots; never hardcode their numeric identities.

Extract `prepare_system_for_session(repository, raw_system_data, workspace=None)` from the load helper's pre-save body: upgrade → import/materialize/size-check → distinctify → `ModelWeb`. The old helper calls prepare then persist; generated modeling calls prepare, existing completeness validator, then persist once. Scratch remains valid for ordinary reset without passing completeness. Serialize Task 1's built System through the inputs-only library boundary and explicitly empty UI settings again before generation preparation.

Generate checks saved emptiness and trimmed blank description before inference. On expected provider/parse/schema/build/computation/size rejection, create a fresh repository for saved-state rendering, return fixed stage-specific visible input feedback (200), and retain escaped description. The saved scratch payload/settings remain unchanged. Non-empty generation neither calls the provider nor resets data. Unexpected storage/infrastructure failures retain ordinary error handling; do not claim a cross-backend atomic guarantee.

On successful persistence, calculate non-fatal metrics and compose summary context into the same builder render. Both panels extend the existing shell and have the AI marker Task 3 will recognize. Input has one required textarea, approved guidance/disclosures, a directly locked Generate form and a submit override without the shell's Results-recompute click. Summary has no form or Save footer; only the inherited close cross, ordered review, metrics qualifications/substitutions, prompt-loss notice and collapsed escaped/selectable prompt. No custom clipboard, summary store, reopen URL or teardown listener.

## Earlier tasks

Task 1 introduces `service.generate/build_answer`, `Completion/GeneratedModel`, safe errors, `complete_mistral`, availability and `estimate_call`. Reuse these contracts; don't import development `Completion`, provider registry, pricing or evaluation runner. Task 3 supplies discoverable entry controls/first-run handling; expose the backend now and test it directly.

## Reuse

`get_example_system_data(SCRATCH_ID)`, `is_empty_model`, existing payload limits, `ModelWeb.persist_to_cache` canonical/recovery serialization, and `render_model_builder` slot deduplication. Use [workspace view tests](../../../../tests/integration/test_workspace_views.py) for slot/ID seeding patterns and [workspace import rejection coverage](../../../../tests/integration/test_workspace_file.py) for saved-settings isolation.

## Invariants and traps

Setting empty config replaces prior authored settings; omitting it lets `save_data` merge old settings into the new graph. Read recovery through a fresh repository after rejection. `persist_to_cache` is the graph publication boundary, with existing shared-workspace budget validation before writes. Prompt/raw answer/metrics must never be assigned to session/config/model JSON; generated graph fields remain the normal saved model. Capture logs with distinct prompt/raw/model-content sentinels, including exception messages containing them. Do not echo validation/SDK exceptions into UI or AI logs.

## Validation

New `tests/unit_tests/adapters/views/test_views_ai_bootstrap.py` owns Django client/session assertions; use `@pytest.mark.django_db`, dummy key/flag and patch the provider at the new view's lookup site. Supply a local `StaticFilesStorage` settings fixture: the existing [integration conftest](../../../../tests/integration/conftest.py) does not apply in the new location. Preserve useful generation assertions from the PoC file; remove replaced endpoint cases while leaving edit-helper-only removal to Task 4.

Parametrize both active slots, reference survival after remove/re-add, populated sibling/empty target, scratch ID collision, edge replacement, discarded selected-input/Sankey settings, and exact sibling payload/settings survival. Exercise invalid/incomplete answers, provider timeout/truncation, compute and budget rejection; assert no graph save on failure, unchanged scratch settings, retained escaped description and no sensitive log/export/session content. Test unavailable flag/key, GET rejection, fresh-only rejection and estimator failure after a successful save. Assert summary/control markup and reload's absence of AI details. Re-run ordinary load/reset/example/import regressions after extraction.

```sh
poetry run pytest tests/unit_tests/adapters/views/test_views_ai_bootstrap.py tests/unit_tests/adapters/views/test_build_workspace_slots.py tests/integration/test_workspace_views.py tests/integration/test_workspace_file.py tests/integration/test_ai_bootstrap.py
```

## Out of scope

New rollback/storage mechanisms, domain completeness rules, browser confirmation logic, view-control redesign, changing edge visibility preference, and retaining/restoring the discarded model.

## Unverified

No unresolved design assumption. Actual view/template/persistence behavior requires implementation tests; browser lifecycle is Task 3, with slot/error permutations kept here.
