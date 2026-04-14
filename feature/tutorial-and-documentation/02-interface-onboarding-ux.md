# Topic 2 — Interface onboarding UX

First-run experience for the e-footprint-interface. Covers who we are
onboarding, how they land, what they see, and how the interface teaches
itself as they use it. Self-contained so the exploration can resume cold
from this file alone.

---

## Audience

- **Primary:** the non-technical product person. Must be usable with zero
  Python, zero modeling background. Tone, vocabulary, and defaults are
  tuned for this user first.
- **Secondary:** technical users (engineers, e-footprint owners). They
  should very quickly sense that depth and customization exist beneath
  the surface, and be able to drop into it without friction.
- **Guiding principle:** no one left behind, depth available on demand.
  e-footprint aims to be a tool every profile in a product team can use.

The audience decision rules out wizard-style onboarding (feels
bureaucratic, teaches one rigid procedure, ages badly) and rules out
Python-first framing in any first-run copy.

---

## Primary mode

Three layers, stacked:

1. **Starter template (substrate).** The user lands on a picker and
   chooses a pre-loaded, working tiny system to mutate. Several
   templates cover different shapes of digital service (see below).
   "Start from scratch / blank model" is a first-class option in the
   picker, not hidden.
2. **Guided tour (first-run overlay).** A short, dismissible tour
   pointing at the real interface, explaining where things live, where
   contextual help is, and the recommended order to model in. Two
   flavors (template tour vs blank tour) — see below.
3. **Contextual help (long tail).** Info icons on every field, a help
   drawer, tooltips on disabled buttons, deep-links into mkdocs for
   longer-form explanations. This is what users fall back to after the
   tour is dismissed.

Explicitly **not** in the onboarding mix:
- No step-by-step wizard (replacement flow that owns the screen).
- No videos (per top-level constraint — too hard to keep up to date).

---

## Starter templates

Several templates are offered. Each is a real, mutable system the user
can tweak immediately. Initial set:

- **Classical e-commerce** — canonical web service shape, good default
  for most product people.
- **AI chatbot** — showcases LLM-style workloads and the modeling of
  inference-heavy services.
- **Industrial setup with IoT** — showcases edge modeling in context.
  This is where edge concepts are introduced organically, without an
  up-front "web or edge?" prompt.
- **Blank / start from scratch** — first-class option for users who
  already know what they want to model.

Introducing edge through the IoT template (rather than as a separate
mode selector) is a deliberate decision and feeds directly into Topic 3
(web vs edge modeling).

### Storage

Naming note: both the library and the interface use the term
**"modeling template"** for a runnable example scenario. See Topic 4
for the full scheme. For the introductory templates specifically:

- Each introductory template is a serialized `System` JSON under
  `model_builder/domain/reference_data/modeling_templates/introductory/`,
  e.g. `ecommerce.json`, `ai_chatbot.json`, `iot_industrial.json`.
  Loaded by the same mechanism that loads default system data today.
- A Python registry at
  `model_builder/domain/reference_data/modeling_templates/introductory/registry.py`
  holds per-template metadata: display name, short description, icon,
  showcased concepts (list of tokens), optional extra tags, and the
  path to the system JSON. Keeps each JSON a pure, loadable system
  snapshot without polluting it with UI-only metadata.
- The template picker additionally surfaces **how-to modeling
  templates** imported from the library via
  `efootprint.modeling_templates.list_how_to_templates` (owned by
  the library, shipped with the package), and **other modeling
  templates** from a sibling interface registry. Introductory
  templates appear on first-run; the full browser (accessible from
  the help menu) merges all three categories. See Topic 4 for the
  full ownership split and discovery mechanism.

---

## Guided tour

Two flavors, same interface-orientation content, different anchoring:

- **Template tour.** Overlaid on the pre-loaded system from the chosen
  template. Points at the concrete cards and panels the user can
  already see.
- **Blank tour.** For users who picked "start from scratch". Same
  content but without a pre-filled system — uses placeholders, empty
  columns, and a concrete suggestion of the first thing to create.

### Scope of both tours

- Interface orientation: where servers live, where usage journeys live,
  where usage patterns live, where results appear, where contextual
  help lives.
- Recommended **modeling order**: start in the middle (usage journey
  column) → then infrastructure → then usage patterns. Results become
  available once the model is complete. The tour makes this order
  explicit; the disabled-button UX (see below) reinforces it implicitly.
- Contextual-help discoverability: the tour shows where the info icons
  are and how to open the help drawer.

### Out of scope for the tour

- Domain explanations of what a usage pattern *is*, why servers have
  jobs, etc. These live in **contextual help** (info icons, drawer
  content) and **mkdocs deep-links**, not in the tour itself. The tour
  teaches the *map*; the contextual help teaches the *concepts*.

### Persistence and replay

- Auto-run only on first-ever visit. Tracked in user profile when
  logged in, localStorage as fallback when not.
- **Replay entry point** in a help menu, so a user can re-watch the
  tour any time.
- **Templates entry point** in the same help menu, so a user can
  re-open the template picker mid-session to start over or try a
  different template.

---

## Disabled-instead-of-error UX (cross-cutting)

Current state: the interface raises errors after the fact when a user
tries to do something that isn't yet valid — e.g. adding a job when no
server exists, requesting results when the model is incomplete, adding
an edge usage pattern when no edge usage journey exists. This is
punitive and a poor teaching experience for the target audience.

