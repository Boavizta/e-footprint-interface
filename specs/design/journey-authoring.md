# Authoring a journey HTML doc

> How to write a `specs/design/journeys/<name>.html` that is **faithful to the deployed app** and consistent with the others. [`journeys/build-a-model.html`](journeys/build-a-model.html) is the **reference implementation** — copy its `<style>` block and mirror its structure.

A journey doc is a self-contained HTML file: a user-facing flow shown as a sequence of simplified-but-faithful **desktop browser-window mocks**, each sitting next to the narrative and the states that change it. It is **intent-level + UI-faithful** — what the user does and what they see, not how the code is wired.

---

## Ground every screen in the real app

The spec states *intent*; the deployed app is the *truth*, and a journey must match what actually ships — the labels, the screen order, which affordances are live. Specs lag code: a flow the spec frames as one step may be two screens, an affordance it describes may be deferred, a default it implies may be the opposite. So read the real template, its view, and the presenter before drawing a screen, and trust the code over the prose.

Method:

1. **Find the route** in `e_footprint_interface/urls.py` / `model_builder/urls.py` and the **view** that handles it (`model_builder/adapters/views/*.py`).
2. **Read the template it renders** (`model_builder/templates/model_builder/...`) **and the presenter** (`adapters/presenters/htmx_presenter.py`) — the real labels, the OOB regions, the branches live there.
3. **Trace the HTMX flow**: what does each `hx-get` / `hx-post` target and swap? A "save" that returns OOB fragments patches several regions at once — that's one screen with several visible effects, not several screens.
4. **Copy exact strings** — button labels, panel headers, modal copy, tooltip/toast text — from the templates and from `adapters/ui_config/` (e.g. `constraint_messages.py`). Don't paraphrase. Many user-facing strings are built in the presenter or use-case — grep for them.
5. When unsure about a behavior, grep the template/view rather than infer from the spec.

Start from `specs/architecture.md` — it maps the layers (views, presenters, render layer) and the named patterns (OOB regions, creation constraints, dict relationships, the edge toggle), so it usually points straight at the file you need.

---

## Visual template — copy, don't reinvent

`journeys/build-a-model.html` carries the canonical `<style>` block. **Copy it verbatim** into the new file; it's the shared CSS toolkit, with the app palette baked in as CSS vars. Page anatomy, in order:

1. `.crumb` — `← Design hub · journeys`
2. `<h1>`, optionally a `.role` pill — only when a journey is scoped to one audience/paradigm. `build-a-model` spans both web and edge, so it carries none; use `.role` (or `.role.edge`) only if a future journey is genuinely paradigm-specific.
3. `.lede` — who & why, 2–3 sentences. Success = the real outcome (a complete, computable model — not "an object created").
4. `.note` — **provenance**: the real template / view / presenter files this draws from + the spec sections.
5. `.phase` dividers grouping screens — **named to match the real flow** (Add an object, Edit, Delete), not abstract phases.
6. Per-screen **blended units** (see below).
7. Collapsible `<details class="fold">` for asides/branches (`.s-tag.alt` ↩ Alt, `.s-tag.danger` for blocked paths) and a wide `details.fold.zoomfold` for a mechanism deep-dive (collapsed by default).
8. `Decisions taken` table — cross-cutting why-not-X, at the functional level (the *reasoning*, not the files).
9. `details.ptr` — **Implementation pointers (for agents)**: the file/route/mechanism map, collapsed and low-emphasis.
10. `<footer>`.

### The per-screen unit (the core pattern)

One `.screen` = two columns, blending sequence / mock / states into one place, for locality:

```
.screen
├─ .mock-col        430px browser-window mock  +  .mock-help caption ("On this screen …")
└─ .info-col        .step (number + title) · narrative <p> · .states grid
```

`.states` lists **only the states relevant to that screen** (`.state` with a `.k` label + `.v` value; `.state.variant` for an alternate/edge mode, in purple; `.state.deferred` for not-yet-built / out-of-scope, in grey). No global "key states" section — each state lives next to the screen it changes.

### The browser-window mock

The mock unit is `.win` — a desktop browser window (titlebar + URL chip) wrapping the app chrome, because this is a **desktop-first** app (see `mission.md`). Inside the window, build only what the screen needs from the chrome:

