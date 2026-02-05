# AGENTS — tests/integration

These tests are **integration tests of the clean-architecture layer** (adapters → use cases → domain),
run **without Django** by relying on `InMemorySystemRepository`.

## Goals

- Validate end-to-end flows (create/edit/delete) via:
  - `model_builder.adapters.forms.form_data_parser.parse_form_data`
  - `model_builder.application.use_cases.*`
  - `model_builder.domain.entities.web_core.model_web.ModelWeb`
- Keep tests **easy to write, read, and maintain**.

## Non-goals

- No Django request/session scaffolding.
- No testing of HTML rendering / templates / HTMX responses.

## Fixtures to use

- see tests/fixtures/system_builders.py for builders of test systems and repositories.

## Form data generation (preferred workflow)

Always build “HTTP-like” form payloads with:

- `tests.fixtures.form_data_builders.create_post_data_from_class_default_values`

Then parse them with:

- `parse_form_data(post_data, post_data["type_object_available"])`

…and feed the parsed dict to the use case.

### Why this matters

`create_post_data_from_class_default_values(...)` makes post data cheap to create and consistent with the UI:

- Fills scalar quantity defaults as `Class_attr` + `Class_attr_unit`.
- Uses web-wrapper defaults (`*.default_values`) when available (so web-specific defaults are honored).
- Supports nested forms and explainable objects “form_inputs” via `__` overrides (see below).

### Patterns to follow

- **Plain scalar/ids overrides:** pass overrides as clean keys; the helper will prefix them:
  - `create_post_data_from_class_default_values("X", "Job", server=server_id)`
  - becomes `Job_server = server_id`

- **Nested object forms:** pass `*_form_data` dicts; the helper JSON-encodes them:
  - `create_post_data_from_class_default_values("Server", "Server", Storage_form_data=storage_post_data)`

- **ExplainableObject form inputs:** override with `attr__form_input_key=value`:
  - Usage patterns:
    - `hourly_usage_journey_starts__initial_volume=1000`
    - `hourly_edge_usage_journey_starts__initial_volume=100`
  - The helper merges these into the default `form_inputs` and emits keys like:
    - `UsagePattern_hourly_usage_journey_starts__initial_volume`

## Use case execution (preferred workflow)

- Create: `CreateObjectUseCase(repository).execute(CreateObjectInput(...))`
- Edit: `EditObjectUseCase(ModelWeb(repository)).execute(EditObjectInput(...))`
- Delete: `DeleteObjectUseCase(ModelWeb(repository)).execute(DeleteObjectInput(...))`

## Assertions (keep stable)

- Prefer **structure-based** assertions over full JSON equality:
  - Use a helper like `_current_structure(ModelWeb(repo))` (class → set(ids)).
- For computed impacts, assert coarse signals:
  - “network energy footprint increases after increasing data transferred”
  - “emissions series is non-empty and non-zero for key categories”

## Style guardrails

- Keep tests short, linear, and readable.
- Use double quotes for strings.
- Respect 120-character lines and don’t systematically break lines between parameters.
- If you must add new test data, extend the generic form builder first rather than writing class-specific builders.
