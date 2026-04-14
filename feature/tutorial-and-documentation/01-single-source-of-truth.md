# Topic 1 — Single source of truth for descriptive content

This file captures the decisions about **where descriptive content lives** so
that mkdocs (e-footprint library docs) and the e-footprint-interface both
consume it without duplication, and so that it stays up to date by design.

See `00-index.md` for the overall context and the list of topics.

---

## Problem statement

We need:

1. Descriptive content (what an object is, what a param means, how to use
   it, common pitfalls, how it differs from siblings) that is consumed by
   both the mkdocs site and the interface.
2. A structure that keeps content **in one place** and **as close to the
   code as possible** so renaming, refactoring, or adding an object can't
   silently break documentation.
3. Compliance with Clean Architecture principles in the interface (domain
   must not depend on presentation).
4. A place to put contextual content (interactions, disambiguation,
   pitfalls) that was always missing from the auto-generated reference.

## Reframing the Clean Architecture concern

Clean Architecture forbids **inner layers depending on outer layers** —
domain must not import presentation, framework types, tooltip widgets, i18n
machinery, or HTML.

It does **not** forbid semantic metadata about domain concepts living with
the domain. A class docstring saying *"A Server represents a physical or
virtual machine that processes jobs"* is domain self-description in domain
terms, not a presentation concern. Pint units, attribute names, the
`calculated_attributes` list, and the `default_values` dict are all already
human-readable metadata living in the class. Adding descriptions is
structurally the same kind of thing.

A second observation: **e-footprint is a library, not a layered app**. Its
public API *is* its domain. The inner/outer ring problem it faces is minimal.
The CA question that actually matters is how the **interface** consumes
descriptive content without coupling its domain layer to a presentation
choice. Answer: the same way the interface consumes calculation results — via
an adapter. A `DescriptionProvider` port in
`model_builder/domain/interfaces/` with a concrete
`EfootprintDescriptionProvider` adapter keeps the interface domain layer
clean regardless of where descriptions physically live in the e-footprint
repo.

## Content kinds and their homes

Not all descriptive content is the same and not all of it needs to live in
the same place. We separate it by **who reads it** and **whether the fact
diverges between consumers**.

| Content kind | Example | Diverges between consumers? | Home |
|---|---|---|---|
| Class semantics (what it *is*) | "A Server is a machine that processes jobs." | No | Class docstring in efootprint |
| Param semantics | "Average grid carbon intensity over lifetime." | No | `param_descriptions` dict on the class in efootprint |
| Calculated attribute semantics | "Hourly energy consumed by all instances." | No | Docstring of the `update_<attr>` method on the class in efootprint |
| Disambiguation from sibling classes | "Use `GPUServer` for GPU-bound workloads…" | No | `disambiguation` class attribute in efootprint, single string with placeholders |
| Common pitfalls / failure modes | "If `power` is unset a generic default is used." | No | `pitfalls` class attribute in efootprint, single string with placeholders |
| How to interact from **Python** | "Instantiate with `Server(name=…, power=…)` and link jobs via the `jobs` attribute." | n/a — this *is* the library consumer | `interactions` class attribute in efootprint |
| How to interact from **the interface** | "Add via the infrastructure panel, then drag jobs onto the card." | n/a — this *is* the interface consumer | optional `interactions` field added to `class_ui_config.json` in the interface |
| Narrative (methodology, how-to guides, why edge vs web…) | long-form prose | single consumer per document | Hand-written mkdocs pages; the interface deep-links to them via `{doc:...}` tokens |

Three categories (disambiguation, pitfalls, library interactions) live only
in e-footprint and are read by the interface via the `DescriptionProvider`
adapter. One category (interface interactions) lives only in the interface
because the library should not know an interface exists. Everything else is
single-consumer.

**Typical value ranges and units** are intentionally out of scope for now.
They may be added ad hoc inside interaction-specific text later if needed.

**Markdown formatting** is not allowed inside descriptions. Formatting is a
consumer-side concern and descriptions may be presented differently in
different contexts. Descriptions are plain strings with placeholders.

**English only.** No translation is anticipated. If i18n becomes a real
need later the strings can move out of code into structured files, but
designing for it now is premature.

## Shape of the content in e-footprint

Everything semantic about a class lives in the class file. Example for
`Server`:

