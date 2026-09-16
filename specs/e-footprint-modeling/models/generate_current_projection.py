"""Generate importable operational models for the implementation and adoption scenarios."""

from __future__ import annotations

import argparse
import json
import math
import runpy
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
INTERFACE_VERSION = runpy.run_path(
    str(MODELING_ROOT.parents[1] / "e_footprint_interface" / "version.py")
)["__version__"]
ACTION_EVIDENCE_PATH = MODELING_ROOT / "benchmarks" / "results" / "2026-09-15-action-evidence.json"
IMPLEMENTATION_PROFILES_PATH = MODELING_ROOT / "optimizations" / "implementation-profiles.json"

START = datetime(2025, 9, 1)
END = datetime(2034, 1, 1)
PUBLIC_LAUNCH = (2026, 10)
WORK_HOURS = tuple(range(9, 17))
WORK_DAYS = tuple(range(5))

REFERENCE_HOST_VCPU = 24
REFERENCE_HOST_MANUFACTURING_KG = 600
REFERENCE_HOST_MAX_POWER_W = 300
REFERENCE_HOST_IDLE_POWER_W = 50
KEEP_ALIVE_RAM_MB = 1


ADOPTION_SHAPES = {
    "niche": {
        "active_team_anchors": {2026: 5, 2027: 15, 2028: 30, 2029: 45, 2030: 50, 2031: 50, 2032: 50},
        "mature_exploratory_sessions_per_month": 250,
    },
    "central": {
        "active_team_anchors": {
            2026: 10,
            2027: 30,
            2028: 90,
            2029: 180,
            2030: 260,
            2031: 295,
            2032: 300,
        },
        "mature_exploratory_sessions_per_month": 2_000,
    },
    "breakout": {
        "active_team_anchors": {
            2026: 20,
            2027: 100,
            2028: 400,
            2029: 1_000,
            2030: 1_600,
            2031: 1_950,
            2032: 2_000,
        },
        "mature_exploratory_sessions_per_month": 15_000,
    },
}

ACTIVITY_REGIMES = {
    "human-led": {
        "models_per_team": 4,
        "interactive_sessions_per_team_month": 6,
        "automated_runs_per_model_month": 0.5,
    },
    "team-integrated": {
        "models_per_team": 10,
        "interactive_sessions_per_team_month": 8,
        "automated_runs_per_model_month": 4,
    },
    "agent-intensive": {
        "models_per_team": 20,
        "interactive_sessions_per_team_month": 10,
        "automated_runs_per_model_month": 30,
    },
}

SCENARIOS = {
    "niche-human": {"label": "Niche, human-led", "adoption_shape": "niche", "activity_regime": "human-led"},
    "central-human": {"label": "Central, human-led", "adoption_shape": "central", "activity_regime": "human-led"},
    "central-team": {
        "label": "Central, team-integrated",
        "adoption_shape": "central",
        "activity_regime": "team-integrated",
    },
    "breakout-team": {
        "label": "Breakout, team-integrated",
        "adoption_shape": "breakout",
        "activity_regime": "team-integrated",
    },
    "breakout-agent": {
        "label": "Breakout, agent-intensive",
        "adoption_shape": "breakout",
        "activity_regime": "agent-intensive",
    },
}

