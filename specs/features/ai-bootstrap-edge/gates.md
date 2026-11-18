# AI bootstrap for edge systems — gates (for the user, after the run)

## Standing calls

- **One run, every lot.** The invocation granted full autonomy and approved the paid runs, so the
  four lots are delivered in one run and the decisions are handed over grouped by lot.
- **Gate sorting.**
  - `library-server-calls`: no user-held gate. It lands in `../e-footprint` on `dev`, with its own
    commit range; the map cannot see it and read the lot as delivered from the start.
  - `scope-and-format`: no user-held gate, no paid call.
  - `edge-builder`: an evidence gate, the paid runs of cases 03 and 04. The user's word for them
    was given at the invocation ("I approve the paid runs that need be done at the end of the
    implementation"), so the run makes them itself, at low effort, once the lot is reviewed. The
    raw readings are under "Evidence".
  - `scope-choice`: a validation by eye of the scope radio and its disclosure. The lot ships
    fully tested; the check is under "Checklist".
- **The `efootprint` dependency.** `pyproject.toml` and `poetry.lock` already pointed at the local
  checkout (`../e-footprint`, editable) before the run, uncommitted. The run leaves both files as
  it found them and commits neither.
- **Not built, for the user to decide: a stated web volume is applied at the usage's start, not
  at the web year.** A usage pattern's volume is the first value of its Growth projection inputs.
  With a fleet in service since a past date, web usage starts on that date with today's stated
  volume, so a stated growth rate compounds from too high a base (first run, case 03 rep 2: 40 %
  a year from 2022-12 gave 203 t of user-device manufacturing against about 10 t elsewhere).
  Without a stated growth nothing is off. The fix would discount the volume back from 2027-01-01
  to the start, and the editor would then open on a figure the user did not write.
- **Supervisor model.** The supervisor ran on `claude-fable-5-2`; `implementer-hard` pins
  `claude-fable-5-1[1m]`.

## Checklist

1. **The scope choice and its two disclosures, by eye.** Nothing downstream waits on it but the
   feature's archive. No paid call is made by these steps.
   1. `AI_BOOTSTRAP_ENABLED=1 MISTRAL_API_KEY=dummy poetry run python manage.py runserver`, open
      `http://localhost:8000/model_builder/`, then Modeling actions → Start with AI.
   2. Web only is checked, with its guidance and its cost and impact line.
   3. Type a description, check Web + edge: the guidance and the cost and impact line change, the
      typed text stays. Read the Web + edge guidance and disclosure wording: both are new copy.
      The web part of the Web + edge guidance leaves out two hints the Web only text gives
      (users against visits, session or step durations).
   4. Do not submit: with the dummy key the provider refuses at no cost, but the description
      would still be sent to it.

   Verdict:
2. **A Web + edge generation, by eye, on the test fake** (the development server has no fake
   switch): `poetry run pytest tests/e2e/test_ai_bootstrap.py -k "web_edge_generation or scope_choice" --headed --slowmo 400`
   (prefix `PWDEBUG=1` to step through). It starts its own server and answers with handwritten
   answer 04. Look at the summary's edge checks after the web ones, the edge objects on the
   canvas, and the generated web usage pattern opening on 12 years from 2024-01-01.

   Verdict:

## Post-run operations

1. **Release the library before the interface's deployment commit.** The lot `library-server-calls`
   changed `efootprint` on `dev` (`../e-footprint`, range `afc60887..f9ad5688`): a server need's
   volume now counts every unit of its device, and its attribute is renamed
   `hourly_volume_per_usage_pattern`. The interface's Web + edge bootstrap needs that release: on
   the published `27.0.1` a grouped device sends one unit's calls. Follow
   `../e-footprint/RELEASE_PROCESS.md` (its `## [Unreleased]` section of `CHANGELOG.md` is
   written), then restore the published pin here as `RELEASE_PROCESS.md` says.
2. **The release must move the version number.** A modeling saved with its computed state at
   `27.0.1` on the local checkout, holding a grouped device with a server need, keeps its stale
   server volume while the version is unchanged; any version change, a patch included, discards
   the stored state and recomputes. Only local sessions on the editable checkout are concerned.

## Evidence

### Paid runs of cases 03 and 04 (lot `edge-builder`)

Made by the run on the user's word given at the invocation. Command, from the repository root:
`poetry run python -m ai_sandbox.run --scope web_edge --cases 03 04 --models zai-glm-5-3-flash --effort low --reps 3 --max-cost-usd 0.5`.
The raw readings are local and git-ignored, under `ai_sandbox/runs/<run>/` (`summary.md`, one json
a call).

**Run `20261118-003854`**, on the build at `e8949fc1` (the lot as reviewed, before the prompt edit
that follows). Total cost USD 0.0096.

| Case | Rep | Built first try | Checks | In tok | Out tok | Reasoning tok | Latency s | Cost USD | Total kg CO2e | Devices in service as 2027 opens |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 03 | 1 | yes | 10/10 | 2,678 | 2,158 | 5 | 10.47 | 0.0015 | 704,008 | 1,474 gateways, 58,960 sensors |
| 03 | 2 | yes | 8/10 | 2,678 | 2,571 | 453 | 16.11 | 0.0017 | 542,569 | 2,998 gateways, 119,920 sensors |
| 03 | 3 | yes | 8/10 | 2,678 | 2,430 | 492 | 14.63 | 0.0016 | 258,352 | 2,206 gateways, 88,240 sensors |
| 04 | 1 | yes | 7/8 | 2,704 | 2,696 | 565 | 18.76 | 0.0018 | 1,826,819 | 5,240 controllers |
| 04 | 2 | yes | 7/8 | 2,704 | 2,462 | 536 | 19.56 | 0.0016 | 1,087,527 | 6,224 controllers |
| 04 | 3 | yes | 8/8 | 2,704 | 1,980 | 240 | 12.83 | 0.0014 | 828,182 | 4,434 controllers |

Stated fleets: 1,500 gateways and 60,000 sensors (03), 4,200 controllers (04). The six failed
checks are the device totals of four calls; every other check passed on every call (a server
shared by devices and people, groups, a usage pattern for every journey, server calls). What the
four answers wrote: a fleet that reaches its stated size at the end of 2024, on 2025-01-01 or on
2026-01-01, then the stated growth from that date to the end of 2027. Three of the six answers
also dated a usage pattern the description does not date.

**Run `20261118-004330`**, on the build at `4224af9b` (the prompt now dates the description's
present to 2027-01-01 and tells the answer to leave a usage pattern's start date out unless the
description gives one). Total cost USD 0.0091. This is the build the lot `scope-choice` discloses.

| Case | Rep | Built first try | Checks | In tok | Out tok | Reasoning tok | Latency s | Cost USD | Total kg CO2e | Devices in service as 2027 opens |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 03 | 1 | yes | 8/10 | 2,825 | 2,226 | 281 | 20.25 | 0.0015 | 148,768 | 1,536 gateways, 61,440 sensors |
| 03 | 2 | yes | 9/10 | 2,825 | 1,838 | 282 | 10.30 | 0.0013 | 471,299 | 1,536 gateways, 61,440 sensors |
| 03 | 3 | yes | 10/10 | 2,825 | 2,513 | 530 | 15.14 | 0.0017 | 213,818 | 1,536 gateways, 61,440 sensors |
| 04 | 1 | yes | 8/8 | 2,851 | 1,854 | 419 | 12.38 | 0.0014 | 704,500 | 4,293 controllers |
| 04 | 2 | yes | 8/8 | 2,851 | 2,529 | 598 | 31.05 | 0.0017 | 661,000 | 4,275 controllers |
| 04 | 3 | yes | 7/8 | 2,851 | 2,167 | 181 | 17.19 | 0.0015 | 1,314,876 | 5,293 controllers |

Failed checks: 03 rep 1, the number of journeys and the low-volume journey (the answer holds
placeholder keys such as `journeys_2_placeholder`, dropped as unknown, and one journey); 03 rep 2,
the server shared by devices and people; 04 rep 3, the device total (108 a month from 2024-09-01
and 75 a month from 2024-07-01, both to 2026-12-31, then 80 a month from 2027-01-01). No answer
dates a usage pattern. The prompt was not edited again.

What the two runs do not settle, read by the lot's reviewer on the raw answers of the first run:
the computed totals spread threefold on each case with the checks passing. On case 03 device
manufacturing dominates and the sensor's manufacturing footprint ranges from 0.1 to 5 kg (the
case's facts: 30 g of electronics), the gateway's from 25 to 60 kg. On case 04 station
electricity dominates and the controller's power ranges from 5 to 15 W (the facts: 8 W). Lifespans
and usage spans of 8 to 10 years against the facts' 5 to 8 lengthen every horizon.

## Watch in normal use

## Parked

## Leads for the global review

### library-server-calls

- Added in the library: a server, a storage, a job and a server need in the edge-device-group
  integration fixture (`tests/integration_tests/integration_edge_device_group_base_class.py`),
  its reference `edge_device_group_system.json` regenerated; the test helper
  `_contain_in_one_usage_pattern` in `tests/usage/edge/test_recurrent_server_need.py`.
- Renamed: `RecurrentServerNeed.unitary_hourly_volume_per_usage_pattern` to
  `hourly_volume_per_usage_pattern`; the two job sites multiply it by the job weight only. The
  printed cell output of the library's `tutorial.ipynb` still shows the old name until the release
  refreshes it.
- The library's `CHANGELOG.md` `## [Unreleased]` already holds a `Fixed` and a `Changed` line for
  this lot: the end of the run adds the interface's entry only, and writes the library's no second
  time.
- **Predates this work, not acted on**: building a new `EdgeDeviceGroup` around an
  already-computed device left that device's `total_nb_of_units` stale until a later edit, in the
  reviewer's scratch run (`new_group.py` in the session scratchpad, gone after a reboot). The AI
  bootstrap builds every object before the system, so it is not reached here; whether the
  interface's own "add a group" path reaches it was not checked.

### scope-and-format

- Two `Scope` dataclasses: the service's (prompt file, schema) and the sandbox's in
  `ai_sandbox/run.py` (system prompt, validate, build), whose `_production` reaches into the
  service's table.
- The scope strings `"web"` and `"web_edge"` are literals in the view, the summary template, the
  tests and the sandbox; the scope-choice radio adds one more place.
- The view defaults an absent scope to `"web"`. Once the radio always posts the field, that
  default guards a request nothing real sends, against the plan's "no guard": settled in the lot
  `scope-choice`.
- `specs/architecture/layers-and-wrappers.html` says the response context carries "the
  description and summary metrics"; it now carries the scope too.
- `validate_tolerating_extras` changes the dict it is given (predates the run), and
  `ai_sandbox/run.py` depends on that before it builds.
- Misses seen in the measured sandbox runs (`ai_sandbox/runs/20261117-224245`, local and
  git-ignored) that the plan's record does not name, so the prompt was not edited for them: a
  group used as a country fleet (case 04, 17.7 million controllers), sensors running no edge
  function and so never deployed (case 03), a journey with no usage pattern (case 04). The paid
  runs of `edge-builder` read whether the shipped prompt still makes them.
- A replay of a run recorded under the removed sandbox scope `web_edge_hw` now raises `KeyError`.
  Local runs only.
- The map's `help` verb crashes (`comprehension-harness/map.mjs:571`: `fileURLToPath` is called
  with no import from `node:url`). Tooling, outside the feature, not fixed.

