# Step 2 — SSOT metadata in e-footprint

Detailed implementation plan for adding structured description metadata to every concrete e-footprint class and writing the tests that enforce completeness. This is the authorship step that Steps 3, 4, and 6 all depend on.

**Repo:** e-footprint (library only)

**Draws from:** `01-single-source-of-truth.md` (shape of content, placeholder syntax, tests), `05-maintainability-and-build.md` (SSOT description tests, phasing).

---

## Deliverables overview

1. `param_descriptions` dict on every concrete class
2. Class docstring on every concrete class that lacks one
3. Docstring on every `update_<attr>` method
4. Optional `disambiguation`, `pitfalls`, `interactions`, `param_interactions` class attributes where warranted
5. `tests/test_descriptions.py` enforcing completeness
6. Upgraded `generate_object_reference.py` reading the new attributes

---

## Sub-step 2.1 — Test file `tests/test_descriptions.py`

Write the test file first. It drives content authorship: tests fail until descriptions are written.

### What the tests check

The tests walk every class in `ALL_EFOOTPRINT_CLASSES` (from `efootprint/all_classes_in_order.py`). For each concrete class:

**Check 1 — Docstring presence:**
Every concrete class has a non-empty `__doc__`.

**Check 2 — `param_descriptions` coverage:**
`param_descriptions` must be present as a class attribute (dict). Its keys must exactly match the `__init__` params minus `self` and `name`. Use `get_init_signature_params(cls)` (from `efootprint/utils/tools.py`) to introspect params.

Special cases to handle:
- `Country.__init__` has a `short_name: str` parameter that is not in `default_values` and is not an ExplainableObject. It should still be covered by `param_descriptions`.
- Abstract base classes (`HardwareBase`, `InfraHardware`, `ServerBase`, `JobBase`, etc.) are not in `ALL_EFOOTPRINT_CLASSES` and are not checked. Only concrete classes listed in the `ALL_EFOOTPRINT_CLASSES` list are iterated.
- Some concrete classes inherit `__init__` from a parent (e.g. `Server` inherits from `ServerBase`). The test should resolve the actual `__init__` signature regardless of where it is defined — `get_init_signature_params` already handles this via `inspect.signature`.

**Check 3 — `update_<attr>` docstrings:**
For each entry in the class's `calculated_attributes` property, assert that the corresponding `update_<attr>` method exists and has a non-empty `__doc__`. Note: `calculated_attributes` is a property, not a class attribute, so it must be called on an instance or read carefully. Since instantiation requires valid arguments, the approach is:
- Iterate over concrete classes.
- For each class, get its `calculated_attributes` by introspecting `update_<attr>` methods directly: scan the MRO for methods matching `update_<attr_name>` and check their docstrings.

```python
for attr_name in calculated_attr_names:
    method = getattr(cls, f"update_{attr_name}", None)
    assert method is not None, f"{cls.__name__} missing update_{attr_name}"
    assert method.__doc__, f"{cls.__name__}.update_{attr_name} has no docstring"
```

The challenge is getting `calculated_attr_names` without an instance. Since `calculated_attributes` is a `@property`, we cannot call it on the class. Two options:
1. Walk the MRO and collect all methods matching `update_*`, then check docstrings on those. This is conservative (checks more than strictly needed) but safe.
2. Use the docs_case instances. The reference generator already instantiates every class for the docs. We can import those instances and call `.calculated_attributes` on them.

**Decision needed:** Which approach to use for getting `calculated_attributes`. Recommend option 2 (reuse docs_case instances) for accuracy, with option 1 as a fallback/supplementary check.

**Check 4 — `param_interactions` subset:**
If a class defines `param_interactions`, its keys must be a subset of the class's `param_descriptions` keys.

