# Dynamic `Initial volume` label and tooltip in `hourly_quantities_from_growth`

## Goal

Make the `Initial volume` subfield inside
`hourly_quantities_from_growth.html` use a class-specific label and tooltip for:

- `UsagePatternWeb`
- `EdgeUsagePatternWeb`

This change only affects display metadata. It must **not** change:

- the numeric default value for `initial_volume`
- the default `initial_volume_timespan`
- form parsing or saved payload shape

## Current state

The composite timeseries field is generated as a single field with:

- `input_type = "hourly_quantities_from_growth"`
- `default = default.form_inputs`

The nested `Initial volume` UI is then hardcoded directly in
`model_builder/templates/model_builder/side_panels/dynamic_form_fields/hourly_quantities_from_growth.html`.

Today this creates two problems:

1. The sub-label is fixed to `Initial volume`.
2. There is no hook to inject a per-class tooltip for that nested subfield.

The existing `field.tooltip` mechanism is not enough because it applies to the top-level field,
not to the inner `initial_volume` row inside the composite widget.

## Design choice

Keep the template generic and move class-specific wording into the web wrapper layer.

Do **not** add class conditionals in the template such as:

```django
{% if object_type == "UsagePattern" %}...{% endif %}
```

Instead, extend the generated field context with nested metadata for composite subfields.

## Planned implementation

### 1. Add declarative UI metadata on usage pattern web classes

Add a class attribute on `UsagePatternWebBaseClass` for UI metadata related to the
`hourly_quantities_from_growth` composite field.

Recommended shape:

```python
hourly_quantities_from_growth_ui_config = {
    "initial_volume": {
        "label": "Initial volume",
        "tooltip": None,
    },
}
```

Then override this attribute in:

- `UsagePatternWeb`
- `EdgeUsagePatternWeb`

Each subclass will provide its own `label` and `tooltip` for `initial_volume`.

This keeps the ownership in the same layer that already defines class-specific form behavior and
defaults, and it matches the repository’s existing declarative style based on class attributes such
as `default_values`, `form_creation_config`, and `form_edition_config`.

### 2. Inject nested UI metadata during form generation

In `model_builder/adapters/forms/form_field_generator.py`, update the
`ExplainableHourlyQuantitiesFromFormInputs` branch so the generated field dict includes a nested
metadata block.

Recommended shape:

```python
structure_field.update({
    "input_type": "hourly_quantities_from_growth",
    "default": default.form_inputs,
    "subfields": corresponding_web_class.hourly_quantities_from_growth_ui_config,
})
```

That gives the template a stable contract such as:

```python
field["subfields"]["initial_volume"]["label"]
field["subfields"]["initial_volume"]["tooltip"]
```

This approach is preferable to overloading `field.tooltip` because it scales naturally if other
subfields later need class-specific wording.

### 3. Update the template to consume nested metadata

In `hourly_quantities_from_growth.html`:

- replace the hardcoded `Initial volume` text with the injected label
- render a tooltip icon next to the label only when a tooltip is present

The template should use the existing tooltip component rather than introducing a new popover
pattern, because side panel popovers are already initialized centrally.

Recommended rendering pattern:

- wrap the label and icon in a small row similar to `dynamic_form_fields/label.html`
- temporarily bind the nested tooltip value into `field.tooltip` when including the shared tooltip
  partial, or extract a tiny dedicated include if that is cleaner

Important constraint:

- keep the HTML ids and input names unchanged so parsing and tests do not break

### 4. Preserve fallback behavior

The base class attribute should provide a safe default label and no tooltip.

That ensures:

- other classes inheriting the same composite widget continue to render correctly
- the template does not need defensive branching for missing config

## Files expected to change

- `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py`
- `model_builder/domain/entities/web_core/usage/usage_pattern_web.py`
- `model_builder/domain/entities/web_core/usage/edge/edge_usage_pattern_web.py`
- `model_builder/adapters/forms/form_field_generator.py`
- `model_builder/templates/model_builder/side_panels/dynamic_form_fields/hourly_quantities_from_growth.html`

## Testing plan

### Unit / snapshot coverage

Update the creation structure snapshots so the generated field now includes the nested metadata:

- `tests/unit_tests/domain/entities/class_structures/UsagePatternWeb_creation_structure.json`
- `tests/unit_tests/domain/entities/class_structures/EdgeUsagePatternWeb_creation_structure.json`

Expected assertions:

- `UsagePatternWeb` snapshot contains the `initial_volume` label and tooltip under `subfields`
- `EdgeUsagePatternWeb` snapshot contains its own distinct `initial_volume` label and tooltip

### UI verification

Manual verification in both add and edit side panels:

1. Open a `UsagePattern` form and confirm the `Initial volume` row shows the intended label and tooltip.
2. Open an `EdgeUsagePattern` form and confirm the same row shows the alternate label and tooltip.
3. Hover or focus the tooltip icon and confirm the popover appears.
4. Save both forms and confirm the submitted payload and behavior are unchanged.

### Regression checks

Verify that this feature does not alter:

- `initial_volume` form values
- `initial_volume_timespan` values
- chart refresh behavior triggered by the existing `_=` handlers
- side panel popover initialization

## Notes for implementation

- Keep the change additive and localized. No parser or use-case code should be touched.
- Avoid introducing template logic that depends on concrete class names.
- Prefer a nested `subfields` structure over ad hoc top-level keys like
  `initial_volume_label` / `initial_volume_tooltip`; the nested structure is clearer and easier to
  extend.
