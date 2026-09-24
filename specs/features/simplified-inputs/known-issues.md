# Known issues found during Simplified inputs planning

## SI-1 — Shared-controller dependents overwrite each other

Status: confirmed on 23 September 2026; not fixed.
Owner: e-footprint library, not the interface.

Source: [ModelingObject.attributes_with_depending_values()](../../../../e-footprint/efootprint/abstract_modeling_classes/modeling_object.py).

The helper builds a controller-to-dependent-fields lookup. It checks whether the **dependent**
attribute is already a key, but then writes under the **controller** key. When two fields depend
on the same controller, the second assignment overwrites the first.

### Minimal reproduction

Standalone Python check against the existing library (no repository file changes):

```python
from types import SimpleNamespace
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

metadata = SimpleNamespace(conditional_list_values={
    "first": {"depends_on": "controller"},
    "second": {"depends_on": "controller"},
})

print(ModelingObject.attributes_with_depending_values.__func__(metadata))
```

Observed: `{'controller': ['second']}`.
Expected: `{'controller': ['first', 'second']}`.

The reproduction was run through the library's Poetry environment. It demonstrates the helper
defect; it does not establish that a shipped modeling currently declares this exact arrangement.
The helper is used by existing conditional-value validation, so dropping dependents can omit checks.

### Planned follow-up

- Correct accumulation under the controller key in the library; do not compensate in interface code.
- Add a focused regression in [test_modeling_object.py](../../../../e-footprint/tests/abstract_modeling_classes/test_modeling_object.py)
  covering two dependent inputs sharing one controller.
- Carry this as an explicit library fix in the feature's later task breakdown. No implementation
  or task file is created by this note.

This helper groups class metadata. Fixing it does not add the model-wide selection logic needed
by Simplified inputs, nor does it establish a new cycle-rejection policy.
