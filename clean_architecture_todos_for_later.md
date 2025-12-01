# Clean Architecture TODOs for Later

This file documents remaining work to complete the Clean Architecture refactoring.

## Current Status: All Tests Passing (71/71 Python + Cypress E2E)

### Phase 1: Repository Pattern ✅ COMPLETE
- `ISystemRepository` interface created
- `SessionSystemRepository` implementation
- `ModelWeb` accepts repository instead of session directly

### Phase 2: Use Cases ✅ MOSTLY COMPLETE (functional, minor cleanup remaining)

**Completed:**
- `CreateObjectUseCase` - Working with hooks pattern
- `EditObjectUseCase` - Working
- `DeleteObjectUseCase` - Working
- `HtmxPresenter` - Formats use case outputs as HTTP responses
- Hooks pattern implemented for class-specific logic:
  - **Creation**: `pre_create`, `prepare_creation_input`, `pre_add_to_system`, `handle_creation_error`, `post_create`
  - **Deletion**: `pre_delete`
  - **Edition**: `pre_edit`
- `skip_parent_linking` class attribute for objects that link via field instead of list

**Classes using hooks:**
- `EdgeDeviceWeb` - `prepare_creation_input` (empty components)
- `ServerWeb` - `pre_create`, `pre_edit` (storage handling)
- `EdgeComputerWeb` - `pre_create`, `pre_edit` (storage handling)
- `UsagePatternWebBaseClass` - `pre_add_to_system`, `pre_delete` (system list management)
- `RecurrentEdgeDeviceNeedWeb` - `prepare_creation_input`
- `ExternalApiWeb` - `pre_create`, `handle_creation_error`, `post_create` (complex multi-object creation)
- `ServiceWeb` - `prepare_creation_input`, `skip_parent_linking`

**Remaining cleanup (non-blocking):**
1. Use cases still import Django's `render_to_string` for HTML generation (e.g., `_link_to_parent`)
2. Could move HTML generation entirely to presenter layer for purer separation
3. QueryDict still passed to use cases (works but not ideal)

---

## Phase 3: Extract Domain Services (NEXT)

**Goal:** Extract domain logic from `ModelWeb` and utility functions into focused domain services that don't depend on Django.

### Candidate Services to Extract

#### 1. ObjectLinkingService
Handles parent-child linking logic currently in `CreateObjectUseCase._link_to_parent`:
- Find correct list attribute for linking
- Build edit data for parent
- Could be reused by other use cases

```python
# domain/services/object_linking_service.py
class ObjectLinkingService:
    def link_child_to_parent(self, child_obj, parent_obj) -> str:
        """Links child to parent, returns the attribute name used."""
        ...

    def find_list_attribute_for_type(self, parent_class, child_type) -> str:
        """Finds which list attribute accepts the given child type."""
        ...
```

#### 2. ObjectCreationService
Consolidates object creation logic from `create_efootprint_obj_from_post_data`:
- Form data to kwargs conversion
- Type annotation handling
- Default value handling

```python
# domain/services/object_creation_service.py
class ObjectCreationService:
    def create_from_form_data(self, form_data: dict, object_type: str, model_web) -> ModelingObject:
        """Creates efootprint object from form data."""
        ...
```

#### 3. SystemValidationService
Extract validation from `ModelWeb.raise_incomplete_modeling_errors`:
- Check for required objects
- Validate relationships
- Return structured validation results

```python
# domain/services/system_validation_service.py
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]

class SystemValidationService:
    def validate(self, system) -> ValidationResult:
        ...
```

#### 4. EmissionsCalculationService
Extract emissions aggregation from `ModelWeb.system_emissions`:
- Daily emissions timeseries
- Energy vs fabrication breakdown
- Could support different calculation strategies

```python
# domain/services/emissions_service.py
class EmissionsCalculationService:
    def calculate_daily_emissions(self, system) -> EmissionsTimeseries:
        ...
```

### Benefits of Phase 3
1. **Testability**: Services can be unit tested without Django
2. **Reusability**: Logic can be used in different contexts (CLI, API, batch processing)
3. **Clarity**: Clear separation between orchestration (use cases) and domain logic (services)
4. **Reduced coupling**: Services don't know about HTTP, sessions, or templates

### Implementation Order
1. Start with `ObjectLinkingService` - currently mixed into use case
2. Then `ObjectCreationService` - currently in `object_creation_and_edition_utils.py`
3. Then `SystemValidationService` - simpler, fewer dependencies
4. Finally `EmissionsCalculationService` - may need careful handling of efootprint types

---

## Phase 2 Remaining Cleanup (can be done after Phase 3)

### HTML Generation in Use Cases
The `_link_to_parent` method imports `django.template.loader.render_to_string`:

```python
# Current (in CreateObjectUseCase._link_to_parent)
from django.template.loader import render_to_string
html_updates += f"<div hx-swap-oob='outerHTML:#{mirrored_card.web_id}'>"
html_updates += render_to_string(f'model_builder/object_cards/{mirrored_card.template_name}_card.html', ...)
```

**Options:**
1. **Accept it**: HTMX architecture blurs presentation/business boundaries
2. **Return data, not HTML**: Use case returns list of objects to re-render, presenter generates HTML
3. **Inject renderer**: Pass a renderer interface to use case

### QueryDict in Use Cases
Use cases accept `Dict[str, Any]` but views pass `request.POST` (QueryDict) directly:

```python
# Current
input_data = CreateObjectInput(
    object_type=object_type,
    form_data=request.POST,  # QueryDict passed directly
    ...
)
```

**Ideal:**
```python
# Views should map to plain dict
input_data = CreateObjectInput(
    object_type=object_type,
    form_data=RequestMapper.to_dict(request.POST),
    ...
)
```

---

## Remaining Web Classes with Override Methods

These have custom methods that could potentially use hooks instead:

### Delete Logic
- `ServerWeb.self_delete` - Deletes services before server (may need `pre_delete` hook or is fine as-is)

### Ask Delete Modal
- `ServerWeb.generate_ask_delete_http_response` - Custom modal when server has jobs

---

## Future Considerations

### Phase 4: Split ModelingObjectWeb
After domain services are extracted, `ModelingObjectWeb` can be simplified:
- Keep only wrapper/delegation logic
- Move presentation to presenters
- Move form generation to form services

### Phase 5: Clean Up Views
Make views true thin adapters:
- Map request to input
- Call use case
- Call presenter
- Return response

Currently views are mostly there, but some still have logic in them.