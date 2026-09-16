# No-AI, low-optimization projection v1 — 2026-09-16

This central counterfactual keeps the current product, journeys, traffic, geography, user devices and network. It
retains eager selective recomputation and a partial NumPy implementation. It removes pull computation and the other
identified speed and memory optimizations. AI development and inference footprints are not modeled.

## Implementation profile

- Weighted modeled actions are about 4.8–5.4× slower depending on the adoption mix. Individual journey estimates are
  5.9× for S1, 6.5× for S2, 5.2× for S3, 4.1× for S4, 4.4× for S5 and 4.8× for S6.
- The maximum-request reconstruction starts from the measured 2,674 MiB five-pattern cold-Sankey peak before bounded
  attribution retention. Removing the pull-engine memory benefit, full NumPy, float32, lazy compression and
  explanation-parent cleanup gives 23,020 MiB (about 22.5 GiB).
- The repeated-load `__slots__` factor is excluded from the fresh-request peak.
- With 1.1 GiB provisionally unavailable and an 85% computation ceiling, 2XL provides only about 19.5 GiB safe RAM.
  The smallest sufficient catalog tier is therefore 3XL: 16 vCPU, 32 GiB nominal, 30.9 GiB process-visible and about
  26.3 GiB safe RAM.
- The generic physical-host proxy allocates 16/24 of a 600 kg, 300 W maximum, 50 W idle reference host to each 3XL
  instance. This is a low-confidence environmental allocation, not a claim about Clever Cloud hardware.

## Generated results

The total footprint includes identical user-device time in both implementations. The server-only comparison therefore
shows the operational implementation difference more directly than the total-system ratio.

Each row is maintained as one `current-vs-no-ai-low-optim-<scenario>.e-f.json` workspace. Opening it loads the current
system as the Reference and the counterfactual as its Comparison sibling, ready for the interface comparison view.

| Scenario | Usage occurrences | Current total | No-AI total | Total ratio | Current server | No-AI server | Maximum instances current → no-AI |
|---|---:|---:|---:|---:|---:|---:|---:|
| Low | 6,875 | 100.723 kgCO₂e | 244.820 kgCO₂e | 2.43× | 47.908 kgCO₂e | 191.877 kgCO₂e | 1 → 1 |
| Medium | 11,375 | 124.448 kgCO₂e | 269.005 kgCO₂e | 2.16× | 47.927 kgCO₂e | 192.215 kgCO₂e | 1 → 1 |
| High | 42,125 | 285.601 kgCO₂e | 434.309 kgCO₂e | 1.52× | 48.099 kgCO₂e | 195.343 kgCO₂e | 1 → 1 |
| Team | 391,625 | 922.385 kgCO₂e | 1,119.374 kgCO₂e | 1.21× | 49.220 kgCO₂e | 228.100 kgCO₂e | 1 → 3 |
| Agent | 3,826,625 | 1,294.684 kgCO₂e | 2,120.339 kgCO₂e | 1.64× | 71.090 kgCO₂e | 692.284 kgCO₂e | 5 → 21 |

The quiet scenarios are dominated by the minimum provisioned container: the 3XL allocation makes their server
footprint about four times the current M allocation even before traffic causes additional instances. In the agent case,
slower actions increase the hourly peak to 21 instances and the server footprint to about 9.7× current.

These are scenario results, not measured historical behavior. The most consequential uncertainties are the
counterfactual memory-factor overlap, the provisional 1.1 GiB reserve on 3XL, action CPU occupancy and the generic
vCPU-proportional physical-host proxy. Price is retained in the profile as a financial co-benefit but is not used as an
environmental factor.
