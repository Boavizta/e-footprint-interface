# Leaderlines for Grouped Edge Infrastructure

## Goal

Extend the existing leaderline system so that target-side accordion state affects
the endpoint of the line.

This is needed for grouped edge infrastructure, and it should also improve the
existing server/service case:

- service job -> service row when visible, else server card
- recurrent edge device need -> device row when visible, else subgroup/root group
- recurrent edge component need -> component row when visible, else device/group
- collapsed `EdgeFunction` -> summary lines to the same concrete targets its child
  recurrent needs would point to

## Non-Regression

Do not change existing source-side leaderline semantics.

In particular:

- when a source accordion is collapsed, it must keep showing the same summary lines
  it shows today
- when a source accordion is expanded, it must keep delegating visually to its
  child sources as it does today

This feature should only make target resolution smarter on the Infrastructure side.
It should not redesign source-side line semantics.

## Core Rule

Keep `data-link-to` as-is.

- it already supports multiple targets
- it already uses unique DOM ids
- we do not need a second target attribute or a semantic-id migration

The change is in the JS resolver:

- if the target element is visible, connect to it
- if it is hidden, walk up to the nearest visible ancestor anchor
- draw the line to that resolved anchor

So the rule is: **connect to the deepest visible anchor on the target side**.

## Examples

- service hidden inside a collapsed server -> line ends on server
- grouped component hidden inside a collapsed device accordion -> line ends on device
- grouped device hidden inside a collapsed subgroup -> line ends on subgroup
- grouped device hidden inside a collapsed root group -> line ends on root group

## DOM Requirements

Any node that may become a line endpoint must be marked as a leaderline anchor.

Relevant anchors:

- server cards
- service rows
- root edge-device groups
- subgroup rows
- grouped device rows
- grouped component rows

The resolver only needs:

- the target DOM id from `data-link-to`
- whether that target is currently visible
- the ancestor chain of `.leaderline-anchor` elements

## Current Foundation

The prerequisite work is now in place:

- `e-footprint` now exposes structural input-dict parentage through
  `contextual_modeling_obj_containers`
- `e-footprint-interface` now lets `ModelingObjectWeb.mirrored_cards`,
  `web_id`, and `accordion_parent` work with dict-backed rendered parents too

So grouped device/component mirrors are no longer blocked by missing parent context.

## Target-ID Assumption

This feature can proceed on the assumption that `data-link-to` is already the right
source of target ids:

- `EdgeDeviceGroup` is purely structural
- the semantic end objects remain the direct modeled targets: services, servers,
  edge devices, edge components
- `links_to` already follows those direct modeling-object links

This should still be checked in the DOM early during implementation, but it is no
longer a design blocker.

## JS Implementation Shape

In `leaderline_utils.js`, for each source element:

1. parse ids from `data-link-to`
2. resolve each id to a DOM element
3. if that element is visible, keep it
4. otherwise walk up to the nearest visible `.leaderline-anchor`
5. deduplicate resolved endpoints
6. draw lines to those endpoints

Visibility should be based on actual DOM state. If an element sits inside a
collapsed `.accordion-collapse`, it is not a valid endpoint.

## Rebuild Rule

The current source-local accordion update logic is not enough, because opening a
group on the Infrastructure side may change the endpoint of many unrelated lines.

Use a broad rebuild rule:

- on relevant accordion open/close, rebuild all leaderlines

To avoid flicker:

- rebuild only on `shown.bs.collapse` / `hidden.bs.collapse`
- in `requestAnimationFrame`, compute the full new line set
- create the new lines first
- remove the old lines only after the new ones exist
- swap the line registry in one pass

This should behave like a batched line-set swap, not a visible tear-down/redraw.

## Likely Files

- `model_builder/domain/entities/web_abstract_modeling_classes/modeling_object_web.py`
- `theme/static/scripts/leaderline_utils.js`
- `model_builder/templates/model_builder/object_cards/server_card.html`
- `model_builder/templates/model_builder/object_cards/edge_device_group_card.html`
- `model_builder/templates/model_builder/object_cards/partials/group_content.html`
- `model_builder/templates/model_builder/object_cards/edge_component_card.html`
- `model_builder/templates/model_builder/object_cards/resource_need_card.html`
- `model_builder/templates/model_builder/object_cards/resource_need_with_accordion_card.html`
- `model_builder/templates/model_builder/object_cards/journey_step_card.html`
- possibly:
  - `model_builder/domain/entities/web_core/usage/job_web.py`
  - `model_builder/domain/entities/web_core/usage/edge/recurrent_server_web.py`
  - `model_builder/domain/entities/web_core/usage/edge/recurrent_edge_device_need_base_web.py`
  - `model_builder/domain/entities/web_core/usage/edge/recurrent_edge_component_need_web.py`
  - `model_builder/domain/entities/web_core/usage/edge/edge_function_web.py`

## JS Test Targets

Do not add E2E coverage for this feature.

If the resolver is factored into small enough helpers, add a few focused tests in
`js_tests` for the resolution logic only.

Good candidates:

1. visible target -> resolver returns the target itself
2. hidden target inside collapsed accordion -> resolver returns the nearest visible
   ancestor `.leaderline-anchor`
3. grouped component hidden by closed device accordion -> resolver returns device
4. grouped device hidden by closed subgroup/root group -> resolver returns the
   nearest visible group anchor
5. service row hidden by closed server card -> resolver returns server card
6. several target ids resolving to the same visible ancestor -> resolver
   deduplicates endpoints

Do not try to unit-test `LeaderLine` itself. The useful automated coverage here is
the DOM resolution logic that decides which endpoint id should be used.