**Check 5 — Placeholder resolution:**
Every `{kind:target}` placeholder in any description string (class docstring, `param_descriptions` values, `update_<attr>` docstrings, `interactions`, `disambiguation`, `pitfalls`, `param_interactions` values) must resolve:
- `{class:X}` — `X` exists in `ALL_EFOOTPRINT_CLASSES_DICT` (which includes both concrete and canonical classes).
- `{param:X.y}` — class `X` exists in `ALL_EFOOTPRINT_CLASSES_DICT` and `y` is one of its `__init__` params (via `get_init_signature_params`).
- `{calc:X.y}` — class `X` exists and `y` is in its `calculated_attributes` (requires instance or MRO scan).
- `{doc:...}` — allowed in library strings, but target validation deferred to mkdocs build (not checked here).

**Check 6 — Forbidden placeholder kinds:**
`{ui:...}` is rejected in all library-side strings. Any `{kind:...}` where `kind` is not in `{class, param, calc, doc}` is a failure.

### Implementation notes

- Use `re.findall(r"\{(\w+):([^}]+)\}", text)` to extract all placeholders from a string.
- Write a helper `collect_all_description_strings(cls)` that gathers all relevant strings from a class into a flat list of `(source_label, text)` tuples for uniform checking.
- Parametrize tests with `@pytest.mark.parametrize` over `ALL_EFOOTPRINT_CLASSES` so failures are reported per-class.
- All checks are **hard failures from day one** — they drive content authorship.

---

## Sub-step 2.2 — Add `param_descriptions` and class docstrings

For every concrete class in `ALL_EFOOTPRINT_CLASSES`, add:

1. **A class docstring** if missing. One sentence describing what the object represents in domain terms.
2. **A `param_descriptions` class-level dict** whose keys exactly cover `__init__` params minus `self` and `name`.

### Where to define `param_descriptions`

Define `param_descriptions` on the **most specific concrete class** — the one listed in `ALL_EFOOTPRINT_CLASSES`. When the `__init__` is inherited from a parent (e.g. `Server` inherits from `ServerBase`), put `param_descriptions` on `Server` (the concrete class), not on `ServerBase` (the abstract base). This avoids inheritance confusion and keeps each concrete class self-contained.

If two concrete siblings share the same `__init__` signature (e.g. `Server` and `GPUServer` both inherit from `ServerBase`), each gets its own `param_descriptions`. This allows descriptions to be tailored — e.g. `GPUServer`'s `compute` param description can mention GPUs while `Server`'s mentions CPU cores.

### Content guidelines

- Plain English, no markdown.
- No UI-specific words (`click`, `button`, `drag`).
- No Python-specific words in context-free strings (`instantiate`, `import`, backticks) — except in `interactions` and `param_interactions` which are explicitly Python-usage strings.
- Placeholders like `{class:GPUServer}` are encouraged for cross-references.
- Descriptions should be about the domain concept, not about how to use the code or the UI.

### Class inventory

The full list of concrete classes to annotate (from `ALL_EFOOTPRINT_CLASSES`):

**Core — Usage:**
- `UsageJourneyStep`
- `UsageJourney`
- `UsagePattern`
- `Job`
- `GPUJob`

**Core — Hardware:**
- `Server`
- `GPUServer`
- `Device`
- `Network`
- `Storage`
- `Country`

**Core — Edge usage:**
- `EdgeUsageJourney`
- `EdgeFunction`
- `EdgeUsagePattern`
- `RecurrentEdgeStorageNeed`
- `RecurrentEdgeDeviceNeed`
- `RecurrentServerNeed`
- `RecurrentEdgeComponentNeed`

**Core — Edge hardware:**
- `EdgeRAMComponent`
- `EdgeCPUComponent`
- `EdgeWorkloadComponent`
- `EdgeStorage`
- `EdgeDevice`
- `EdgeDeviceGroup`

**Builders — Hardware:**
- `BoaviztaCloudServer`
- `EdgeAppliance`, `EdgeApplianceComponent`
- `EdgeComputer`, `EdgeComputerRAMComponent`, `EdgeComputerCPUComponent`

**Builders — Services:**
- `VideoStreaming`
- `VideoStreamingJob`

**Builders — External APIs:**
- `EcoLogitsGenAIExternalAPI`
- `EcoLogitsGenAIExternalAPIServer`
- `EcoLogitsGenAIExternalAPIJob`

