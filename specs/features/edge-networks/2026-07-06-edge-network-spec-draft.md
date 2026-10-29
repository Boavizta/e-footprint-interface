# Spec draft — edge/IoT wireless networks in e-footprint

Date: 2026-07-06 · Status: **draft for discussion** · Companion: `2026-07-06-edge-network-modeling-note.md`

## 1. Goal

Model energy + carbon of local wireless IoT links (device radio → gateway → backhaul) in e-footprint, with a power model (baseline + per-message + synchronization) instead of kWh/GB, per the literature note. All parameters overridable so users who know their material (device radio, gateway/relay) can document it and seek optimizations; technology table provides defaults for everyone else.

## 2. Scope

**v1**: LoRaWAN, SIGFOX, NB-IoT, BLE, WiFi (battery devices, 802.11 PSM parameters), and Thread (802.15.4 radio + IPv6 mesh; modeled node = battery "sleepy end device", border router = `EdgeGateway`). Uplink-dominated periodic messaging.
**Out of scope v1**: mesh routing detail (only `n_hops` multiplier), downlink-heavy traffic, wired LAN/WAN (separate topic — no radio states, constant-power switches; closer to existing `Network`/server modeling), battery→lifespan coupling (v2, see §8).

## 3. New modeling objects

Follows existing `EdgeComponent` / `RecurrentEdgeComponentNeed` patterns in the e-footprint edge module.

### 3.1 `EdgeNetworkInterface(EdgeComponent)`

The radio module of an `EdgeDevice`. One per device.

| Attribute | Default (per technology) | Unit | Source |
|---|---|---|---|
| `technology` | — (enum: LORAWAN, SIGFOX, NB_IOT, BLE, WIFI, THREAD) | — | user choice |
| `p_tx` | table §5 | mW | Casals/Gomez/Lauridsen/Morin |
| `p_rx` | table §5 | mW | idem |
| `p_sleep` | table §5 | µW | idem |
| `bitrate` | table §5 | bit/s | idem |
| `overhead_per_frame` | table §5 | bits | Morin Figs. 2–11 |
| `max_payload_per_frame` | table §5 | B | Morin Table III |
| `energy_fixed_per_message` | table §5 | mJ | wake-up + idle, per tech |
| `rx_listen_time_per_message` | table §5 | ms | ACK/RX windows |
| `sync_period` | table §5 (∞ for asynchronous techs) | s | keep-alive/poll interval |
| `energy_per_sync` | table §5 | µJ | one keep-alive/poll exchange |
| `packet_error_rate` | 0 | — | user hypothesis |
| `n_hops` | 1 | — | mesh only |
| `carbon_footprint_fabrication_per_unit` | Pirson & Bol connectivity block | kg CO2e | BoaviztAPI |
| `lifespan` | inherited from EdgeDevice | yr | — |

Every attribute is an `ExplainableQuantity` with source → user override = standard e-footprint pattern, provenance kept.

### 3.2 `RecurrentMessagingNeed` (usage side)

Mirrors `RecurrentEdgeComponentNeed`: attaches to an `EdgeNetworkInterface`, carries `messages_per_hour` (168-h weekly pattern, replayed) and `payload_size` (B).

### 3.3 `EdgeGateway`

Shared local infrastructure (LoRaWAN gateway/relay, Thread border router; NB-IoT is operator-side → see note below).

| Attribute | Default | Unit |
|---|---|---|
| `power` | 5 W | W |
| `carbon_footprint_fabrication` | 25 kg CO2e (Pirson & Bol blocks, to refine) | kg |
| `lifespan` | 6 yr | yr |
| `n_devices_served` | user input | — |

Allocation: **per device-hour** (time/subscriber key), never per GB — Mytton 2024, ITU-T L.1410.
NB-IoT: no user-owned gateway; default to per-subscription network figure (Malmodin/Ruiz: order 20 kWh/yr + infra embodied per subscription) instead of `EdgeGateway`.
Thread: `EdgeGateway` plays the border router (always-on, mains-powered); mains-powered Thread routers along the mesh path are neglected in v1 (marginal per-message energy ≈ 0 on always-on nodes; their embodied share deferred).