### edge-builder

- The hourly editor's duration limit was written in three places (the template's `max`, the
  script `usage_pattern_timeseries.js`, the preview view); the lot's review fix gives it one
  source. Check that no fourth literal is left.
- When the hourly editor opens on a stored duration above its limit, the script rewrites the
  value to the limit and shows an error, so a save that looks unchanged stores the cut value. The
  builder no longer emits such a period; a hand-imported one still meets it. Predates the run,
  left as found.
- A save from the hourly editor rewrites the form inputs as strings (`'38'`, `'60.0'`), so an
  unchanged save is a real change that recomputes. Predates the run.
- New private helpers in the bootstrap DSL module: `_weekly`, `_duration`, `_reserve`,
  `_deployment_spans`. New public constants: `WEB_YEAR_START`, `WEB_YEAR_END`,
  `MAX_DEFAULT_SPAN_YEARS`; the sandbox reads `WEB_YEAR_START`.
- Test helpers `HourlyEditorInputs`, `as_numbers` and `at_web_year_start` live in the narrative
  test file; the browser tests of `scope-choice` may want them.
- The Web only schema accepts a `start_date` on a usage pattern, which its prompt never offers.
- The shared start is the earliest date of anything dated: a dated usage pattern earlier than
  every deployment pulls the undated deployments with it. It matches the plan's clause and the
  prompt; the spec's rule speaks of "the earliest deployment start".