**Builders — Usage:**
- `RecurrentEdgeProcess`, `RecurrentEdgeProcessRAMNeed`, `RecurrentEdgeProcessCPUNeed`, `RecurrentEdgeProcessStorageNeed`
- `RecurrentEdgeWorkload`, `RecurrentEdgeWorkloadNeed`

**Top-level:**
- `System`

Total: ~45 concrete classes. This is the bulk of the authorship work.

---

## Sub-step 2.3 — Add `update_<attr>` method docstrings

For every `update_<attr>` method on every concrete class (and its abstract parents where the method is defined), add a one-sentence docstring describing what the calculated attribute represents.

The docstring goes on the **method that contains the implementation**, not on abstract stubs. For example:
- `InfraHardware.update_instances_fabrication_footprint` — gets a docstring here (this is where the logic lives).
- `InfraHardware.update_raw_nb_of_instances` — abstract method, no docstring here. The docstring goes on `ServerBase.update_raw_nb_of_instances` (or `Server.update_raw_nb_of_instances` if overridden).

### Approach

Since the test in sub-step 2.1 checks docstrings on the resolved method (via `getattr(instance_or_cls, "update_<attr>")`), the docstring just needs to be reachable through the MRO. The safest approach:
- Add docstrings to the **concrete implementation** of each `update_<attr>` method.
- If the method is defined on an abstract parent (like `InfraHardware.update_instances_fabrication_footprint`), add the docstring there — it will be inherited by all concrete subclasses.

---

## Sub-step 2.4 — Add optional class attributes

For classes where it adds value, add:

- **`disambiguation`** (string): Distinguishes this class from siblings. Example: `Server` vs `GPUServer` vs `BoaviztaCloudServer`.
- **`pitfalls`** (string): Common mistakes or surprising behavior.
- **`interactions`** (string): How to use the class from Python. This is the only field where Python-specific language is allowed.
- **`param_interactions`** (dict, sparse): Per-param Python usage notes. Keys must be a subset of `param_descriptions` keys.

These are all **optional**. A missing attribute means the section is not rendered. Don't force content where there's nothing useful to say.

### Classes most likely to benefit from optional attributes

- **`Server` / `GPUServer` / `BoaviztaCloudServer`**: Strong disambiguation case (three server types with different use cases). Pitfalls around `server_type` / `fixed_nb_of_instances` interaction.
- **`Job` / `GPUJob`**: Disambiguation between the two. Pitfalls around resource units.
- **`EdgeDevice` / `EdgeDeviceGroup`**: Disambiguation. Pitfalls around component-device-group nesting.
- **`UsagePattern` / `EdgeUsagePattern`**: Disambiguation (web vs edge).
- **`RecurrentServerNeed`**: Key bridge class between edge and web paradigms — interactions and disambiguation are valuable.

---

## Sub-step 2.5 — Upgrade `generate_object_reference.py`

The existing reference generator (`docs_sources/doc_utils/generate_object_reference.py`) currently produces descriptions by inspecting live object instances and formatting labels/units. It falls back to `"description to be done"` when it can't derive a description (line 64).

### Changes

1. **Read `param_descriptions`**: In `obj_to_md(input_obj, attr_name)`, before falling through to the generic type-based logic, check if the owning class has a `param_descriptions` dict and if `attr_name` is in it. If so, use that as the primary description text instead of the label-based fallback. The type information (unit, linked class) should still be appended as supplementary info.

2. **Read class docstrings**: In `write_object_reference_file(mod_obj)`, include the class's `__doc__` as an introductory paragraph in the generated page, above the params section.

3. **Read `update_<attr>` docstrings**: In `calc_attr_to_md(input_obj, attr_name)`, prepend the method docstring as the primary description, keeping the existing calculation graph and dependency info below it.

4. **Read optional attributes**: Add sections for `disambiguation`, `pitfalls`, and `interactions` in the generated page when the corresponding class attribute is present.