### 3.4 Backhaul

Existing `Network` (kWh/GB) from gateway to cloud, fed by message payloads volume. Aslan boundary starts there — no double counting.

## 4. Formulas

Per device, per hourly bucket Δt = 1 h:

```
E_interface = p_sleep × Δt + N_msg × E_msg + N_sync × energy_per_sync

E_msg = n_hops × [ energy_fixed_per_message
                   + Ntr × Nfr × (b_frame / bitrate) × p_tx
                   + rx_listen_time × p_rx ]

Nfr     = ceil(payload_size / max_payload_per_frame)
b_frame = min(payload_size / Nfr) × 8 + overhead_per_frame
Ntr     = 1 / (1 − packet_error_rate)
N_sync  = max(0, Δt / sync_period − N_msg)   # data frames count as sync (Morin: Nsyn − NdataSyn); 0 for asynchronous techs
```

Sync as separate recurring term is load-bearing: for Matter-over-Thread devices, keep-alive polling is 94.5–99.3% of annual energy (Nordic nwp_049) — folding it into per-message energy would zero it out for rarely-messaging devices.

```
gateway_share_per_device_hour =
    ( carbon_footprint_fabrication / lifespan
      + power × Δt × country.average_carbon_intensity ) / n_devices_served
```

```
CO2_hour = E_interface × country.average_carbon_intensity
           + interface fabrication amortization (EdgeComponent standard)
           + gateway_share_per_device_hour
           + backhaul via Network(payload volume)
```

## 5. v1 default parameter table

| Param | LoRaWAN (SF7–SF12 EU) | SIGFOX (EU 100 b/s) | NB-IoT | BLE (5.0, 2 Mb/s) | WiFi (802.11 PSM) | Thread (802.15.4) |
|---|---|---|---|---|---|---|
| p_tx | 420 mW (14 dBm) | 147 mW | 750 mW (23 dBm) | 24.1 mW (0 dBm) | 700 mW (18 dBm) | 24.1 mW (0 dBm) |
| p_rx | 44 mW | 39 mW | 225 mW | 19.3 mW | 170 mW | 19.3 mW |
| p_sleep | 4.3 µW | 4.3 µW | 25 µW (PSM: 15–35 µW) | 3.2 µW | 9.5 µW | 8 µW (measured: 2.65 µA @ 3 V, nRF52840 SED) |
| bitrate | 5.5 kb/s (SF7) default; SF param | 100 b/s | 25 kb/s effective | 2 Mb/s | 11 Mb/s | 250 kb/s |
| max_payload | 222 B (SF7) / 51 B (SF12) | 12 B | 1600 B | 245 B | 1280 B | ~100 B useful (127 B frame) |
| fixed extras | RX1+RX2 windows | ×3 replicas built-in (fold into Ntr_base=3) | RRC/DRX per message | master poll per message | beacon listen + DIFS/backoff | data poll to parent per message |
| sync_period / energy_per_sync | ∞ (async) | ∞ (async) | ∞ (PSM between messages) | 32 s / poll exchange | ~18 h max (listen interval) / beacon listen | poll period, default 2.5 s slow poll / **53 µJ per poll** (17.63 µC @ 3 V, measured) |
| n_hops default | 1 | 1 | 1 | 1 | 1 | 1 (device→parent; mesh beyond parent neglected v1) |

