# Add-or-link: offer "Link existing" alongside "Add new" on child object buttons

## Context

When clicking an "Add [type]" button inside an object card (e.g. "Add job" inside a usage journey
step card), the only option is to create a new object. However, the same child object (a job, a
usage journey step, etc.) can be shared across multiple parents. The "link existing" capability
already exists in the edit-parent flow via the `select_multiple` field, but it is buried there.

**Goal:** When there are already linkable objects of the child type in the system, surface a second
"Link existing [type]" button next to the "Add [type]" button. Clicking it opens a focused side
panel showing only the `select_multiple` field for that list attribute, submitting to the existing
`edit_object` endpoint.

## Save button refactor (prerequisite cleanup)

The Save button pattern is duplicated across 7 existing templates that all extend
`side_panel_structure.html`, in two variants:

- **Full onclick** (3 templates): `addEmptyValueWhenSelectMultipleFieldsHaveNoSelectedOption(); setRecomputationToTrueIfResultPaneIsOpen(); document.getElementById('sidePanelForm').requestSubmit()`
- **Partial onclick** (3 templates): `document.getElementById('sidePanelForm').requestSubmit()` only — the two guards are safe to call unconditionally, so these are just incomplete copies
- **`type="submit"`** (2 templates: `rename_system.html`, `import_model.html`) — these need a native submit, not JS-driven

Move the Save button into `side_panel_structure.html` as a `{% block save_button %}` default.
All templates that currently inline the full or partial onclick variant simply remove their Save
button div; they inherit the default. The two `type="submit"` templates override the block.

### `side_panel_structure.html`

Add after the `panel-body` div, before `{{ dynamic_form_data|... }}`:

```html
{% block save_button %}
<div class="mb-3">
    <button id="btn-submit-form" class="btn btn-primary rounded-pill w-100"
            onclick="addEmptyValueWhenSelectMultipleFieldsHaveNoSelectedOption();
                     setRecomputationToTrueIfResultPaneIsOpen();
                     document.getElementById('sidePanelForm').requestSubmit()">
        Save
    </button>
</div>
{% endblock %}
```

### Templates that remove their inline Save button (use the default)

Remove the `<div class="mb-3"><button id="btn-submit-form" ...>Save</button></div>` block from:
- `add/add_panel__generic.html`
- `add/add_object_with_storage.html`
- `add/add_edge_device.html`
- `add/add_recurrent_edge_component_need.html`
- `edit/edit_panel__generic.html`
- `edit/edit_recurrent_edge_component_need.html`

### Templates that override the block label

`import_model.html` has a different button label ("Use your model"). Pass it via a context
variable `save_button_label` with a default of "Save" in `side_panel_structure.html`:

```html
{% block save_button %}
<div class="mb-3">
    <button id="btn-submit-form" class="btn btn-primary rounded-pill w-100"
            onclick="addEmptyValueWhenSelectMultipleFieldsHaveNoSelectedOption();
                     setRecomputationToTrueIfResultPaneIsOpen();
                     document.getElementById('sidePanelForm').requestSubmit()">
        {{ save_button_label|default:"Save" }}
    </button>
</div>
{% endblock %}
```

In `import_model.html`, remove the inline button div and pass `save_button_label` from the view:

```python
context = {"save_button_label": "Use your model", ...}
```

`rename_system.html` uses "Save" so it needs no change beyond removing its inline button div.

---

## What does NOT change

- `add_object_button.html` (standalone top-level buttons without a parent context) — not affected
- `edit_object` view, `EditObjectUseCase`, `parse_form_data` — fully reused, zero changes
- `select_multiple.html` template and `select_multiple.js` — fully reused, zero changes
- All domain / use-case / presenter logic — no changes

## Files to modify

### 1. `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`

Augment `child_sections` to include `linkable_existing_count` per section. This is the number of
objects of that child type that exist in the system but are not already linked to this parent.

