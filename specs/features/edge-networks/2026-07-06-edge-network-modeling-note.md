# Edge/IoT networks in e-footprint — literature review

Date: 2026-07-06
Seed article: Morin et al. 2017. Companion documents: `2026-07-06-edge-network-spec-draft.md` (spec), `2026-07-06-early-exploration-feedback.md` (comments on the initial exploration).

---

## 1. Seed article — Morin et al. 2017

**Comparison of the Device Lifetime in Wireless Networks for the Internet of Things** — É. Morin, M. Maman, R. Guizzetti, A. Duda (IEEE Access, 2017). [ResearchGate](https://www.researchgate.net/publication/316021797_Comparison_of_the_Device_Lifetime_in_Wireless_Networks_for_the_Internet_of_Things) — open-source analyzer: https://gitlab.imag.fr/morine/iot-analyzer

Key points:
- 4-state energy model: **E(t) = Σ_S P_S × t_S**, S ∈ {Tx, Rx, Idle, Sleep} (Eq. 3). Per-state powers from best-in-class hardware (Tables V–VI); state durations derived from MAC-layer operation of each technology.
- Technologies compared on equal basis: BLE, 802.15.4, TSCH, 802.11 PSM, 802.11ah, LoRa, SIGFOX. Application model: payload s_a every period t_a.
- Protocol overhead & fragmentation: Nfr frames per application packet (max payload per technology); retransmissions **Ntr = 1/(1−PER)** (Eq. 5); synchronization cost for synchronous technologies (keep-alive every t_syn); clock-drift guard time Tg = 2Δ·t_CI (Eq. 6).
- Validated within 5–7% of published measurements (SmartMeshIP, GreenNet, Siekkinen, Martinez).
- **Findings that matter for a simplified model**:
  1. At low traffic intensity, **P_Sleep dominates lifetime** — not Tx/Rx. A per-message-only model is wrong at low rates.
  2. Retransmissions (PER = 0.2) change absolute values ~10% but never the technology ranking → a footprint model can treat PER as a second-order correction.
  3. Asynchronous technologies (LoRa, SIGFOX) win at very low rates because they pay no synchronization/guard-time cost.
  4. Energy per delivered bit explodes for small payloads (fixed overhead dominance).

Limits (stated by authors): single-link star topology, uplink only, no state-transition energy, linear battery model, no security overhead.

---

## 2. Literature review

### A. Device-level energy models (parametric, per-technology)

1. **Martinez, Montón, Vilajosana, Prades (2015)** — *The Power of Models: Modeling Power Consumption for IoT Devices*, IEEE Sensors Journal 15(10). [PDF](http://mariusmonton.com/wp-uploads/2011/01/JSEN2445094.pdf)
   - System-level decomposition: communication + processing + sensing + sleep baseline; E = Σ (energy profile × event frequency) + P_sleep floor.
   - Applied to real SIGFOX smart-parking device; non-radio overheads (MCU wake-up, sensing) can dominate at low message rates.
   - Methodological ancestor of Morin et al.; designed to parameterize from datasheets.
   - → Exactly the abstraction level for e-footprint: `E = baseline + N_msg × E_per_message`.

2. **Casals, Mir, Vidal, Gomez (2017)** — *Modeling the Energy Performance of LoRaWAN*, Sensors 17(10):2364. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5677147/)
   - Measurement-calibrated 11-state model of LoRaWAN Class A device; closed-form time-on-air from SF/BW/payload.
   - DR5 ≈ 2.76× less energy than DR0; energy per bit rises ~2 orders of magnitude for tiny payloads.
   - Retransmissions in acknowledged mode: up to 10× current increase at BER 10⁻³.
   - 2400 mAh, 1 msg/5 min → ~1 year; asymptotic max ~6 years (sleep floor).
   - → Ready per-state currents/durations + energy-per-message(payload, DR) for LoRaWAN defaults.

3. **Bouguera et al. (2018)** — *Energy Consumption Model for Sensor Nodes Based on LoRa and LoRaWAN*, Sensors 18(7):2104. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6068831/) / [HAL](https://hal.science/hal-01828769v1)
   - E_total = E_sleep + E_active (6 active components: wake-up, measurement, processing, transceiver wake-up, Tx, Rx/ACK).
   - Parameterized by SF, BW, coding rate, payload, Tx power; ACK reception costs 12–22% of battery life.
   - → Cleanest per-message decomposition, maps one-to-one to a parametric function with defaults.

4. **Lauridsen et al. (2018)** — *An Empirical NB-IoT Power Consumption Model for Battery Lifetime Estimation*, IEEE VTC Spring. [AAU open access](https://vbn.aau.dk/en/publications/an-empirical-nb-iot-power-consumption-model-for-battery-lifetime-/)
   - Measured commercial NB-IoT devices: Tx@23dBm ≈ 710–840 mW, Rx ≈ 210–240 mW, DRX sleep ≈ 21–23 mW, PSM ≈ 14–35 µW.
   - Real devices consume more than 3GPP theory → 21–85% shorter battery life; beware datasheet-only parameterization.
   - → Measured 4-state numbers for the cellular-IoT branch.

5. **Andres-Maldonado et al. (2019)** — *Analytical Modeling and Experimental Validation of NB-IoT Device Energy Consumption*, IEEE IoT Journal 6(3). [AAU](https://vbn.aau.dk/en/publications/analytical-modeling-and-experimental-validation-of-nb-iot-device-)
   - Closed-form 6-state Markov model, validated on commercial UEs; max lifetime error ~21%.
   - Coverage class (repetitions) as energy multiplier — the NB-IoT analogue of LoRa SF.
   - → Proves state-weighted average-power models are accurate enough (~20%) for footprint-grade estimates.

6. **Gomez et al. (2019)** — *A Sigfox Energy Consumption Model*, Sensors 19(3):681. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6387435/)
   - Measured SIGFOX state machine incl. mandatory triple transmission; bidirectional costs up to 4× unidirectional.
   - 2400 mAh, 1 msg/10 min → 1.5–2.5 years; asymptotic 14.6 years.
   - → Completes LPWAN trio; enables one unified function with per-technology parameter tables.

7. **Kim, Kumar, Culler (2019)** — *Thread/OpenThread: A Compromise in Low-Power Wireless Multihop Network Architecture for the IoT*, IEEE Communications Magazine 57(7). [PDF](https://rise.cs.berkeley.edu/wp-content/uploads/2019/06/KIM_LAYOUT.pdf)
   - First academic analysis of Thread; OpenThread on RIOT-OS/Hamilton platform.
   - Leaf (sleepy end device) "wakes, sends, sleeps" — no rendezvous cost; ~30 µA average at 10 s TX period → 5.3 yr on 1400 mAh.
   - Routers always-on, only leaves sleep → model applies radio states to end devices only.
   - → Peer-reviewed anchor for Thread defaults and validation target.

8. **Nordic Semiconductor (2023, vendor measurement)** — *Analyzing Power Consumption in Thread Sleepy End Devices*. [blog](https://devzone.nordicsemi.com/nordic/nordic-blog/b/blog/posts/analyzing-power-consumption-in-thread-sleepy-end-devices)
   - nRF52840, 3 V, 0 dBm, PPK2: sleep floor 2.65 µA (SED) / 2.70 µA (SSED); 17.63 µC per data poll (≈53 µJ); SSED (CSL) ~12% lower at 1 s poll.
   - → Direct per-poll fixed energy + sleep floor defaults for Thread.

9. **Nordic Semiconductor (2025, vendor white paper)** — *Matter over Thread: Power Consumption and Battery Life*, nwp_049. [PDF](https://www.globalspec.com/NordicSemiconductorASA/ref/nwp_049.pdf)
   - Real Matter devices (door lock, alarm, covering) on nRF52840/nRF5340/nRF54L15, commercial ecosystems.
   - **Idle networking (keep-alive polling + subscriptions) = 94.5–99.3% of annual energy** → synchronization must be a separate recurring term in any model.
   - Annual figures: door lock 78–113 mAh/yr; extra ecosystem subscription +23%.
   - → Richest Thread defaults source; poll-period sensitivity.

10. **McGuinness (2025, independent measurement — not peer-reviewed)** — *Matter — Low Power on an ESP32-H2*. [blog](https://tomasmcguinness.com/2025/08/29/matter-low-power-on-an-esp32-h2/)
    - ESP32-H2 ≈ 16× worse than nRF52840 builds; board regulator/peripherals cost 3× the chip.
    - → Upper-bound sanity check; shows the SoC spread that defaults must span.

Note: only Kim et al. is peer-reviewed for Thread specifically; vendor sources flagged as such.

### B. Network energy allocation for footprinting

11. **Coroamă & Hilty (2014)** — *Assessing Internet energy intensity*, Env. Impact Assessment Review 45. [DOI](https://doi.org/10.1016/j.eiar.2013.12.004)
    - Published kWh/GB estimates diverge by ~4 orders of magnitude; boundary definition is the main cause.
    - → Any energy-intensity parameter must state boundary + year.

12. **Coroamă, Schien, Preist, Hilty (2014)** — *The Energy Intensity of the Internet: Home and Access Networks*, Springer. [DOI](https://doi.org/10.1007/978-3-319-09228-7_8)
    - Home router/CPE power ≈ constant, traffic-independent → time-based or per-subscriber allocation, not per-GB.
    - Core networks: volume-proportional sharing acceptable (dimensioned for aggregate traffic).
    - → Direct precedent for hybrid model: baseline power × time locally, kWh/GB upstream.

13. **Aslan, Mayers, Koomey, France (2018)** — *Electricity Intensity of Internet Data Transmission*, J. Industrial Ecology 22(4). [open access](https://onlinelibrary.wiley.com/doi/10.1111/jiec.12630)
    - Harmonized fixed-line intensity: 0.06 kWh/GB (2015), halving every ~2 years; boundary excludes CPE/WiFi/user devices.
    - → Source of e-footprint's existing kWh/GB convention; proves its boundary stops before the edge segment (no double counting).

14. **Mytton, Lundén, Malmodin (2024)** — *Network energy use not directly proportional to data volume: the power model*, J. Industrial Ecology 28(4). [open access](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13512)
    - Network energy = per-connection baseline + small marginal per-GB term; kWh/GB alone contradicted by idle power of routers/base stations.
    - Reference: fixed broadband line ≈ 160 kWh/yr (~18 W); mobile subscription ≈ 20 kWh/yr.
    - → Main methodological blueprint for the edge extension.

15. **Coroamă (2021)** — *Investigating the Inconsistencies among Energy and Energy Intensity Estimates of the Internet*, SFOE report. [PDF](https://vs.inf.ethz.ch/publ/papers/Coroama2021_InternetEnergy.pdf)
    - Average intensity = valid attributional key; marginal intensity ≈ 0 short-term; never mix the two.
    - → Documents which allocation logic e-footprint should expose and state.

16. **Guennebaud & Bugeau (2024)** — *Energy consumption of data transfer: intensity indicators versus absolute estimates*, J. Industrial Ecology 28(4). [DOI](https://doi.org/10.1111/jiec.13513)
    - Parametric bottom-up territory-scale model; energy follows dimensioning (busy-hour peak), not transferred volume.
    - → Closest in spirit to e-footprint; supports uptime/capacity-based edge allocation.

### C. Embodied carbon of devices & infrastructure

17. **Pirson & Bol (2021)** — *Assessing the embodied carbon footprint of IoT edge devices with a bottom-up life-cycle approach*, J. Cleaner Production 322. [arXiv](https://arxiv.org/abs/2105.02082)
    - Parametric functional-block model (processing, connectivity, PCB, casing, power…); >150× spread across device classes — no single average valid.
    - Basis of BoaviztAPI IoT module. Follow-up applies it to LPWAN sensor nodes incl. transmission energy ([Pirson et al., ACM IoT 2022](https://dl.acm.org/doi/abs/10.1145/3567445.3567448)).
    - → Canonical source for embodied factors of device + gateway; maps directly to e-footprint objects.

18. **La Rocca, Guennebaud, Bugeau, Ligozat (2024)** — *Estimating the carbon footprint of digital agriculture deployment*, J. Industrial Ecology 28(6). [arXiv](https://arxiv.org/abs/2409.17617)
    - Extends Pirson & Bol to fleet/territory scale; fleet composition dominates total footprint.
    - → Closest published analogue to the whole exercise; template for deployment-level modeling.

19. **Ruiz et al. (2022)** — *LCI and carbon footprint of wireless ICT networks for six demographic areas*, Resources, Conservation & Recycling 176. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0921344921005607)
    - Full 4G network LCA: 81–103 kgCO2e/subscription/yr (1.35–1.73 kgCO2e/GB); **68–86% from end-user devices, mostly embodied**; rural density penalty.
    - → Per-subscription allocation figures + proof embodied dominates.

20. **Malmodin & Lundén (2018)** — *Energy and Carbon Footprint of Global ICT and E&M Sectors 2010–2015*, Sustainability 10(9). [MDPI](https://www.mdpi.com/2071-1050/10/9/3027)
    - Operator-data-based sector totals; per-subscription network figures declining despite traffic growth.
    - → Top-down anchor / sanity check for per-subscriber amortization defaults.

21. **ITU-T L.1410 (2024) / L.1450 (2025)** — LCA methodology for ICT goods, networks, services. [L.1410](https://www.itu.int/epublications/publication/itu-t-l-1410-2024-11-methodology-for-environmental-life-cycle-assessments-of-information-and-communication-technology-goods-networks-and-services) / [L.1450](https://www.itu.int/epublications/publication/itu-t-l-1450-2025-12-methodologies-for-the-assessment-of-the-environmental-impact-of-the-information-and-communication-technology-sector)
    - Standard allocation keys for shared infrastructure (volume, subscription, time), chosen and justified per segment; embodied impacts mandatory; screening tiers legitimize simplified parametric approach.
    - → Standards cover for e-footprint's allocation choices.

22. **Freitag et al. (2021)** — *The real climate and transformative impact of ICT*, Patterns 2(9). [open access](https://www.sciencedirect.com/science/article/pii/S2666389921001884)
    - ~23% of ICT footprint is embodied; truncation of embodied emissions is the main systematic bias; IoT growth a key driver.
    - → Justifies embodied amortization in scope.

**Gap noted**: no published standalone LCA of a LoRaWAN gateway or NB-IoT base station. Substitute: build gateway profile from Pirson & Bol functional blocks, or per-subscriber figures from Ruiz/Malmodin.

---

## 3. Recommended formula

Consensus structure across all sources — a **power model**, not a per-GB model, with three additive blocks:

### Block 1 — device transmission energy (per device, per hour)

```
E_device_hour = P_sleep × Δt  +  N_msg × E_msg  +  N_sync × E_sync

E_msg  = E_fixed  +  Ntr × Nfr × (b_frame / R) × P_tx  +  t_rx × P_rx
N_sync = max(0, Δt / t_sync − N_msg)     # data frames count as sync; 0 for asynchronous technologies

with:
  Nfr     = ceil(s_a / max_payload)              # fragmentation
  b_frame = payload_per_frame + overhead_bits    # protocol overhead
  Ntr     = 1 / (1 − PER)                        # retransmissions, default PER = 0
  E_fixed = wake-up + idle energy per message (per-technology constant)
  E_sync  = one keep-alive/poll exchange; t_sync = keep-alive period
  R       = bitrate; t_rx = ACK/poll listen time
```

The separate synchronization term is load-bearing: for Matter-over-Thread devices, keep-alive polling represents 94.5–99.3% of annual energy (Nordic nwp_049) — folding it into per-message energy would zero it out for rarely-messaging devices. Same mechanism covers BLE connInterval polls and WiFi beacon listens; asynchronous technologies (LoRa, SIGFOX) set t_sync = ∞.

Per-technology parameter table {P_tx, P_rx, P_sleep, R, overhead_bits, max_payload, E_fixed, t_sync, E_sync}, defaults from: Morin (BLE, 802.15.4/Thread, WiFi), Casals/Bouguera (LoRaWAN), Gomez (SIGFOX), Lauridsen (NB-IoT), Kim/Nordic (Thread). Optional integer `n_hops` (default 1) multiplies E_msg for mesh technologies.

### Block 2 — gateway / local infrastructure (shared, time-allocated)

```
footprint_gateway_per_device_hour =
    ( GWP_fab_gateway / lifespan  +  P_gateway × CI_elec ) / N_devices_served
```

Time/subscriber allocation, not per-GB (Mytton, Coroamă, ITU-T L.1410). Gateway embodied from Pirson & Bol blocks / BoaviztAPI.

### Block 3 — upstream backhaul

Reuse existing e-footprint `Network` (kWh/GB) from gateway to cloud — Aslan boundary starts precisely there; no double counting.

### Carbon

```
CO2_hour = (E_device_hour + E_gateway_share) × CI_country + fabrication amortizations
```

Device fabrication: already handled by e-footprint `EdgeDevice` — radio module = one more component (Pirson & Bol connectivity block). Optional refinement: battery-powered devices' lifespan derived from Block 1 (lifetime = E_battery / avg power), coupling transmission behavior to embodied amortization — the seed article's core quantity reused for footprint.

### Minimal user-facing parameters

technology (enum), messages per hour (timeseries), payload size, [PER, n_hops optional]. Everything else defaulted.

*See companion spec: `2026-07-06-edge-network-spec-draft.md` (v1 scope: LoRaWAN, SIGFOX, NB-IoT, BLE, WiFi, Thread).*