5. **Resolve placeholders**: Add a simple resolver that processes `{kind:target}` tokens in all rendered strings:
   - `{class:X}` → `[X](X.md)` (mkdocs link)
   - `{param:X.y}` → `[X.y](X.md#y)` (in-page anchor)
   - `{calc:X.y}` → `[X.y](X.md#y)` (in-page anchor)
   - `{doc:topic}` → link to the corresponding docs page
   - `{ui:...}` → should not appear in library strings; raise an error if encountered.

6. **Update `obj_template.md`**: Extend the Jinja template to include the new sections (class description, disambiguation, pitfalls, interactions).

7. **Eliminate fallbacks**: The `"description to be done"` fallback on line 64 should become unreachable once `param_descriptions` covers all params. During the transition, it can remain as a safety net, but the Step 7 build review will assert it never fires.

### Template structure (updated `obj_template.md`)

```markdown
# {{ obj_dict["class"] }}

{{ obj_dict["class_description"] }}

{% if obj_dict["disambiguation"] %}
## When to use this class
{{ obj_dict["disambiguation"] }}
{% endif %}

{% if obj_dict["pitfalls"] %}
## Common pitfalls
{{ obj_dict["pitfalls"] }}
{% endif %}

## Params
{% for param_desc in obj_dict["params"] %}
{{ param_desc | safe }}
{% endfor %}

## Backwards links
{% for linked_obj in obj_dict["modeling_obj_containers"] %}
- [{{ linked_obj }}]({{ linked_obj }}.md)
{% endfor %}

## Calculated attributes
{% for calculated_attr_desc in obj_dict["calculated_attrs"] %}
{{ calculated_attr_desc | safe }}
{% endfor %}

{% if obj_dict["interactions"] %}
## Usage from Python
{{ obj_dict["interactions"] }}
{% endif %}
```

---

## Sub-step 2.6 — Placeholder resolution module

Create a small utility module `efootprint/utils/placeholder_resolver.py` (or place it in `docs_sources/doc_utils/`) that:

1. Parses `{kind:target}` tokens from a string using regex.
2. Accepts a dict of `kind -> handler` functions.
3. Returns the resolved string.

This module is used by:
- `generate_object_reference.py` (mkdocs resolver: `class` → md link, `param`/`calc` → anchor, `doc` → page link, `ui` → error)
- `tests/test_descriptions.py` (validation resolver: checks that targets exist, rejects `ui` kind)
- Later, the interface's `DescriptionProvider` adapter (Step 3)

### API sketch

```python
import re
from typing import Callable

PLACEHOLDER_PATTERN = re.compile(r"\{(\w+):([^}]+)\}")

def resolve_placeholders(text: str, handlers: dict[str, Callable[[str], str]]) -> str:
    """Replace all {kind:target} tokens using the provided handler functions."""
    def replacer(match):
        kind, target = match.group(1), match.group(2)
        handler = handlers.get(kind)
        if handler is None:
            raise ValueError(f"Unknown placeholder kind: {kind}")
        return handler(target)
    return PLACEHOLDER_PATTERN.sub(replacer, text)

def extract_placeholders(text: str) -> list[tuple[str, str]]:
    """Return all (kind, target) pairs found in text."""
    return PLACEHOLDER_PATTERN.findall(text)
```

---

## Implementation order

The sub-steps have the following dependency structure:

```
2.1 (tests) ──────────────────────────────┐
2.6 (placeholder module) ─────────────────┤
                                          ├── can be done in parallel
2.2 (param_descriptions + docstrings) ────┤
2.3 (update_<attr> docstrings) ───────────┤
2.4 (optional attributes) ────────────────┘
                                          │
                                          ▼
                               2.5 (upgrade reference generator)
```

Recommended sequence for the coding agent:

1. **2.6** — Write the placeholder resolution utility. Small, self-contained, no dependencies.
2. **2.1** — Write `tests/test_descriptions.py`. All tests will fail (expected). This validates the test logic against the current codebase before content is added.
3. **2.2 + 2.3 + 2.4** — Content authorship. Work through classes one file at a time. Run the test after each file to confirm it passes for that class. This is the bulk of the work.
4. **2.5** — Upgrade the reference generator. At this point all content exists and the generator can read it.

### Batching strategy for content authorship (2.2 + 2.3 + 2.4)

