"""Deterministic resolution of catalog choices the LLM should not have to memorize.

Two catalogs are *conditional list values* in the library: a GenAI API's model_name depends on its provider
(EcoLogits catalog), and a cloud server's instance_type depends on its provider (Boavizta catalog). The model
expresses intent (provider, a model name it believes exists, a size in cores and GB); this module snaps it to a
real catalog entry and reports how it did, so the run record shows exact / normalized / prefix / fallback.

Instance specs (vCPU, RAM) only exist behind the live Boavizta API, so `refresh_instance_specs` fetches a
curated set of general-purpose families once and caches them in `catalogs/boavizta_instance_specs.json`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CATALOG_DIR = Path(__file__).parent / "catalogs"
INSTANCE_SPECS_PATH = CATALOG_DIR / "boavizta_instance_specs.json"


@dataclass
class Resolution:
    kind: str          # "genai_model" | "cloud_instance" | "provider"
    requested: str
    resolved: str
    how: str           # "exact" | "normalized" | "prefix" | "fallback" | "sized"

    def as_dict(self):
        return dict(self.__dict__)


def _normalize(name: str) -> str:
    name = name.strip().lower().replace(".", "-").replace("_", "-").replace(" ", "-")
    name = re.sub(r"-(latest|preview)$", "", name)
    name = re.sub(r"-(\d{8}|\d{4}-\d{2}-\d{2}|\d{4})$", "", name)
    return name


def _snap(requested: str, candidates: list[str], fallback: str) -> tuple[str, str]:
    """exact -> normalized -> prefix either way -> containment (org/name catalogs) -> fallback."""
    if requested in candidates:
        return requested, "exact"
    norm = _normalize(requested).split("/")[-1]
    # When several catalog names normalize alike (mistral-small-2603, mistral-small-latest), prefer the alias.
    by_norm = {}
    for c in sorted(candidates, key=lambda c: (not c.endswith("-latest"), len(c))):
        by_norm.setdefault(_normalize(c).split("/")[-1], c)
    if norm in by_norm:
        return by_norm[norm], "normalized"
    if len(norm) >= 4:
        prefixed = [(len(n), c) for n, c in by_norm.items() if n.startswith(norm) or norm.startswith(n)]
        if prefixed:
            best = min(prefixed, key=lambda item: abs(item[0] - len(norm)))
            return best[1], "prefix"
        containing = [(len(n), c) for n, c in by_norm.items() if norm in n]
        if containing:
            return min(containing)[1], "contains"
    return fallback, "fallback"


# --- EcoLogits GenAI models --------------------------------------------------------------------

GENAI_PROVIDER_ALIASES = {
    "openai": "openai", "anthropic": "anthropic", "claude": "anthropic",
    "mistralai": "mistralai", "mistral": "mistralai", "mistral-ai": "mistralai",
    "google_genai": "google_genai", "google": "google_genai", "gemini": "google_genai", "google-genai": "google_genai",
    "cohere": "cohere",
    "huggingface_hub": "huggingface_hub", "huggingface": "huggingface_hub", "hf": "huggingface_hub",
    "meta": "huggingface_hub", "llama": "huggingface_hub",
}
GENAI_DEFAULT_MODEL = {
    "openai": "gpt-5-mini", "anthropic": "claude-sonnet-5-5", "mistralai": "mistral-small-latest",
    "google_genai": "gemini-2.5-flash", "cohere": "command-a-03-2025",
}


def genai_models_by_provider() -> dict[str, list[str]]:
    from ecologits.model_repository import models
    out: dict[str, list[str]] = {}
    for m in models.list_models():
        out.setdefault(m.provider.name, []).append(m.name)
    return {k: sorted(v) for k, v in out.items()}


def resolve_genai(provider: str, model_name: str | None, resolutions: list[Resolution]) -> tuple[str, str]:
    catalog = genai_models_by_provider()
    if not model_name:
        provider_key = GENAI_PROVIDER_ALIASES.get(provider.strip().lower().replace(" ", "_"), "openai")
        default = GENAI_DEFAULT_MODEL.get(provider_key, catalog[provider_key][0])
        resolutions.append(Resolution("genai_model", f"{provider}/<unstated>", f"{provider_key}/{default}", "default"))
        return provider_key, default
    provider_key = GENAI_PROVIDER_ALIASES.get(provider.strip().lower().replace(" ", "_"))
    if provider_key is None:
        # last resort: the provider whose catalog contains the model name
        matches = [p for p, names in catalog.items() if _snap(model_name, names, "")[1] != "fallback"]
        provider_key = matches[0] if matches else "openai"
        resolutions.append(Resolution("provider", provider, provider_key, "fallback"))
    elif provider_key != provider:
        resolutions.append(Resolution("provider", provider, provider_key, "normalized"))
    names = catalog[provider_key]
    fallback = GENAI_DEFAULT_MODEL.get(provider_key) or next(
        (n for key in ("llama-3.3-70b", "llama-3.1-70b", "llama-3.1-8b", "llama-3", "llama")
         for n in names if key in n.lower()), names[0])
    resolved, how = _snap(model_name, names, fallback)
    if how != "exact":
        resolutions.append(Resolution("genai_model", f"{provider}/{model_name}", f"{provider_key}/{resolved}", how))
    return provider_key, resolved


# --- Boavizta cloud instances ------------------------------------------------------------------

CLOUD_PROVIDER_ALIASES = {
    "aws": "aws", "amazon": "aws", "amazon-web-services": "aws", "ec2": "aws",
    "azure": "azure", "microsoft": "azure", "microsoft-azure": "azure",
    "gcp": "gcp", "google": "gcp", "google-cloud": "gcp", "gce": "gcp",
    "ovhcloud": "ovhcloud", "ovh": "ovhcloud",
    "scaleway": "scaleway",
}
# General-purpose families only: sizing by cores and RAM across GPU, memory- or storage-optimized
# instances would pick odd hardware. Patterns are matched against the snapshot's instance names.
GENERAL_PURPOSE_FAMILIES = {
    "aws": r"^m(5|5a|6g|6i|7g|7i)\.(medium|large|xlarge|2xlarge|4xlarge|8xlarge|12xlarge|16xlarge)$",
    "azure": r"^d\d+a?d?s?_v5$",
    "gcp": r"^(n2|c4a|e2)-standard-\d+$",
    "ovhcloud": r"^b3-\d+$",
    "scaleway": r"^(coparm1|ent1|pro2|dev1)-",
}


def cloud_instances_by_provider() -> dict[str, list[str]]:
    from efootprint.builders.hardware.boavizta_cloud_server import boavizta_cloud_snapshot
    return boavizta_cloud_snapshot["instances_by_provider"]


def refresh_instance_specs(verbose=True) -> dict:
    """Fetch vCPU and RAM for the curated families from the Boavizta API and cache them locally."""
    from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi
    specs: dict[str, dict[str, dict]] = {}
    for provider, names in cloud_instances_by_provider().items():
        pattern = re.compile(GENERAL_PURPOSE_FAMILIES[provider])
        for name in names:
            if not pattern.match(name):
                continue
            try:
                response = call_boaviztapi(
                    url="https://api.boavizta.org/v1/cloud/instance", params={"provider": provider, "instance_type": name})
                verbose_part = response["verbose"]
                specs.setdefault(provider, {})[name] = {
                    "vcpu": float(verbose_part["vcpu"]["value"]), "ram_gb": float(verbose_part["memory"]["value"]),
                    "avg_power_w": round(float(verbose_part["avg_power"]["value"]), 2),
                    "embodied_kg": float(response["impacts"]["gwp"]["embedded"]["value"])}
            except Exception as error:  # noqa: BLE001
                if verbose:
                    print(f"  skip {provider}/{name}: {type(error).__name__}: {error}")
        if verbose:
            print(f"{provider}: {len(specs.get(provider, {}))} instances")
    CATALOG_DIR.mkdir(exist_ok=True)
    INSTANCE_SPECS_PATH.write_text(json.dumps(specs, indent=1, sort_keys=True))
    return specs


def load_instance_specs() -> dict:
    if not INSTANCE_SPECS_PATH.exists():
        raise FileNotFoundError(
            f"{INSTANCE_SPECS_PATH} missing: run `poetry run python ai_sandbox/catalogs.py refresh`")
    return json.loads(INSTANCE_SPECS_PATH.read_text())


DEFAULT_CORES, DEFAULT_RAM_GB = 2, 4


def resolve_cloud_instance(provider: str, instance_type: str | None, cores: float | None, ram_gb: float | None,
                           resolutions: list[Resolution]) -> tuple[str, str]:
    provider_key = CLOUD_PROVIDER_ALIASES.get(provider.strip().lower().replace(" ", "-").replace("_", "-"))
    if provider_key is None:
        provider_key = "scaleway"
        resolutions.append(Resolution("provider", provider, provider_key, "fallback"))
    elif provider_key != provider:
        resolutions.append(Resolution("provider", provider, provider_key, "normalized"))
    all_names = cloud_instances_by_provider()[provider_key]
    if instance_type:
        resolved, how = _snap(instance_type, all_names, "")
        if how != "fallback":
            if how != "exact":
                resolutions.append(Resolution("cloud_instance", f"{provider}/{instance_type}", f"{provider_key}/{resolved}", how))
            return provider_key, resolved
    specs = load_instance_specs()[provider_key]
    need_cores, need_ram = cores or DEFAULT_CORES, ram_gb or DEFAULT_RAM_GB
    fitting = [(s["vcpu"], s["ram_gb"], n) for n, s in specs.items() if s["vcpu"] >= need_cores and s["ram_gb"] >= need_ram]
    chosen = min(fitting)[2] if fitting else max((s["vcpu"], s["ram_gb"], n) for n, s in specs.items())[2]
    requested = f"{provider}/{instance_type or '?'} ({need_cores} cores, {need_ram} GB)"
    resolutions.append(Resolution("cloud_instance", requested, f"{provider_key}/{chosen}", "sized" if fitting else "fallback"))
    return provider_key, chosen


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["refresh"]:
        refresh_instance_specs()
    else:
        print("usage: catalogs.py refresh")
