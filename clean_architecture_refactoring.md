# Clean Architecture Refactoring Guide

## Table of Contents
1. [Understanding Clean Architecture](#understanding-clean-architecture)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Identified Violations](#identified-violations)
4. [Refactoring Roadmap](#refactoring-roadmap)
5. [Detailed Action Items](#detailed-action-items)

---

## Understanding Clean Architecture

### Core Principles

Clean Architecture (by Robert C. Martin) organizes code into concentric circles with a strict **Dependency Rule**: dependencies can only point **inward**.

```
        ┌─────────────────────────────────────────┐
        │           Adapters (Outer Layer)         │
        │  ┌─────────────────────────────────────┐ │
        │  │       Application (Use Cases)       │ │
        │  │  ┌────────────────────────────────┐ │ │
        │  │  │        Domain (Core)           │ │ │
        │  │  │  - Entities                    │ │ │
        │  │  │  - Business Rules              │ │ │
        │  │  │  - Interfaces (Ports)          │ │ │
        │  │  └────────────────────────────────┘ │ │
        │  │    Application Services             │ │
        │  │    Use Case Orchestration           │ │
        │  └─────────────────────────────────────┘ │
        │  Views, Controllers, Repositories        │
        │  Presenters, UI, External Services       │
        └─────────────────────────────────────────┘
```

### The Dependency Rule

| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| Domain (innermost) | Only itself and standard library | Application, Adapters, Frameworks |
| Application | Domain, standard library | Adapters, Frameworks |
| Adapters (outermost) | Domain, Application | - |

### Key Concepts

**1. Entities (Domain Layer)**
- Pure business logic and data structures
- No framework dependencies (no Django, no HTTP concepts)
- Should be testable without any external systems

**2. Use Cases (Application Layer)**
- Orchestrate the flow of data to and from entities
- Define application-specific business rules
- Depend on domain, but not on how data gets delivered (HTTP, CLI, etc.)

**3. Interface Adapters (Adapters Layer)**
- Convert data from use cases to external format (HTTP, JSON, HTML)
- Include: Views, Presenters, Repositories, Controllers
- Implement interfaces defined in the domain layer

**4. Dependency Inversion**
- Domain defines interfaces (what it needs)
- Adapters implement those interfaces (how it's done)
- Example: `ISystemRepository` (domain) vs `SessionSystemRepository` (adapter)

---

## Current Architecture Analysis

### Directory Structure

```
model_builder/
├── domain/                          # Business logic layer
│   ├── interfaces/                  # Repository contracts ✓ GOOD
│   │   └── system_repository.py     # ISystemRepository
│   ├── services/                    # Domain services ✓ GOOD
│   │   ├── object_linking_service.py
│   │   ├── system_validation_service.py
│   │   └── emissions_calculation_service.py
│   ├── entities/                    # Web wrappers ⚠️ MIXED
│   │   ├── web_core/               # Core entities
│   │   ├── web_builders/           # Builder entities
│   │   ├── web_abstract_modeling_classes/
│   │   └── efootprint_extensions/  # ExplainableObject extensions
│   ├── object_factory.py            # ⚠️ HAS VIOLATIONS
│   ├── all_efootprint_classes.py
│   └── efootprint_to_web_mapping.py
│
├── application/                     # Use case layer ✓ MOSTLY GOOD
│   └── use_cases/
│       ├── create_object.py        # CreateObjectUseCase
│       ├── edit_object.py          # ⚠️ HAS VIOLATION
│       └── delete_object.py        # DeleteObjectUseCase
│
├── adapters/                        # Interface adapters ✓ GOOD
│   ├── views/                      # HTTP controllers
│   │   ├── views.py
│   │   ├── views_addition.py
│   │   ├── views_edition.py
│   │   ├── views_deletion.py
│   │   └── edit_object_http_response_generator.py  # ⚠️ MIXED CONCERNS
│   ├── presenters/
│   │   └── htmx_presenter.py       # Response formatting ✓ GOOD
│   ├── repositories/
│   │   ├── session_system_repository.py  # ✓ GOOD
│   │   └── in_memory_system_repository.py
│   └── forms/
│       └── class_structure.py      # Form generation (misplaced)
```

### What's Working Well

1. **Repository Pattern**: The `ISystemRepository` interface in domain with `SessionSystemRepository` and `InMemorySystemRepository` implementations is textbook Clean Architecture.

2. **Use Case Pattern**: `CreateObjectUseCase`, `EditObjectUseCase`, and `DeleteObjectUseCase` have clean Input/Output dataclasses and orchestrate business logic well.

3. **Presenter Pattern**: `HtmxPresenter` cleanly separates HTTP response formatting from business logic.

4. **Domain Services**: `ObjectLinkingService`, `SystemValidationService`, and `EmissionsCalculationService` encapsulate pure business logic.

---

## Identified Violations

### Critical Issue 1: Domain Imports from Adapters

**Violation**: The domain layer imports from the adapters layer, creating a circular dependency.

**Affected Files**:

| Domain File | Imports From Adapters |
|-------------|----------------------|
| `domain/object_factory.py:18` | `adapters.forms.class_structure.get_corresponding_web_class` |
| `domain/entities/web_abstract_modeling_classes/modeling_object_web.py:12` | `adapters.forms.class_structure.generate_dynamic_form`, `generate_object_creation_context` |
| `domain/entities/web_builders/services/external_api_web.py:14` | `adapters.forms.class_structure.generate_object_creation_structure` |
| `domain/entities/web_builders/services/service_web.py` | `adapters.forms.class_structure.*` |
| `domain/entities/web_core/hardware/hardware_utils.py:6` | `adapters.forms.class_structure.generate_object_creation_structure` |
| `domain/entities/web_core/hardware/edge/edge_component_base_web.py` | `adapters.forms.class_structure.*` |
| `domain/entities/web_core/usage/job_web.py` | `adapters.forms.class_structure.*` |

**Impact**:
- Breaks the Dependency Rule
- Creates tight coupling between layers
- Makes domain entities untestable without adapters
- Prevents reuse of domain logic in non-web contexts

### Critical Issue 2: Domain Imports Django

**Violation**: Domain layer directly imports Django framework.

**Affected Files**:

| Domain File | Django Import |
|-------------|--------------|
| `domain/object_factory.py:6` | `from django.http import QueryDict` |
| `domain/entities/web_core/hardware/hardware_utils.py:4` | `from django.shortcuts import render` |
| `domain/entities/web_builders/services/external_api_web.py:4` | `from django.http import QueryDict` |
| `domain/entities/web_builders/services/service_web.py:4` | `from django.http import QueryDict` |
| `domain/entities/web_builders/hardware/edge/edge_computer_web.py:4` | `from django.http import QueryDict` |
| `domain/entities/web_core/hardware/server_web.py:4` | `from django.http import QueryDict` |

**Impact**:
- Domain entities are tied to Django's HTTP layer
- Cannot test domain logic without Django installed
- Cannot reuse domain in Flask, FastAPI, CLI, or other contexts

### Issue 3: Use Case Imports from Adapters

**Violation**: Application layer imports presentation logic from adapters.

**Location**: `application/use_cases/edit_object.py:56`
```python
from model_builder.adapters.views.edit_object_http_response_generator import compute_edit_object_html_and_event_response
```

**Impact**:
- Use case becomes tied to HTMX/HTML presentation
- Cannot be reused for API responses or other formats

### Issue 4: Mixed Concerns in Adapter

**Location**: `adapters/views/edit_object_http_response_generator.py`

This file mixes:
- Domain logic (editing objects via `edit_object_in_system`)
- Cascade deletion logic (business rule)
- HTML generation (presentation)

**Code excerpt showing mixed concerns**:
```python
def compute_edit_object_html_and_event_response(edit_form_data, obj_to_edit):
    # Business logic mixed with presentation
    edited_obj = edit_object_in_system(edit_form_data, obj_to_edit)  # Domain operation

    # More business logic (cascade deletion)
    for removed_accordion_child in removed_accordion_children:
        if len(removed_accordion_child.modeling_obj_containers) == 0:
            removed_accordion_child.self_delete()  # Domain operation

    # Presentation logic
    for mirrored_card in mirrored_cards:
        response_html += f"<div hx-swap-oob='outerHTML:..."  # Adapter concern
```

### Issue 5: Web-Specific Methods in Domain Entities

Domain entities contain web/presentation-specific methods:

**`ModelingObjectWeb` class** (`domain/entities/web_abstract_modeling_classes/modeling_object_web.py`):
```python
class ModelingObjectWeb:
    add_template = "add_panel__generic.html"      # Template paths in domain!
    edit_template = "edit_panel__generic.html"

    @classmethod
    def get_htmx_form_config(cls, context_data: dict) -> dict:
        """Returns HTMX configuration..."""        # HTMX in domain!

    def generate_object_edition_context(self):
        """Generates form context..."""            # Form generation in domain!
```

---

## Refactoring Roadmap

### Phase 1: Remove Django from Domain (High Impact, Low Effort)

**Goal**: Domain layer should have zero Django imports.

**Changes**:
1. Replace `QueryDict` with `Dict[str, Any]`
2. Convert `QueryDict` to `dict` at the adapter boundary
3. Remove `django.shortcuts.render` from domain

**Estimated Effort**: 2-4 hours

### Phase 2: Break Domain → Adapters Dependencies (High Impact, Medium Effort)

**Goal**: Domain layer should not import from adapters.

**Strategy**: Use Dependency Inversion - define interfaces in domain, implement in adapters.

**Changes**:
1. Create `IFormGenerator` interface in domain
2. Move form generation implementation to adapters
3. Inject form generator via constructor or method parameters
4. Update all affected domain files

**Estimated Effort**: 1-2 days

### Phase 3: Move HTML Generation to Presenter (Medium Impact, Medium Effort)

**Goal**: Use cases return pure data; presenters generate HTML.

**Changes**:
1. Remove HTML generation from `EditObjectUseCase`
2. Update `EditObjectOutput` to contain data, not HTML
3. Move HTML generation logic to `HtmxPresenter`
4. Update `compute_edit_object_html_and_event_response` to split concerns

**Estimated Effort**: 1 day

### Phase 4: Extract Business Logic from Adapters (Low-Medium Impact)

**Goal**: No business logic in adapter layer.

**Changes**:
1. Move cascade deletion logic from `edit_object_http_response_generator.py` to domain
2. Create `EditService` in domain services if needed
3. Ensure adapters only do data transformation

**Estimated Effort**: 0.5-1 day

---

## Detailed Action Items

### Action 1: Remove Django QueryDict from Domain

**Files to modify**:

1. **`domain/object_factory.py`**
```python
# BEFORE (line 6)
from django.http import QueryDict

def create_efootprint_obj_from_post_data(
    create_form_data: QueryDict, model_web: "ModelWeb", object_type: str):

# AFTER
from typing import Dict, Any

def create_efootprint_obj_from_post_data(
    create_form_data: Dict[str, Any], model_web: "ModelWeb", object_type: str):
```

2. **Adapter conversion** (in views):
```python
# In adapters/views/views_addition.py
from django.http import QueryDict

def add_object(request, object_type):
    # Convert QueryDict to plain dict at boundary
    form_data = dict(request.POST)
    # For single values, unwrap the lists
    form_data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}

    input_data = CreateObjectInput(
        object_type=object_type,
        form_data=form_data,  # Now a plain dict
        ...
    )
```

### Action 2: Create Form Generator Interface

**New file**: `domain/interfaces/form_generator.py`
```python
"""Interface for form generation.

This interface allows domain entities to request form generation
without depending on the specific implementation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from model_builder.domain.entities.web_core.model_web import ModelWeb


class IFormGenerator(ABC):
    """Interface for generating dynamic forms from modeling objects."""

    @abstractmethod
    def generate_dynamic_form(
        self,
        efootprint_class_str: str,
        default_values: dict,
        model_web: "ModelWeb"
    ) -> tuple:
        """Generate form fields for an efootprint class.

        Returns:
            Tuple of (form_fields, form_fields_advanced, dynamic_lists)
        """
        pass

    @abstractmethod
    def generate_object_creation_context(
        self,
        efootprint_class_str: str,
        available_efootprint_classes: list,
        model_web: "ModelWeb"
    ) -> dict:
        """Generate context for object creation forms.

        Returns:
            Dictionary with form_sections, header_name, etc.
        """
        pass

    @abstractmethod
    def get_corresponding_web_class(self, efootprint_class):
        """Get the web wrapper class for an efootprint class."""
        pass
```

**Modify**: `adapters/forms/class_structure.py` to implement this interface:
```python
from model_builder.domain.interfaces.form_generator import IFormGenerator

class DjangoFormGenerator(IFormGenerator):
    """Django-specific implementation of form generation."""

    def generate_dynamic_form(self, efootprint_class_str, default_values, model_web):
        # Existing implementation
        ...
```

### Action 3: Inject Form Generator into Domain Entities

**Option A: Constructor Injection**
```python
# domain/entities/web_abstract_modeling_classes/modeling_object_web.py
class ModelingObjectWeb:
    def __init__(
        self,
        modeling_obj: ModelingObject,
        model_web: "ModelWeb",
        list_container=None,
        form_generator: IFormGenerator = None
    ):
        self._modeling_obj = modeling_obj
        self.model_web = model_web
        self.list_container = list_container
        self._form_generator = form_generator

    def generate_object_edition_context(self):
        if self._form_generator is None:
            raise ValueError("Form generator not provided")
        form_fields, form_fields_advanced, dynamic_lists = (
            self._form_generator.generate_dynamic_form(
                self.class_as_simple_str, self.modeling_obj.__dict__, self.model_web
            )
        )
        ...
```

**Option B: Service Locator / Registry (simpler migration)**
```python
# domain/interfaces/__init__.py
from model_builder.domain.interfaces.system_repository import ISystemRepository
from model_builder.domain.interfaces.form_generator import IFormGenerator

# Registry that adapters can populate
_form_generator = None

def set_form_generator(generator: IFormGenerator):
    global _form_generator
    _form_generator = generator

def get_form_generator() -> IFormGenerator:
    if _form_generator is None:
        raise RuntimeError("Form generator not configured")
    return _form_generator
```

### Action 4: Move HTML Generation from Use Case to Presenter

**Modify** `application/use_cases/edit_object.py`:
```python
# BEFORE
def execute(self, input_data: EditObjectInput) -> EditObjectOutput:
    ...
    # Compute edit HTML (this also performs the edit via edit_object_in_system)
    html_updates = compute_edit_object_html_and_event_response(input_data.form_data, obj_to_edit)

    return EditObjectOutput(
        ...,
        html_updates=html_updates,  # HTML in use case output!
    )

# AFTER
def execute(self, input_data: EditObjectInput) -> EditObjectOutput:
    ...
    # Perform the edit - NO HTML GENERATION
    edited_obj = edit_object_in_system(input_data.form_data, obj_to_edit)

    return EditObjectOutput(
        edited_object_id=obj_to_edit.efootprint_id,
        edited_object_name=obj_to_edit.name,
        edited_object_type=obj_to_edit.class_as_simple_str,
        template_name=obj_to_edit.template_name,
        web_id=obj_to_edit.web_id,
        mirrored_web_ids=[card.web_id for card in obj_to_edit.mirrored_cards],
        # NO html_updates field
    )
```

**Modify** `adapters/presenters/htmx_presenter.py`:
```python
def present_edited_object(
    self, output: EditObjectOutput, recompute: bool = False, trigger_result_display: bool = False
) -> HttpResponse:
    # Generate HTML here, in the presenter
    edited_obj = self.model_web.get_web_object_from_efootprint_id(output.edited_object_id)

    html_updates = ""
    for mirrored_card in edited_obj.mirrored_cards:
        html_updates += (
            f"<div hx-swap-oob='outerHTML:#{mirrored_card.web_id}'>"
            f"{render_to_string(f'model_builder/object_cards/{mirrored_card.template_name}_card.html',
                               {'object': mirrored_card})}"
            f"</div>"
        )

    # Rest of presentation logic...
```

### Action 5: Extract Cascade Deletion to Domain

**Create**: `domain/services/edit_service.py`
```python
"""Service for editing modeling objects with cascade behavior."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model_builder.domain.efootprint_to_web_mapping import ModelingObjectWeb

class EditService:
    """Service that handles object editing with cascade cleanup."""

    def edit_with_cascade_cleanup(
        self,
        obj_to_edit: "ModelingObjectWeb",
        form_data: dict
    ) -> tuple:
        """Edit an object and clean up orphaned accordion children.

        Returns:
            Tuple of (edited_obj, deleted_children_ids)
        """
        from model_builder.domain.object_factory import edit_object_in_system
        from copy import copy

        # Capture state before edit
        accordion_children_before = {}
        for mirrored_card in obj_to_edit.mirrored_cards:
            accordion_children_before[mirrored_card] = copy(mirrored_card.accordion_children)

        # Perform edit
        edited_obj = edit_object_in_system(form_data, obj_to_edit)

        # Find orphaned children
        accordion_children_after = {}
        for mirrored_card in edited_obj.mirrored_cards:
            accordion_children_after[mirrored_card] = copy(mirrored_card.accordion_children)

        first_mirrored_card = next(iter(accordion_children_after.keys()))
        removed_children = [
            child for child in accordion_children_before[first_mirrored_card]
            if child not in accordion_children_after[first_mirrored_card]
        ]

        # Clean up orphans
        deleted_ids = []
        for child in removed_children:
            if len(child.modeling_obj_containers) == 0:
                deleted_ids.append(child.efootprint_id)
                child.self_delete()

        if deleted_ids:
            obj_to_edit.model_web.update_system_data_with_up_to_date_calculated_attributes()

        return edited_obj, deleted_ids
```

---

## Verification Checklist

After refactoring, verify:

### Domain Layer Tests
- [ ] All domain files import only from domain and standard library
- [ ] No Django imports in domain layer
- [ ] Domain tests run without Django installed (use mocks)

### Application Layer Tests
- [ ] Use cases import only from domain and interfaces
- [ ] Use case outputs contain only data, no HTML
- [ ] Use cases are testable with mock repositories

### Adapter Layer Tests
- [ ] All HTML generation happens in presenters
- [ ] Views are thin (< 30 lines typically)
- [ ] Form generation implements IFormGenerator interface

### Integration Tests
- [ ] Request flow works end-to-end
- [ ] HTMX partial updates still work
- [ ] Object creation/edit/delete work correctly

---

## Quick Reference: Import Rules

```python
# domain/ files can import:
from model_builder.domain.interfaces import ISystemRepository  # ✓ OK
from model_builder.domain.entities.web_core.model_web import ModelWeb  # ✓ OK
from model_builder.domain.services import ObjectLinkingService  # ✓ OK
from efootprint.abstract_modeling_classes import ModelingObject  # ✓ OK (external domain)
import json, os, typing  # ✓ OK (standard library)

# domain/ files CANNOT import:
from django.http import QueryDict  # ✗ VIOLATION
from model_builder.adapters.forms import class_structure  # ✗ VIOLATION
from model_builder.adapters.views import anything  # ✗ VIOLATION

# application/ files can import:
from model_builder.domain import anything  # ✓ OK
from model_builder.domain.interfaces import ISystemRepository  # ✓ OK

# application/ files CANNOT import:
from model_builder.adapters import anything  # ✗ VIOLATION
from django import anything  # ✗ VIOLATION

# adapters/ files can import:
from model_builder.domain import anything  # ✓ OK
from model_builder.application import anything  # ✓ OK
from django import anything  # ✓ OK
```

---

## Summary

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| 1. Remove Django from domain | High | Low | **Immediate** |
| 2. Break domain → adapters deps | High | Medium | **High** |
| 3. Move HTML to presenter | Medium | Medium | Medium |
| 4. Extract business logic from adapters | Low-Medium | Low | Low |

Start with Phase 1 - it's low effort and immediately makes the domain more testable and reusable.
