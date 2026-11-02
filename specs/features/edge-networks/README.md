# Edge wireless networks — feature roadmap

Model the energy and carbon of local wireless IoT links (device radio → gateway → backhaul) in e-footprint and
expose them in the interface. Two specs, delivered in order; each goes through the normal
specify → plan → tasks → implement → archive stages in its own repository.

| # | Spec | Repository | Status | Depends on |
|---|------|-----------|--------|------------|
| 1 | [Library modeling](../../../../e-footprint/specs/features/edge-networks/spec.html) · [draft plan](../../../../e-footprint/specs/features/edge-networks/plan.html) | `e-footprint` | Spec under review · 2026-11-02 | — |
| 2 | [Interface](spec.html) | `e-footprint-interface` | Spec under review · 2026-11-02 | Spec 1 shipped and published to PyPI; interface dependency bumped |

## Why two specs

The library owns the modeling semantics (three-term power model, owned gateway as a countable unit, operator
network as a per-device-hour allocation). The interface adds object types to existing mechanics (component
accordions, need accordions, group membership, results surfaces) and only makes sense once the library objects
exist with their docstrings and parameter descriptions, which the interface reads as its single source of truth.
Splitting keeps each plan reviewable in one pass and lets the interface spec start from shipped library behavior
rather than assumptions about it.

## Sequence

1. **Library** (`e-footprint/specs/features/edge-networks/`): review `spec.html`, refine the draft `plan.html` in a
   fresh `spec-plan` session, then tasks and implementation. The draft plan suggests delivery runs A (technology
   table, interface component, messaging need, operator rows), B (lift the shared hardware-unit parent out of
   `EdgeDevice`), C (gateway, link guard, Sankey atoms), D (registration, docs, changelog).
2. **Publish** the library to PyPI and bump the interface's `efootprint` dependency (constitution gate: PyPI
   dependency, not an editable path, before any commit reaches `main`). During co-development, shadow the local
   checkout as described in `INSTALL.md`.
3. **Interface** (`specs/features/edge-networks/`): review `spec.html`, then `spec-plan` → `spec-tasks` →
   `feature-implement` → `feature-archive`.

## Source documents (kept until both specs archive)

- [`2026-07-06-edge-network-spec-draft.md`](2026-07-06-edge-network-spec-draft.md) — the kickoff draft: objects,
  formulas, default parameter table, design choices.
- [`2026-07-06-edge-network-modeling-note.md`](2026-07-06-edge-network-modeling-note.md) — literature review behind
  the power model, allocation keys and embodied factors.
- [`2026-02 initial exploration on Networks/`](2026-02%20initial%20exploration%20on%20Networks/) — the naive first
  exploration and the 2026-07-06 feedback on it.

## Decisions already taken (do not reopen without new evidence)

- Power model (sleep floor + per-message + synchronization), never kWh/GB, for the device radio and gateway.
- Six v1 technologies in one default table: LoRaWAN, SIGFOX, NB-IoT, BLE, WiFi (power-saving), Thread.
- No distance scaling of transmit power; a single integer hop multiplier for mesh.
- Owned gateway is its own object type with a shared abstract parent with `EdgeDevice`, counted through
  `EdgeDeviceGroup` (names kept); no devices-per-gateway input; no sharing-fraction input.
- Operator networks (NB-IoT, SIGFOX) are per-device-hour allocation rows, not objects.
- Battery-to-lifespan coupling deferred to v2.

## Open across both specs

- Backhaul: the library spec recommends no payload-to-network data path (the server-side job already carries the
  bytes). Confirm during library spec review; the interface results mockup assumes it.
