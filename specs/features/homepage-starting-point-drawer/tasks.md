# Home-page starting-point drawer — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

Three tasks. The first is a pure refactor with no behavioural change; the second and third are the
two user-visible deliveries. Each leaves the app in a working, shippable state.

---

## Task 1 — One card grid behind the picker, and the oversized description trimmed

**Status:** Done.

**Goal:** Extract the template-picker card markup into a shared partial that later surfaces can
reuse, and bring the GenAI marketing video description in line with its peers. Nothing about the
user's flow changes: the picker still auto-fires on an empty model and still looks the same, except
that one card is shorter. This is the foundation the next two tasks build on, landed separately so
the refactor can be reviewed without the feature on top of it.

**Files touched:**
- `model_builder/templates/model_builder/onboarding/_starting_point_cards.html` (new) — the card
  grid lifted out of the picker, parameterised by `groups`, chips/guides visibility, grid columns,
  and whether the cards are rendered outside the builder.
- `model_builder/templates/model_builder/onboarding/template_picker.html` — grid replaced by an
  include; comment block rewritten (it stops describing itself as the *first-run* picker).
- `model_builder/domain/reference_data/modeling_templates/introductory/registry.py` — the
  `genai_video` entry's `description` only, to:
  *"A marketing team generates a social-media video with AI video providers, then edits and
  publishes it."*

**Tests added/changed:**
- `tests/unit_tests/adapters/presenters/test_template_picker_presenter.py` — unchanged, must stay
  green; it is the signal that the catalog layer was not disturbed.
- `tests/integration/test_template_catalog_service.py` — unchanged, must stay green.
- No new test for the partial itself: it has no logic, and Task 2 and Task 3 exercise it through
  the surfaces that include it.

**Acceptance:**
- The in-builder picker renders exactly as before — same groups, order, chips, guide links, dashed
  scratch/upload cards — with its grid now coming from the partial.
- The GenAI card's description is 101 characters, in line with its peers (54–99), and the change
  appears wherever that template is listed, since there is one source.
- `git diff` on `template_picker.html` shows markup *moved*, not rewritten. Divergence here defeats
  the purpose of the extraction.
- Full `pytest` and `npm run jest` green.

**Depends on:** none.

---

## Task 2 — Templates visible on the home page

**Goal:** The first user-visible delivery, and the one that carries the feature's whole point: a
visitor who loads the home page and scrolls can read every template without clicking anything, and
one click loads it. "Start modeling" is untouched in this task — it still goes to the builder, and
the canvas overlay still greets an empty model, so the existing flow stays intact for anyone who
does not use the band.

**Files touched:**
- `model_builder/adapters/presenters/starting_point_presenter.py` (new) — assembles the catalog
  groups, the band's `templates` group, the resume model's name, and the server-side emptiness flag.
  Imports no view module, which is what keeps `e_footprint_interface.views → views_onboarding →
  model_builder…views` from closing into a cycle. Reads the session **read-only** and short-circuits
  on a session-less visitor, so a home-page visit never mints a session.
- `e_footprint_interface/views.py::home` — module-level import of the presenter; passes its context.
- `theme/templates/home.html` — the "Start from a template" band directly under the hero, including
  the shared partial with chips on. Everything below the hero keeps its order.
- `theme/static/scripts/model_builder_main.js` — extend the emptiness resolution in the delegated
  `htmx:confirm` listener: canvas cards when present (unchanged on the builder), otherwise the
  server-set flag. This is the mechanism `conventions.md` mandates; do **not** add an `hx-confirm`.

**Tests added/changed:**
- `tests/integration/` (new) — `GET /` renders all five templates by name; creates **no** session
  for an anonymous visitor; a band card POSTs to `load-template` and lands the builder.
- `js_tests/` (new) — the extended confirm listener: prompts when the server flag says non-empty and
  no cards are present; prompts when cards are present regardless of the flag; stays silent when
  both say empty.
- `tests/e2e/test_onboarding.py` — a case covering "templates readable without clicking" and
  "clicking one lands a filled canvas".

**Acceptance:**
- Loading the home page and scrolling shows all five templates with name, description and chips.
  No click, no network request beyond the page itself.
- Clicking a band card on an empty session loads that model and lands on the filled canvas at
  `/model_builder/`, with no intermediate picker.
- Clicking a band card while a model is in session prompts before replacing it; cancelling leaves
  the model untouched. **This assertion is the point of the task** — the confirmation is the one
  thing that can silently lose a visitor's work.
- `GET /` on a fresh browser leaves `django_session` empty.
- Full `pytest` and `npm run jest` green.

**Depends on:** Task 1.

---

## Task 3 — The drawer, and retiring the welcome overlay

**Goal:** The second user-visible delivery: "Start modeling" opens the starting-point drawer over
the home page instead of navigating, and the canvas stops greeting an empty model with the overlay.
These two land together on purpose — the drawer without the retirement asks the visitor the same
question twice, and the retirement without the drawer leaves the CTA with no way to choose.

**Files touched:**
- `model_builder/templates/model_builder/onboarding/starting_point_drawer.html` (new) — dialog
  semantics (`role="dialog"`, `aria-modal`, labelled heading), the optional "Continue where you left
  off" block, then the shared partial.