The ~45 classes can be grouped by module for efficient file editing:

| Batch | Module path | Classes |
|---|---|---|
| A | `core/usage/` | `UsageJourneyStep`, `UsageJourney`, `UsagePattern`, `Job`, `GPUJob` |
| B | `core/hardware/` | `Server`, `GPUServer`, `Device`, `Network`, `Storage`, `Country` + base classes (`HardwareBase`, `InfraHardware`, `ServerBase`) for `update_<attr>` docstrings |
| C | `core/usage/edge/` | `EdgeUsageJourney`, `EdgeFunction`, `EdgeUsagePattern`, `RecurrentEdgeStorageNeed`, `RecurrentEdgeDeviceNeed`, `RecurrentServerNeed`, `RecurrentEdgeComponentNeed` |
| D | `core/hardware/edge/` | `EdgeRAMComponent`, `EdgeCPUComponent`, `EdgeWorkloadComponent`, `EdgeStorage`, `EdgeDevice`, `EdgeDeviceGroup` |
| E | `builders/hardware/` | `BoaviztaCloudServer`, `EdgeAppliance`, `EdgeApplianceComponent`, `EdgeComputer`, `EdgeComputerRAMComponent`, `EdgeComputerCPUComponent` |
| F | `builders/services/` | `VideoStreaming`, `VideoStreamingJob` |
| G | `builders/external_apis/` | `EcoLogitsGenAIExternalAPI`, `EcoLogitsGenAIExternalAPIServer`, `EcoLogitsGenAIExternalAPIJob` |
| H | `builders/usage/edge/` | `RecurrentEdgeProcess` + its needs, `RecurrentEdgeWorkload` + its needs |
| I | `core/system.py` | `System` |

---

## Decisions and scoping

### What's in scope
- `param_descriptions`, docstrings, optional attributes, tests, reference generator upgrade, placeholder utility.

### What's out of scope (deferred to later steps)
- **`DescriptionProvider` port and adapter** — Step 3.
- **Interface-side `class_ui_config.json` extensions** — Step 3.
- **`{ui:...}` token registry** — Step 3.
- **mkdocs content writing** (how-to guides, FAQ stubs, `web_vs_edge.md`) — Step 4.
- **Modeling templates** — Step 4.
- **mkdocs CI** (`mkdocs build --strict` in GitHub Actions) — Step 4.
- **Library GitHub Actions CI** (existing pytest suite) — Step 1.
- **Ban-word check** — dropped per user decision. Not implemented in tests.

### Resolved open questions

- **Ban-word list:** Dropped. The content guidelines above are advisory, not enforced by tests.
- **`calculated_attributes` access without instantiation:** Use MRO method scanning as the primary approach — iterate `update_*` methods found on the class. Supplement with docs_case instances if needed for edge cases. The test should not require instantiating classes just to get the attribute list.
- **Where to put `param_descriptions` for inherited `__init__`:** On the concrete class, not the abstract parent.
- **Placeholder utility location:** `efootprint/utils/placeholder_resolver.py` — it's a library utility that will be used by tests, the reference generator, and eventually by the interface (via import).

### Open questions for review

1. **`calculated_attributes` from MRO vs docs_case instances:** The MRO scan approach (finding all `update_*` methods) may catch more methods than `calculated_attributes` actually lists (e.g. helper methods like `update_dict_element_in_*` that are not in `calculated_attributes`). Should we:
   - (a) Check docstrings on all `update_*` methods found on the class (conservative, may require docstrings on dict-element helpers), or
   - (b) Use docs_case instances to get the exact `calculated_attributes` list and only check those, or
   - (c) Use a naming convention to distinguish: only check `update_<attr>` where `attr` does not contain `dict_element_in_` ?

2. **Placeholder utility location:** `efootprint/utils/placeholder_resolver.py` vs `docs_sources/doc_utils/placeholder_resolver.py`. The former ships with the PyPI package (slightly increases package size but enables the interface to import it directly). The latter keeps it out of the distributed package but requires the interface to duplicate or vendor it. Recommend the former.