- Handwritten answer 04 deploys Germany at 75 a month from 2024-01-01; the prompt's rule now gives
  80 a month, the stated rate, from about 2024-03-09. The fleet narrative case asserts the 75.
- With fleet totals and no group (case 04), the summary's "Devices per group" check points at
  nothing the user can open.
- A replay of a sandbox run recorded before the format moved drops the removed fields and fails
  the device totals. Local, git-ignored runs only.

### scope-choice

- The scope strings `web` and `web_edge` are written out in the view's start route, the input
  template (two radios, four `data-ai-scope` blocks), the summary template, the stylesheet rule
  and the service's table. A third scope would touch all of them.
- The `checked_scopes` regex of the narrative tests depends on the order of the radio's
  attributes; it fails loudly if they move.
- No test posts an absent scope; an unknown one (`edge_only`) is tested and both reach the same
  lookup failure.
- The journey page's screen 6 describes the edge checks in a state row only, with no mock.
- The sandbox's `summary.md` states no impact of a call: its "total kg CO2e" column is the
  generated modeling's footprint. The disclosure's "below 1 g CO2-eq" was recomputed with
  `estimate_call` on each call's tokens and latency (0.21 to 0.40 g).

## End-of-run gate

Known red before the run's first product commit, and left as found:

- Library: `tests/builders/hardware/test_boavizta_utils.py::test_web_api_and_package_dependency_calls_return_same_results`
  (`'2.5.0' != '2.6.0'`: the installed `boaviztapi` against the version the hosted API reports).
- Interface: `tests/unit_tests/adapters/test_ai_provider.py::test_evaluation_flash_delegates_to_bounded_adapter`
  (`'high' != 'low'`): the test still expects the flash entry to ignore an explicit effort, which
  commit `4c57a120` changed on purpose.

## Spend