```python
class Server(Hardware):
    """A physical or virtual machine that processes jobs."""

    param_descriptions = {
        "power": "Idle-to-max power range used with utilization to compute energy.",
        "average_carbon_intensity": "Average grid carbon intensity over the server's lifetime.",
        # ...
    }

    interactions = (
        "Instantiate {class:Server} with a power range and link "
        "{class:Job}s via the jobs attribute."
    )

    disambiguation = (
        "Use {class:GPUServer} for GPU-bound workloads, or "
        "{class:BoaviztaCloudServer} for managed cloud with Boavizta-"
        "supported emission factors."
    )

    pitfalls = (
        "If {param:Server.power} is unset, a generic default is used that "
        "may not match your hardware."
    )

    param_interactions = {
        # Optional, only when a param has Python-specific guidance worth
        # attaching. Most params will have no entry.
        "power": "Pass as a {class:SourceValue} with idle and max wattage.",
    }

    default_values = {
        # ...
    }
```

And for calculated attributes, the existing `update_<attr>` methods gain a
docstring:

```python
def update_hourly_energy(self):
    """Hourly energy consumed by all instances of this server."""
    # calculation unchanged
```

Key points:

- **One `param_descriptions` dict**, no duplication across files. The
  earlier option of holding contextual content in a sibling JSON would have
  required a second per-param dict in JSON; folding everything into the
  class file eliminates that.
- `interactions`, `disambiguation`, `pitfalls` are **optional** class
  attributes. Classes without siblings need no disambiguation, classes
  without common mistakes need no pitfalls, etc. A missing attribute means
  the section is simply not rendered by consumers.
- `param_interactions` is optional and expected to be sparse. Its keys
  must be a subset of `param_descriptions` keys.
- The rule "descriptions are context-free" applies to class docstring,
  `param_descriptions`, `update_<attr>` docstrings, `disambiguation`, and
  `pitfalls` — none of these should say "click", "button", "instantiate",
  "import", or contain backticks / code samples. `interactions` is
  exempt because it is explicitly a Python-usage string.

## Shape of the content in e-footprint-interface

The interface's existing `class_ui_config.json` already holds per-class UI
metadata (labels, form options). It gains one optional new field:

```json
{
  "Server": {
    "label": "Server",
    "type_object_available": "Available server types",
    "interactions": "Add via {ui:infra_panel_add_button}, then drag {class:Job}s onto the card."
  }
}
```

No new file is created. `field_ui_config.json` could gain a per-field
`interactions` field later if a real need emerges; not created now to avoid
empty scaffolding.

## Placeholder syntax

Cross-references between domain concepts use the form `{kind:target}`. A
consumer registers a handler per kind and resolves placeholders at render
time.

| Token | Meaning | Resolved by |
|---|---|---|
| `{class:GPUServer}` | Linked display label for the class | mkdocs: `[GPU Server](GPUServer.md)`; interface: UI label + HTMX navigation |
| `{param:Server.power}` | Linked display label for a param of a class | mkdocs: in-page anchor; interface: scroll-to-field or tooltip |
| `{calc:Server.hourly_energy}` | Linked display label for a calculated attribute | mkdocs: in-page anchor; interface: result-panel reference |
| `{doc:methodology}` | Link to a hand-written explanation page | mkdocs: link to the `.md`; interface: opens help drawer or new tab |
| `{ui:infra_panel_add_button}` | Interface-only — reference to a UI element | interface: renders button name with optional highlight; mkdocs: no-op that renders target as italic plain text |

Rules:

- `{class:...}`, `{param:...}`, `{calc:...}` are usable anywhere.
- `{doc:...}` is usable anywhere but the target must exist on the consumer.
- `{ui:...}` is **only** allowed in interface-side strings
  (`class_ui_config.json` and anything else the interface owns). A test on
  the e-footprint side rejects `{ui:...}` and any unknown kind in library
  strings.
- An unknown `kind` anywhere is a test failure.
- A known kind with an unknown target is a test failure in the owning
  consumer (e-footprint tests for `class`/`param`/`calc`; interface tests
  for `ui`; mkdocs build for `doc`).

## The `DescriptionProvider` port

The interface's domain layer only ever sees a provider port. The adapter is
the only thing that knows which repo holds which content.

