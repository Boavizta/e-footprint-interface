# Plan — AI bootstrap for edge systems

A scope travels with the generate request and picks the instructions and the schema; the builder
gains the edge sections; the library scales server calls with every device deployed.

## #scope-choice

Above the description, a Web only / Web + edge radio, Web only checked unless Edge modeling is on; a stylesheet rule shows the checked scope's guidance and disclosure alone.

A request per switch would have to carry the description back. The stylesheet's `:has` selector, already used by simplified inputs, needs no script and no request. Each disclosure states its scope's indicative cost, to two significant figures, and its impact, from the sandbox runs of #edge-instructions.

Changed: **The panel opens on Web + edge when Edge modeling is on.** Asked by the user after trying it. The toggle's script checks the radio once on a fresh panel; a refused panel keeps the posted scope. → statement "unless Edge modeling is on"; test "opens on Web + edge"; code "edge_modeling_toggle.js"

Changed: **One browser test and five files beyond the plan.** The test alone sees the editor keep a cut period on reopening. The radio lives in the input template and its stylesheet; the changelog and the architecture page follow the feature. → test "a web usage cut to 10 years"; test "test_a_provider_failure_keeps"; code "ai_bootstrap_input.html"; code "bs_main.css"; code "bs_main.css.map"; code "custom.scss"

Changed: **Both cost lines carry two significant figures.** At one, Web + edge read twice the cost of Web only; measured, it is 0.15 US cent against 0.12. The approved Web only line changes. → reason "two significant figures"

## #scope-in-request

The scope travels with the generate request to the service, back on a refusal, and to the summary, whose checklist adds deployments, devices per group, device characteristics and server calls.

Like the description, it lives in the request and the response alone. An unknown value gets no guard: the scope table's lookup fails inside the generation, which is refused like a bad answer, and only a hand-crafted request sends one.

Changed: **The summary's checklist lives in its template, which no place names.** The view only hands it the scope; the four edge checks are written in the summary template, after the web ones.

## #scope-selects-format

A scope table in the service pairs each scope with its instructions and its schema; one request is made whichever is chosen.

Web only keeps today's flow. A second service per scope was refused: everything after the answer (build, prepare, validate, save) is the same for both scopes.

Changed: **The Web + edge prompt is a product file no place names.** It is the sandbox's measured prompt, moved beside the web one as #edge-instructions says; the plan pointed at the function that reads it, not at the file.

## #edge-instructions

Web + edge gets its own whole prompt: the sandbox's measured one, edited only for the new format and for what cases 03 to 05 missed.

Its edge material runs through the web text, from the paradigms to the field notes, so an addendum would leave the web framing contradicting it. The cost is a copy of the web rules, which a web edit mirrors. Cases 03 and 04 re-run at low effort, each paid run on the user's word; the disclosure's figures come from them.

Changed: **The prompt dates the description's present to 2027-01-01.** In the first paid run four of six answers put today in 2024 to 2026, up to doubling the fleet; after the edit five of six count it right. → code "system_prompt_web_edge.md"

Changed: **Two cases join the measured ones: groups inside groups, and a held-out chain of stores.** On the user's building no answer of six grouped the cabinet; after three prompt edits half are fully right, the rest omitting the building group. → statement "03 to 05"; test "answer 05"; test "held-out answer 06"

## #edge-format

WebEdgeSpec adds edge devices, optional groups, edge functions with server calls, edge journeys and deployments with a start date; a Web only answer's edge sections are dropped as unknown.

No installed-base field: the sandbox schema refused an installed base with no growth, and a past start date says the same within the Growth projection inputs. One schema for both scopes was refused: a Web only answer could then build edge objects.

Changed: **The fix that gave a server call its list of jobs also edits the Web + edge prompt.** One commit holds the schema field and the prompt line that names it, so the prompt file shows under this piece. → code "system_prompt_web_edge.md"

Changed: **A comment written as a number is read as its text.** One answer of eight on case 03 was refused for a comment given as 2500. Both scopes share the comment type, so Web only follows. → test "comment written as a number"

## #edge-builder

The builder makes the edge sections after the web ones, from the sandbox's builder on today's library; each server call targets the jobs it lists, made by the web builder.

Calls reach jobs by name in the one jobs section, so a server that devices and people share is built once. The edge builders join the bootstrap DSL module rather than one of their own: they use its private helpers, and a second module would import them back.

Changed: **A server call lists every job it triggers.** The measured runs lost the database write behind an ingestion call, so devices and the dashboard shared no server; one server need now holds all the call's jobs.

## #edge-device-sizing

The answer gives each device's idle power, reserved RAM and reserved storage; one it omits is derived from the stated hardware, as the sandbox's builder does.

In 12 runs on cases 03 and 04, the AI set all three on every gateway and controller, within the device's limits, and every answer built; the derived idle power doubles case 04's device use. No weekly data fields: their buffers were 0.004 to 0.4 GB beside 2 to 8 GB reserved.

Changed: **An omitted reserved storage is a quarter of the device's storage, the library default at most.** The sandbox fitted it to weekly buffers, which the format dropped; the test's title now names storage.

## #device-groups

Devices described as deployed together become an optional group with counts per group and sub-groups; a deployment then counts one group, each device as many times as it holds.

