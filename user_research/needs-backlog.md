# Needs backlog

Aggregated, de-duplicated user needs, most-actionable first. Recurrence = number of distinct
sources that expressed it. Bump recurrence and link the source when a new source repeats a need.

## Parked / not yet scheduled

| Need | Recurrence | Sources | Status | Notes |
|------|:---:|---------|--------|-------|
| **Attribute network & end-user device impacts to a cloud *provider*** — only `Server`/`Storage` carry a provider, so per-provider totals exclude network and devices. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked (low priority) | Would require significant modeling work. Note: per-*tenant* attribution already covers all tiers, so this only limits supply-side (per-provider) breakdowns. |
| **Interface-editable timeseries builders** — unify `builders/timeseries` (form-input, editable in the interface) with the richer `time_builders` patterns. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked → interface feature | Tracked in e-footprint-interface `roadmap.md`; generalizes the recurrent-quantities weekly-pattern builder. Library tutorial covers discoverability meanwhile. |
| **Operational-data importers** — pull real usage from Vercel / Supabase / CloudWatch / Scaleway to replace hypotheses. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked | Fits the existing `builders/external_apis/` pattern (EcoLogits is the precedent). This is also the preferred path for the parked database modeling logic — ingest measured resource-time units (Aurora ACU, Neon CU, Azure vCore-s, GCP vCPU/GiB-hours); see e-footprint `specs/modeling_logic_roadmap.md`. |
| **Telemetry adapter** — OpenTelemetry span → Job energy/resources. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked | Would let measured spans feed jobs directly. |
| **Lighter authoring path** — CLI scaffolding (`init --template`) and a scenario file (companies, workflows/month) kept separate from the infrastructure model, for sensitivity runs. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked | The interface already covers part of the authoring need; CLI/scenario-file is additive. |
| **Standardized reporting export** — a GHG Protocol / ISO 14067 digital-service summary block (kg CO₂e by phase, by object category) alongside JSON. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked | Reporting-segment need; weigh against the deprioritized reporting audience in comms strategy. |
| **Third-party integration how-tos / templates** — background/OAuth sync workers, webhooks, PDF generation. | 1 | [ecoscan](2026-05-19-ecoscan.md) | parked (clarification pending) | Likely expressible today as Jobs on a server triggered by a usage pattern; pending confirmation of any real primitive gap. May become a docs task. |

## Roadmap (acknowledged long-term)

| Need | Recurrence | Sources | Status | Notes |
|------|:---:|---------|--------|-------|
| **Multicriteria impacts** — water, rare-earth metals, broader PEF set, beyond carbon. | 1 | [ecoscan](2026-05-19-ecoscan.md) | roadmap | Needs a new primitive carrying multiple impacts through the dependency graph; some adpe/pe/wue factors already plumbed (EcoLogits video, electricity mix) but parked. Tracked in e-footprint `specs/roadmap.md`. |

## Addressed by active work (kept for traceability)

| Need | Sources | Resolving work |
|------|---------|----------------|
| Discover & use serverless / per-invocation modeling (don't proxy as a low-utilization VM). | [ecoscan](2026-05-19-ecoscan.md) | e-footprint feature `saas-serverless-modeling-ergonomics` (how-to + discoverability). |
| Read footprint per tenant and per provider. | [ecoscan](2026-05-19-ecoscan.md) | Same feature — docs how-to. Per-tenant: one `UsagePattern` per tenant; per-usage-pattern attribution is built in and covers all tiers. Per-provider: group servers + storage by provider in code. |
| Model a managed database (Supabase/Neon/RDS). | [ecoscan](2026-05-19-ecoscan.md) | Same feature — **docs-only how-to** composing existing primitives (server + storage + jobs); managed = serverless host. The query→resource *modeling logic* is parked → e-footprint `specs/modeling_logic_roadmap.md` (no defensible general model; future path is measured resource-time telemetry). |
| Discover the timeseries builders (don't hand-author 8760 values). | [ecoscan](2026-05-19-ecoscan.md) | Already demonstrated in the library tutorial (uses `time_builders`; no 8760 enforcement). |
| Boavizta API called at import time (slow/offline tests). | [ecoscan](2026-05-19-ecoscan.md) | e-footprint Boavizta import-time fix (lazy load + bundled snapshot). |
| Python install fails on newest interpreter; packaging/DX (wheels, Docker, minimal extra). | [ecoscan](2026-05-19-ecoscan.md) | e-footprint feature `packaging-and-dx` (rolling support window + CI matrix + Docker; deps unchanged — zstd kept per benchmark). Optional heavy deps (viz, pandas) parked on the memory-optimization track. |