```python
@property
def child_sections(self):
    """Structured view of children grouped by their list attribute/type."""
    init_signature = get_init_signature_params(self.efootprint_class)
    sections = []
    for attr_name in self.list_attr_names:
        children = getattr(self, attr_name, []) or []
        annotation = init_signature[attr_name].annotation
        child_type = annotation.__args__[0].__name__
        linked_ids = {child.efootprint_id for child in children}
        all_of_type = self.model_web.get_efootprint_objects_from_efootprint_type(child_type)
        linkable_existing_count = sum(1 for obj in all_of_type if obj.id not in linked_ids)
        sections.append({
            "type_str": child_type,
            "children": children,
            "attr_name": attr_name,
            "linkable_existing_count": linkable_existing_count,
        })
    return sections
```

Note: `get_efootprint_objects_from_efootprint_type` is already available on `self.model_web`.
`obj.id` is used here (not `obj.efootprint_id`) because the objects returned by that method are raw
efootprint `ModelingObject` instances, not web wrappers. The `children` list contains web wrappers,
so use `child.efootprint_id` for those.

### 2. `model_builder/templates/model_builder/object_cards/journey_step_card.html`

Two paths need updating:

**Multi-child-type path** (already iterates `object.child_sections`) — add `linkable_existing_count`:

```html
{% include 'model_builder/components/add_child_button.html' with type_str=section.type_str parent_efootprint_id=object.efootprint_id linkable_existing_count=section.linkable_existing_count %}
```

**Single-child-type path** (currently uses `object.child_object_type_str` directly) — wrap with
`{% with %}` to get the section context:

```html
{% with section=object.child_sections.0 %}
    <div class="w-85 ms-15 px-0 py-1 d-flex justify-content-end position-relative">
        {% include 'model_builder/components/add_child_button.html' with type_str=section.type_str parent_efootprint_id=object.efootprint_id linkable_existing_count=section.linkable_existing_count %}
    </div>
{% endwith %}
```

### 3. `model_builder/templates/model_builder/object_cards/resource_need_with_accordion_card.html`

The include at line 48 already has `section` in scope — just add `linkable_existing_count`:

```html
{% include 'model_builder/components/add_child_button.html' with type_str=section.type_str parent_efootprint_id=object.efootprint_id linkable_existing_count=section.linkable_existing_count %}
```

### 4. `model_builder/templates/model_builder/components/add_child_button.html`

Add a conditional "Link existing" button. The container in the card template already has
`d-flex justify-content-end position-relative`. The "Add new" button loses `w-100` and becomes
`flex-grow-1` so both buttons can sit side by side.

```html
{% load static label_filters %}
<button
        class="btn btn-white text-end flex-grow-1 d-flex flex-row justify-content-end align-items-center rounded-start-2 rounded-end-0 border-2 border-end-0 position-relative"
        hx-get="/model_builder/open-create-object-panel/{{ type_str }}/"
        hx-target="#sidePanel"
        hx-trigger="click"
        hx-swap="innerHTML"
        hx-vals='{"efootprint_id_of_parent_to_link_to": "{{ parent_efootprint_id }}"}'
        hx-disabled-elt="button"
        _="on click removeAllOpenedObjectsHighlights()"
>
    <p class='h8 mb-0 text-break text-addition px-1'>
        {{ type_str|add_child_text }}
    </p>
</button>
{% if linkable_existing_count %}
<button
        class="btn btn-white text-end d-flex flex-row align-items-center rounded-start-2 rounded-end-0 border-2 border-end-0"
        hx-get="/model_builder/open-link-existing-panel/{{ parent_efootprint_id }}/{{ type_str }}/"
        hx-target="#sidePanel"
        hx-trigger="click"
        hx-swap="innerHTML"
        hx-disabled-elt="button"
        _="on click removeAllOpenedObjectsHighlights()"
>
    <p class='h8 mb-0 text-break text-secondary px-1'>
        {{ type_str|link_child_text }}
    </p>
</button>
{% endif %}
<span class="position-absolute top-50 start-100 translate-middle bg-transparent rounded-circle">
    <img src="{% static 'icons/circle_add_icon.svg' %}" width="14" height="14" class="cursor"
         hx-get="/model_builder/open-create-object-panel/{{ type_str }}/"
         hx-target="#sidePanel"
         hx-trigger="click"
         hx-swap="innerHTML"
         hx-vals='{"efootprint_id_of_parent_to_link_to": "{{ parent_efootprint_id }}"}'
         hx-disabled-elt="button"
         _="on click removeAllOpenedObjectsHighlights()"
    >
    <span class="visually-hidden">{{ type_str|add_child_text }}</span>
</span>
```

