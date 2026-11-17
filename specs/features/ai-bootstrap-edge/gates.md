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
- **Supervisor model.** The supervisor ran on `claude-fable-5-2`; `implementer-hard` pins
  `claude-fable-5-1[1m]`.

## Checklist

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
- Sandbox code with no caller until `edge-builder` deletes the module: `edge_dsl`'s
  `validate_tolerating_extras`, `build_edge_device`, `build_system` and `build_answer`;
  `edge_dsl_hw.validate_tolerating_extras` duplicates the production one; `report_html.py` still
  reads `existing_units` and `storage_gb_per_week` (around lines 194 and 205).
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

## End-of-run gate

Known red before the run's first product commit, and left as found:

- Library: `tests/builders/hardware/test_boavizta_utils.py::test_web_api_and_package_dependency_calls_return_same_results`
  (`'2.5.0' != '2.6.0'`: the installed `boaviztapi` against the version the hosted API reports).
- Interface: `tests/unit_tests/adapters/test_ai_provider.py::test_evaluation_flash_delegates_to_bounded_adapter`
  (`'high' != 'low'`): the test still expects the flash entry to ignore an explicit effort, which
  commit `4c57a120` changed on purpose.

## Spend
