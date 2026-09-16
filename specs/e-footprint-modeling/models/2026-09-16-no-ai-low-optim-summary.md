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
system as the Reference and the counterfactual as its Comparison sibling, ready for the interface comparison view. The
Sep 2025–Dec 2033 totals include adoption growth through Dec 2032 and a complete stationary year in 2033.

| Scenario | Usage occurrences | Current total | No-AI total | Total ratio | Current server | No-AI server | Maximum instances current → no-AI |
|---|---:|---:|---:|---:|---:|---:|---:|
| Niche, human-led | 42,586 | 411.813 kgCO₂e | 928.112 kgCO₂e | 2.25× | 171.216 kgCO₂e | 686.493 kgCO₂e | 1 → 1 |
| Central, human-led | 233,172 | 1,463.330 kgCO₂e | 1,993.010 kgCO₂e | 1.36× | 171.704 kgCO₂e | 696.258 kgCO₂e | 1 → 1 |
| Central, team-integrated | 859,863 | 1,717.194 kgCO₂e | 2,319.535 kgCO₂e | 1.35× | 173.872 kgCO₂e | 737.688 kgCO₂e | 1 → 1 |
| Breakout, team-integrated | 5,396,553 | 10,074.792 kgCO₂e | 11,417.459 kgCO₂e | 1.13× | 188.468 kgCO₂e | 1,292.223 kgCO₂e | 2 → 5 |
| Breakout, agent-intensive | 59,922,943 | 12,469.467 kgCO₂e | 23,803.365 kgCO₂e | 1.91× | 568.776 kgCO₂e | 8,694.853 kgCO₂e | 13 → 58 |

The lower-volume scenarios are dominated by the minimum provisioned container: the 3XL allocation makes their server
footprint about four times the current M allocation even before traffic causes additional instances. In the breakout
agent-intensive case, slower actions increase the hourly peak from 13 to 58 instances and the server footprint to about
15.3× current.

These are scenario results, not measured historical behavior. The most consequential uncertainties are the
counterfactual memory-factor overlap, the provisional 1.1 GiB reserve on 3XL, action CPU occupancy and the generic
vCPU-proportional physical-host proxy. Price is retained in the profile as a financial co-benefit but is not used as an
environmental factor.
