# No-AI, low-optimization projection v1 — 2026-09-16

This central counterfactual keeps the current product, journeys, traffic, geography, user devices and network. It
retains eager selective recomputation and a partial NumPy implementation. It removes pull computation and the other
identified speed and memory optimizations. AI development and inference footprints are not modeled.

## Implementation profile

- Weighted modeled actions are about 4.76–4.79× slower depending on the adoption mix. Individual journey estimates are
  6.3× for S1, 4.9× for S2, 5.5× for S3, 4.0× for S4, 4.4× for S5 and 4.8× for S6.
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
| Niche, human-led | 42,586 | 412.372 kgCO₂e | 932.169 kgCO₂e | 2.26× | 171.375 kgCO₂e | 689.434 kgCO₂e | 1 → 1 |
| Central, human-led | 233,172 | 1,466.290 kgCO₂e | 2,014.227 kgCO₂e | 1.37× | 172.532 kgCO₂e | 711.608 kgCO₂e | 1 → 1 |
| Central, team-integrated | 859,863 | 1,725.515 kgCO₂e | 2,397.446 kgCO₂e | 1.39× | 176.404 kgCO₂e | 805.254 kgCO₂e | 1 → 2 |
| Breakout, team-integrated | 5,396,553 | 10,143.556 kgCO₂e | 12,085.548 kgCO₂e | 1.19× | 220.877 kgCO₂e | 1,895.080 kgCO₂e | 2 → 10 |
| Breakout, agent-intensive | 59,922,943 | 13,132.649 kgCO₂e | 30,418.219 kgCO₂e | 2.32× | 893.788 kgCO₂e | 14,937.593 kgCO₂e | 22 → 102 |

The lower-volume scenarios are dominated by the minimum provisioned container: the 3XL allocation makes their server
footprint about four times the current M allocation even before traffic causes additional instances. In the breakout
agent-intensive case, slower actions increase the hourly peak from 22 to 102 instances and the server footprint to
about 16.7× current.

These are scenario results, not measured historical behavior. The most consequential uncertainties are the
counterfactual memory-factor overlap, the provisional 1.1 GiB reserve on 3XL, action CPU occupancy and the generic
vCPU-proportional physical-host proxy. The human pattern uses horizon-average S1–S5 weights, preserving cumulative
journey totals while smoothing their timing. Price is retained in the profile as a financial co-benefit but is not used
as an environmental factor.