```python
class DescriptionProvider(Protocol):
    def class_description(self, name: str) -> str: ...
    def param_description(self, name: str, param: str) -> str: ...
    def calc_description(self, name: str, attr: str) -> str: ...
    def disambiguation(self, name: str) -> str | None: ...
    def pitfalls(self, name: str) -> str | None: ...
    def interactions(self, name: str) -> str | None: ...
```

Backing:

- `class_description`, `param_description`, `calc_description`,
  `disambiguation`, `pitfalls` read directly from the efootprint class via
  introspection.
- `interactions` reads from the interface's `class_ui_config.json`.

All methods return **placeholder-resolved** strings. The interface resolver
handles `class`, `param`, `calc`, `doc`, `ui`. Templates render the results
verbatim — they never see raw `{kind:target}` tokens.

The mkdocs generator uses a near-identical shape (a small provider imported
directly from e-footprint, with its own resolver that handles
`class`/`param`/`calc`/`doc` and treats `ui` as a no-op italic).

## Tests

### In e-footprint

A single `tests/test_descriptions.py` walks `ALL_EFOOTPRINT_CLASSES`:

1. Every concrete class has a non-empty `__doc__`.
2. `param_descriptions` keys exactly match `__init__` params minus `self`
   and `name`.
3. Every entry in `calculated_attributes` has a corresponding
   `update_<attr>` method whose `__doc__` is non-empty.
4. If `param_interactions` exists, its keys are a subset of
   `param_descriptions` keys.
5. Every `{kind:target}` placeholder in docstrings, `param_descriptions`,
   `update_<attr>` docstrings, `interactions`, `disambiguation`,
   `pitfalls`, and `param_interactions` resolves:
   - `class:X` → `X` exists in `ALL_EFOOTPRINT_CLASSES`.
   - `param:X.y` → class `X` exists and `y` is one of its init params.
   - `calc:X.y` → class `X` exists and `y` is in its `calculated_attributes`.
6. Unknown `kind` outside `{class, param, calc, doc}` in library strings is
   a failure. `{ui:...}` specifically rejected on the library side.
7. Banned-word / character check on context-free strings (class docstring,
   `param_descriptions`, `update_<attr>` docstrings, `disambiguation`,
   `pitfalls`): `click`, `button`, `instantiate`, `import`, backtick. Not
   applied to `interactions` or `param_interactions`. Tunable list.

### In e-footprint-interface

A test walks `class_ui_config.json`:

1. Every class key exists in `ALL_EFOOTPRINT_CLASSES`.
2. Every placeholder in the new `interactions` field resolves against the
   interface's own resolver (`class`, `param`, `calc`, `doc`, `ui`).
3. Every `{ui:target}` resolves to a registered UI element token.
4. A `DescriptionProvider` round-trip test constructs the provider, calls
   each method on a representative class, and asserts non-None for the
   fields that should be present.

### In mkdocs build

The build step runs the object reference generator, which now reads
descriptions and resolves placeholders. Missing resolutions fail the build.
The mkdocs build should be part of CI (covered in topic 5).

## Residual open points

- **`pitfalls` as single string vs list of strings.** Currently single
  string. Migrate to list only if writers actually want bullets.
- **Inheritance footgun.** `interactions`, `disambiguation`, `pitfalls` are
  class attributes and are inherited by subclasses. Usually fine
  (`GPUServer` inheriting `Server`'s pitfall can be correct) but sometimes
  wrong (the inherited text references `{class:Server}` when the child
  needs a different reference). No automated check catches this. Document
  the gotcha for now; add a test if it bites in practice.
- **Banned-word strictness.** Start as hard failures with a short list;
  relax to warnings or tune the list if too many false positives show up.
- **Should `{doc:...}` target validation happen in the e-footprint tests
  or only in the mkdocs build?** Leaning toward mkdocs build only, since
  mkdocs is the authoritative source for `doc:` targets. The interface
  only needs to know the URL to link to.

## Relationship to other topics

- **Topic 2 (e-footprint docs overhaul)** will consume these descriptions
  to fill the empty Explanation/How-to/Reference pages. The auto-generated
  reference gets richer content immediately.
- **Topic 3 (interface onboarding UX)** will use the interface-side
  `interactions` field and `{ui:...}` placeholders to drive tour steps
  and contextual help. The onboarding text itself is a consumer of the
  same description layer.
- **Topic 5 (maintainability and build)** codifies the tests described
  here as part of CI.