The `link_child_text` filter is defined in step 5 below.

### 5. `model_builder/templatetags/label_filters.py`

Add a `link_child_text` filter, consistent with the existing `add_child_text`:

```python
@register.filter
def link_child_text(class_name: str) -> str:
    """Generate 'Link existing {label}' text for a class name.

    Usage: {{ child_object_type_str|link_child_text }}
    """
    if class_name is None:
        return ""
    label = LabelResolver.get_class_label(class_name).lower()
    return f"Link existing {label}"
```

### 6. `model_builder/adapters/forms/form_field_generator.py`

Extract a standalone `generate_select_multiple_field` function from `generate_dynamic_form` and
call it in the existing list-attribute branch. This eliminates the duplication with the new view.

```python
def generate_select_multiple_field(
    attr_name: str, id_prefix: str, selected_objects: list, child_type_str: str, model_web: "ModelWeb"
) -> dict:
    """Build a select_multiple field dict for a list attribute.

    Args:
        attr_name: The list attribute name (e.g. 'jobs')
        id_prefix: The class name prefix used for web_id (e.g. 'UsageJourneyStep')
        selected_objects: Raw ModelingObject instances currently linked
        child_type_str: Class name of child objects (e.g. 'Job')
        model_web: ModelWeb instance for querying available objects
    """
    field_config = FieldUIConfigProvider.get_config(attr_name)
    unselected = [
        {"value": option.id, "label": option.name}
        for option in model_web.get_efootprint_objects_from_efootprint_type(child_type_str)
        if option not in selected_objects
    ]
    selected = [{"value": elt.id, "label": elt.name} for elt in selected_objects]
    return {
        "web_id": f"{id_prefix}_{attr_name}",
        "attr_name": attr_name,
        "label": field_config.get("label", attr_name),
        "tooltip": field_config.get("tooltip", False),
        "input_type": "select_multiple",
        "selected": selected,
        "unselected": unselected,
        "selected_json": json.dumps(selected),
        "unselected_json": json.dumps(unselected),
    }
```

Replace the inline block in `generate_dynamic_form` (lines 105–122) with a call to this function:

```python
if get_origin(annotation) and get_origin(annotation) in (list, List):
    list_attribute_object_type_str = get_args(annotation)[0].__name__
    selected_objects = default_values.get(attr_name, [])
    structure_field.update(
        generate_select_multiple_field(attr_name, id_prefix, selected_objects, list_attribute_object_type_str, model_web)
    )
```

Note: `structure_field` is already initialised with `web_id`, `attr_name`, `label`, `tooltip`
before this block — `generate_select_multiple_field` returns those same keys too, so the
`.update()` is a clean full replacement of those fields.

### 7. `model_builder/adapters/views/views_edition.py`

Add a new view `open_link_existing_panel`. It uses `generate_select_multiple_field` from
`form_field_generator.py` to build the field, then renders a focused panel. No new POST endpoint
is needed — the form submits to the existing `edit_object/<parent_id>/` endpoint.