- `.appbar` — the model **tab strip** (`.tab.active` "Reference model", `.tab.add` "＋ Add ▾", `.tab.compare.disabled` "⇄ Compare") + the per-model `.toolbar` (open / export / reset `.tbtn`s and the `.edgetoggle`).
- `.stage` — the workspace, `position:relative` so a panel/modal can dock over it.
- `.canvas` with three `.col`s (Usage patterns · Usage journeys · Infrastructure), each with `<h5>`, `.addbtn`s, and `.ocard` object cards. Add `.canvas.dim` behind a panel/modal.
- `.panel` — the right-docked side panel for add/edit forms (dock it over a dimmed canvas).
- `.modal-mock` > `.dialog` — centered confirm/can't-delete dialogs.
- `.resultsbar` (`.locked` when the model isn't computable) and a transient `.toast-mock`.

Simplified but faithful: real structure, real copy, app palette; never pixel-perfect. One window per screen.

---

## Conventions

| Rule | Detail |
|---|---|
| **Centered, not full-bleed** | `body { max-width: 70rem; margin: 0 auto }`. |
| **One window per screen** | 430px `.win`. Show only the chrome the screen needs. |
| **App-faithful palette** | Primary **navy `--new-primary #2D4675`**, `--new-light-primary #e8eaf4`, the `--gray-50…500` ramp, edge accent **`#7B5DC7`**, danger `#dc2626`. All as CSS vars in the template; values taken from `theme/static/scss/custom.scss`. |
| **Help beside the window** | The `.mock-help` "On this screen" caption sits **below** the window — never overlaid on the screen content. |
| **Real strings** | Button labels, panel headers, modal/tooltip/toast copy are copied from the templates / presenter / `ui_config`, not paraphrased. |
| **Disabled-not-errored is the spine** | The app's defining rule: an impossible action is disabled with a tooltip reason, never offered then rejected. Show the gated state (locked add button + `.lock-tip`, dimmed `.resultsbar`) wherever it's part of the flow. |
| **Branches stay in place, de-emphasized** | An alternate / blocked path is a collapsed `<details class="fold">` placed **where it belongs in the flow**, not appended at the end. |
| **Zoom a mechanism, don't park implementation** | A `details.fold.zoomfold` that **breaks out wide when open** for a cross-cutting mechanism (e.g. how OOB regions patch the canvas). Collapsed by default. |
| **Lean & functional in the body** | The main flow is for people: narrative, states, and decisions stay at the **functionality + pattern** level. Keep prose tight and let the mocks carry the load — a journey is meant to be *seen*, not read like a spec. |
| **Code-level detail is collapsed, for agents** | File names, routes, function names, mechanism tables — useful to agents, noise to people. Strip them from the body and collect them in one **low-emphasis collapsed `details.ptr`** ("Implementation pointers — for agents") at the foot, organised by area. Link to it once from the top note. Don't sprinkle `(file.py)` citations through the states. |
| **Stay at altitude** | Beyond the pointers fold, exclude the implementation parking-lot — migration numbers, repository internals, exhaustive prop lists. That's `plan.html` / `architecture.md` territory. |

### Class vocabulary (full set in `build-a-model.html`)

- **Layout:** `.screen`, `.mock-col`, `.info-col`, `.phase`(`.alt`), `.step .n`(`.alt`)
- **Info:** `.states` / `.state`(`.variant` purple, `.deferred` grey), `.mock-help`(`.edge`) + `.lbl`
- **Window shell:** `.win`(`.titlebar`/`.dots`/`.url`), `.appbar`, `.tabs`/`.tab`(`.active`/`.add`/`.compare`/`.disabled`), `.toolbar`/`.tbtn`, `.edgetoggle`(`.on`)
- **Canvas:** `.stage`, `.canvas`(`.dim`), `.col`(`.edgecol`), `.addbtn`(`.locked`/`.edge`), `.lock-tip`, `.ocard`(`.opened`/`.fresh`, `.ic`/`.pencil`)
- **Side panel:** `.panel`, `.phead`(`.x`/`.trash`), `.field`(`.qty` with `.row`/`.unit`, `.inp`), `select.dd` (real dropdowns — unit / type / object pickers, with a CSS chevron; never a fake `▾` span), `.accsec`(`.h`/`.b`), `.advtoggle`, `.helptxt`, `.dictsec`, `.calcsec`, `.savebtn`
- **Relationship widgets:** `.cmp`/`.cmpcol`(+`.ttl`/`.kind`), `.pcard`, `.flabel`(`.w`/`.w.web`), `.hint`, `.selrow` + `select.dd` + `.plus-btn` (or `.btn-mini` for a labeled add), `.dicttable` + `.drow`(`.sub`, `.nm`/`.cnt`/`.sort`/`.rm`), `.designnote` — list links and weighted dicts share the `.dicttable`/`.drow` row widget (label · `.sort` ↑↓ · `.rm` ×); the dict just adds the `.cnt` column. The reverse-membership panel (child managing its parents) reuses the same `.pcard`/`.dicttable`/`.drow` with a `.btn-mini` "Add to {parent}".
- **Modal:** `.modal-mock`, `.dialog`(`.warn`/`.msg`/`.sub`/`.acts` with `.del`/`.back`/`.ok`)
- **Chrome bits:** `.resultsbar`(`.locked`), `.toast-mock`
- **Folds:** `details.fold`(`.zoomfold`), `summary` + `.s-tag`(`.alt`/`.danger`)/`.s-sub`, `.fold-body`; `details.ptr` (low-emphasis "for agents" pointer fold) + `.a-tag` + `.pbody`(with `dl`/`dt`/`dd`)

Reuse these first; only add a class when a genuinely new UI element appears, and keep it in the file's `<style>`.

---

## Checklist

1. Read the spec sections (or the live `.md` specs) for **who/why** and the **decisions** (the why-not-X calls).
2. Read the **real templates + views + presenter**; trace the HTMX flow; write down the **true screen order**.
3. Copy `build-a-model.html`'s `<style>`; build the per-screen units.
4. Pull **exact strings** from the templates / presenter / `ui_config` into the mocks.
5. Collapse asides/zooms; place branches where they belong in the flow.
6. Write the `Decisions taken` table at the functional level; move all file/route/mechanism detail into the collapsed `details.ptr` "Implementation pointers" fold at the foot, and strip inline `(file.py)` citations from the body.
7. **Render & verify**: open `file://…/<name>.html` in a browser, full-page screenshot. Check: centered; captions below (not over) the window; folds collapsed by default and the zoom breaks out when open; panel docks cleanly over the dimmed canvas; no overlap; real copy.
8. Wire it into `index.html` — change the journey card from `.card.inert` (no link) to `<a class="card" href="journeys/<name>.html">`, drop its `.ord` build-order chip and `To author` pill, and keep only the `Web` / `Edge` paradigm pill. An authored journey is a clickable card carrying just its paradigm; a `To author` pill now signals the exception — not yet built.

---

**Pattern — one journey for a paradigm seam, not two.** The web/edge toggle changes which objects exist and which canvas sections show, but the add/edit/delete loop, side panel, OOB patches and gate are identical. So `build-a-model` is **one** journey covering both: the A–D screens carry the web case with `.state.variant` rows for the edge differences inline, and a single late phase (**Phase E**) shows the toggle revealing the edge object types. Don't split a paradigm that shares its whole loop into a second journey — the copies drift. Spin a journey off only when the flow genuinely differs, not when only the object palette does.

**Pattern — unify shared mechanics into one section.** When several features share one UX (here every relationship — single link, list link, weighted dict, nested edge group — shares the list / select-＋ / unlink widget family), give them a **single dedicated section** (`<h2 class="sec">`, with a `.cmp` row of side-by-side `.pcard` mocks + a mechanics table) instead of re-explaining the pattern at each screen where it appears. The flow screens then just point to it. `build-a-model`'s **Relationships** section is the reference for this shape.

**Pattern — the in-place OOB patch.** When one action (add / edit / delete) updates **several regions at once** (the changed card, a re-locked/unlocked add button, the edge toggle, a toast), render it as **one screen** showing all the effects together, and explain the mechanism in a collapsed `details.fold.zoomfold` rather than inflating the mainline. `oob_regions.py` / `htmx_presenter.py` are the files of record; `build-a-model.html`'s "One save, several patches" zoom is the reference for this shape.