Sources to pin during implementation: Casals 2017, Bouguera 2018 (LoRaWAN); Gomez 2019 (SIGFOX); Lauridsen 2018, Andres-Maldonado 2019 (NB-IoT); Morin 2017 Tables III & V for BLE and WiFi PSM columns. Thread: Kim, Kumar & Culler 2019 (peer-reviewed anchor: leaf ~30 µA avg at 10 s TX period, 5.3 yr / 1400 mAh) + Nordic measurements (SED blog 2023: sleep floor 2.65 µA, 17.63 µC/poll; white paper nwp_049 2025: idle polling = 94.5–99.3% of annual energy) — Tx/Rx state powers from Morin 802.15.4 column. Caveat: Thread SoC spread is wide (ESP32-H2 ≈ 16× worse than nRF52840; board regulator can cost 3× the chip) — defaults are best-in-class, users with real hardware should override. Values above from literature note; verify each against paper tables when coding defaults. SIGFOX triple transmission modeled as base multiplier 3 on Tx term, not via PER. WiFi column targets battery devices in power-saving mode; always-on WiFi devices (mains) are better modeled as plain `EdgeDevice` power draw.

## 6. User API mock-up

```python
interface = EdgeNetworkInterface.from_technology(
    "LoRaWAN",                      # all defaults loaded, each overridable:
    p_sleep=SourceValue(2.1 * u.uW, source="bench measurement 2026-05"),
    spreading_factor=9,
)
device = EdgeDevice("soil sensor", components=[cpu, ram, interface], lifespan=...)
messaging = RecurrentMessagingNeed(
    edge_network_interface=interface,
    messages_per_hour=weekly_pattern([...]),   # 168 values
    payload_size=SourceValue(24 * u.B),
)
gateway = EdgeGateway("farm LoRa gateway", n_devices_served=SourceValue(80 * u.dimensionless))
usage = EdgeUsagePattern(..., edge_gateway=gateway, network=backhaul_network, country=france)
```

Optimization workflow enabled: swap SF, batch messages (payload↑, N_msg↓), compare chips via p_sleep, tune poll period, resize fleet per gateway.

## 7. Tests

- Unit: `E_msg` against published figures — Casals Table (1 msg/5 min, 2400 mAh ≈ 1 yr equivalent avg power), Gomez SIGFOX (~900 mJ per 12 B message, Martinez cross-check), Lauridsen NB-IoT state powers.
- Unit: fragmentation (payload > max_payload → Nfr), Ntr at PER 0.2 = 1.25, SIGFOX ×3 replicas, Thread per-message poll energy present.
- Unit: dimensional checks (pint units end-to-end).
- Integration: full system CO2 with gateway allocation + backhaul, no double counting (backhaul GB = payload only).
- Sensitivity sanity: at 1 msg/day, sleep term > 90% of E_interface for asynchronous techs (Morin finding #3); for Thread at 2.5 s poll period, sync term dominates (Nordic nwp_049: 94.5–99.3%).
- Validation: Thread leaf at 10 s message period ≈ 30 µA average (Kim et al. 2019).

## 8. Design choices & open points

1. **Gateway**: full `EdgeGateway` object (rather than a single allocation constant) — needed for the "know their material" optimization use case and as Thread border router.
2. **Battery→lifespan coupling**: deferred to v2. Default lifespans exist (`EdgeDevice`/`EdgeComponent` default 6 yr; PEP ecopassport reference lifetimes usable as per-product sources), so deferral does not load the user. v2: `lifespan = battery_energy / avg_power`, feeding fabrication amortization — creates a calculation dependency loop to design carefully.
3. Open: exact class placement in the e-footprint edge module (`efootprint/core/hardware/edge/`) and whether `RecurrentMessagingNeed` merges into the existing recurrent-need hierarchy.

## 9. Expansion path (v2+): remaining technologies

| Technology | Why deferred | Effort when needed |
|---|---|---|
| TSCH (802.15.4e) | industrial only; same hardware as 802.15.4, different MAC timing | Low–medium |
| 802.11ah HaLow | niche adoption | Low |
| Wired LAN/WAN | different physics (constant-power switches, PoE); separate spec, closer to existing Network/server modeling | Separate topic |

Table design must make adding a column trivial: technology enum + default dict, no per-technology code paths except flagged specifics (SIGFOX ×3, NB-IoT subscription allocation).