PRELAUNCH_MONTHLY_OCCURRENCES = 50
PRELAUNCH_MIX = {"S1": 0.10, "S2": 0.55, "S3": 0.20, "S4": 0.15, "S5": 0.0, "S6": 0.0}
PUBLIC_EXPLORER_MIX = {"S1": 0.70, "S2": 0.20, "S3": 0.03, "S4": 0.02, "S5": 0.05, "S6": 0.0}
TEAM_INTERACTIVE_MIX = {"S1": 0.05, "S2": 0.35, "S3": 0.25, "S4": 0.15, "S5": 0.20, "S6": 0.0}
AUTOMATION_RAMP_MONTHS = 24
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
COUNTERFACTUAL_SOURCE = Source(
    "No AI, low optimization implementation profile",
    "https://github.com/Boavizta/e-footprint-interface/blob/main/specs/e-footprint-modeling/optimizations/implementation-profiles.json",
    id="no-ai-low-optim-profile-2026-09-16",
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


@dataclass(frozen=True)
class ImplementationProfile:
    profile_id: str
    label: str
    file_prefix: str
    tier: str
    vcpu: int
    nominal_ram_gib: float
    process_visible_ram_mib: float
    safe_ram_mib: float
    monthly_price_eur: float
    estimated_max_request_peak_mib: float | None
    default_duration_factor: float
    default_transfer_factor: float
    action_duration_factors: dict[str, float]
    action_transfer_factors: dict[str, float]
    confidence: str
    comment: str


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


def load_implementation_profiles() -> dict[str, ImplementationProfile]:
    document = json.loads(IMPLEMENTATION_PROFILES_PATH.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported implementation-profile schema")

    plans = {plan["tier"]: plan for plan in document["plan_catalog"]}
    capacity = document["capacity_assumptions"]
    unavailable_ram_gib = float(capacity["unavailable_ram_gib"])
    guard_ratio = float(capacity["computation_guard_ratio"])
    profiles = {}
    for profile_id, raw in document["profiles"].items():
        selection = raw["tier_selection"]
        peak_mib = selection.get("estimated_max_request_peak_mib")
        if selection["mode"] == "observed":
            tier = selection["tier"]
            process_visible_ram_mib = float(selection["process_visible_ram_mib"])
        elif selection["mode"] == "minimum_safe_capacity":
            tier = None
            process_visible_ram_mib = None
            for plan in document["plan_catalog"]:
                visible_mib = max(0, (float(plan["nominal_ram_gib"]) - unavailable_ram_gib) * 1024)
                if float(peak_mib) <= visible_mib * guard_ratio:
                    tier = plan["tier"]
                    process_visible_ram_mib = visible_mib
                    break
            if tier is None:
                ceiling = document["plan_catalog"][-1]
                ceiling_safe_mib = max(
                    0, (float(ceiling["nominal_ram_gib"]) - unavailable_ram_gib) * 1024 * guard_ratio
                )
                raise ValueError(
                    f"{profile_id} requires {float(peak_mib):.1f} MiB, above the 3XL safe ceiling "
                    f"of {ceiling_safe_mib:.1f} MiB"
                )
        else:
            raise ValueError(f"Unsupported tier-selection mode for {profile_id}: {selection['mode']}")

        plan = plans[tier]
        profiles[profile_id] = ImplementationProfile(
            profile_id=profile_id,
            label=raw["label"],
            file_prefix=raw["file_prefix"],
            tier=tier,
            vcpu=int(plan["vcpu"]),
            nominal_ram_gib=float(plan["nominal_ram_gib"]),
            process_visible_ram_mib=float(process_visible_ram_mib),
            safe_ram_mib=float(process_visible_ram_mib) * guard_ratio,
            monthly_price_eur=float(plan["monthly_price_eur"]),
            estimated_max_request_peak_mib=float(peak_mib) if peak_mib is not None else None,
            default_duration_factor=float(raw["default_duration_factor"]),
            default_transfer_factor=float(raw["default_transfer_factor"]),
            action_duration_factors={key: float(value) for key, value in raw["action_duration_factors"].items()},
            action_transfer_factors={key: float(value) for key, value in raw["action_transfer_factors"].items()},
            confidence=raw["confidence"],
            comment=raw["comment"],
        )

        derivation = selection.get("memory_derivation")
        if derivation:
            derived_peak_mib = float(derivation["base_peak_mib"])
            for factor in derivation["factors"]:
                derived_peak_mib *= float(factor["factor"])
            if not math.isclose(derived_peak_mib, float(peak_mib), rel_tol=1e-12):
                raise ValueError(f"{profile_id} maximum-memory derivation is inconsistent")

    required_actions = {action for recipe in JOURNEY_RECIPES.values() for action, _ in recipe}
    required_actions.update(action for action, _ in SHARED_MODEL_RECIPE)
    counterfactual = profiles["no-ai-low-optim"]
    if set(counterfactual.action_duration_factors) != required_actions:
        raise ValueError("Counterfactual duration factors do not match the modeled action catalogue")
    if not set(counterfactual.action_transfer_factors).issubset(required_actions):
        raise ValueError("Counterfactual transfer factors contain an unknown modeled action")
    return profiles


def validate_scenario_config() -> None:
    journey_ids = set(JOURNEY_USER_MINUTES)
    mixes = {
        "prelaunch": PRELAUNCH_MIX,
        "public explorer": PUBLIC_EXPLORER_MIX,
        "team interactive": TEAM_INTERACTIVE_MIX,
    }
    for name, mix in mixes.items():
        if set(mix) != journey_ids:
            raise ValueError(f"{name} journey mix does not match {sorted(journey_ids)}")
        if not math.isclose(sum(mix.values()), 1.0):
            raise ValueError(f"{name} journey mix sums to {sum(mix.values())}, not 1")
    for name, scenario in SCENARIOS.items():
        if scenario["adoption_shape"] not in ADOPTION_SHAPES:
            raise ValueError(f"{name} references an unknown adoption shape")
        if scenario["activity_regime"] not in ACTIVITY_REGIMES:
            raise ValueError(f"{name} references an unknown activity regime")
    for name, shape in ADOPTION_SHAPES.items():
        anchors = shape["active_team_anchors"]
        if sorted(anchors) != list(range(2026, 2033)):
            raise ValueError(f"{name} must define year-end active-team anchors from 2026 through 2032")
        if any(next_value < value for value, next_value in zip(anchors.values(), list(anchors.values())[1:])):
            raise ValueError(f"{name} active-team anchors must not decrease")


def build_system(
    scenario_name: str, evidence: dict[str, ActionEvidence], profile: ImplementationProfile
) -> System:
    scenario_label = SCENARIOS[scenario_name]["label"]
    server = build_server(profile)
    benchmark_jobs = build_benchmark_jobs(server, evidence, profile)
    journeys = build_journeys(server, benchmark_jobs, evidence, profile)
    countries = build_countries()
    device = build_device()
    network = build_network()

    usage_patterns = []
    for geography_name, geography in GEOGRAPHIES.items():
        for journey_id, journey in journeys.items():
            hourly_values = build_hourly_traffic(scenario_name, journey_id, geography_name)
            usage_patterns.append(
                UsagePattern(
                    f"{scenario_label} – {geography_name} – {journey_id}",
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
    system_name = (
        f"e-footprint-interface current operation – {scenario_label} – Sep 2025 to Dec 2033"
        if profile.profile_id == "current"
        else f"e-footprint-interface {profile.label.lower()} – {scenario_label} – Sep 2025 to Dec 2033"
    )
    return System(
        system_name,
        usage_patterns=usage_patterns,
        edge_usage_patterns=[],
    )


def build_server(profile: ImplementationProfile) -> Server:
    vcpu_allocation_share = profile.vcpu / REFERENCE_HOST_VCPU
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
    profile_source = DEPLOYMENT_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE
    return Server(
        # Keep the semantic id stable across implementation profiles so the interface comparison
        # recognizes one changed allocation rather than one removed server plus one added server.
        "Clever Cloud application container allocation",
        server_type=SourceObject(
            "autoscaling",
            source=profile_source,
            confidence="medium",
            comment=(
                "Autoscaling is used with a synthetic keep-alive request to approximate minimum_nb_of_instances=1. "
                f"The {profile.tier} tier is the implementation profile's selected per-container unit."
            ),
        ),
        carbon_footprint_manufacturing=source_value(
            REFERENCE_HOST_MANUFACTURING_KG * vcpu_allocation_share * u.kg,
            INFRA_SOURCE,
            "low",
            f"{profile.vcpu}/24 of a generic 600 kg, 24-core host, allocated in proportion to vCPU for the "
            f"{profile.tier} tier; replace with provider hardware and allocation data.",
        ),
        power=source_value(
            REFERENCE_HOST_MAX_POWER_W * vcpu_allocation_share * u.W,
            INFRA_SOURCE,
            "low",
            f"{profile.vcpu}/24 of a generic 300 W host maximum power, allocated in proportion to vCPU.",
        ),
        lifespan=source_value(6 * u.year, INFRA_SOURCE, "low", "Generic server lifetime hypothesis."),
        idle_power=source_value(
            REFERENCE_HOST_IDLE_POWER_W * vcpu_allocation_share * u.W,
            INFRA_SOURCE,
            "low",
            f"{profile.vcpu}/24 of a generic 50 W host idle power, allocated in proportion to vCPU.",
        ),
        ram=source_value(
            profile.process_visible_ram_mib * u.MB_ram,
            MEMORY_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE,
            "medium" if profile.profile_id == "current" else "low",
            (
                "Process-visible production constraint retained from the production-container observations."
                if profile.profile_id == "current"
                else f"{profile.tier} nominal RAM minus the provisional 1.1 GiB unavailable allowance; "
                f"85% safe capacity is {profile.safe_ram_mib:.1f} MiB and the reconstructed maximum request is "
                f"{profile.estimated_max_request_peak_mib:.1f} MiB."
            ),
        ),
        compute=source_value(
            profile.vcpu * u.cpu_core,
            profile_source,
            "high" if profile.profile_id == "current" else "medium",
            f"The {profile.tier} Docker tier is allocated {profile.vcpu} vCPUs.",
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
            MEMORY_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE,
            "medium" if profile.profile_id == "current" else "low",
            "The modeled RAM value is already process-visible capacity, so no second headroom factor is applied.",
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


def build_benchmark_jobs(
    server: Server, evidence: dict[str, ActionEvidence], profile: ImplementationProfile
) -> dict[str, Job]:
    jobs = {}
    request_ram_mib = profile.process_visible_ram_mib - KEEP_ALIVE_RAM_MB
    for journey_id, recipe in JOURNEY_RECIPES.items():
        for action, _ in recipe:
            if action in jobs:
                continue
            measured = evidence[action]
            duration_factor = profile.action_duration_factors.get(action, profile.default_duration_factor)
            transfer_factor = profile.action_transfer_factors.get(action, profile.default_transfer_factor)
            modeled_duration_ms = measured.calibrated_production_ms * duration_factor
            if profile.profile_id == "current":
                request_comment = (
                    f"Proxy for server service time. Ten-run local median={measured.local_median_ms:.3f} ms; "
                    f"single production browser observation={measured.production_ms:.3f} ms; common calibration "
                    f"factor={measured.calibration_factor:.3f}; modeled duration={modeled_duration_ms:.3f} ms. "
                    "The common factor preserves the stable local action shape while matching the production total. "
                    "Replace with correlated server-log service time."
                )
                duration_source = BENCHMARK_SOURCE
                duration_confidence = "low"
            else:
                request_comment = (
                    f"Counterfactual central estimate: {duration_factor:g} × the current calibrated action duration "
                    f"of {measured.calibrated_production_ms:.3f} ms = {modeled_duration_ms:.3f} ms. Selective "
                    "recomputation and a partial NumPy implementation are retained; other optimization families "
                    "are removed."
                )
                duration_source = COUNTERFACTUAL_SOURCE
                duration_confidence = "low"
            jobs[action] = Job(
                f"{journey_id} benchmark action – {action}",
                server=server,
                data_transferred=source_value(
                    250 * transfer_factor * u.kB,
                    INFRA_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE,
                    "low",
                    f"Current placeholder is 250 kB; the {profile.profile_id} profile applies a "
                    f"{transfer_factor:g}× action-specific transfer factor.",
                ),
                data_stored=source_value(
                    0 * u.kB_stored,
                    INFRA_SOURCE,
                    "low",
                    "Session/cache writes are not yet inventoried as persistent storage growth.",
                ),
                request_duration=source_value(
                    modeled_duration_ms * u.ms, duration_source, duration_confidence, request_comment
                ),
                compute_needed=source_value(
                    0.5 * u.cpu_core,
                    INFRA_SOURCE,
                    "low",
                    "Average CPU occupancy hypothesis; replace with CPU-ms divided by service time from correlated logs.",
                ),
                ram_needed=source_value(
                    request_ram_mib * u.MB_ram,
                    USER_SCOPE_SOURCE,
                    "medium",
                    f"Reserves the single-worker {profile.tier} container for one request. One MiB is left for the "
                    "synthetic keep-alive demand, so one real request plus keep-alive fits exactly and a concurrent "
                    "request requires another instance. Tier selection is driven separately by the profile's "
                    "maximum-request memory requirement.",
                ),
            )
    return jobs


def build_journeys(
    server: Server,
    jobs: dict[str, Job],
    evidence: dict[str, ActionEvidence],
    profile: ImplementationProfile,
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
        duration_factor = profile.action_duration_factors.get(action, profile.default_duration_factor)
        transfer_factor = profile.action_transfer_factors.get(action, profile.default_transfer_factor)
        complex_duration_ms = base.calibrated_production_ms * duration_factor * 1.5
        complex_job = Job(
            f"S5 complex shared model – {action}",
            server=server,
            data_transferred=source_value(
                500 * transfer_factor * u.kB,
                INFRA_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE,
                "low",
                f"Twice the ordinary placeholder for the larger shared model, with the {profile.profile_id} "
                f"profile's {transfer_factor:g}× transfer factor.",
            ),
            data_stored=source_value(
                0 * u.kB_stored, INFRA_SOURCE, "low", "Read-only shared exploration; no persistent growth modeled."
            ),
            request_duration=source_value(
                complex_duration_ms * u.ms,
                USER_SCOPE_SOURCE if profile.profile_id == "current" else COUNTERFACTUAL_SOURCE,
                "low",
                f"No S5 benchmark exists yet. Uses 1.5 × the {profile.profile_id} duration for {action}: current "
                f"calibrated duration {base.calibrated_production_ms:.3f} ms × implementation factor "
                f"{duration_factor:g}. This represents a more complex-than-average shared model.",
            ),
            compute_needed=source_value(
                0.5 * u.cpu_core, INFRA_SOURCE, "low", "Same provisional average CPU occupancy as benchmarked jobs."
            ),
            ram_needed=source_value(
                (profile.process_visible_ram_mib - KEEP_ALIVE_RAM_MB) * u.MB_ram,
                USER_SCOPE_SOURCE,
                "medium",
                f"Same exclusive single-worker {profile.tier} container reservation as benchmarked requests.",
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
    shape = ADOPTION_SHAPES[scenario["adoption_shape"]]
    regime = ACTIVITY_REGIMES[scenario["activity_regime"]]
    mature_team_occurrences = (
        regime["interactive_sessions_per_team_month"]
        + regime["models_per_team"] * regime["automated_runs_per_model_month"]
    )
    mature_monthly_volume = (
        shape["mature_exploratory_sessions_per_month"]
        + shape["active_team_anchors"][2032] * mature_team_occurrences
    )
    comment = (
        f"Ground-up {scenario['label']} trajectory: {PRELAUNCH_MONTHLY_OCCURRENCES} monthly development occurrences "
        f"before the Oct 2026 public launch, then monthly interpolation between the "
        f"{scenario['adoption_shape']} year-end active-team anchors {shape['active_team_anchors']}. "
        f"At maturity, each team maintains {regime['models_per_team']} models, performs "
        f"{regime['interactive_sessions_per_team_month']} interactive sessions per month and triggers "
        f"{regime['automated_runs_per_model_month']:g} automated S6 runs per model per month. Public exploration "
        f"scales with team adoption to {shape['mature_exploratory_sessions_per_month']:,} sessions per month. "
        f"The resulting mature volume is {mature_monthly_volume:,.0f} occurrences per month and is held constant "
        "through the full 2033 stationary year. Automated frequency ramps to its regime target during the first "
        f"{AUTOMATION_RAMP_MONTHS} months after launch. "
        f"Traffic share: {geography_name}={geography_share:.0%}. Usage occurrences are spread evenly over "
        f"Monday–Friday 09:00–17:00 local time. Pre-launch mix={PRELAUNCH_MIX}; public-explorer mix="
        f"{PUBLIC_EXPLORER_MIX}; team-interactive mix={TEAM_INTERACTIVE_MIX}. "
        "S6 occurrences are automated model-maintenance runs with no user device time. No holidays, seasonality, "
        "bursts, churn, or landing-page-only visits are represented."
    )
    return SourceHourlyValues(
        Quantity(values, u.occurrence),
        start_date=START,
        source=USER_SCOPE_SOURCE,
        confidence="low",
        comment=comment,
    )


def monthly_volume_and_mix(scenario_name: str, month_key: tuple[int, int]) -> tuple[float, dict[str, float]]:
    occurrences = monthly_journey_occurrences(scenario_name, month_key)
    volume = sum(occurrences.values())
    return volume, {journey_id: count / volume for journey_id, count in occurrences.items()}


def monthly_journey_occurrences(scenario_name: str, month_key: tuple[int, int]) -> dict[str, float]:
    if month_number(month_key) < month_number(PUBLIC_LAUNCH):
        return {
            journey_id: PRELAUNCH_MONTHLY_OCCURRENCES * share
            for journey_id, share in PRELAUNCH_MIX.items()
        }

    scenario = SCENARIOS[scenario_name]
    shape = ADOPTION_SHAPES[scenario["adoption_shape"]]
    regime = ACTIVITY_REGIMES[scenario["activity_regime"]]
    active_teams = interpolated_active_teams(shape, month_key)
    mature_teams = float(shape["active_team_anchors"][2032])
    exploratory_sessions = shape["mature_exploratory_sessions_per_month"] * active_teams / mature_teams
    interactive_sessions = active_teams * regime["interactive_sessions_per_team_month"]
    months_after_launch = month_number(month_key) - month_number(PUBLIC_LAUNCH)
    automation_ramp = min(1.0, (months_after_launch + 1) / AUTOMATION_RAMP_MONTHS)
    automated_runs = (
        active_teams
        * regime["models_per_team"]
        * regime["automated_runs_per_model_month"]
        * automation_ramp
    )
    return {
        journey_id: (
            exploratory_sessions * PUBLIC_EXPLORER_MIX[journey_id]
            + interactive_sessions * TEAM_INTERACTIVE_MIX[journey_id]
            + (automated_runs if journey_id == "S6" else 0)
        )
        for journey_id in JOURNEY_USER_MINUTES
    }


def interpolated_active_teams(shape: dict, month_key: tuple[int, int]) -> float:
    points = [((2026, 9), 0.0)] + [
        ((year, 12), float(value)) for year, value in shape["active_team_anchors"].items()
    ]
    target = month_number(month_key)
    for (left_month, left_value), (right_month, right_value) in zip(points, points[1:]):
        left = month_number(left_month)
        right = month_number(right_month)
        if target <= right:
            fraction = (target - left) / (right - left)
            return left_value + (right_value - left_value) * fraction
    return points[-1][1]


def month_number(month_key: tuple[int, int]) -> int:
    return month_key[0] * 12 + month_key[1] - 1


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
            "One MB complements each real job's profile-specific reservation without forcing a second instance.",
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
    total = 0.0
    year, month = START.year, START.month
    while (year, month) < (END.year, END.month):
        total += monthly_volume_and_mix(scenario_name, (year, month))[0]
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return total


def serialize_and_validate(
    system: System, scenario_name: str, profile: ImplementationProfile
) -> tuple[dict, float, float]:
    document = system_to_json(system, output_filepath=None, save_computed_state=False)
    class_objects, _, _ = json_to_system(json.loads(json.dumps(document)))
    loaded_system = next(iter(class_objects["System"].values()))
    expected_pattern_count = len(GEOGRAPHIES) * len(JOURNEY_USER_MINUTES) + 1
    if len(loaded_system.usage_patterns) != expected_pattern_count:
        raise ValueError(
            f"Round-tripped model contains {len(loaded_system.usage_patterns)} usage patterns, "
            f"expected {expected_pattern_count}"
        )
    if BENCHMARK_SOURCE.id not in document["Sources"] or USER_SCOPE_SOURCE.id not in document["Sources"]:
        raise ValueError("Expected traceability sources are absent from generated JSON")
    if profile.profile_id != "current" and COUNTERFACTUAL_SOURCE.id not in document["Sources"]:
        raise ValueError("Counterfactual profile source is absent from generated JSON")
    traffic_total = sum(
        pattern.hourly_occurrences.sum().to(u.occurrence).magnitude
        for pattern in loaded_system.usage_patterns
        if pattern.name != "Minimum one application instance"
    )
    if not math.isclose(traffic_total, expected_usage_total(scenario_name), rel_tol=1e-7, abs_tol=0.05):
        raise ValueError(f"Generated traffic sums to {traffic_total}, not the expected scenario total")
    instances = loaded_system.servers[0].nb_of_instances
    if instances.min().magnitude != 1:
        raise ValueError("Synthetic keep-alive failed to preserve a minimum of one application instance")
    return document, traffic_total, float(instances.max().magnitude)


def write_and_validate(
    system: System, output_path: Path, scenario_name: str, profile: ImplementationProfile
) -> None:
    document, traffic_total, max_instances = serialize_and_validate(system, scenario_name, profile)
    output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(
        f"{profile.profile_id}/{scenario_name}: wrote {output_path} "
        f"({traffic_total:,.0f} modeled usage occurrences, instances 1–{max_instances:g}, "
        f"tier {profile.tier}, {output_path.stat().st_size / 1_000_000:.1f} MB)"
    )


def comparable_object_ids(document: dict) -> set[str]:
    """Return modeling-object ids that the interface uses to pair comparison rows."""
    excluded = {"System", "Sources", "calculation_graph", "interface_config"}
    return {
        object_id
        for class_name, objects in document.items()
        if class_name not in excluded and isinstance(objects, dict)
        for object_id in objects
    }


def write_comparison_workspace(
    scenario_name: str,
    evidence: dict[str, ActionEvidence],
    profiles: dict[str, ImplementationProfile],
    output_path: Path,
) -> None:
    """Write the current and counterfactual systems as sibling models in one interface workspace."""
    documents = []
    diagnostics = []
    for profile_id in ("current", "no-ai-low-optim"):
        profile = profiles[profile_id]
        document, traffic_total, max_instances = serialize_and_validate(
            build_system(scenario_name, evidence, profile), scenario_name, profile
        )
        documents.append(document)
        diagnostics.append((profile, traffic_total, max_instances))

    system_ids = [next(iter(document["System"])) for document in documents]
    if len(set(system_ids)) != 2:
        raise ValueError("Comparison siblings must have distinct System ids")
    if comparable_object_ids(documents[0]) != comparable_object_ids(documents[1]):
        raise ValueError("Comparison siblings do not share the same semantic modeling-object ids")

    workspace = {
        "efootprint_workspace_version": INTERFACE_VERSION,
        "active_slot": 0,
        "models": documents,
    }
    output_path.write_text(json.dumps(workspace, indent=2) + "\n", encoding="utf-8")
    current, counterfactual = diagnostics
    print(
        f"comparison/{scenario_name}: wrote {output_path} "
        f"({current[1]:,.0f} modeled usage occurrences per sibling, "
        f"instances current 1–{current[2]:g} vs no-ai-low-optim 1–{counterfactual[2]:g}, "
        f"tiers {current[0].tier} vs {counterfactual[0].tier}, "
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
    parser.add_argument(
        "--implementation",
        choices=["all", "current", "no-ai-low-optim", "comparison"],
        default="current",
        help=(
            "Generate a standalone profile, both standalone profiles, or one two-model comparison "
            "workspace per scenario."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ModelingObject._use_name_as_id = True
    Source._use_name_as_id = True
    validate_scenario_config()
    evidence = load_benchmark_evidence()
    profiles = load_implementation_profiles()
    selected_scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]
    if args.implementation == "comparison":
        for scenario_name in selected_scenarios:
            write_comparison_workspace(
                scenario_name,
                evidence,
                profiles,
                args.output_dir / f"current-vs-no-ai-low-optim-{scenario_name}.e-f.json",
            )
        return

    selected_profiles = profiles if args.implementation == "all" else [args.implementation]
    for profile_id in selected_profiles:
        profile = profiles[profile_id]
        for scenario_name in selected_scenarios:
            system = build_system(scenario_name, evidence, profile)
            write_and_validate(
                system,
                args.output_dir / f"{profile.file_prefix}-{scenario_name}.e-f.json",
                scenario_name,
                profile,
            )


if __name__ == "__main__":
    main()
