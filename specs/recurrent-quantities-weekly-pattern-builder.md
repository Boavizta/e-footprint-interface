# Weekly-pattern builder for `ExplainableRecurrentQuantities`

**Status:** Functional spec — implementation plan to follow.
**Date:** 2026-04-21.

## 1. Context and goal

`ExplainableRecurrentQuantities` represents a quantity defined over a canonical week of 168 hours (7 days × 24 hours). Today the only user-authorable builder is `ExplainableRecurrentQuantitiesFromConstant`, which fills every one of the 168 hours with the same value. This is insufficient as soon as a user wants to express the natural rhythm of a workload — e.g. higher load during office hours on weekdays, quieter evenings, empty weekends.

This spec introduces a second, much more flexible builder that lets the user describe the weekly dynamic in a user-friendly way, while keeping the existing constant builder for the degenerate case.

As part of this change, the form field used to author an `ExplainableRecurrentQuantities` (and more generally any polymorphic explainable-quantity field) is upgraded to a **composite field with a builder-type selector**, so that the user can choose *how* they want to describe the timeseries.

## 2. Scope

**In scope**
- A new user-facing builder for `ExplainableRecurrentQuantities` based on **day profiles + week assignment**.
- A generalized composite form field that surfaces a builder-type selector whenever more than one builder is available for the underlying explainable type.
- The same composite form field mechanism also applies to `ExplainableHourlyQuantities` fields; when only one builder is registered (currently the case for hourly quantities), **the selector is hidden and the form looks identical to today** — i.e. zero UX change for fields with a single builder.

**Out of scope (V1)**
- A visual week editor (drag-and-drop timeline, painted 7×24 grid). The V1 widget is form-based.
- A live chart preview of the resulting 168-hour array while editing. The existing read-only recurrent chart continues to be shown on the calculated-attribute panel after save.
- CSV import of a weekly pattern.
- Sub-hour granularity inside a day profile.
- Changing or renaming `ExplainableRecurrentQuantitiesFromConstant` (kept as-is for V1; implementation plan will revisit).

## 3. Mental model: day profiles + week assignment

A weekly pattern is described as:

- **A single unit**, defined once at the field level (read-only, inherited from the attribute's default — same behavior as `FromConstant` today). All values entered by the user in the pattern share this unit.
- **One to seven day profiles**. Each profile represents a "type of day" (e.g. *weekday*, *weekend*, *market-day*).
- **A total-coverage assignment** of the 7 days of the week to those profiles: every one of Mon, Tue, Wed, Thu, Fri, Sat, Sun is assigned to exactly one profile.

Each day profile contains:

- A **name** (user-editable string, must be unique within the pattern).
- A **set of day checkboxes** (Mon..Sun) declaring which days of the week this profile applies to.
- A **baseline value** (numeric, default `0` in the field's unit) used for every hour not covered by an explicit range.
- An **ordered list of time ranges**. Each range has:
    - a **start hour** in `{0, 1, …, 23}`,
    - an **end hour** in `{1, 2, …, 24}` (24 means midnight of the next day),
    - a **value** in the field's unit.

Ranges describe the hours of the day where the quantity differs from the baseline. A profile with no ranges is simply "baseline for 24 hours".

### Example

```
Unit: concurrent

Profile "weekday"
  Days:     [✓ Mon] [✓ Tue] [✓ Wed] [✓ Thu] [✓ Fri] [ ] Sat [ ] Sun
  Baseline: 0
  Ranges:
    07:00 – 12:00 : 60
    12:00 – 14:00 : 40
    14:00 – 18:00 : 80
    18:00 – 22:00 : 20

Profile "weekend"
  Days:     [ ] Mon [ ] Tue [ ] Wed [ ] Thu [ ] Fri [✓ Sat] [✓ Sun]
  Baseline: 5
  Ranges:
    10:00 – 20:00 : 30
```

This describes a week where weekdays follow an office-hours curve with a lunch dip, and weekends have a light constant background with a daytime bump.

## 4. Composite explainable-quantity form field

The existing `ExplainableRecurrentQuantities` (and `ExplainableHourlyQuantities`) form field is replaced by a **composite field** composed of:

1. **A builder-type selector** at the top of the field (e.g. a dropdown or small tab group), listing the builder options available for that explainable type. Possible labels (subject to wording review):
    - `Constant value` → `ExplainableRecurrentQuantitiesFromConstant`
    - `Weekly pattern` → the new builder introduced by this spec.
2. **One sub-form per builder**, only the selected one is displayed.

Behavior:

- **Single-builder case:** if only one builder is registered for the explainable type (currently all `ExplainableHourlyQuantities` fields), the selector is hidden and the field renders exactly as today. This keeps the hourly UX unchanged.
- **Switching preserves per-builder state:** when the user switches from *Constant value* to *Weekly pattern* and back, each builder's inputs retain whatever the user had typed, so exploring options is lossless. Only the selected builder's inputs are submitted on save.
- **Initial selection:** when opening an existing attribute, the selector defaults to the builder that matches the current stored value. When creating a new object, the selector defaults to the builder used by the attribute's default value (today this is the constant builder everywhere).

## 5. Form UX of the weekly-pattern sub-form

Layout of the sub-form when *Weekly pattern* is selected:

- **Header**: the field's unit, displayed once (read-only) — e.g. `Unit: concurrent`.
- **Profiles area**: a vertical list of **profile cards**. Each card contains:
    - Profile **name** input.
    - **Day assignment checkboxes** (Mon..Sun). A day checked on this profile is automatically uncheckable on other profiles (single-assignment invariant).
    - **Baseline** numeric input (default `0`).
    - **Ranges** list: rows of `[ start_hour ] – [ end_hour ] : [ value ]` with a per-row remove button, plus an **Add range** button that appends a new row pre-filled with sensible defaults.
    - A **Remove profile** button (disabled when only one profile remains).
- **Add profile** button below the list (disabled when 7 profiles are already defined).
- Small helper text describing the semantics, comparable to today's constant builder helper ("This pattern repeats every week; each hour of each day takes the value of its profile's baseline unless overridden by a range.").

### Defaults on first open

When the user first switches a field from *Constant value* to *Weekly pattern* (or opens a newly created object with *Weekly pattern* as initial mode), the sub-form is pre-filled with **two profiles**:

- `weekday`, days Mon–Fri, baseline equal to the field's current constant value (or the attribute default), no ranges.
- `weekend`, days Sat–Sun, baseline equal to the same value, no ranges.

This choice matches the most common real-world pattern and means the degenerate "all hours the same value" case is already well represented out of the box — the user just has to add ranges to express deviations.

## 6. Validation rules

The form refuses to save if any of the following is violated:

1. **Profile count:** between 1 and 7 profiles inclusive.
2. **Unique profile names:** no two profiles share the same name. Profile names are non-empty strings.
3. **Full day coverage:** each of Mon, Tue, Wed, Thu, Fri, Sat, Sun is checked on **exactly one** profile — no unassigned day, no double-assigned day.
4. **Time range bounds:** for each range, `0 ≤ start_hour < end_hour ≤ 24`, with `start_hour` and `end_hour` integers.
5. **No overlapping ranges within a profile:** within a given profile, ranges must be pairwise disjoint. Ranges across different profiles are independent.
6. **Numeric values:** baseline and range values are valid numbers in the field's unit.

Validation errors are surfaced inline on the offending profile/range, consistently with other form fields.

## 7. Computed output semantics

The builder produces a 168-element quantity (in the field's unit) following the existing day ordering convention for `ExplainableRecurrentQuantities` (Mon 0h..23h, Tue 0h..23h, …, Sun 0h..23h — to confirm at implementation time; the spec assumes the existing convention is preserved).

For each of the 7 days of the week, given its assigned profile `P`:

1. The 24 hourly values of that day are initialized to `P.baseline`.
2. For each range `(start, end, value)` in `P.ranges`, every hour `h` such that `start ≤ h < end` is set to `value`.

Because ranges within a profile are validated to be disjoint, order of application does not matter.

The result is a 168-element array, stored/served exactly like the array produced by `FromConstant` today (same unit handling, same lazy evaluation pattern, same downstream consumers).

## 8. Relationship with `ExplainableRecurrentQuantitiesFromConstant`

For V1, the constant builder is kept as-is and coexists with the weekly-pattern builder. The composite form field simply lists both as available options.

Whether to eventually subsume the constant builder into a degenerate case of the weekly-pattern builder (one profile, all seven days, no ranges, baseline = constant) is left as an **open question for the implementation plan**, since it has migration and schema implications.

## 9. Out of scope / deferred

- **Chart preview while editing.** The existing recurrent-attribute chart on the calculated-attribute panel continues to work unchanged after save.
- **Visual week editor.** Drag-and-drop / grid painting widgets are deferred; form fields are sufficient for V1.
- **Sub-hour granularity.** Integer hour boundaries only for V1.
- **Baseline expressions / formulas.** Baseline and range values are numeric literals only.
- **Cross-profile templates / copy-from-profile.** Each profile is authored independently.
- **Per-profile units.** A single unit at the field level.

## 10. Open questions to resolve in the implementation plan

- Exact naming of the new builder class and its JSON schema.
- How builders are registered and discovered so that the composite form field can enumerate them, and where per-builder UI metadata (label, template, default `form_inputs`) lives.
- Whether `FromConstant` stays an independent class long-term, or is eventually subsumed.
- The wire format for per-builder state preservation when the selector is toggled (pure client-side vs. hidden inputs vs. HTMX round-trip).
- Confirmation of day ordering convention in the underlying `ExplainableRecurrentQuantities` so that the "Mon/Tue/.../Sun" labels in the form map to the correct indices of the 168-hour array.
- Migration story for existing saved systems: none required for V1 if the constant builder stays, but to revisit if/when we unify.
