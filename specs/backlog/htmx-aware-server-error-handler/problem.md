# One server-side fallback for uncaught failures on HTMX requests

**Status:** Parked simplification; no implementation scheduled.
**Recorded:** 2026-10-19, during the request-lifecycle-simplification plan review.

## Problem and evidence

An HTMX request whose view raises an uncaught exception is invisible in the browser. HTMX refuses to swap a
4xx/5xx body by default, and the project has no global `htmx:responseError` handler: the only listener on that
event, in [`support.js`](../../../theme/static/scripts/support.js) line 56, follows the feedback link as an
ordinary navigation when its request fails. In production the project-wide `handler500` in
[`urls.py`](../../../e_footprint_interface/urls.py) renders the recovery page, which an HTMX request also
drops. The Simplified-inputs read view
[`simplified_inputs()`](../../../model_builder/adapters/views/views_simplified_inputs.py) is one such view:
a failure leaves the slot empty or stale with no message.

Views make their failures visible today in two ways, both server-rendered through
[`render_exception_modal()`](../../../model_builder/adapters/views/exception_handling.py), which returns the
error modal out-of-band with `HX-Reswap: none` so the main target is untouched:

- 17 views use the bare `@render_exception_modal_if_error` decorator: catch everything, status 500, no flags.
- 14 views call it explicitly because their response differs: status 422 for validation errors,
  `preserve_workspace` or `preserve_panels` so the modal does not clear the panels, or an appended fragment
  (the rejected-field fragment in Simplified inputs).

The convention adopted with request-lifecycle-simplification says server failures are visible, not softened
by client code. Visibility therefore has to come from the server, and today it depends on each view remembering
to catch.

## Candidate direction

Make `handler500` HTMX-aware: when the request carries `HX-Request`, return `render_exception_modal()` for the
current exception (`sys.exc_info()`), status 500, instead of the recovery page; full-page requests keep the
recovery page. With that single fallback in place, the 17 bare decorator uses add nothing and can be retired.
The 14 explicit calls stay, since each chooses a status, a preservation flag or a fragment the global handler
cannot know.

## Why parked

It is server-side error presentation outside the client-lifecycle feature's scope, and it touches every view.
Nothing is broken that a user has reported; the uncaught case is visible in the server console.

## Constraints and questions

- Django calls `handler500` only when `DEBUG` is off ([settings](../../../e_footprint_interface/settings.py)
  sets it to `False` for production at line 220). In development an uncaught exception returns Django's
  technical page, which HTMX also drops; the traceback is in the server console. Decide whether that is
  acceptable for development or whether the same HTMX branch should run in a middleware so both modes behave alike.
- Tests run with `RAISE_EXCEPTIONS`, which makes `render_exception_modal()` re-raise; the new fallback must
  respect the same switch so failures still surface as exceptions in the test runner.
- Confirm which of the 17 decorated views would need `preserve_workspace` or `preserve_panels` if the
  decorator goes: the bare decorator passes neither today, so a straight replacement keeps behaviour, but the
  audit is the moment to notice a view that should have passed one.
- [`ComputationMemoryMiddleware`](../../../e_footprint_interface/computation_memory_middleware.py) already
  answers `ComputationMemoryLimitExceeded` with the exception modal itself and re-raises everything else, and it
  defines `process_exception`; the new fallback sits behind it and must not change that memory-limit response.
