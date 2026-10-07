# Shared message when a request gets no response

**Status:** Parked usability improvement; no implementation scheduled.
**Recorded:** 2026-10-07, during save-error refactor review.

## Problem and evidence

If a request loses its connection before a response arrives, the browser cannot confirm whether a submitted change was saved. A user on an unreliable connection may need clear guidance. Read-only inspection found no app-wide message for this case: the [workspace mutation guard](../../../theme/static/scripts/model_builder_main.js) settles HTMX requests, while some operations use separate `fetch` calls, including [card ordering](../../../theme/static/scripts/model_builder_main.js) and [Sankey deletion](../../../theme/static/scripts/sankey.js). No user incident was reported.

## Why parked

This is a shared transport concern, not part of the save-error refactor's HTTP response handling. Per-field reload or retry logic would add complexity without resolving whether an unanswered request reached the server.

## Constraints and questions

- Prefer one message for requests with no response, such as “Connection problem. We couldn't confirm your last action. Reconnect, then reload.” Do not claim the save failed, automatically reload or retry, or show the message for deliberate cancellation or an HTTP 422/500 response.
- Should the message cover all requests or only mutations? Which direct `fetch` operations should call the same shared presenter alongside HTMX requests?
- Where should the message remain visible until the user has seen it, without repeating for every failed request?
