# Generated operational models

`generate_current_projection.py` builds the first operational model of the current e-footprint-interface version from
the benchmark campaign and the documented adoption hypotheses. It emits five independent files because low, medium,
high, team-scale, and agent-scale adoption are alternatives rather than additive workloads.

From the `e-footprint-interface` repository:

```bash
poetry run python specs/e-footprint-modeling/models/generate_current_projection.py
```

The generated `current-low.e-f.json`, `current-medium.e-f.json`, `current-high.e-f.json`, `current-team.e-f.json`, and
`current-agent.e-f.json` files can be opened from the interface's **Open a file** action. Re-running the command replaces
those generated files deterministically.

The JSON `Sources` section and the `source`, `confidence`, and `comment` fields on inputs distinguish measurements,
user-provided scope, published reference data, and first-version hypotheses. The largest remaining limitation is that
browser action latency is being used as a proxy for server request duration until the correlated production logs are
extracted.

The application allocation currently models the production container as 4 vCPU and 2,926 MB process-visible RAM. Its
environmental proxy allocates 4/24 of a generic 24-core physical host: 100 kgCO₂e manufacturing, 50 W maximum power and
8.33 W idle power. The vCPU count is operator-provided; the proportional physical-host allocation remains a low-
confidence hypothesis until Clever Cloud hardware and allocation data are available.

The team and agent cases add S6, an automated build/maintenance journey that imports a model, changes an assumption,
computes results, inspects one explanation, and exports the updated model. S6 has no user-device time. Its totals cover
the load imposed on e-footprint-interface, not the external compute or inference used by the calling agent; that must
be added when agent model, token, region, and execution-host evidence exists.
