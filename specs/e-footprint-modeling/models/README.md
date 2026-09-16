# Generated operational models

`generate_current_projection.py` builds operational models from one shared set of journeys and adoption hypotheses plus
an explicit implementation profile. The maintained comparison deliverables are five workspace files: one per adoption
scenario, with the current optimized system and the no-AI, low-optimization system as sibling models. This lets **Open
a file** restore the pair and enables the interface's comparison view immediately.

From the `e-footprint-interface` repository:

```bash
# Regenerate the five comparison workspaces
poetry run python specs/e-footprint-modeling/models/generate_current_projection.py \
  --implementation comparison

# Generate the standalone current models when needed for diagnostics
poetry run python specs/e-footprint-modeling/models/generate_current_projection.py

# Generate standalone no-AI, low-optimization models when needed for diagnostics
poetry run python specs/e-footprint-modeling/models/generate_current_projection.py \
  --implementation no-ai-low-optim

# Regenerate both implementation profiles
poetry run python specs/e-footprint-modeling/models/generate_current_projection.py \
  --implementation all
```

The generated `current-vs-no-ai-low-optim-{low,medium,high,team,agent}.e-f.json` files can each be opened from the
interface's **Open a file** action. The current optimized model is the active Reference slot and the counterfactual is
the Comparison slot. Both siblings preserve the same semantic object IDs so changed jobs and infrastructure pair
directly in the comparison instead of appearing as removed and added objects. Re-running the command replaces the
workspace files deterministically.

Within each workspace, the siblings use the same traffic, geography, journeys, user devices and network assumptions.
Only the implementation-dependent action durations, transferred bytes and selected Docker tier differ. Their source of
truth is [`../optimizations/implementation-profiles.json`](../optimizations/implementation-profiles.json); the profile
retains eager selective recomputation and a partial NumPy implementation while removing the other identified speed and
memory optimizations. AI development and runtime inference remain outside both operational profiles. Standalone files
remain generator options, but are not needed for the maintained comparison workflow.

The JSON `Sources` section and the `source`, `confidence`, and `comment` fields on inputs distinguish measurements,
user-provided scope, published reference data, and first-version hypotheses. The largest remaining limitation is that
browser action latency is being used as a proxy for server request duration until the correlated production logs are
extracted.

The application allocation currently models the production container as 4 vCPU and 2,926 MB process-visible RAM. Its
environmental proxy allocates 4/24 of a generic 24-core physical host: 100 kgCO₂e manufacturing, 50 W maximum power and
8.33 W idle power. The vCPU count is operator-provided; the proportional physical-host allocation remains a low-
confidence hypothesis until Clever Cloud hardware and allocation data are available.

The no-AI profile reconstructs a 23,020 MiB maximum request. Tier selection subtracts the provisional 1.1 GiB
unavailable allowance and applies the 85% computation ceiling to each catalog tier, selecting 3XL (16 vCPU, 32 GiB
nominal, 30.9 GiB process-visible and about 26.3 GiB safe). If future evidence changes the maximum request, the generator
reselects the smallest sufficient tier and fails explicitly if the documented 3XL ceiling is exceeded.

The team and agent cases add S6, an automated build/maintenance journey that imports a model, changes an assumption,
computes results, inspects one explanation, and exports the updated model. S6 has no user-device time. Its totals cover
the load imposed on e-footprint-interface, not the external compute or inference used by the calling agent; that must
be added when agent model, token, region, and execution-host evidence exists.