Target state: such buttons are **preemptively disabled** and carry a
hover tooltip explaining *why* they are disabled and what the user
needs to do to enable them.

This is not an onboarding-only concern — it is a general UX principle
that affects the whole model_builder. It deserves its own phase in the
implementation plan and may require a small refactor (see below).

### Where the logic already lives

- **Model completeness** → `SystemValidationService` already exists
  (referenced in `model_web.py`). Drives the "Get results" button
  state. Reuse as-is.
- **Per-action preconditions** → already encoded on web classes as
  `get_creation_prerequisites`. Today this lives on at least:
  - `model_builder/domain/entities/web_core/usage/job_web.py`
  - `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py`
  - `model_builder/domain/entities/web_core/usage/edge/recurrent_server_web.py`
  - `model_builder/domain/entities/web_core/usage/edge/recurrent_edge_device_need_base_web.py`
  - `model_builder/domain/entities/web_core/hardware/edge/edge_device_group_web.py`
  - plus call sites in
    `model_builder/adapters/forms/form_context_builder.py`,
    `model_builder/adapters/forms/strategies/simple.py`,
    `model_builder/adapters/forms/strategies/parent_selection.py`.

### Refactor required

Today `get_creation_prerequisites` is invoked inside the creation path
and effectively raises at creation time. For disabled-button UX, the
same logic must be **queryable ahead of time** to produce, for any
action button, a pair `(enabled: bool, disabled_reason: str)` that the
presenter/template layer can render as button state + tooltip.

Rough shape (not a commitment):
- Expose a predicate form on each web class, e.g.
  `cls.can_create(model) -> (bool, reason)`, backed by the existing
  prerequisites logic — a single source of truth, queried two ways.
- Presenter calls the predicate when rendering action buttons; the
  creation use case still enforces the same check as a last line of
  defense (so the two consumer sites can't diverge).
- Existing tests that assert the raising behavior shift to (or are
  paired with) tests asserting the predicate form.

This refactor is flagged as a **prerequisite** for the disabled-button
UX, not a side effect of onboarding. It should land before or
alongside onboarding phase work.

---

## Decisions locked in

- Audience: non-technical product person primary, technical users
  secondary, depth on demand.
- Primary mode: starter template + guided tour + contextual help. No
  wizard, no video.
- Template picker with blank as a first-class option. Multiple
  templates: e-commerce, AI chatbot, IoT (edge).
- Native interface-first scenarios; no alignment with
  `e-footprint/tutorial.ipynb`. The notebook remains as a Python-only path
  and is out of scope for this overhaul.
- Introductory templates stored as serialized `System` JSONs under
  `model_builder/domain/reference_data/modeling_templates/introductory/`,
  with a sibling `registry.py` for per-template metadata. See Topic 4 for
  the full three-category template scheme.
- Two tour flavors (template, blank). Scope: interface map +
  contextual-help discoverability + recommended modeling order.
- Domain explanations stay in contextual help / mkdocs, not in the
  tour.
- Auto-run only on first-ever visit; replay + templates entry points
  in a help menu.
- Disabled-instead-of-error UX as a cross-cutting principle, reusing
  `SystemValidationService` and a refactored predicate form of
  `get_creation_prerequisites`.

---

## Open questions

- **Help menu placement.** Where does the help menu with "replay tour"
  and "open templates" live in the current layout? Navbar, floating
  button, side panel?
- **Contextual help content source.** Info-icon text and help-drawer
  content should be fed from the Topic 1 SSOT plumbing (class
  docstrings, `param_descriptions`, `interactions`, etc.) via the
  `DescriptionProvider` port. Confirm no new parallel content store is
  introduced for onboarding copy.
- **Tour copy authoring.** Where does the tour's own step content
  live? Likely a small JSON or Python module on the interface side,
  since the tour is interface-specific and not derivable from library
  classes. Should it use the `{kind:target}` placeholder syntax from
  Topic 1 so it can reference classes and UI elements by stable token?
- **Template "showcased concepts".** The manifest lists showcased
  concepts per template — are these free-form strings, or tokens that
  resolve via the placeholder registry to canonical class/concept
  names? The latter is more maintainable.
- **Blank-tour first suggestion.** What does the blank tour suggest as
  the first concrete action? Probably "create a usage journey" to
  match the recommended modeling order, but worth confirming.
- **Analytics / telemetry.** Do we want to know whether users complete
  the tour, which template they pick, where they drop off? Out of
  scope unless the project already has a telemetry story.
- **Multi-language.** Topic 1 decided English-only for library-side
  strings. Confirm the same for onboarding copy.

---

## How this topic connects to the others

- **Topic 1 (SSOT).** Onboarding consumes description content via the
  `DescriptionProvider` port. Info icons, help drawer, and tooltip
  text for disabled buttons all pull from there. No parallel content
  store.
- **Topic 3 (web vs edge).** Edge is introduced through the IoT
  starter template rather than an up-front mode selector. The
  recommended modeling order applies identically to edge and web.
- **Topic 4 (e-footprint docs overhaul).** Contextual help deep-links
  into mkdocs pages for longer-form explanations — which means the
  mkdocs pages those links point at must actually exist and be
  maintained. Topic 4 needs to deliver those targets.
- **Topic 5 (maintainability and build).** The disabled-button
  predicates, the template JSONs, and the manifest all need tests and
  CI checks so they stay honest as the codebase evolves.
