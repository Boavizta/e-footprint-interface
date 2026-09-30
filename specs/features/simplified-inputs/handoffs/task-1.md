# Task 1 implementation handoff

## Implementation ranges

- `e-footprint`: `b718142e075f1e4216af7ea556b75be1a920082d..84d8a950a4262e84ceb27a7fe389e45130fbf4dd`
- `e-footprint-interface`: `741979aefdf7c4e9f8677654d43b300683fbf6c0..76d2a14274943a0da68c619c7d0104d17d58228c`

## Review pointers

The library package and public API now use `efootprint.modeling_examples`; resource globs, registries, authoring helpers, tests and how-to deep links use the Examples terminology. The serialized scenario JSON files retain their content and IDs.

The interface catalog, presenter, route names, picker context/DOM selectors, authoring script names and UI copy use Examples. The shareable route is `/example/<id>/`. The Django rendering file remains `model_builder/templates/model_builder/onboarding/template_picker.html`.

## Unresolved check

The full interface pytest suite still reports `tests/test_no_dev_dependency.py` against the pre-existing editable sibling dependency in `pyproject.toml`. That editable dependency and its lockfile changes were explicitly preserved and excluded from the implementation commit; rerun the dependency guard after restoring the published dependency before merge/release.
