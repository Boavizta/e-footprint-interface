"""Generate importable current-version operational models for the five adoption scenarios."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import (
    SourceHourlyValues,
    SourceObject,
    SourceTimezone,
    SourceValue,
)
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


HERE = Path(__file__).resolve().parent
MODELING_ROOT = HERE.parent
ACTION_EVIDENCE_PATH = MODELING_ROOT / "benchmarks" / "results" / "2026-09-15-action-evidence.json"

START = datetime(2025, 9, 1)
END = datetime(2028, 1, 1)
WORK_HOURS = tuple(range(9, 17))
WORK_DAYS = tuple(range(5))

SERVER_RAM_MB = 2_926
SERVER_VCPU = 4
REFERENCE_HOST_VCPU = 24
REFERENCE_HOST_MANUFACTURING_KG = 600
REFERENCE_HOST_MAX_POWER_W = 300
REFERENCE_HOST_IDLE_POWER_W = 50
KEEP_ALIVE_RAM_MB = 1
REQUEST_RAM_MB = SERVER_RAM_MB - KEEP_ALIVE_RAM_MB


SCENARIOS = {
    "low": {
        "postlaunch_monthly_occurrences": (200, 500),
        "postlaunch_mix": {"S1": 0.30, "S2": 0.35, "S3": 0.10, "S4": 0.10, "S5": 0.15, "S6": 0.0},
    },
    "medium": {
        "postlaunch_monthly_occurrences": (300, 1_000),
        "postlaunch_mix": {"S1": 0.30, "S2": 0.25, "S3": 0.10, "S4": 0.10, "S5": 0.25, "S6": 0.0},
    },
    "high": {
        "postlaunch_monthly_occurrences": (400, 5_000),
        "postlaunch_mix": {"S1": 0.20, "S2": 0.15, "S3": 0.05, "S4": 0.05, "S5": 0.55, "S6": 0.0},
    },
    "team": {
        "postlaunch_monthly_occurrences": (2_000, 50_000),
        "postlaunch_mix": {"S1": 0.05, "S2": 0.10, "S3": 0.05, "S4": 0.05, "S5": 0.05, "S6": 0.70},
    },
    "agent": {
        "postlaunch_monthly_occurrences": (10_000, 500_000),
        "postlaunch_mix": {"S1": 0.01, "S2": 0.01, "S3": 0.01, "S4": 0.01, "S5": 0.01, "S6": 0.95},
    },
}

PRELAUNCH_MIX = {"S1": 0.10, "S2": 0.55, "S3": 0.20, "S4": 0.15, "S5": 0.0, "S6": 0.0}
GEOGRAPHIES = {
    "France": {"share": 0.50, "short_name": "FRA", "carbon_intensity": 44, "timezone": "Europe/Paris"},
    "Europe": {"share": 0.25, "short_name": "EUR", "carbon_intensity": 117, "timezone": "Europe/Brussels"},
    "United States": {
        "share": 0.25,
        "short_name": "USA",
        "carbon_intensity": 383,
        "timezone": "America/New_York",
    },
}

JOURNEY_USER_MINUTES = {
    "S1": 10,
    "S2": 45,
    "S3": 20,
    "S4": 15,
    "S5": 15,
    "S6": 0,
}

JOURNEY_RECIPES = {
    "S1": [
        ("load_ecommerce_template", 2),
        ("open_results_and_generate_cold_sankey", 6),
        ("refine_warm_sankey", 2),
    ],
    "S2": [
        ("add_usage_journey_step", 5),
        ("add_direct_server_job", 5),
        ("increase_usage_volume", 5),
        ("increase_server_ram", 5),
        ("open_results_for_richer_model", 15),
        ("update_model_with_results_open", 10),
    ],
    "S3": [
        ("duplicate_built_model", 3),
        ("rename_alternative", 2),
        ("reduce_alternative_usage_volume", 3),
        ("increase_alternative_step_count", 2),
        ("compare_reference_and_alternative", 8),
        ("export_comparison_workspace", 2),
    ],
    "S4": [
        ("export_model_for_reuse", 1),
        ("reset_active_model_before_reuse", 1),
        ("import_previously_built_model", 2),
        ("open_calculated_value_explanation", 3),
        ("open_calculus_graph", 3),
        ("open_reused_model_results", 3),
        ("export_sources", 1),
        ("export_reused_model", 1),
    ],
    "S6": [
        ("import_previously_built_model", 0),
        ("increase_usage_volume", 0),
        ("open_results_for_richer_model", 0),
        ("open_calculated_value_explanation", 0),
        ("export_reused_model", 0),
    ],
}

SHARED_MODEL_RECIPE = [
    ("import_previously_built_model", 2),
    ("open_reused_model_results", 6),
    ("refine_warm_sankey", 2),
    ("open_calculated_value_explanation", 2),
    ("open_calculus_graph", 3),
]


BENCHMARK_SOURCE = Source(
    "Usage-journey benchmark campaign, 2026-09-15",
    "https://github.com/Boavizta/e-footprint-interface/tree/main/specs/e-footprint-modeling/benchmarks/results",
    id="usage-benchmark-2026-09-15",
)
USER_SCOPE_SOURCE = Source(
    "Operational modeling scope agreed for the 2026 carbon case",
    "https://github.com/Boavizta/e-footprint-interface/tree/main/specs/e-footprint-modeling",
    id="operational-model-scope-2026-09-15",
)
INFRA_SOURCE = Source(
    "Clever Cloud physical allocation hypothesis",
    "https://github.com/Boavizta/e-footprint-interface/blob/main/specs/e-footprint-modeling/README.md",
    id="clever-cloud-allocation-hypothesis-v1",
)
DEPLOYMENT_SOURCE = Source(
    "Clever Cloud production allocation reported by the operator",
    "https://github.com/Boavizta/e-footprint-interface/blob/main/specs/e-footprint-modeling/README.md",
    id="clever-cloud-production-allocation-2026-09",
)
MEMORY_SOURCE = Source(
    "Observed production container memory limits",
    "https://github.com/Boavizta/e-footprint-interface/blob/main/performance/memory/results/2026-08-28-production-container.md",
    id="production-container-memory-2026-08-28",
)
OWID_SOURCE = Source(
    "Our World in Data electricity carbon intensity",
    "https://ourworldindata.org/grapher/carbon-intensity-electricity",
    id="owid-electricity-carbon-intensity",
)
ADEME_SOURCE = Source(
    "Base ADEME v19",
    "https://data.ademe.fr/datasets/base-carbone(r)",
    id="base-ademe-v19",
)
TRAFICOM_SOURCE = Source(
    "Traficom communications-network energy study",
    "https://www.traficom.fi/en/news/first-study-energy-consumption-communications-networks",
    id="traficom-network-energy-study",
)
STORAGE_SOURCE = Source(
    "The Dirty Secret of SSDs: Embodied Carbon",
    "https://arxiv.org/abs/2207.10793",
    id="ssd-embodied-carbon-study",
)


@dataclass(frozen=True)
class ActionEvidence:
    local_median_ms: float
    production_ms: float
    calibrated_production_ms: float
    calibration_factor: float


def source_value(value, source: Source, confidence: str, comment: str) -> SourceValue:
    return SourceValue(value, source=source, confidence=confidence, comment=comment)


def load_benchmark_evidence() -> dict[str, ActionEvidence]:
    document = json.loads(ACTION_EVIDENCE_PATH.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported action-evidence schema")

    rows = document.get("actions", {})
    required_actions = {action for recipe in JOURNEY_RECIPES.values() for action, _ in recipe}
    required_actions.update(action for action, _ in SHARED_MODEL_RECIPE)
    if set(rows) != required_actions:
        raise ValueError("Compact action evidence does not match the modeled journey actions")

    calibration_factor = float(document["calibration_factor"])
    evidence = {}
    for action, row in rows.items():
        item = ActionEvidence(
            local_median_ms=float(row["local_median_ms"]),
            production_ms=float(row["production_ms"]),
            calibrated_production_ms=float(row["calibrated_production_ms"]),
            calibration_factor=calibration_factor,
        )
        if not math.isclose(
            item.calibrated_production_ms,
            item.local_median_ms * calibration_factor,
            abs_tol=0.001,
        ):
            raise ValueError(f"Inconsistent calibrated duration for {action}")
        evidence[action] = item
    return evidence


def validate_scenario_config() -> None:
    journey_ids = set(JOURNEY_USER_MINUTES)
    mixes = {"prelaunch": PRELAUNCH_MIX, **{name: scenario["postlaunch_mix"] for name, scenario in SCENARIOS.items()}}
    for name, mix in mixes.items():
        if set(mix) != journey_ids:
            raise ValueError(f"{name} journey mix does not match {sorted(journey_ids)}")
        if not math.isclose(sum(mix.values()), 1.0):
            raise ValueError(f"{name} journey mix sums to {sum(mix.values())}, not 1")


def build_system(scenario_name: str, evidence: dict[str, ActionEvidence]) -> System:
    server = build_server()
    benchmark_jobs = build_benchmark_jobs(server, evidence)
    journeys = build_journeys(server, benchmark_jobs, evidence)
    countries = build_countries()
    device = build_device()
    network = build_network()

    usage_patterns = []
    for geography_name, geography in GEOGRAPHIES.items():
        for journey_id, journey in journeys.items():
            hourly_values = build_hourly_traffic(scenario_name, journey_id, geography_name)
            usage_patterns.append(
                UsagePattern(
                    f"{scenario_name.title()} – {geography_name} – {journey_id}",
                    usage_journeys={
                        journey: source_value(
                            1 * u.dimensionless,
                            USER_SCOPE_SOURCE,
                            "high",
                            "This pattern is already sliced by journey; one occurrence is one session of this journey.",
                        )
                    },
                    devices=[] if journey_id == "S6" else [device],
                    network=network,
                    country=countries[geography_name],
                    hourly_occurrences=hourly_values,
                )
            )

    usage_patterns.append(build_keep_alive_pattern(server, network, countries["France"]))
    return System(
        f"e-footprint-interface current operation – {scenario_name} adoption – Sep 2025 to Dec 2027",
        usage_patterns=usage_patterns,
        edge_usage_patterns=[],
    )


def build_server() -> Server:
    vcpu_allocation_share = SERVER_VCPU / REFERENCE_HOST_VCPU
    storage = Storage(
        "Application backing storage proxy",
        carbon_footprint_manufacturing_per_storage_capacity=source_value(
            160 * u.kg / u.TB_stored,
            STORAGE_SOURCE,
            "medium",
            "Published SSD embodied-carbon factor; storage remains at zero because v1 does not yet inventory PostgreSQL and Redis capacity.",
        ),
        lifespan=source_value(6 * u.year, INFRA_SOURCE, "low", "Generic SSD lifetime hypothesis."),
        storage_capacity=source_value(1 * u.TB_stored, STORAGE_SOURCE, "medium", "Reference capacity unit."),
        data_replication_factor=source_value(
            1 * u.dimensionless, INFRA_SOURCE, "low", "No storage growth is modeled in v1, so replication is inert."
        ),
        base_storage_need=source_value(
            0 * u.TB_stored,
            INFRA_SOURCE,
            "low",
            "PostgreSQL and Redis capacity are intentionally excluded pending a deployment inventory.",
        ),
        data_storage_duration=source_value(
            1 * u.year, INFRA_SOURCE, "low", "Inert while modeled job storage writes are zero."
        ),
    )
    return Server(
        "Clever Cloud application container allocation",
        server_type=SourceObject(
            "autoscaling",
            source=INFRA_SOURCE,
            confidence="medium",
            comment="Autoscaling is used with a synthetic keep-alive request to approximate minimum_nb_of_instances=1.",
        ),
        carbon_footprint_manufacturing=source_value(
            REFERENCE_HOST_MANUFACTURING_KG * vcpu_allocation_share * u.kg,
            INFRA_SOURCE,
            "low",
            "Four twenty-fourths of a generic 600 kg, 24-core host, allocated in proportion to vCPU; replace with "
            "provider hardware and allocation data.",
        ),
        power=source_value(
            REFERENCE_HOST_MAX_POWER_W * vcpu_allocation_share * u.W,
            INFRA_SOURCE,
            "low",
            "Four twenty-fourths of a generic 300 W host maximum power, allocated in proportion to vCPU.",
        ),
        lifespan=source_value(6 * u.year, INFRA_SOURCE, "low", "Generic server lifetime hypothesis."),
        idle_power=source_value(
            REFERENCE_HOST_IDLE_POWER_W * vcpu_allocation_share * u.W,
            INFRA_SOURCE,
            "low",
            "Four twenty-fourths of a generic 50 W host idle power, allocated in proportion to vCPU.",
        ),
        ram=source_value(
            SERVER_RAM_MB * u.MB_ram,
            MEMORY_SOURCE,
            "medium",
            "Process-visible production constraint retained from the production-container observations.",
        ),
        compute=source_value(
            SERVER_VCPU * u.cpu_core,
            DEPLOYMENT_SOURCE,
            "high",
            "The production Docker container is allocated four vCPUs.",
        ),
        power_usage_effectiveness=source_value(
            1.2 * u.dimensionless, INFRA_SOURCE, "low", "Generic datacenter PUE hypothesis."
        ),
        average_carbon_intensity=source_value(
            44 * u.g / u.kWh,
            OWID_SOURCE,
            "medium",
            "France grid is used as the production-location proxy until the Clever Cloud zone is recorded.",
        ),
        utilization_rate=source_value(
            1 * u.dimensionless,
            MEMORY_SOURCE,
            "medium",
            "The 2,926 MB value is already the process-visible capacity, so no second headroom factor is applied.",
        ),
        base_ram_consumption=source_value(
            0 * u.MB_ram,
            MEMORY_SOURCE,
            "medium",
            "Baseline process memory is already treated as unavailable within the observed process-visible capacity proxy.",
        ),
        base_compute_consumption=source_value(
            0 * u.cpu_core,
            INFRA_SOURCE,
            "low",
            "Idle compute is represented through idle power rather than a permanent CPU reservation.",
        ),
        storage=storage,
    )


def build_benchmark_jobs(server: Server, evidence: dict[str, ActionEvidence]) -> dict[str, Job]:
    jobs = {}
    for journey_id, recipe in JOURNEY_RECIPES.items():
        for action, _ in recipe:
            if action in jobs:
                continue
            measured = evidence[action]
            request_comment = (
                f"Proxy for server service time. Ten-run local median={measured.local_median_ms:.3f} ms; "
                f"single production browser observation={measured.production_ms:.3f} ms; common calibration "
                f"factor={measured.calibration_factor:.3f}; modeled duration={measured.calibrated_production_ms:.3f} ms. "
                "The common factor preserves the stable local action shape while matching the production total. "
                "Replace with correlated server-log service time."
            )
            jobs[action] = Job(
                f"{journey_id} benchmark action – {action}",
                server=server,
                data_transferred=source_value(
                    250 * u.kB,
                    INFRA_SOURCE,
                    "low",
                    "Request/response byte sizes were not captured; 250 kB per measured action is a v1 placeholder.",
                ),
                data_stored=source_value(
                    0 * u.kB_stored,
                    INFRA_SOURCE,
                    "low",
                    "Session/cache writes are not yet inventoried as persistent storage growth.",
                ),
                request_duration=source_value(
                    measured.calibrated_production_ms * u.ms, BENCHMARK_SOURCE, "low", request_comment
                ),
                compute_needed=source_value(
                    0.5 * u.cpu_core,
                    INFRA_SOURCE,
                    "low",
                    "Average CPU occupancy hypothesis; replace with CPU-ms divided by service time from correlated logs.",
                ),
                ram_needed=source_value(
                    REQUEST_RAM_MB * u.MB_ram,
                    USER_SCOPE_SOURCE,
                    "medium",
                    "Reserves the single-worker container for one request. One MB is left for the synthetic keep-alive demand, so one real request plus keep-alive fits exactly and a concurrent request requires another instance.",
                ),
            )
    return jobs


def build_journeys(
    server: Server,
    jobs: dict[str, Job],
    evidence: dict[str, ActionEvidence],
) -> dict[str, UsageJourney]:
    journeys = {}
    for journey_id, recipe in JOURNEY_RECIPES.items():
        steps = []
        for action, user_minutes in recipe:
            steps.append(
                UsageJourneyStep(
                    f"{journey_id} step – {action}",
                    user_time_spent=source_value(
                        user_minutes * u.min,
                        USER_SCOPE_SOURCE,
                        "low",
                        f"Informed user-time hypothesis. Allocations sum to {JOURNEY_USER_MINUTES[journey_id]} minutes for {journey_id}.",
                    ),
                    jobs={
                        jobs[action]: source_value(
                            1 * u.dimensionless,
                            BENCHMARK_SOURCE,
                            "high",
                            "The Playwright journey triggers this measured action once at this point in the sequence.",
                        ),
                    },
                )
            )
        journeys[journey_id] = UsageJourney(
            f"{journey_id} – {journey_name(journey_id)}",
            uj_steps={
                step: source_value(
                    1 * u.dimensionless, USER_SCOPE_SOURCE, "high", "Each ordered step occurs once per session."
                )
                for step in steps
            },
        )

    shared_steps = []
    for action, user_minutes in SHARED_MODEL_RECIPE:
        base = evidence[action]
        complex_duration_ms = base.calibrated_production_ms * 1.5
        complex_job = Job(
            f"S5 complex shared model – {action}",
            server=server,
            data_transferred=source_value(
                500 * u.kB,
                INFRA_SOURCE,
                "low",
                "Twice the ordinary placeholder to represent a larger shared model response.",
            ),
            data_stored=source_value(
                0 * u.kB_stored, INFRA_SOURCE, "low", "Read-only shared exploration; no persistent growth modeled."
            ),
            request_duration=source_value(
                complex_duration_ms * u.ms,
                USER_SCOPE_SOURCE,
                "low",
                f"No S5 benchmark exists yet. Uses 1.5 × calibrated F1 duration for {action} "
                f"({base.calibrated_production_ms:.3f} ms), representing a more complex-than-average shared model.",
            ),
            compute_needed=source_value(
                0.5 * u.cpu_core, INFRA_SOURCE, "low", "Same provisional average CPU occupancy as benchmarked jobs."
            ),
            ram_needed=source_value(
                REQUEST_RAM_MB * u.MB_ram,
                USER_SCOPE_SOURCE,
                "medium",
                "Same exclusive single-worker container reservation as benchmarked requests.",
            ),
        )
        shared_steps.append(
            UsageJourneyStep(
                f"S5 step – {action}",
                user_time_spent=source_value(
                    user_minutes * u.min,
                    USER_SCOPE_SOURCE,
                    "low",
                    "Informed user-time allocation for read-only exploration of a shared complex model.",
                ),
                jobs={
                    complex_job: source_value(
                        1 * u.dimensionless,
                        USER_SCOPE_SOURCE,
                        "medium",
                        "The provisional shared-model journey triggers this operation once.",
                    ),
                },
            )
        )
    journeys["S5"] = UsageJourney(
        "S5 – Explore a shared complex model",
        uj_steps={
            step: source_value(
                1 * u.dimensionless, USER_SCOPE_SOURCE, "medium", "Each provisional S5 step occurs once."
            )
            for step in shared_steps
        },
    )
    return journeys


def build_hourly_traffic(scenario_name: str, journey_id: str, geography_name: str) -> SourceHourlyValues:
    hours = [START + timedelta(hours=index) for index in range(int((END - START).total_seconds() / 3_600))]
    eligible_by_month = Counter(
        (hour.year, hour.month) for hour in hours if hour.weekday() in WORK_DAYS and hour.hour in WORK_HOURS
    )
    values = np.zeros(len(hours), dtype=np.float32)
    geography_share = GEOGRAPHIES[geography_name]["share"]

    for index, hour in enumerate(hours):
        if hour.weekday() not in WORK_DAYS or hour.hour not in WORK_HOURS:
            continue
        month_key = (hour.year, hour.month)
        monthly_occurrences, mix = monthly_volume_and_mix(scenario_name, month_key)
        values[index] = monthly_occurrences * mix[journey_id] * geography_share / eligible_by_month[month_key]

    scenario = SCENARIOS[scenario_name]
    start_volume, end_volume = scenario["postlaunch_monthly_occurrences"]
    comment = (
        f"User-provided trajectory with linear monthly anchors: 50 usage occurrences in Sep 2025 to 200 in Sep 2026; "
        f"then {start_volume} in Oct 2026 to {end_volume} in Dec 2027 for {scenario_name}. "
        f"Traffic share: {geography_name}={geography_share:.0%}. Usage occurrences are spread evenly over "
        f"Monday–Friday 09:00–17:00 local time. Pre-launch journey mix={PRELAUNCH_MIX}; "
        f"post-launch mix={scenario['postlaunch_mix']}. "
        "S6 occurrences are automated model-maintenance runs with no user device time. No holidays, seasonality, "
        "bursts, or landing-page-only visits are represented."
    )
    return SourceHourlyValues(
        Quantity(values, u.occurrence),
        start_date=START,
        source=USER_SCOPE_SOURCE,
        confidence="low",
        comment=comment,
    )


def monthly_volume_and_mix(scenario_name: str, month_key: tuple[int, int]) -> tuple[float, dict[str, float]]:
    month_index = (month_key[0] - START.year) * 12 + month_key[1] - START.month
    if month_index <= 12:
        return 50 + (200 - 50) * month_index / 12, PRELAUNCH_MIX

    postlaunch_index = month_index - 13
    postlaunch_month_count = 15
    start_volume, end_volume = SCENARIOS[scenario_name]["postlaunch_monthly_occurrences"]
    volume = start_volume + (end_volume - start_volume) * postlaunch_index / (postlaunch_month_count - 1)
    return volume, SCENARIOS[scenario_name]["postlaunch_mix"]


def build_countries() -> dict[str, Country]:
    countries = {}
    for name, details in GEOGRAPHIES.items():
        countries[name] = Country(
            f"{name} user-location proxy",
            details["short_name"],
            source_value(
                details["carbon_intensity"] * u.g / u.kWh,
                OWID_SOURCE,
                "medium",
                f"Country proxy used for the agreed {name} traffic share; constant average over the full period.",
            ),
            SourceTimezone(
                pytz.timezone(details["timezone"]),
                source=USER_SCOPE_SOURCE,
                confidence="medium",
                comment=f"Representative timezone for the {name} work-hours traffic slice.",
            ),
        )
    return countries


def build_device() -> Device:
    return Device(
        "User laptop",
        carbon_footprint_manufacturing=source_value(
            156 * u.kg, ADEME_SOURCE, "medium", "Laptop manufacturing archetype."
        ),
        power=source_value(50 * u.W, USER_SCOPE_SOURCE, "low", "Laptop active-power archetype."),
        lifespan=source_value(6 * u.year, USER_SCOPE_SOURCE, "low", "Laptop lifetime hypothesis."),
        fraction_of_usage_time=source_value(
            7 * u.hour / u.day,
            USER_SCOPE_SOURCE,
            "low",
            "Assumed average daily use across all activities for manufacturing amortization.",
        ),
    )


def build_network() -> Network:
    return Network(
        "User Wi-Fi and fixed network",
        bandwidth_energy_intensity=source_value(
            0.05 * u.kWh / u.GB,
            TRAFICOM_SOURCE,
            "medium",
            "Wi-Fi/fixed-network proxy applied to the placeholder transferred bytes.",
        ),
    )


def build_keep_alive_pattern(server: Server, network: Network, country: Country) -> UsagePattern:
    duration_hours = int((END - START).total_seconds() / 3_600)
    keep_alive_job = Job(
        "Synthetic minimum-one-instance keep-alive",
        server=server,
        data_transferred=source_value(
            0 * u.kB, INFRA_SOURCE, "medium", "Synthetic modeling job; it transfers no data."
        ),
        data_stored=source_value(0 * u.kB_stored, INFRA_SOURCE, "medium", "Synthetic modeling job; it stores no data."),
        request_duration=source_value(
            1 * u.hour,
            INFRA_SOURCE,
            "medium",
            "One-hour segments tile one continuous logical keep-alive thread. A single multi-year Job would extend "
            "e-footprint's convolution output beyond the requested modeling horizon.",
        ),
        compute_needed=source_value(
            0.0001 * u.cpu_core,
            INFRA_SOURCE,
            "medium",
            "Minimal non-zero demand used only to keep autoscaling ceil at one instance.",
        ),
        ram_needed=source_value(
            KEEP_ALIVE_RAM_MB * u.MB_ram,
            INFRA_SOURCE,
            "medium",
            "One MB complements each real job's 2,925 MB reservation without forcing a second instance.",
        ),
    )
    keep_alive_step = UsageJourneyStep(
        "One hour of minimum-one-instance keep-alive",
        user_time_spent=source_value(
            0 * u.s, INFRA_SOURCE, "high", "Synthetic infrastructure event with no human device time."
        ),
        jobs={
            keep_alive_job: source_value(
                1 * u.dimensionless, INFRA_SOURCE, "high", "One segment starts in each modeled hour."
            )
        },
    )
    keep_alive_journey = UsageJourney(
        "Infrastructure keep-alive over full modeling period",
        uj_steps={
            keep_alive_step: source_value(1 * u.dimensionless, INFRA_SOURCE, "high", "One synthetic start event.")
        },
    )
    occurrences = np.ones(duration_hours, dtype=np.float32)
    return UsagePattern(
        "Minimum one application instance",
        usage_journeys={
            keep_alive_journey: source_value(
                1 * u.dimensionless, INFRA_SOURCE, "high", "One keep-alive journey per synthetic occurrence."
            )
        },
        devices=[],
        network=network,
        country=country,
        hourly_occurrences=SourceHourlyValues(
            Quantity(occurrences, u.occurrence),
            START,
            source=INFRA_SOURCE,
            confidence="medium",
            comment="One one-hour segment per hour represents a single continuous logical keep-alive thread.",
        ),
    )


def journey_name(journey_id: str) -> str:
    return {
        "S1": "Explore an example",
        "S2": "Build and refine a model",
        "S3": "Compare an alternative",
        "S4": "Audit and reuse a model",
        "S5": "Explore a shared complex model",
        "S6": "Agent builds or maintains a model",
    }[journey_id]


def expected_usage_total(scenario_name: str) -> float:
    prelaunch = 13 * (50 + 200) / 2
    start_volume, end_volume = SCENARIOS[scenario_name]["postlaunch_monthly_occurrences"]
    postlaunch = 15 * (start_volume + end_volume) / 2
    return prelaunch + postlaunch


def write_and_validate(system: System, output_path: Path, scenario_name: str) -> None:
    document = system_to_json(system, output_filepath=None, save_computed_state=False)
    output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    class_objects, _, _ = json_to_system(json.loads(output_path.read_text(encoding="utf-8")))
    loaded_system = next(iter(class_objects["System"].values()))
    expected_pattern_count = len(GEOGRAPHIES) * len(JOURNEY_USER_MINUTES) + 1
    if len(loaded_system.usage_patterns) != expected_pattern_count:
        raise ValueError(
            f"Round-tripped model contains {len(loaded_system.usage_patterns)} usage patterns, "
            f"expected {expected_pattern_count}"
        )
    if BENCHMARK_SOURCE.id not in document["Sources"] or USER_SCOPE_SOURCE.id not in document["Sources"]:
        raise ValueError("Expected traceability sources are absent from generated JSON")
    traffic_total = sum(
        pattern.hourly_occurrences.sum().to(u.occurrence).magnitude
        for pattern in loaded_system.usage_patterns
        if pattern.name != "Minimum one application instance"
    )
    if not math.isclose(traffic_total, expected_usage_total(scenario_name), abs_tol=0.05):
        raise ValueError(f"Generated traffic sums to {traffic_total}, not the expected scenario total")
    instances = loaded_system.servers[0].nb_of_instances
    if instances.min().magnitude != 1:
        raise ValueError("Synthetic keep-alive failed to preserve a minimum of one application instance")
    print(
        f"{scenario_name}: wrote {output_path} "
        f"({traffic_total:,.0f} modeled usage occurrences, instances 1–{instances.max().magnitude:g}, "
        f"{output_path.stat().st_size / 1_000_000:.1f} MB)"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["all", *SCENARIOS],
        default="all",
        help="Generate all five scenarios or one selected scenario.",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ModelingObject._use_name_as_id = True
    Source._use_name_as_id = True
    validate_scenario_config()
    evidence = load_benchmark_evidence()
    selected = SCENARIOS if args.scenario == "all" else [args.scenario]
    for scenario_name in selected:
        system = build_system(scenario_name, evidence)
        write_and_validate(system, args.output_dir / f"current-{scenario_name}.e-f.json", scenario_name)


if __name__ == "__main__":
    main()
