# A standalone build of the interface that runs entirely in the browser

**Status:** Parked exploration; no spike run, nothing measured in a browser yet.
**Recorded:** 2026-11-18, during a technology exploration on deploying e-footprint inside a large company.

## Problem and evidence

The interface is being deployed as an open source tool inside a large company. Microsoft Copilot builds the
modeling from user input and internal data and outputs a JSON file, which the user loads in the hosted
interface. The modeling is then uploaded to an external server, held in its session store and computed there.
Internal data leaving the company for a third-party server is a likely long-term security objection.

Two alternatives were raised and compared:

- **A desktop app (Electron).** Rejected as a first move. It does not remove the Python problem: it would
  bundle a browser engine plus a Python runtime and its dependencies, need code signing, per-OS builds and
  update infrastructure, and installing a desktop binary in a large company usually takes more review than
  allowing a URL.
- **Python in the browser.** Pyodide is CPython compiled to WebAssembly. With it, the modeling never leaves
  the user's machine, and the app becomes static files that a company can host internally with far less
  review than Django, Redis and Postgres. A strict content security policy would make "data never leaves the
  browser" enforced by the browser rather than promised. A build like this is installable from Edge and
  works offline, so it also covers most of what a desktop app would offer.

The company self-hosting the existing Docker image is the baseline to compare against: no engineering on our
side, ongoing operations on theirs.

## Candidate direction: one codebase, two build targets

Do not rewrite the interface in JavaScript and do not fork it. Run the existing Django app inside Pyodide, as
a second build target of this repository:

- the hosted target stays what it is today, for casual users;
- the standalone target is a static site in which a service worker intercepts the app's requests and hands
  them to a web worker running Pyodide, which calls Django and returns the response.

Templates, HTMX flows, forms and the domain layer are shared unchanged. That is what keeps the two in sync:
there is one set of views and templates, and the standalone target differs only in settings, storage adapters
and a small bridge.

The standalone target would consist of:

1. A standalone settings module: in-browser session and cache backends, no Postgres or Redis, the two
   `psutil` middlewares and `django_browser_reload` removed, admin and auth dropped if nothing relies on them.
2. The bridge: service worker, web worker loader, and a thin Python entry point that calls Django.
3. A browser variant of `CacheBackend`, which today contains raw Postgres SQL in `touch_postgres` and
   `delete_expired_postgres`.
4. A build script that bundles the library, the interface and the collected static files.
5. The AI bootstrap feature switched off, or later offered with a user-supplied key.

The existing Playwright suite takes a `base_url`, so the same end-to-end tests could run against the
standalone build in CI. That is the proposed guard against the two targets drifting apart.

A side benefit: with one user and a long-lived worker, the model can stay in memory between requests. The
hosted version's binding constraints (session-store RAM and a JSON round-trip per request) would not apply.

## Evidence gathered on 18 November

Interface, checked in the code:

- No `models.py`: the database only backs sessions and the cache table.
- `request.session` is used in 16 files, but session and cache backends are chosen in settings, so views
  would not change.
- No streaming responses, websockets, threads or subprocesses; every route is plain request and response.
- Templates reference no external CDN.
- About 148 templates (72 with HTMX attributes), 62 routes, 15k lines of Python in `model_builder`.

Library, checked against the Pyodide package list (version 314.0.8):

- Available in Pyodide: numpy, scipy, pandas, matplotlib, pydantic, pydantic_core, orjson, zstandard, pytz,
  wrapt, requests. `pint` is pure Python.
- Not available: `ciso8601` (C extension). It would need replacing with `datetime.fromisoformat`.
- `ecologits` is not a blocker: its requirements are pydantic, wrapt and packaging.
- A separate change, decided the same day, makes `boaviztapi` and the visualisation dependencies optional
  extras and removes the scipy call. Measured on Linux wheels, that takes the library from 83 packages and
  129 MB of download to 22 packages and 26 MB, which is also what makes the browser payload reasonable.

## Why parked

Nothing has been measured in a browser. The go/no-go question is speed: efootprint is heavy pure Python, which
runs slower in WebAssembly, and cold start (Pyodide plus importing Django, pint and efootprint) is expected to
take several seconds. Until a spike gives those two numbers on a large modeling, this is an idea, not a plan.
The dependency slimming in the library comes first and is useful on its own.

## Known constraints

- **Worker lifetime.** A web worker dies when its page navigates, so a full page load would restart Python.
  The usual answer is a thin outer page that owns the worker and never navigates, with the Django UI in an
  iframe inside it.
- **Cookies.** Browsers ignore `Set-Cookie` on responses built by a service worker, so the bridge has to
  carry the session and CSRF cookies itself.
- **Persistence.** In-memory state is lost on reload. Options are browser storage behind the session, JSON
  export and import, or a linked local folder (see
  [local folder link](../../features/local-folder-link/README.md), which is designed to work on both targets).
- **File upload and download.** JSON import and Excel export have to pass through the bridge as bytes.
- **First visit.** The service worker must be installed before it can intercept anything, so the first load
  needs a bootstrap page.
- **Download size.** Estimated at 15 to 25 MB on first load, cached afterwards; updates would re-fetch only
  the few MB of application code. This is an estimate, not a measurement.
- **Boavizta server builders.** They call `api.boavizta.org`. From a browser that depends on the API allowing
  cross-origin requests (not checked), and a fully offline build would need snapshot data instead.

## Copilot and the AI feature

- A page in a browser tab cannot be a tool for Copilot: Copilot agents connect to remote MCP servers. A native
  link would be a small stateless e-footprint MCP server hosted by the company (model description in,
  validated JSON and results out), which is a separate piece from this build.
- The cheapest robust link is today's flow, hardened: Copilot produces JSON, the user imports it, and the
  import validates it against a published schema.
- A user-supplied API key suits the public instance but is of little use inside a company whose employees
  have Copilot rather than API keys.

## Questions before promoting to `specs/features/`

- Spike 1: load efootprint in Pyodide with a large modeling JSON and time cold start and recompute against
  native. Is the result acceptable?
- Spike 2: serve the model-builder page and one edit round-trip through the bridge with standalone settings.
  Does anything in Django or the app's middleware resist it?
- Does anything rely on `django.contrib.auth` or the admin, or can both be dropped in the standalone target?
- Which persistence option is the default, and what is the fallback where the folder picker is unavailable?
- Who hosts the standalone build: the project publicly, each company internally, or both? What does that
  imply for updates and versioning?
- What is the content security policy, and does it allow the Boavizta API or forbid all outbound requests?
- Is the hosted target kept indefinitely, or does the standalone target eventually become the public
  instance too?
