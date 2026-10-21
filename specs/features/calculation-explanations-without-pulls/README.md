# Calculation explanations after reload — decision record

Status: decided 2026-10-19, superseding the 2026-10-15 discussion synthesis. The feature shipped in efootprint 27.0.0 (library-driven,
cross-repo); its spec folder `e-footprint/specs/features/explanation-links-from-formula-and-slots/` is archived in git history.
This file records why the direction changed and is kept for context only.

## Observed failure

In the introductory **GenAI for Marketing video on social** example, the Google Veo server's
**Instances manufacturing footprint** formula renders as `* ( / ( * one hour ) ) + * ( / ( * one hour ) )` after a
reload. The numeric value is intact; the operand references are lost. Two further symptoms of the same mechanism
were measured during the 2026-10-19 session on the saved and reloaded example:

| Link source after reload (Veo instances manufacturing footprint) | Count |
|---|---|
| Serialized ancestor addresses | 6 |
| `direct_ancestors_with_id` after load | 0 |
| Same, after computing one void operand | 0 |
| Root slot calculus dependencies | 6 |
| An input's `direct_children_with_id` after load | 0 |
| Same input's slot dependents | 5 |

So after a reload the formula text, the calculus graph page (which walks `direct_ancestors_with_id`) and the
"Direct children" list (which walks `direct_children_with_id`) are all incomplete, and none of them recover when the
missing values are later computed.

## Mechanism

A saved computed value carries two copies of its ancestry: the formula tree (`explain_nested_tuples`, with operand
addresses at its leaves) and a separate `direct_ancestors_with_id` address list. Children are not saved; the loader
derives them by inverting the ancestor lists of cached values.

On load, the ancestor list is hydrated on its first access, which happens inside the loader's children-inversion pass,
before anything is computed. Addresses are resolved by peeking; void slots resolve to `None` and are dropped; a
one-shot flag then prevents any later re-resolution. Every non-serialized operand is void at that moment, so the list
freezes empty. The formula tree uses the same peeking resolver but is deserialized lazily on display, so its leaves
also resolve to `None`. The children list only ever contains cached values, so void dependents never appear.

The reactive slot graph does not have this problem: the `calculation_graph` section is reinstalled at load
independently of values, so slot dependencies and dependents are complete.

## Options considered

1. **Stored topology, no computation** (the 2026-10-15 direction). Render formula and graph from saved addresses and
   labels only, with a reference leaf type for void operands and compute-on-click for values. Rejected: it adds a leaf
   type, two stored facts per node (kind and unit), presenter and template branches, and still cannot show scalar
   magnitudes, to save a recompute nobody had measured.
2. **Invalidate the root and recompute it in the view.** Zero library change, but the invalidation wave drops the
   root's dependents for the request, the recompute stops at the next cached serialized value (so the system total's
   graph truncates one level down), and children stay incomplete.
3. **Re-resolving hydration with two resolvers.** Keeps both persisted copies and the inversion pass; children stay
   incomplete.
4. **Derive the links from the formula and the slot graph; the resolver pulls.** Chosen.

## Decision

- **Direct ancestors** of a value are the attached leaves of its formula. This already holds by construction for fresh
  values; loaded values derive the list from the deserialized formula instead of a separate key.
- **Direct children** of a value are the computed slots whose calculus dependencies include its slot, pulled.
- **The address resolver pulls** instead of peeking. Once ancestor hydration is gone, the formula deserializer is its
  only caller, so there is one resolver with one policy. A void operand means "compute me, I am part of what is being
  explained".
- **Deleted**: the `direct_ancestors_with_id` JSON key and writer, the hydration state and
  `load_ancestors_and_children_from_json`, the stored children list and its add/remove helpers, the children
  bookkeeping in `set_modeling_obj_container`, `all_descendants_with_id` (no callers), and the loader's
  children-inversion pass.
- **Interface code is unchanged.** The renderer, presenter and templates already read `direct_ancestors_with_id`,
  `direct_children_with_id` and the formula tree; they now receive complete results. Interface work is tests and an
  architecture-page update.

Pulling is what the next click would have computed anyway, and `ModelWeb` rebuilds the object graph from JSON on every
request, so nothing computed for a display survives to the next request today either. The cost is the same class as
clicking a non-serialized attribute. Further optimization happens only if measured latency demands it; option 1 is the
fallback.

## Accepted trade-offs

- Pulling a child computes that child's whole void subtree; an input with many consumers is the heaviest display.
  A measured baseline on the Veo and CDN examples belongs in the plan.
- The children filter must keep calculus dependents with getters and drop structural-only dependents (for example
  computed-dict key-set slots).
- Removing the ancestor key saves only 1–3% of saved JSON on the introductory examples (ancestors 0.8–3.4%, formula
  1.0–4.6%, calculation graph 17–31%). Size is a side effect, not a motive.
- The graph may show a dependency the formula does not (a computed value read only in a conditional records a slot
  edge but no formula leaf). Accepted: the graph answers "what influences this", the formula "how is it computed".

## Related

- Parked library refactor: `e-footprint/specs/backlog/automatic-input-read-dependencies/plan.html` (record input reads
  during computation automatically; remove `generate_explainable_object_with_logical_dependency`). Independent of this
  feature: "logically dependent on" leaves remain formula leaves either way.
