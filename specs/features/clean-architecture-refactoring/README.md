# Clean Architecture refactoring — draft feature kickoff

Status: discussion context and proposed roadmap · 2026-11-04 · Interface-owned.
No specification, detailed implementation plan or task breakdown has been approved.
Continue with `spec-specify clean-architecture-refactoring` in a fresh session. This note preserves
the architectural discussion; it does not authorize implementation of the broader refactoring.

## Motivation and priority

Review of `bug-fixes-2026-10` Run A, Task 6, exposed two issues in
`ModelingObjectWeb.has_canvas_card`: a hardcoded root-type list duplicates canvas selection, and
canvas placement participates in the edit use case. Reviewing the surrounding class revealed a
broader mixture of model mutation, editor policies, form preparation and presentation.

The goal is to make model-changing behavior understandable without reading card code, while
allowing presentation to communicate and use the editor's semantics. Merely relocating classes
or removing Django imports does not establish that boundary: a pure Python
`OobRegion("model_canvas")` still describes a presentation decision.

Priority agreed in discussion:

1. Explicit editor relationship/lifecycle rules have high value because they affect saved-model
   correctness. The existing bug batch documents failures around unlinking and orphan cleanup.
2. Separating mutation results from canvas refresh planning is worth doing incrementally.
3. Moving every presentation property into a perfectly named package is lower urgency. Moving
   files alone is not the objective.

Over the next couple of years, new relationship types and library builders could otherwise require
reasoning about wrapper dispatch, form strategies, mutation hooks, cascades and card placement
together. Public model sharing/forking, upgrade comparison and the candidate convergence of
creation-time linking paths are relevant roadmap contexts, not prerequisites or approved scope
for this refactoring. Do not delay them for a complete architectural rewrite without evidence.

## Important clarification: the editor has legitimate application-specific semantics

The first proposal to separate model ownership from visual nesting was too categorical. The web
editor can define what is created together, edited together, removed from a container or deleted
together. Not all such rules belong in the library. A thin interface-specific policy layer is
legitimate, even when its concepts are closely reflected by the UI.

For example, an editor rule may say that deleting an owner deletes its owned component, or that
removing the last owner deletes an otherwise orphaned component. Showing that component inside
the owner's card communicates the rule. Both the mutation and the presentation can depend on
the same meaning; Clean Architecture does not require semantic independence between them.

The problematic direction is allowing visual arrangement to define lifecycle behavior implicitly.
Nesting can mean several different things:

| Relationship meaning | Possible operation semantics |
|---|---|
| Owned component | Delete with its owner, according to the explicit policy |
| Reference to an independent object | Unlink and retain the object |
| One occurrence of a shared object | Remove that occurrence without deleting other occurrences |
| Calculated detail | Let the library manage its regeneration/lifetime |

These are illustrative distinctions, not settled rules for every existing class. Audit actual
relationships before assigning policies. Constructor list/dict annotations alone do not prove
ownership. Likewise, do not mechanically rename a rendering flag to `owns_children`.

A useful design test: moving a component from an accordion to a separate panel should not change
its deletion behavior unless the product intentionally changes the operation. If the UI offers
different operations, make their meanings explicit (for example, remove-from versus delete).

## Current code evidence and reading route

Start with [the architecture router](../../architecture/index.html), then the owning
[layers/wrappers](../../architecture/layers-and-wrappers.html),
[forms/relationships](../../architecture/forms-and-relationships.html), and
[rendering](../../architecture/rendering.html) pages. Respect
[the constitution](../../constitution.md) and [mission](../../mission.md).

Re-read current code: the pointers below describe the review baseline and may evolve.

| Code | Responsibility/coupling to examine |
|---|---|
| `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py` | Template names, HTMX configuration, DOM IDs, membership/child sections, mirrors, accordion ancestry, model proxying, deletion, constraint diffs and OOB descriptors coexist. |
| `model_builder/domain/services/edit_service.py::EditService.edit_with_cascade_cleanup` | Discovers removed children through mirrored cards and accordion children, then performs orphan deletion. |
| `model_builder/application/use_cases/delete_object.py::_container_removal_targets` | Uses `renders_relationship_children_as_nested_cards` when deciding relationships to unlink. |
| `model_builder/domain/entities/web_core/usage/usage_pattern_web_base_class.py` | Overrides relationship/mirror/child discovery to express references rather than ownership. |
| `model_builder/domain/entities/web_core/hardware/server_web.py` | Combines templates/form layout, nested storage mutation, deletion blockers and service deletion. |
| `model_builder/domain/entities/web_core/hardware/edge/edge_device_group_web.py` | Combines membership choices, validation, group entry presentation and canvas-region replacement. |
| `model_builder/domain/efootprint_to_web_mapping.py` | Wrapper selection is also used to dispatch application hooks. |
| `model_builder/domain/entities/web_core/model_web.py` | Loading, indexing, model access, registration, serialization coordination and web wrapping are coupled. |
| `model_builder/domain/oob_region.py` and create/edit/delete use-case outputs | Inner layers carry DOM-region decisions and rendering identities. |
| `model_builder/adapters/presenters/htmx_presenter.py` and `adapters/card_order.py` | Existing natural owners for refresh planning and canvas selection. |

