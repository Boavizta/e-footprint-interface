# Clean Architecture TODOs for Later

This file documents remaining work to complete the Clean Architecture refactoring.

## Current Status: All Tests Passing (71/71 Python + Cypress E2E)

### Phase 1: Repository Pattern ✅ COMPLETE
- `ISystemRepository` interface created
- `SessionSystemRepository` implementation
- `ModelWeb` accepts repository instead of session directly

### Phase 2: Use Cases ✅ COMPLETE

**Completed:**
- `CreateObjectUseCase` - Working with hooks pattern, no Django imports
- `EditObjectUseCase` - Working
- `DeleteObjectUseCase` - Working
- `HtmxPresenter` - Formats use case outputs as HTTP responses
- Hooks pattern implemented for class-specific logic:
  - **Creation**: `pre_create`, `prepare_creation_input`, `pre_add_to_system`, `handle_creation_error`, `post_create`
  - **Deletion**: `pre_delete`
  - **Edition**: `pre_edit`
- `skip_parent_linking` class attribute for objects that link via field instead of list
- HTML generation moved from use cases to presenter (Phase 2 cleanup done)

**Classes using hooks:**
- `EdgeDeviceWeb` - `prepare_creation_input` (empty components)
- `ServerWeb` - `pre_create`, `pre_edit` (storage handling)
- `EdgeComputerWeb` - `pre_create`, `pre_edit` (storage handling)
- `UsagePatternWebBaseClass` - `pre_add_to_system`, `pre_delete` (system list management)
- `RecurrentEdgeDeviceNeedWeb` - `prepare_creation_input`
- `ExternalApiWeb` - `pre_create`, `handle_creation_error`, `post_create` (complex multi-object creation)
- `ServiceWeb` - `prepare_creation_input`, `skip_parent_linking`

**Remaining (low priority):**
- QueryDict still passed to use cases (works, but not ideal - see Phase 6)

---

## Phase 3: Extract Domain Services ✅ COMPLETE

**Goal:** Extract domain logic from `ModelWeb` and utility functions into focused domain services that don't depend on Django.

### Implemented Services

#### 1. ObjectLinkingService ✅
Location: `model_builder/domain/services/object_linking_service.py`
- `find_list_attribute_for_child()` - Finds which list attribute on parent accepts child type
- `build_link_edit_data()` - Builds edit data dict with semicolon-separated IDs
- `link_child_to_parent()` - Orchestrates above, returns `LinkResult` dataclass
- Used by `CreateObjectUseCase._link_to_parent()`

#### 2. SystemValidationService ✅
Location: `model_builder/domain/services/system_validation_service.py`
- `validate_for_computation()` - Returns `ValidationResult` with errors
- `ValidationResult.raise_if_invalid()` - Raises ValueError if invalid
- Checks: usage patterns exist, usage journeys have steps
- Used by `ModelWeb.raise_incomplete_modeling_errors()`

#### 3. EmissionsCalculationService ✅
Location: `model_builder/domain/services/emissions_calculation_service.py`
- `calculate_daily_emissions()` - Returns `EmissionsResult` with dates and values
- `SystemWithFootprints` Protocol for flexible typing (works with mocks)
- Aggregates energy and fabrication footprints by category
- Used by `ModelWeb.system_emissions`

### NOT Extracted (deferred)

#### ObjectCreationService
`create_efootprint_obj_from_post_data` in `object_creation_and_edition_utils.py` is complex:
- Tightly coupled to form data parsing
- Uses `model_web` for object lookups
- Would require significant refactoring
- Current implementation works well, defer to later phase

---

### Original Candidate Services (for reference)

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

## Remaining Web Classes with Override Methods

These have custom methods that could potentially use hooks instead:

### Delete Logic
- `ServerWeb.self_delete` - Deletes services before server (may need `pre_delete` hook or is fine as-is)

### Ask Delete Modal
- `ServerWeb.generate_ask_delete_http_response` - Custom modal when server has jobs

---

## Future Considerations

### Phase 4: Split ModelingObjectWeb ✅ PARTIAL (cleanup done)
Removed deprecated HTTP methods from `ModelingObjectWeb`:
- `add_new_object_and_return_html_response` (→ CreateObjectUseCase)
- `generate_delete_http_response` (→ DeleteObjectUseCase)
- `generate_ask_delete_http_response` (→ HtmxPresenter)

**Result:** ModelingObjectWeb reduced from 486 to 373 lines (-23%)

**Remaining (optional):**
- `generate_object_creation_context` could move to a FormService
- `generate_object_edition_context` could move to a FormService
- `edit_object_and_return_html_response` could be removed (only delegates)

### Phase 5: Clean Up Views
Make views true thin adapters:
- Map request to input
- Call use case
- Call presenter
- Return response

Currently views are mostly there, but some still have logic in them.

### Phase 6: Extract Form Handling Services
Extract form parsing logic from `object_creation_and_edition_utils.py`:

**Current state:**
- `create_efootprint_obj_from_post_data()` mixes form parsing with object creation
- `edit_object_in_system()` has similar mixed concerns
- Both accept QueryDict but work with plain dict too

**Target architecture:**
```python
# adapters/mappers/form_data_mapper.py
class FormDataMapper:
    """Maps raw form data to typed creation/edit inputs."""
    def map_creation_data(self, form_data: dict, object_type: str) -> ObjectCreationInput:
        """Converts form data to typed input for object creation."""
        ...

    def map_edit_data(self, form_data: dict, obj_to_edit) -> ObjectEditInput:
        """Converts form data to typed input for object editing."""
        ...

# domain/services/object_factory.py
class ObjectFactory:
    """Creates efootprint objects from typed inputs."""
    def create_object(self, input: ObjectCreationInput, model_web) -> ModelingObject:
        """Creates efootprint object from typed input."""
        ...
```

**Benefits:**
1. Clear separation: form parsing (adapter) vs object creation (domain)
2. Typed inputs make use cases more testable
3. Form parsing can be unit tested independently
4. Easier to add new input sources (API, CLI, etc.)