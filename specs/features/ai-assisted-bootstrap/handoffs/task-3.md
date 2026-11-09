# Task 3 — Entry points and stable view controls

Repository and implementation range: `e-footprint-interface`, `feac27aa..f0a8e462`.
Companion library reference: `e-footprint` at `afc60887`, unchanged.

## Review pointers

- Both availability-gated entries POST Start with the same active-canvas confirmation. The picker card belongs only to the presenter. The picker now sits below the toolbar so Modeling actions remains usable when an empty-model import reopens it.
- Explicit Modeling/Simplified inputs destinations use the existing workspace owner, pressed states and slot memory. Reselecting the current view is a no-op, including dirty Configure; actual exits retain Save/Discard/Stay without replay.
- Supervisor-approved integration ownership extends to `model_builder_main.html` and `components/results_bar_button.html`: whole-builder AI responses must render open panel/canvas/button classes directly. HTMX settling otherwise restores hidden/full-width response classes after the shell opens the panel.
- `test_ai_bootstrap.py` scopes settings, fake inference, offline Boavizta, isolated caches and `base_url` to its module. Its page fixture starts/stops Playwright inside the transactional DB lifetime, avoiding async-safety opt-ins or shared fixture changes. Generated JS bundles/maps were rebuilt and remain ignored under the repository's existing asset policy; CSS/maps are committed.
