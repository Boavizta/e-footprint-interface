# Topic 3 — Web vs edge modeling

Clarifying what "edge" means in e-footprint, why it was not obvious, and
how both the library docs and the interface should surface it so users
can discover it without being overwhelmed by it. Self-contained so the
exploration can resume cold from this file alone.

---

## The mental model (canonical)

e-footprint has two paradigms for sizing environmental impact. They
differ in what drives the model:

- **Web (demand-driven).** Historical default. A *centralized*
  infrastructure (servers, storage, network) must **adapt to external
  usage**. Usage is described as hourly demand — how many people click,
  how many requests per hour, how many usage journeys start per hour.
  Infrastructure is sized by that demand. The direction of causality
  is **usage → infrastructure**.
- **Edge (deployment-driven).** Introduced later. Impact comes from
  the **deployment of units** (IoT devices, sensors, industrial PCs,
  and more generally any decentralized hardware — could be smartphones
  or servers from the perspective of their manufacturers). Usage is
  described **per unit deployed**, with a recurrent resource
  consumption pattern on each edge device. The direction of causality
  is **number of units × per-unit behaviour → impact**.

Put bluntly: in the web case, infrastructure depends on usage; in the
edge case, usage depends on number of units deployed.

### Where the two paradigms meet

They are not mutually exclusive. A fleet of deployed edge devices can
call web servers during its operation. The bridge is
`RecurrentServerNeed`:

- Each `RecurrentServerNeed` is attached to an `EdgeDevice` and holds a
  `recurrent_volume_per_edge_device` as a 168-hour weekly pattern
  (`ExplainableRecurrentQuantities`).
- It references `jobs: List[JobBase]` — the same `Job` objects used on
  the web side.
- At calculation time, the recurrent per-unit volume is multiplied by
  the number of units deployed to produce the hourly demand those jobs
  impose on the web infrastructure.

So industrial users can legitimately model a mixed system: deployed
hardware with its own fabrication/usage footprint, plus the web-side
services that fleet calls home to.

### Anchors in the code (for future readers)

The mental model above is not derived from vibes — it is what the
classes already encode:

- `EdgeUsagePattern.hourly_edge_usage_journey_starts` is the hourly
  rate of **device come-online events**, not user clicks.
- `EdgeUsageJourney.usage_span` defaults to **6 years** — it represents
  a deployed unit's lifetime, not a session length. Compare to the web
  `UsageJourney`, which measures "a visit."
- `EdgeDeviceGroup` with nested `sub_group_counts` and
  `edge_device_counts` is an explicit fleet-hierarchy abstraction (root
  groups, sub-groups, effective counts within root).
- `RecurrentServerNeed.recurrent_volume_per_edge_device` is the
  per-unit weekly recurrent pattern; the class holds
  `jobs: List[JobBase]` as the bridge into the web side.

---

## Typical audiences

- **Web-app product teams** (e.g. an e-commerce or SaaS product team).
  Will very likely never touch the edge subsystem. They benefit from
  edge being *out of the way* by default, but should still be able to
  discover it if a use case appears.
- **Industrial users** (e.g. Schneider Electric-style deployments).
  Will build complex mixed models with both edge and web. They need
  the edge subsystem to be fully accessible and for mixed models to
  remain readable.

The onboarding decision in Topic 2 (edge introduced *through* the IoT
starter template, not via an up-front mode selector) matches this
audience split: each audience meets edge at the right moment.

---

## Decisions

### Library-side (e-footprint)

- **No object hierarchy reorganization.** The current code
  organization — sibling `core/usage/edge/` and
  `core/hardware/edge/` sub-packages, with distinctly named classes
  (`EdgeUsageJourney` vs `UsageJourney`) — is fine as is. A shared
  base class (`UsageJourneyBase` or similar) was considered and
  rejected: the two paradigms differ enough (`usage_span` vs hourly
  inputs, recurrent vs demand-driven) that forcing a shared base
  would create awkward contortions with no real payoff. Explanation
  is the missing piece, not reorganization.
- **No mkdocs nav restructure.** The reference is already organized
  around core concepts (Hardware, Services, Usage, …) with Edge as
  a nested sub-bucket inside Hardware and Usage. The "two parallel
  subtrees" framing from earlier exploration notes was imprecise —
  that restructure already exists.
