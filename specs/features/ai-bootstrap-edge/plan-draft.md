# Decisions already made — ai-bootstrap-edge

- Two scopes only, `web` and `web_edge`; no edge-only variant.
- One AI model for both scopes: `zai-glm-5-3-flash` on Mistral. Only `reasoning_effort` may differ by
  scope, chosen between `low` and `high`: Mistral refuses `medium` for this model (supported: low,
  high, max).
- The effort for each scope is chosen from sandbox runs (`ai_sandbox/`) restricted to
  `zai-glm-5-3-flash`. Paid runs need the user's word for each run. Web only, 2026-11-17 (cases 01
  and 02, no retry): low 6/6 first-try success, 18–28 s, about USD 0.0012 a call; high 6/6, 22–44 s,
  about USD 0.0020–0.0025 a call (about twice the output tokens), at the production adapter's 45 s
  timeout; one further high call lost its connection before answering. The checks pass at both
  efforts, so on these cases high buys no measured gain for Web only.
- The sandbox gets its edge material back from git history: commit `6671a149` removed the edge
  paradigm section of `system_prompt.md`, the `edge_devices` / `edge_functions` / `edge_deployments`
  format and field notes, the edge part of the DSL builder in `dsl.py`, the edge checks and reports,
  and case `03_smart_building_edge.json` with `_handwritten_03_smart_building.json`. Read it with
  `git show 6671a149^:ai_sandbox/<path>`. The library's edge API has moved since (edge usage journeys
  hold edge functions, `RecurrentServerNeed`, `EdgeDeviceGroup` with `sub_group_counts` and
  `edge_device_counts`); the old builder is a starting point, not a drop-in.
- `EdgeDeviceGroup` is part of the Web + edge format, optional: the prompt says when to use it
  (devices deployed together per site, vehicle or building), and never requires it.
- The scope travels with the generate request and is re-rendered on a refused generation; nothing
  of it is persisted.
