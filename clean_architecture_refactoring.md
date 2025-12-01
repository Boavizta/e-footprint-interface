# Clean Architecture Refactoring Guide for e-footprint-interface

This document provides a comprehensive analysis of the current architecture against Clean Architecture principles, explains the concepts with concrete examples from this codebase, and proposes a prioritized refactoring path.

---

## Table of Contents

1. [Clean Architecture Fundamentals](#clean-architecture-fundamentals)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Violations and Their Impact](#violations-and-their-impact)
4. [Proposed Target Architecture](#proposed-target-architecture)
5. [Refactoring Path](#refactoring-path)
6. [Implementation Examples](#implementation-examples)

---

## Clean Architecture Fundamentals

### The Core Principles

Clean Architecture, introduced by Robert C. Martin (Uncle Bob), organizes code into concentric layers where **dependencies point inward**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRAMEWORKS & DRIVERS                         │
│  (Django, HTMX, Templates, Session Storage, External APIs)     │
├─────────────────────────────────────────────────────────────────┤
│                    INTERFACE ADAPTERS                           │
│  (Controllers/Views, Presenters, Gateways, Repositories)       │
├─────────────────────────────────────────────────────────────────┤
│                    APPLICATION BUSINESS RULES                   │
│  (Use Cases / Interactors)                                      │
├─────────────────────────────────────────────────────────────────┤
│                    ENTERPRISE BUSINESS RULES                    │
│  (Entities / Domain Objects - efootprint)                      │
└─────────────────────────────────────────────────────────────────┘
```

**The Dependency Rule**: Source code dependencies can only point inward. Nothing in an inner circle can know anything about something in an outer circle.

### The Layers Explained

#### 1. **Enterprise Business Rules (Entities/Domain)**
- Core business logic that would exist even without any application
- In this project: **The `efootprint` package** - carbon modeling, energy calculations, `System`, `Server`, `UsagePattern`, etc.
- These know nothing about Django, HTTP, sessions, or forms

#### 2. **Application Business Rules (Use Cases)**
- Application-specific business logic
- Orchestrates data flow to and from entities
- Examples: "Create a new server", "Calculate system emissions", "Edit a usage pattern"
- **Currently missing** in this codebase - this logic is scattered

#### 3. **Interface Adapters**
- Convert data between the format most convenient for use cases/entities and the format most convenient for frameworks
- Controllers (receive requests), Presenters (format responses), Gateways (data access)
- In Django: Views should be thin adapters, not contain business logic

#### 4. **Frameworks & Drivers**
- Django framework, HTMX, templates, session storage
- The outermost, most volatile layer
- Should be easily replaceable without affecting business logic

### Key Principles We Should Apply

| Principle | Description | Our Goal |
|-----------|-------------|----------|
| **Single Responsibility (SRP)** | A class should have only one reason to change | Split `ModelingObjectWeb` (486 lines, 9+ responsibilities) |
| **Open/Closed (OCP)** | Open for extension, closed for modification | Add new object types without modifying existing code |
| **Liskov Substitution (LSP)** | Subtypes must be substitutable for their base types | Web wrappers should be interchangeable |
| **Interface Segregation (ISP)** | Many client-specific interfaces are better than one general-purpose interface | Don't force clients to depend on unused methods |
| **Dependency Inversion (DIP)** | Depend on abstractions, not concretions | Use interfaces for repositories, not concrete Django sessions |

---

## Current Architecture Analysis

### Overview of Current Structure

```
e-footprint-interface/
├── e_footprint_interface/     # Django project config
├── model_builder/             # Main application code (PROBLEMATIC)
│   ├── web_core/              # ModelWeb, utilities
│   ├── web_abstract_modeling_classes/  # Web wrappers
│   ├── web_builders/          # Specialized builders
│   ├── addition/              # Object creation views
│   ├── edition/               # Object editing views
│   ├── efootprint_extensions/ # Timeseries extensions
│   └── templates/             # Django templates
├── theme/                     # Static assets
└── tests/                     # Python tests
```

### Current Layer Mixing (The Problem)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CURRENT STATE                               │
├─────────────────────────────────────────────────────────────────────┤
│  Views (views.py, views_*.py)                                       │
│    ↓ calls directly                                                 │
│  Web Wrappers (ModelingObjectWeb, ModelWeb)                         │
│    • Contains HTTP handling (QueryDict, HttpResponse)               │
│    • Contains presentation logic (template selection)               │
│    • Contains form generation                                       │
│    • Contains session management                                    │
│    • Contains deletion logic                                        │
│    ↓ calls directly                                                 │
│  efootprint Domain (external package)                               │
│    ↓ persists via                                                   │
│  Django Sessions (direct access throughout)                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Detailed Code Analysis

#### 1. ModelWeb (`model_builder/web_core/model_web.py`) - 327 lines

**Current Responsibilities (8+):**
```python
class ModelWeb:
    def __init__(self, session: SessionBase):  # 1. Session access
        self.session = session
        self.system_data = session["system_data"]  # 2. Data deserialization
        # 3. Version upgrade handling
        self.response_objs, self.flat_efootprint_objs_dict = json_to_system(...)  # 4. Domain instantiation
        self.system = wrap_efootprint_object(...)  # 5. Object wrapping

    def to_json(self, save_calculated_attributes=True):  # 6. Serialization
        ...

    def update_system_data_with_up_to_date_calculated_attributes(self):  # 7. Persistence
        self.session.modified = True
        self.session["system_data"] = self.to_json(...)

    def raise_incomplete_modeling_errors(self):  # 8. Validation
        ...

    # Plus 15+ property accessors (servers, services, jobs, etc.)
```

**Problems:**
- Directly depends on Django's `SessionBase` (framework coupling)
- Mixes data access (sessions) with domain orchestration
- Handles both reading AND writing to storage
- Contains validation logic that belongs in use cases

#### 2. ModelingObjectWeb (`model_builder/web_abstract_modeling_classes/modeling_object_web.py`) - 486 lines

**Current Responsibilities (9+):**
```python
from django.http import QueryDict, HttpResponse  # VIOLATION: HTTP in business layer
from django.shortcuts import render              # VIOLATION: Rendering in business layer

class ModelingObjectWeb:
    # 1. Model wrapping/delegation
    def __getattr__(self, name):
        attr = getattr(self._modeling_obj, name)
        ...

    # 2. Web ID generation (presentation concern)
    @property
    def web_id(self):
        return f"{self.class_as_simple_str}-{self._modeling_obj.id}"

    # 3. Template selection (presentation concern)
    @property
    def template_name(self):
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', self.class_as_simple_str).lower()
        return f"{snake_case}"

    # 4. Form context generation (should be separate)
    @classmethod
    def generate_object_creation_context(cls, model_web, ...):
        ...

    # 5. HTTP response building (VIOLATION: should be in views)
    @classmethod
    def add_new_object_and_return_html_response(cls, request, model_web, object_type):
        new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, ...)
        added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)
        response = render(request, f"model_builder/object_cards/{added_obj.template_name}_card.html", ...)
        response["HX-Trigger-After-Swap"] = json.dumps({...})
        return response

    # 6. Edit coordination (mixes HTTP with business)
    def edit_object_and_return_html_response(self, edit_form_data: QueryDict):
        return compute_edit_object_html_and_event_response(edit_form_data, self)

    # 7. Deletion logic
    def self_delete(self):
        ...
        self.model_web.response_objs[obj_type].pop(object_id, None)

    # 8. Modal generation (presentation)
    def generate_ask_delete_modal_context(self):
        ...

    # 9. HTTP response for deletion
    def generate_delete_http_response(self, request):
        ...
        http_response = HttpResponse(status=204)
        http_response["HX-Trigger"] = json.dumps({...})
        return http_response
```

**Key Violations:**
- Django HTTP imports (`QueryDict`, `HttpResponse`, `render`) in what should be a business layer
- Methods that return HTTP responses directly
- Template rendering mixed with business logic
- Tightly coupled to Django's request/response cycle

#### 3. Views (`model_builder/views.py`, `addition/views_addition.py`, etc.)

**Current Pattern:**
```python
def add_object(request, object_type):
    model_web = ModelWeb(request.session)  # Direct session access
    object_web_class = EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING[object_type]
    http_response = object_web_class.add_new_object_and_return_html_response(
        request, model_web, object_type)  # Business class returns HTTP response!
    return http_response
```

**Problems:**
- Views are thin but delegate to wrong layer
- Business classes (`ModelingObjectWeb`) handle HTTP responses
- No use case layer between views and domain

#### 4. Form Generation (`model_builder/class_structure.py`) - 259 lines

**Current Pattern:**
```python
def generate_dynamic_form(efootprint_class_str: str, default_values: dict, model_web: "ModelWeb"):
    # 1. Class introspection (could be domain)
    init_sig_params = get_init_signature_params(efootprint_class)

    # 2. Form field structure generation (presentation)
    for attr_name in init_sig_params.keys():
        annotation = init_sig_params[attr_name].annotation
        if issubclass(annotation, ExplainableQuantity):
            structure_field.update({"input_type": "input", "unit": ..., "default": ...})
        elif issubclass(annotation, ModelingObject):
            # 3. Data access for options (should be repository)
            selection_options = model_web.get_efootprint_objects_from_efootprint_type(...)

    return structure_fields, structure_fields_advanced, dynamic_lists
```

**Problems:**
- Mixes class introspection with presentation decisions
- Depends on `model_web` for data access within form generation
- No separation between "what fields exist" and "how to render them"

---

## Violations and Their Impact

### 1. Single Responsibility Principle Violations

| Class | Lines | Responsibilities | Impact |
|-------|-------|------------------|--------|
| `ModelingObjectWeb` | 486 | 9+ (wrapping, IDs, templates, forms, HTTP, deletion, modals) | Hard to test, hard to modify, changes ripple |
| `ModelWeb` | 327 | 8+ (session, serialization, validation, accessors) | God class, testing requires session mocking |
| `class_structure.py` | 259 | 4+ (introspection, form gen, data access, timeseries detection) | Tightly coupled, hard to extend |

### 2. Dependency Inversion Violations

**Django Framework in Business Layer:**
```python
# model_builder/web_abstract_modeling_classes/modeling_object_web.py:5-6
from django.http import QueryDict, HttpResponse
from django.shortcuts import render

# model_builder/web_core/model_web.py:7
from django.contrib.sessions.backends.base import SessionBase
```

**Impact:** Cannot test business logic without Django test infrastructure. Cannot switch frameworks.

### 3. Interface Segregation Violations

`ModelingObjectWeb` forces all consumers to depend on 486 lines of interface even if they only need:
- Object wrapping (50 lines)
- Form generation (30 lines)
- HTTP responses (100 lines)

### 4. Open/Closed Principle Violations

Adding a new object type requires:
1. Adding to `EFOOTPRINT_CLASS_STR_TO_WEB_CLASS_MAPPING`
2. Potentially creating a new `*Web` subclass
3. Adding form field references
4. Creating templates

The system is not easily extensible without modification.

### 5. Practical Consequences

| Issue | Consequence |
|-------|-------------|
| HTTP in business layer | Cannot unit test without HTTP mocking |
| Session coupling | Tests require Django session infrastructure |
| God classes | Changes to one feature affect unrelated features |
| Mixed concerns | Debugging requires understanding multiple domains |
| No use cases | Business logic scattered across views and wrappers |

---

## Proposed Target Architecture

### Target Layer Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRAMEWORKS & DRIVERS                                               │
│  ├── Django (settings, WSGI, middleware)                           │
│  ├── HTMX (client-side)                                            │
│  └── Session Storage (implementation detail)                       │
├─────────────────────────────────────────────────────────────────────┤
│  INTERFACE ADAPTERS                                                 │
│  ├── Controllers (Django views - thin!)                            │
│  ├── Presenters (format responses for HTMX/HTML)                   │
│  ├── Repositories (SessionSystemRepository)                        │
│  └── DTOs (data transfer between layers)                           │
├─────────────────────────────────────────────────────────────────────┤
│  APPLICATION BUSINESS RULES (Use Cases)                            │
│  ├── CreateObjectUseCase                                           │
│  ├── EditObjectUseCase                                             │
│  ├── DeleteObjectUseCase                                           │
│  ├── GetSystemEmissionsUseCase                                     │
│  └── ValidateModelingUseCase                                       │
├─────────────────────────────────────────────────────────────────────┤
│  ENTERPRISE BUSINESS RULES (Domain)                                │
│  ├── efootprint package (external, unchanged)                      │
│  └── Domain Interfaces (ISystemRepository)                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Proposed Directory Structure

```
model_builder/
├── domain/                    # Domain interfaces (no Django imports!)
│   ├── __init__.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── system_repository.py    # ISystemRepository interface
│   │   └── object_factory.py       # IObjectFactory interface
│   └── value_objects/
│       └── form_field.py           # Pure data structures for forms
│
├── application/               # Use cases (no Django imports!)
│   ├── __init__.py
│   ├── use_cases/
│   │   ├── __init__.py
│   │   ├── create_object.py        # CreateObjectUseCase
│   │   ├── edit_object.py          # EditObjectUseCase
│   │   ├── delete_object.py        # DeleteObjectUseCase
│   │   ├── get_emissions.py        # GetSystemEmissionsUseCase
│   │   └── validate_modeling.py    # ValidateModelingUseCase
│   └── services/
│       ├── __init__.py
│       ├── form_builder.py         # FormBuilderService (introspection)
│       └── object_wrapper.py       # ObjectWrapperService
│
├── adapters/                  # Interface adapters (Django-aware)
│   ├── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── session_system_repository.py  # SessionSystemRepository
│   ├── presenters/
│   │   ├── __init__.py
│   │   ├── htmx_presenter.py       # Format responses for HTMX
│   │   ├── form_presenter.py       # Format form structures
│   │   └── card_presenter.py       # Format object cards
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── object_controller.py    # Thin HTTP handlers
│   │   └── result_controller.py
│   └── mappers/
│       ├── __init__.py
│       └── request_mapper.py       # Map QueryDict to use case inputs
│
├── infrastructure/            # Framework code
│   ├── __init__.py
│   └── django/
│       ├── views.py               # Entry points that delegate to controllers
│       └── urls.py
│
├── web_wrappers/              # Simplified wrappers (presentation only)
│   ├── __init__.py
│   ├── modeling_object_presenter.py   # Only presentation concerns
│   └── model_presenter.py             # Only presentation concerns
│
└── templates/                 # Unchanged
```

---

## Refactoring Path

### Phase 1: Extract Repository Pattern (High Priority)

**Goal:** Decouple business logic from Django sessions

**Current (Violation):**
```python
# In ModelWeb.__init__
self.session = session
self.system_data = session["system_data"]

# In ModelWeb.update_system_data_with_up_to_date_calculated_attributes
self.session.modified = True
self.session["system_data"] = self.to_json(...)
```

**Target:**
```python
# domain/interfaces/system_repository.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class ISystemRepository(ABC):
    @abstractmethod
    def get_system_data(self) -> Dict[str, Any]:
        """Retrieve the current system data."""
        pass

    @abstractmethod
    def save_system_data(self, system_data: Dict[str, Any]) -> None:
        """Persist the system data."""
        pass

# adapters/repositories/session_system_repository.py
from django.contrib.sessions.backends.base import SessionBase
from model_builder.domain.interfaces.system_repository import ISystemRepository

class SessionSystemRepository(ISystemRepository):
    def __init__(self, session: SessionBase):
        self._session = session

    def get_system_data(self) -> Dict[str, Any]:
        return self._session.get("system_data", {})

    def save_system_data(self, system_data: Dict[str, Any]) -> None:
        self._session["system_data"] = system_data
        self._session.modified = True
```

**Refactored ModelWeb:**
```python
# web_core/model_web.py (refactored)
class ModelWeb:
    def __init__(self, repository: ISystemRepository):  # Now accepts interface
        self.repository = repository
        self.system_data = repository.get_system_data()
        # ... rest of initialization

    def save(self) -> None:
        self.repository.save_system_data(self.to_json(save_calculated_attributes=True))
```

**Migration Steps:**
1. Create `domain/interfaces/system_repository.py` with `ISystemRepository`
2. Create `adapters/repositories/session_system_repository.py`
3. Modify `ModelWeb.__init__` to accept `ISystemRepository` instead of `SessionBase`
4. Update all view call sites to inject the repository
5. Write unit tests for `ModelWeb` using a mock repository

### Phase 2: Extract Use Cases (High Priority)

**Goal:** Create explicit application layer between views and domain

**Current (Violation):**
```python
# In ModelingObjectWeb.add_new_object_and_return_html_response
@classmethod
def add_new_object_and_return_html_response(cls, request, model_web, object_type):
    # Business logic
    new_efootprint_obj = create_efootprint_obj_from_post_data(request.POST, model_web, object_type)
    added_obj = model_web.add_new_efootprint_object_to_system(new_efootprint_obj)

    # Presentation logic (should be separate!)
    response = render(request, f"model_builder/object_cards/{added_obj.template_name}_card.html", ...)
    response["HX-Trigger-After-Swap"] = json.dumps({...})
    return response
```

**Target:**
```python
# application/use_cases/create_object.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class CreateObjectInput:
    object_type: str
    form_data: Dict[str, Any]
    parent_id: Optional[str] = None

@dataclass
class CreateObjectOutput:
    created_object_id: str
    created_object_name: str
    object_type: str
    parent_was_modified: bool
    modified_parent_id: Optional[str] = None

class CreateObjectUseCase:
    def __init__(self, repository: ISystemRepository, object_factory: IObjectFactory):
        self.repository = repository
        self.object_factory = object_factory

    def execute(self, input_data: CreateObjectInput) -> CreateObjectOutput:
        # 1. Load system
        model_web = ModelWeb(self.repository)

        # 2. Create object (business logic)
        new_obj = self.object_factory.create_from_form_data(
            input_data.form_data, model_web, input_data.object_type)

        # 3. Add to system
        added_obj = model_web.add_new_efootprint_object_to_system(new_obj)

        # 4. Handle parent linking if needed
        parent_modified = False
        if input_data.parent_id:
            parent_modified = self._link_to_parent(model_web, added_obj, input_data.parent_id)

        # 5. Save
        model_web.save()

        # 6. Return pure data (no HTTP!)
        return CreateObjectOutput(
            created_object_id=added_obj.efootprint_id,
            created_object_name=added_obj.name,
            object_type=input_data.object_type,
            parent_was_modified=parent_modified,
            modified_parent_id=input_data.parent_id if parent_modified else None
        )

    def _link_to_parent(self, model_web, child, parent_id) -> bool:
        # Business logic for linking
        ...
```

**Refactored View:**
```python
# adapters/controllers/object_controller.py
from model_builder.application.use_cases.create_object import CreateObjectUseCase, CreateObjectInput
from model_builder.adapters.presenters.htmx_presenter import HtmxPresenter

def add_object(request, object_type):
    # 1. Map request to input
    input_data = CreateObjectInput(
        object_type=object_type,
        form_data=dict(request.POST),
        parent_id=request.POST.get("efootprint_id_of_parent_to_link_to")
    )

    # 2. Execute use case
    repository = SessionSystemRepository(request.session)
    use_case = CreateObjectUseCase(repository, ObjectFactory())
    output = use_case.execute(input_data)

    # 3. Present result
    presenter = HtmxPresenter(request)
    return presenter.present_created_object(output)
```

**Migration Steps:**
1. Create `application/use_cases/` directory
2. Extract `CreateObjectUseCase` with pure input/output dataclasses
3. Create `EditObjectUseCase`, `DeleteObjectUseCase`
4. Create presenter classes for HTTP response formatting
5. Refactor views to use use cases + presenters
6. Remove HTTP-related code from `ModelingObjectWeb`

### Phase 3: Split ModelingObjectWeb (Medium Priority)

**Goal:** Separate responsibilities into focused classes

**Current (9+ responsibilities in one class):**
```python
class ModelingObjectWeb:
    # Wrapping, IDs, templates, forms, HTTP, deletion, modals, etc.
```

**Target (Multiple focused classes):**

```python
# web_wrappers/modeling_object_wrapper.py
class ModelingObjectWrapper:
    """Pure wrapper around efootprint object with ID generation."""

    def __init__(self, modeling_obj: ModelingObject, model_web: "ModelWeb"):
        self._modeling_obj = modeling_obj
        self.model_web = model_web

    @property
    def efootprint_id(self) -> str:
        return self._modeling_obj.id

    @property
    def web_id(self) -> str:
        return f"{self.class_as_simple_str}-{self._modeling_obj.id}"

    def __getattr__(self, name):
        # Delegation logic only
        ...

# adapters/presenters/object_presenter.py
class ObjectPresenter:
    """Handles presentation concerns for modeling objects."""

    def __init__(self, wrapper: ModelingObjectWrapper):
        self.wrapper = wrapper

    @property
    def template_name(self) -> str:
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', self.wrapper.class_as_simple_str).lower()
        return f"{snake_case}"

    def to_card_context(self) -> Dict[str, Any]:
        return {"object": self.wrapper, "template": self.template_name}

# adapters/presenters/form_presenter.py
class FormPresenter:
    """Generates form structures for objects."""

    def generate_creation_context(self, object_type: str, model_web) -> Dict[str, Any]:
        ...

    def generate_edition_context(self, wrapper: ModelingObjectWrapper) -> Dict[str, Any]:
        ...

# application/services/deletion_service.py
class DeletionService:
    """Handles object deletion logic."""

    def can_delete(self, wrapper: ModelingObjectWrapper) -> Tuple[bool, Optional[str]]:
        """Returns (can_delete, reason_if_not)."""
        ...

    def delete(self, wrapper: ModelingObjectWrapper) -> None:
        """Performs deletion."""
        ...
```

**Migration Steps:**
1. Extract `ObjectPresenter` with template and display logic
2. Extract `FormPresenter` with form generation logic
3. Extract `DeletionService` with deletion logic
4. Move HTTP response generation to controllers
5. Simplify `ModelingObjectWeb` to just wrapper + delegation
6. Rename to `ModelingObjectWrapper`

### Phase 4: Decouple Form Generation (Medium Priority)

**Goal:** Separate "what fields exist" from "how to render them"

**Current:**
```python
def generate_dynamic_form(efootprint_class_str, default_values, model_web):
    # Mixes introspection + presentation + data access
```

**Target:**
```python
# application/services/class_introspector.py
class ClassIntrospector:
    """Analyzes efootprint class structure."""

    def get_field_definitions(self, class_name: str) -> List[FieldDefinition]:
        """Returns pure field definitions without presentation."""
        efootprint_class = MODELING_OBJECT_CLASSES_DICT[class_name]
        init_params = get_init_signature_params(efootprint_class)

        fields = []
        for name, param in init_params.items():
            fields.append(FieldDefinition(
                name=name,
                annotation=param.annotation,
                default=self._get_default(efootprint_class, name),
                is_list=self._is_list_type(param.annotation)
            ))
        return fields

# adapters/presenters/form_presenter.py
class FormPresenter:
    """Converts field definitions to renderable form structures."""

    def __init__(self, introspector: ClassIntrospector, repository: ISystemRepository):
        self.introspector = introspector
        self.repository = repository

    def build_form(self, class_name: str, defaults: Dict) -> FormStructure:
        fields = self.introspector.get_field_definitions(class_name)
        model_web = ModelWeb(self.repository)

        form_fields = []
        for field in fields:
            form_fields.append(self._to_form_field(field, defaults, model_web))

        return FormStructure(fields=form_fields)

    def _to_form_field(self, field: FieldDefinition, defaults: Dict, model_web) -> FormField:
        # Presentation logic only
        ...
```

### Phase 5: Clean Up Views (Lower Priority)

**Goal:** Make views true thin adapters

**Current:**
```python
def model_builder_main(request, reboot=False):
    # Contains logic for reboot handling
    if reboot == "reboot":
        with open(...) as file:
            system_data = json.load(file)
        request.session["system_data"] = system_data
        model_web = ModelWeb(request.session)
        model_web.update_system_data_with_up_to_date_calculated_attributes()
        gc.collect()
        return redirect("model-builder")

    # Contains version checking
    if "efootprint_version" not in request.session["system_data"]:
        request.session["system_data"]["efootprint_version"] = "9.1.4"

    # Multiple concerns mixed
    ...
```

**Target:**
```python
# adapters/controllers/main_controller.py
def model_builder_main(request, reboot=False):
    repository = SessionSystemRepository(request.session)

    if reboot == "reboot":
        use_case = ResetSystemUseCase(repository)
        use_case.execute()
        return redirect("model-builder")

    if not repository.has_system_data():
        return redirect("model-builder", reboot="reboot")

    use_case = LoadSystemUseCase(repository)
    system_data = use_case.execute()

    presenter = MainPagePresenter(request)
    return presenter.render(system_data)
```

---

## Implementation Examples

### Example 1: Repository Pattern Implementation

```python
# domain/interfaces/system_repository.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ISystemRepository(ABC):
    """Interface for system data persistence."""

    @abstractmethod
    def get_system_data(self) -> Optional[Dict[str, Any]]:
        """Get the current system data, or None if not exists."""
        pass

    @abstractmethod
    def save_system_data(self, data: Dict[str, Any]) -> None:
        """Save system data."""
        pass

    @abstractmethod
    def has_system_data(self) -> bool:
        """Check if system data exists."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all system data."""
        pass
```

```python
# adapters/repositories/session_system_repository.py
from django.contrib.sessions.backends.base import SessionBase
from model_builder.domain.interfaces.system_repository import ISystemRepository

class SessionSystemRepository(ISystemRepository):
    """Session-based implementation of system repository."""

    SYSTEM_DATA_KEY = "system_data"

    def __init__(self, session: SessionBase):
        self._session = session

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        return self._session.get(self.SYSTEM_DATA_KEY)

    def save_system_data(self, data: Dict[str, Any]) -> None:
        self._session[self.SYSTEM_DATA_KEY] = data
        self._session.modified = True

    def has_system_data(self) -> bool:
        return self.SYSTEM_DATA_KEY in self._session

    def clear(self) -> None:
        self._session.pop(self.SYSTEM_DATA_KEY, None)
        self._session.modified = True
```

```python
# For testing: In-memory implementation
class InMemorySystemRepository(ISystemRepository):
    """In-memory implementation for testing."""

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self._data = initial_data

    def get_system_data(self) -> Optional[Dict[str, Any]]:
        return self._data

    def save_system_data(self, data: Dict[str, Any]) -> None:
        self._data = data

    def has_system_data(self) -> bool:
        return self._data is not None

    def clear(self) -> None:
        self._data = None
```

### Example 2: Use Case Implementation

```python
# application/use_cases/edit_object.py
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class EditObjectInput:
    object_id: str
    form_data: Dict[str, Any]

@dataclass
class EditObjectOutput:
    object_id: str
    object_name: str
    modified_attributes: List[str]
    affected_object_ids: List[str]  # Objects whose cards need refresh

class EditObjectUseCase:
    """Use case for editing an existing modeling object."""

    def __init__(self, repository: ISystemRepository):
        self.repository = repository

    def execute(self, input_data: EditObjectInput) -> EditObjectOutput:
        # 1. Load system
        model_web = ModelWeb(self.repository)

        # 2. Get object to edit
        obj_wrapper = model_web.get_web_object_from_efootprint_id(input_data.object_id)

        # 3. Determine what changed
        changes = self._compute_changes(obj_wrapper, input_data.form_data)

        # 4. Apply changes
        if changes:
            self._apply_changes(obj_wrapper, changes)

        # 5. Save
        model_web.save()

        # 6. Return result
        return EditObjectOutput(
            object_id=obj_wrapper.efootprint_id,
            object_name=obj_wrapper.name,
            modified_attributes=[c.attr_name for c in changes],
            affected_object_ids=self._get_affected_ids(obj_wrapper)
        )

    def _compute_changes(self, obj, form_data) -> List[Change]:
        # Business logic for change detection
        ...

    def _apply_changes(self, obj, changes) -> None:
        # Business logic for applying changes
        ...

    def _get_affected_ids(self, obj) -> List[str]:
        # Compute which object cards need refresh
        return [card.web_id for card in obj.mirrored_cards]
```

### Example 3: Presenter Implementation

```python
# adapters/presenters/htmx_presenter.py
import json
from django.http import HttpResponse
from django.shortcuts import render

class HtmxPresenter:
    """Formats use case outputs as HTMX-compatible HTTP responses."""

    def __init__(self, request):
        self.request = request

    def present_created_object(self, output: CreateObjectOutput) -> HttpResponse:
        """Format a created object response."""
        # Get wrapper for template rendering
        model_web = ModelWeb(SessionSystemRepository(self.request.session))
        obj = model_web.get_web_object_from_efootprint_id(output.created_object_id)

        template_name = self._get_card_template(output.object_type)
        response = render(self.request, template_name, {"object": obj})

        # Add HTMX triggers
        response["HX-Trigger-After-Swap"] = json.dumps({
            "resetLeaderLines": "",
            "setAccordionListeners": {"accordionIds": [obj.web_id]},
            "displayToastAndHighlightObjects": {
                "ids": [obj.web_id],
                "name": output.created_object_name,
                "action_type": "add_new_object"
            }
        })

        return response

    def present_edited_object(self, output: EditObjectOutput) -> HttpResponse:
        """Format an edited object response."""
        ...

    def present_deleted_object(self, output: DeleteObjectOutput) -> HttpResponse:
        """Format a deletion response."""
        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps({
            "resetLeaderLines": "",
            "displayToastAndHighlightObjects": {
                "ids": [],
                "name": output.object_name,
                "action_type": "delete_object"
            }
        })
        return response

    def _get_card_template(self, object_type: str) -> str:
        snake_case = self._to_snake_case(object_type)
        return f"model_builder/object_cards/{snake_case}_card.html"
```

---

## Testing Benefits After Refactoring

### Before (Hard to Test)

```python
# Requires Django session infrastructure
def test_add_object():
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.post('/add/Server/', data={...})
    request.session = {}  # Complex session mocking needed
    response = add_object(request, 'Server')
```

### After (Easy to Test)

```python
# Pure unit test - no Django needed
def test_create_object_use_case():
    # Arrange
    repository = InMemorySystemRepository(initial_data=DEFAULT_SYSTEM)
    use_case = CreateObjectUseCase(repository, ObjectFactory())
    input_data = CreateObjectInput(
        object_type="Server",
        form_data={"name": "Test Server", ...}
    )

    # Act
    output = use_case.execute(input_data)

    # Assert
    assert output.created_object_name == "Test Server"
    assert repository.get_system_data()["Server"][output.created_object_id] is not None
```

---

## Summary of Changes by Priority

### High Priority (Phase 1-2)
1. **Extract Repository Pattern** - Decouple from Django sessions
2. **Create Use Cases** - Explicit application layer

### Medium Priority (Phase 3-4)
3. **Split ModelingObjectWeb** - Single responsibility
4. **Decouple Form Generation** - Separate concerns

### Lower Priority (Phase 5)
5. **Clean Up Views** - True thin adapters

### Metrics for Success

| Metric | Current | Target |
|--------|---------|--------|
| `ModelingObjectWeb` lines | 486 | <100 |
| Django imports in `web_core/` | 5 | 0 |
| Use case classes | 0 | 5+ |
| Unit tests without Django | Few | Many |
| Files with HTTP imports | 10+ | 3 (controllers only) |

---

## Getting Started

1. **Start with Phase 1**: Create `ISystemRepository` and `SessionSystemRepository`
2. **Modify `ModelWeb`** to accept `ISystemRepository` instead of `SessionBase`
3. **Update view call sites** to inject the repository
4. **Write tests** using `InMemorySystemRepository`
5. **Proceed to Phase 2** once Phase 1 is stable

This incremental approach allows you to improve the architecture gradually without breaking existing functionality.