- **Add a canonical Explanation page** `web_vs_edge.md` at the top of
  the Explanation section. One short page. Defines the two paradigms,
  explains when to use each, points at `RecurrentServerNeed` as the
  bridge. Intros of the Hardware/Edge and Usage/Edge reference
  sub-buckets deep-link to this page.
- **How-to guides** for concrete edge tasks live in the How-to
  section, not inside the Explanation page. Likely initial set:
  - "How to model a device fleet"
  - "How to bridge edge and web via RecurrentServerNeed"
  - (more as they become needed)

### Interface-side (e-footprint-interface)

- **Navbar toggle: "Edge modeling: off / on."**
  - **Off** → edge object types are absent from add-menus. The UI is
    focused on web modeling. This is the default for web-only
    templates (e-commerce, AI chatbot, blank).
  - **On** → edge object types appear in the add-menus alongside web
    ones. No separate column, no alternate view. The IoT starter
    template ships with the toggle already **on** because the loaded
    system contains edge objects from the start.
  - **Latched on** whenever the current model contains at least one
    edge object. The toggle cannot be flipped off in that state — it
    is disabled with a hover tooltip explaining why (consistent with
    Topic 2's "disabled-instead-of-error" principle).
  - **Tooltip** on the toggle: one-liner defining edge, with a
    deep-link to the canonical `web_vs_edge.md` Explanation page.
- **No separate column for edge.** Edge objects are intermixed with
  web ones in the existing columns (usage journeys, infrastructure,
  usage). Keeping the current layout avoids a large structural change
  and matches how mixed models already work in the library.
- **Subtle badges** on edge object cards (small icon or coloured dot)
  so industrial users working on mixed models can tell at a glance
  which layer a card belongs to. Badges are aesthetic, not functional
  — they do not gate behaviour.
- **In-interface lighter helpers** in addition to the mkdocs page:
  - Short glossary entries in contextual help for edge-specific
    classes (`EdgeUsageJourney`, `EdgeUsagePattern`, `EdgeDevice`,
    `EdgeDeviceGroup`, `RecurrentServerNeed`), consumed via the
    Topic 1 `DescriptionProvider` port from class docstrings and
    `param_descriptions`.
  - A short inline note near the toggle's first use, deep-linking
    to the full mkdocs page for the long-form explanation.
  - No duplication of the canonical page content in the interface.
    SSOT: the mkdocs page is the only place that explanation lives.

---

## Open questions

- **Badge visual design.** Icon, colored dot, corner stripe? Out of
  scope for Topic 3 but flagged for the implementation plan.
- **"Edge modeling" toggle placement in the navbar.** Left, right,
  inside a help/settings cluster? Minor but needs a call when the UI
  work lands.
- **Latch tooltip wording.** When the toggle is latched on because
  edge objects exist, what does the hover tooltip say? Draft: "Edge
  modeling is in use in this model. Remove all edge objects to turn
  it off." To confirm during implementation.
- **Glossary coverage.** Which edge classes get first-class contextual
  help entries (beyond the five listed)? Probably driven by whichever
  classes appear as user-facing add-menu items; to enumerate when
  Topic 2's onboarding implementation starts.
- **Cross-linking from reference pages.** The Hardware/Edge and
  Usage/Edge reference sub-bucket intros should deep-link to
  `web_vs_edge.md`. Where exactly does the intro text live — in a
  hand-written `index.md` per sub-bucket, or injected by the
  auto-generator? Deferred to Topic 4 (e-footprint docs overhaul).

---

## How this topic connects to the others

- **Topic 1 (SSOT).** Contextual help entries for edge classes are
  fed by the `DescriptionProvider` port from library-side docstrings
  and `param_descriptions`. No interface-side duplication of edge
  semantics.
- **Topic 2 (interface onboarding).** Edge is introduced through the
  IoT starter template. The navbar toggle is the persistent
  discoverability mechanism for users on web-only templates. The
  disabled-instead-of-error principle governs the latch behaviour.
- **Topic 4 (e-footprint docs overhaul).** Delivers the canonical
  `web_vs_edge.md` Explanation page and the edge-related How-to
  guides that interface tooltips deep-link to. Also owns the
  question of how Hardware/Edge and Usage/Edge reference sub-bucket
  intros get written.
- **Topic 5 (maintainability and build).** The latch rule, the
  toggle default per template, and the presence of the canonical
  `web_vs_edge.md` deep-link target all deserve tests so they don't
  silently rot.
