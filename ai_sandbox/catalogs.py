"""Developer-only refresh of the production sizing snapshot."""
import json
import re

from model_builder.application.ai_bootstrap.catalogs import (
    CATALOG_DIR, INSTANCE_SPECS_PATH, GENERAL_PURPOSE_FAMILIES, cloud_instances_by_provider,
)


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



if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["refresh"]:
        refresh_instance_specs()
    else:
        print("usage: python -m ai_sandbox.catalogs refresh")
