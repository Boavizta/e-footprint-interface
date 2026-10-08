"""Normalize repository-owned interface settings independently of version migrations."""

from model_builder.domain.services.simplified_inputs import normalize_definition


def normalize_interface_config(config: dict) -> dict:
    """Add optional definition defaults on every read, including current-version files."""
    config = dict(config)
    config["simplified_inputs"] = normalize_definition(config.get("simplified_inputs"))
    return config
