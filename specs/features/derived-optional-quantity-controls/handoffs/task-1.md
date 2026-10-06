# Task 1 — Declare and validate optional quantity units

Implemented; full-suite validation remains unresolved.

Repositories and implementation ranges: library `f480dfc7a3b323d935d6653f84c3311b4a2257a2..b0cc172a5a9bfd74a05795aeb80e653828f4b1cc`; interface baseline `f87c24b505c3b0c3011c5f26c52cbb8106302724` with no product changes for this task.

## Review pointers

- Task 2 imports `get_expected_input_unit(cls, param_name)` from `efootprint.utils.tools`. It returns a Pint `Unit`, preferring an `ExplainableQuantity` class default over quantity-member `InputUnit` metadata, and raises `TypeError` naming the class and parameter when neither supplies a unit. `InputUnit` lives in the same module; `InstanceCountQuantity` lives in `core.hardware.hardware_base`.
- `get_init_signature_params()` keeps resolved ordinary types; optional scalar validation resolves the declared unit before returning for an empty input. Existing nonoptional quantity and other union behavior is preserved.

## Open concerns

- The required full library suite reports 18 failures in `tests/builders/external_apis/ecologits/test_ecologits_generative_ai.py`: its unchanged `mistralai` / `open-mistral-7b` fixtures are rejected because the installed EcoLogits catalogue no longer lists that model. The first failure reproduces against an archive of library baseline `f480dfc7` using the current environment. No dependency files or unrelated EcoLogits tests were changed. The full-suite gate remains unresolved.