Related evidence: [bug-batch smell sweep](../bug-fixes-2026-10/smell-sweep.md), especially S1/S7
(deletion and reference/ownership), S4 (wrapper dispatch), and
[Task 6 handoff](../bug-fixes-2026-10/handoffs/task-6.md).
The sweep records historical findings, some addressed in Run A: verify current behavior rather
than treating every entry as an outstanding bug.

## Proposed responsibility boundary

| Layer | Intended responsibility |
|---|---|
| `efootprint` library | Modeling objects, calculations, relationships and model invariants. Remains the domain truth. |
| Interface application/editor policies | Create/edit/delete workflows, application-specific ownership and lifecycle rules, persistence coordination. |
| Presentation/form adapters | View models, form layout, choices and disabled-state presentation, DOM IDs, canvas occurrences, templates and HTMX refresh plans. |
| Repository adapters | Concrete loading/saving of model state and interface settings. |

Some rules apply to every valid library caller and belong in the library; others define this
editor's actions and belong in the interface. Decide per rule. UI affordances must not be the
only enforcement for application commands that direct requests can invoke.

Retain convenient template wrappers as presentation view models. They can read model objects and
prepare display data, but should not implement mutation workflows. Form choice filtering can
consume application/library rules without owning those invariants.

Application code may use `efootprint` objects directly. Do not duplicate the full graph into DTOs,
create interfaces for every class, or rebuild the domain model inside the interface.

## Proposed incremental roadmap

### 1. Make relationship and lifecycle rules explicit

Inventory ownership, references, shared membership, independent existence, generated children,
unlink semantics, deletion blockers and cascades. Extract existing intended behavior into small
policies/functions. Remove mirror/accordion traversal from mutation and orphan cleanup.
Resolve ambiguous behavior with evidence and product decisions instead of preserving accidental
behavior under new terminology. Cover shared children, multiple parents and detached references.

### 2. Extract mutation behavior from web-wrapper hooks

Separate operations such as creating/editing a server with storage, membership changes and deletion
cascades from templates, form strategies and card selection. Preserve source metadata, conditional
input repair, parent-owned edits and saved Simplified-input selections. Small functions/strategies
are preferred to a replacement hierarchy of services.

### 3. Separate mutation results from refresh planning

Use-case results describe changed objects/inputs, changed relationships, removed objects and
automatic repairs. Presentation translates these facts into card refreshes, notifications, result
updates and OOB regions. Capture necessary facts before deletion makes objects unavailable.
A small result object is sufficient; no event bus or general change-tracking framework is assumed.
Preserve existing behavior for full-canvas updates, metadata-only edits and inline counts.

### 4. Relocate/simplify remaining wrappers and model context

Move presentation wrappers into adapters once application code no longer relies on their mutation
hooks. Separate the model context's lookup/index/registration and serialization coordination from
web wrapping. Reuse repository contracts and library objects. The interface's own domain layer
may shrink; do not impose an empty layer or change persistence just for symmetry.

The order above is a candidate delivery sequence, not approved tasks. Each increment should leave
the application working. Avoid a broad rewrite spanning unrelated features.

## Immediate Task 6 cleanup — separately authorized

The user separately authorized a small cleanup in `bug-fixes-2026-10` after committing this note:

- Move canvas root selection and card-presence logic into adapters, sharing the unordered root
  collections with `ordered_card_lists` instead of duplicating a root-type list.
- Let the presenter check placement before mirror discovery for edited objects and repaired owners.
- Remove placement checking and mirror preparation from the edit use case.
- Preserve storage saves, notifications, constraints, Results updates and visible custom-device
  component refreshes. Do not refresh a parent solely because its storage has no card.
- Leave ownership, deletion, mutation hooks and the wrapper hierarchy unchanged in this cleanup.

The cleanup is implemented in the commit introducing `model_builder/adapters/canvas.py`; see
the Task 6 handoff for review pointers and any outstanding validation. Do not schedule it again.
This does not eliminate mirror traversal inside existing mutation services; that is broader work
above. A possible future `card_occurrences(object_id)` operation could unify presence and mirrors,
but is not required for this small cleanup. Verify the cleanup's actual commit/handoff in the
bug-batch working set before continuing; do not schedule it twice.

## Success criteria and open questions for specification

Desired architectural outcomes:

- Changing relationship layout does not accidentally change mutation semantics.
- Deletion/unlink behavior can be understood and tested without card code.
- Use cases run without presentation wrappers or rendering configuration.
- Presentation updates all occurrences of affected shared objects without changing saved state.
- Existing supported save/load, recovery, create/edit/delete and comparison behavior is preserved,
  except for separately approved corrections to discovered bugs.

Questions still to resolve:

- Which lifecycle rules are library invariants versus editor policies?
- Which existing nested relationships express ownership, references or both in different actions?
- What minimal mutation result supports refreshes and deletion confirmations without graph copies
  or expensive model-wide snapshots?
- Where should capability/constraint comparisons live, and what must be captured before mutation?
- Which wrapper specializations remain useful as view models, and which disappear?
- What is the smallest useful first increment after the current bug batch?

Validation should include model-operation integration tests, shared/multi-parent deletion cases,
layout-independent lifecycle checks and focused browser regressions for cards, results and feedback.
Run repository-required gates for implemented increments. Update owning architecture pages and
AGENTS/CLAUDE guidance as patterns change; do not document this proposal as current implementation.
