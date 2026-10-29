# Feedback on early exploration (naive_e2e_networks_modeling)

Date: 2026-07-06 · Refers to: `inputs/2026-02-26-naive_e2e_networks_modeling.docx` · Companion: `2026-07-06-edge-network-modeling-note.md`

## Sound and aligned with literature

- Items 1–3: 4-state ΣP×t core — exactly the consensus structure across the device-energy literature (Martinez, Casals, Bouguera, Lauridsen, Andres-Maldonado, Gomez).
- Items 5–6: protocol overhead + fragmentation via Nfr — correct reading of the seed article.
- Item 7: Ntr = 1/(1−PER) — correct (1.25 for 20% loss).
- Items 8–10: idle/Rx add-ons, sync energy, sleep as remaining time — correct, and item 10 captures the crucial sleep-floor effect (Morin finding: P_Sleep dominates lifetime at low traffic).
- Item 13: amortize infrastructure LCA per message — right instinct, matches ITU-T allocation logic and Ruiz et al.

## Issues

- **Items 4 & 6 — dimensional error**: "time spent in TX = speed of transmission × qty of bits" — must be *divide*: `t_TX = bits / bitrate`. (Multiplying gives bits²/s.)
- **Item 11 — distance scaling of P_TX**: `P_TX_real = P_TX × (d_real/d_max)` is not physically grounded. Radio link budget scales *received* power as d^−n (n≈2–4), so required *radiated* power would scale as (d/d_max)^n — but radiated power is only part of P_TX (fixed circuit/PA overhead dominates at low output; PA efficiency ~37% for NB-IoT per Lauridsen), and real devices have discrete Tx power steps. Distance-based continuous scaling adds parameters and false precision without accuracy. **Dropped in the spec**: technology choice + datasheet P_TX already encode range class.
- **Item 12 — Nsegments = d_real/d_max**: LPWAN/cellular/WiFi are star topologies — one hop to gateway, no chaining of segments. Multi-hop only exists in mesh technologies (802.15.4/Thread, BLE mesh). **Replaced in the spec** by optional integer `n_hops` (default 1) for mesh cases.
- **Missing — device embodied footprint**: Ruiz et al. find 68–86% of wireless-network footprint sits in end-user devices, mostly fabrication. The transmission-energy term is small; the embodied term must not be an afterthought. (e-footprint's `EdgeDevice` fabrication amortization covers this — the radio module becomes one more component.)
- **Missing — synchronization as recurring term**: sync/keep-alive cost exists whether or not messages are sent (item 9 touches it but ties it to transmission periodicity). Measured Matter-over-Thread data (Nordic nwp_049) shows keep-alive polling is 94.5–99.3% of annual energy — the spec makes it an explicit third term.
- **Framing** — don't collapse to kWh/GB: Mytton/Malmodin/Guennebaud show network energy ≠ proportional to volume. The docx's structure (per-message + sleep floor) is already the right "power model"; keep it, never convert to per-GB.