Grouping stays the AI's choice: the sandbox's group-required check remains informative, and device totals are the correctness check. Groups are built children first, since a group takes its sub-groups at construction.

Changed: **A device written among a group's sub-groups counts as that device.** One nested answer in three was refused for that slip; the summary lists the move. A name that is neither a group nor a device still refuses the answer. → test "written as a sub-group"; test "declared neither as a group"; test "a sub-group no group declares"

Changed: **A device no deployment runs is listed as left out of the footprint.** It shows in its group on the canvas, yet the library counts neither its use nor its manufacturing. → test "is listed as left out"

Changed: **The summary's "Catalog substitutions" heading becomes "Changes made to the AI answer".** It already covered renamed labels and dropped comments, and now moved and left-out devices. The Web only summary changes too. → code "ai_bootstrap_summary.html"

## #deployments-over-time

Web usage runs from the earliest stated start (1 January 2027 by default) until the last device retires; deployments end with 2027; each may start later or end earlier.

Growth projection inputs are what the only hourly editor prefills; a raw series opens empty. A fleet in service since 2022 deploys from 2022, and its dashboard is counted for as long as devices report to it. The usage span defaults to the shortest device lifespan, six years at most; the sandbox's noon-of-day-one spike goes.

Changed: **A usage pattern may state its own start date.** The clause needs the usage's own start date and no place added the field; the Web + edge prompt alone offers it. → code "system_prompt_web_edge.md"

Changed: **Beyond the hourly editor's 10 years, web usage is cut and listed.** The editor silently cut a longer generated period on opening. Its limit now lives in one place, unchanged; a deployment longer than it is refused. → code "form_field_generator.py"; code "views_timeseries_preview.py"; code "usage_pattern_web_base_class.py"; code "hourly_quantities_from_growth.html"; code "usage_pattern_timeseries.js"; test "beyond the editor's limit"; test "until the last device retires, within the editor's limit"; test "until the last device retires [shared-period]"

Changed: **A deployment may state an end date.** Case 04's Dutch fleet no longer grows, and deploying it through 2027 put it a third too high; stated, the end date closes that deployment's period. → statement "end earlier"; test "stated end date closes"

Changed: **A stated web volume is that of 2027-01-01, discounted to an earlier start.** With a past start, a stated growth compounded from too high a base, 203 t against 10 in one run. The field's comment says how. → test "reaches its stated volume on 2027-01-01"

Changed: **A usage span above its devices' shortest lifespan is cut to it and listed.** The library refuses such a span, which refused the whole answer: three of eight at high effort. → test "usage span above its devices"

Changed: **The growth and recurrent editors accept any decimal.** A generated weekly volume, or a workload of 0.05, opened on a value the browser refused to save unchanged: 28 of 96 recorded answers. This changes these editors for every user. → code "recurrent_quantities_from_constant.html"; code "recurrent_quantities_from_weekly_pattern.html"; code "weekly_pattern_builder.js"

To confirm: **Should the hourly editor accept a negative growth rate?** The library computes a decline above −100 % a year, but the editor and its preview refuse one. A generated negative growth is set to 0 and listed for now; accepting it changes the editor for every user.

## #server-calls-scale

In the library, a server call's volume is multiplied by its device's total number of units, so calls scale with every device deployed, grouped or not.

Today RecurrentServerNeed scales its volume by deployments only, against its own parameter description. Fixed in e-footprint with its own commit range before the interface's lots, tested against the local checkout; no guard here. The interface's narrative case proves it across both.

Note: **The server need now owns the whole volume.** Renamed to hourly_volume_per_usage_pattern, it multiplies by the device's units per deployment and by deployments in parallel; a device in no group counts one unit, so a fleet total scales through deployments.

## The sandbox measures what ships

#scope-selects-format, #edge-instructions and #edge-builder: the sandbox's Web + edge scope reads the production instructions, schema and builder. Its own edge module goes but for its device-total check, redefined on devices in service during the web year. Handwritten answers 03 and 04 move to start dates; the narrative cases read them.

## Rules no test holds

- **one-request** The service calls the provider once on every path, and the scope only picks the instructions and the schema it sends; the existing service test of no retry holds the single call.
- **nothing-stored** The scope is a request field handed to the service and the response context; the saved modeling is the library graph's JSON, which has no place for it, and no new line writes the session.

## Delivery

- **library-server-calls** (easy) #server-calls-scale — In e-footprint, its own commits and tests, before every lot here. It has no site in this repository, so its narrative case moved to #edge-builder and the map reads this lot as delivered from the start.
- **scope-and-format** #edge-format #scope-selects-format #edge-instructions #scope-in-request — The scope carried to the schema, with no screen. #scope-selects-format and #edge-instructions are one commit: the table names the prompt file. That commit points the sandbox's Web + edge scope at production. No paid call.
- **edge-builder** (hard) #edge-device-sizing #device-groups #deployments-over-time #edge-builder — Hard: one period for web usage and deployments, from a past start to the last device's retirement, in the editor's fields. The last two pieces are one commit. Gate: paid runs of cases 03 and 04, on the user's word.
- **scope-choice** #scope-choice — Last: its disclosure states the cost and impact the gated runs measured, and its radio opens the Web + edge flow the earlier lots finished. The browser tests of the AI bootstrap run.
