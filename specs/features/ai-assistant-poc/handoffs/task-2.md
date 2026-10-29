# Task 2 — Builder tables and read-back
Repositories and implementation ranges: e-footprint-interface `7fbeac3e..a9f11234`.

## Review pointers
- `_Shared.label` became the module function `_label(name, resolutions)`, so `build_server` and the other builders
  take no `_Shared` except `build_usage_pattern`. It is now called once per server instead of twice (storage name and
  server name), which drops a duplicate "humanized" resolution; the dry-run export is otherwise identical modulo ids.
- `ai_sandbox/edit.py` `library_objects(system)` returns each DSL section's library objects as lists (duplicates
  kept) for task 3's name lookups. Jobs that are neither `Job`/`GPUJob` nor a GenAI job (e.g. video-generation jobs
  in `genai_video`) read back as name only, so steps still list them; a plain `Server` reads back without
  `cloud_provider`/`instance_type` but keeps `carbon_intensity_g_per_kwh` and `storage_gb`.
- Read-back of a form series converts a non-yearly growth timespan to a yearly rate; a non-form series reads back as
  its average yearly total (`sum * 8760 / len`), growth 0. Step weights round to at least one listing.

## Open concerns
- Unverified items settled: every bundled example (library `ecommerce`, `machine_learning_workflow`, interface
  introductory examples) has single-journey patterns with form series; the non-form path was exercised by replacing
  `ecommerce`'s series in memory (5.84 M over 3 years read back as 1 947 840 per year).