- `model_builder/adapters/views/views_onboarding.py` — `starting_point_drawer(request)` returning
  the fragment, plus the upload hand-off: "Load a json file" has no `#sidePanel` to target from the
  home page, so land on the builder and ask it to open the panel via `HX-Trigger-After-Settle`,
  mirroring the existing `initModelBuilderMain` trigger. No inline JS.
- `model_builder/urls.py` — the drawer route, in the `model_builder` namespace beside
  `load-template`.
- `theme/templates/home.html` — CTA becomes `hx-get` → the drawer with **no** `hx-push-url`; drawer
  mount point and backdrop; "Other ways to start →" link.
- `theme/static/scripts/starting_point_drawer.js` (new) + `theme/templates/base.html` — open/close,
  backdrop, <kbd>Esc</kbd>, focus trap, focus restored to the opener. IIFE, nothing on `window`,
  dispatching via `data-action` on **both** open and close (not a URL-matching selector).
- `model_builder/adapters/views/views.py::model_builder_main` — `show_template_picker=False`.
  `is_empty_model` keeps its other two jobs (the `model_is_empty` flag, the blank-flavoured tour).
- `theme/static/scripts/onboarding_first_run.js` — its `#template-picker` deferral guard was written
  for the auto-overlay. Keep it for the Help-menu path, but re-read the comment and the
  `htmx:afterSettle` target matching: entry now arrives from a `load-template` POST.
- `theme/static/scss/` — only if the slide-in and backdrop need rules Bootstrap utilities cannot
  express. Never edit `bs_main.css` by hand.
- `specs/architecture.md` → the "First-run template picker" section, which documents the auto-overlay
  as the entry point. The heading loses "first-run".
- `specs/design/journeys/onboarding.html` — screens A·1 and A·2 and the implementation-pointers
  footer all describe the old flow.

**Tests added/changed:**
- `tests/integration/` — the drawer endpoint returns the resume block only when the session model is
  non-empty; `GET /model_builder/` on an empty session renders **no** `#template-picker`;
  `open-template-picker` still does.
- `js_tests/` — `starting_point_drawer.js`: open, close by backdrop, close by Esc, focus restored.
- `tests/e2e/test_onboarding.py` — the main rewrite. CTA opens the drawer with the URL unchanged;
  Esc and backdrop dismiss to an untouched home page; a returning session shows "Continue where you
  left off" first; the canvas never shows the overlay on entry; the guided tour still auto-runs once
  on a loaded canvas. Check `tests/e2e/pages/model_builder_page.py` and `tests/e2e/conftest.py` for
  picker helpers other suites lean on (`test_forms.py` uses them) before changing signatures.

**Acceptance:**
- Clicking "Start modeling" opens the drawer in place; the address bar does not move until a choice
  is made. Esc, the backdrop and the close control each return the page untouched, nothing loaded.
- A returning visitor sees "Continue where you left off" first, naming their model.
- "Load a json file" from the home page opens the import panel on the builder, with no inline JS in
  the markup.
- Reaching the canvas from the home page never shows the welcome overlay; Help ▸ Open templates and
  a model reset still do.
- The guided tour still auto-runs exactly once on a loaded canvas — the prototype confirmed this
  survives, but it is entangled with the picker's presence, so it needs an explicit assertion.
- The drawer is operable by keyboard alone and traps focus while open.
- Full `pytest` (including e2e) and `npm run jest` green.

**Depends on:** Task 2.

---

## Ordering rationale

**Why three and not six.** The atomic units here are many — a partial, a presenter, two templates, a
view, a route, two JS modules, a one-line view change, a one-field catalog edit, three test layers
and two docs pages — but they collapse into three review-sized commits at the points where the app's
*behaviour* actually changes.

**Task 1 is split out because it is invisible.** Extracting the card grid touches the markup every
later surface depends on, and a reviewer can check "this moved, it did not change" against a picker
that still behaves exactly as before. Bundled into Task 2, that signal would be lost in a diff that
also introduces a presenter, a band and a confirmation change. The description trim rides along
rather than becoming a trivial fourth task — it is one field, and it is the same kind of change
(what the cards say, not how the app flows).

**Task 2 keeps the presenter, its first consumer and the confirmation extension together.** The
presenter with no page to render it is infrastructure landed unused, and the confirmation change is
meaningless until something outside the builder can replace a model — these have no behavioural pause
point between them. Splitting at the layer boundary (presenter / template / JS) would create three
reviews of one delivery.

**Task 3 is the largest, and cannot be usefully split.** The drawer and the overlay's retirement are
a single behavioural change viewed from two sides: ship the drawer alone and the visitor is asked
where to start twice; ship the retirement alone and the CTA leads to a canvas with no way to choose.
The upload hand-off is in scope for the same reason — the drawer offers "Load a json file", so the
drawer is not complete without it working. Docs land here because this is where the architecture
actually changes.

**Tests travel with the code that needs them** rather than collecting in a final task. A "tests and
docs" task at the end would leave Tasks 2 and 3 shippable-but-unverified, which the constitution's
quality gates do not allow.

**CHANGELOG.** Per constitution §2.6, a task run standalone via `task-implement` adds its own entry;
run as a `feature-implement` loop, the supervisor writes one consolidated entry at the end.

**Out of the task list, into the review:** the plan's §7 still carries two open implementation
details — what element carries the server-set emptiness flag (Task 2 decides it) and whether the
upload hand-off reuses the existing side-panel route or warrants its own (Task 3 decides it). Both
are small enough to settle during implementation rather than blocking the task breakdown.