```python
@render_exception_modal_if_error
@time_it
def open_link_existing_panel(request, parent_id, child_type_str):
    from typing import get_args
    from efootprint.utils.tools import get_init_signature_params
    from model_builder.adapters.ui_config.class_ui_config_provider import ClassUIConfigProvider
    from model_builder.adapters.forms.form_field_generator import generate_select_multiple_field

    model_web = ModelWeb(SessionSystemRepository(request.session))
    parent_obj = model_web.get_web_object_from_efootprint_id(parent_id)

    # Find the list attribute on the parent that holds objects of child_type_str
    init_sig = get_init_signature_params(parent_obj.efootprint_class)
    attr_name = next(
        attr for attr in parent_obj.list_attr_names
        if get_args(init_sig[attr].annotation)[0].__name__ == child_type_str
    )

    # currently_linked from the raw efootprint object (ModelingObject instances,
    # consistent with what get_efootprint_objects_from_efootprint_type returns)
    currently_linked = getattr(parent_obj._modeling_obj, attr_name, []) or []

    field = generate_select_multiple_field(
        attr_name, parent_obj.class_as_simple_str, currently_linked, child_type_str, model_web)

    context = {
        "header_name": f"Link existing {ClassUIConfigProvider.get_label(child_type_str).lower()} to {parent_obj.name}",
        "parent_id": parent_id,
        "field": field,
    }

    http_response = render(request, "model_builder/side_panels/link/link_existing_panel.html", context=context)
    http_response["HX-Trigger-After-Settle"] = "initDynamicForm"
    return http_response
```

### 7. New file: `model_builder/templates/model_builder/side_panels/link/link_existing_panel.html`

A focused panel showing only the `select_multiple` field. The form submits to the existing
`edit_object/<parent_id>/` endpoint. The HTMX response (OOB swap of parent card) and
`closeAndEmptySidePanel()` are identical to the edit flow.

```html
{% extends "model_builder/side_panels/side_panel_structure.html" %}

{% block panel_body %}
    <form id="sidePanelForm"
          hx-post="/model_builder/edit-object/{{ parent_id }}/"
          hx-swap="none"
          hx-disabled-elt="button"
          hx-on::after-request="closeAndEmptySidePanel()"
    >
        {% csrf_token %}
        {% include "model_builder/side_panels/dynamic_form_fields/select_multiple.html" %}
    </form>
{% endblock %}
```

The Save button is inherited from `side_panel_structure.html` — no override needed.

### 8. `model_builder/urls.py`

Add the new URL after the existing edit-object pattern:

```python
path("open-link-existing-panel/<parent_id>/<child_type_str>/",
     model_builder.adapters.views.views_edition.open_link_existing_panel,
     name="open-link-existing-panel"),
```

## Data flow summary

```
User clicks "Link existing job"
  → GET /model_builder/open-link-existing-panel/<journey_step_id>/Job/
  → open_link_existing_panel view
      - loads parent (UsageJourneyStep)
      - finds attr_name = "jobs"
      - builds select_multiple field: selected=[currently linked jobs], unselected=[others]
      - renders link_existing_panel.html
  → side panel shows select_multiple with existing jobs
  → user selects/deselects, clicks Save
  → POST /model_builder/edit-object/<journey_step_id>/
      - parse_form_data parses "UsageJourneyStep_jobs" hidden input (semicolon-separated IDs)
      - EditObjectUseCase updates parent with new jobs list
      - HtmxPresenter.present_edited_object → OOB swap of parent card
  → side panel closes, parent card re-renders with updated job list
```

## Verification

The core scenario is covered by `TestJobs.test_link_existing_job_to_step` in
`tests/e2e/objects/test_jobs.py`. The test:

1. Loads a system with one journey, two steps, and one job linked only to the first step.
2. Asserts the step already holding the job has **no** "link existing" button (`JobBase` child type).
3. Asserts the empty step **has** a "link existing" button.
4. Clicks the button → side panel opens with "Link existing" in the header.
5. Selects "Test Job" via `add_to_select_multiple` → submits → panel closes.
6. Asserts "Test Job" card is now visible inside the previously empty step.

Run with:
```bash
poetry run pytest tests/e2e/objects/test_jobs.py::TestJobs::test_link_existing_job_to_step --base-url http://localhost:8000
```

Additional manual checks:
- Confirm "Add job" button still opens the creation panel unchanged.
- Repeat for another child type (e.g. `UsageJourneyStep` in a `UsageJourney`) to confirm the generic mechanism works across object types.
