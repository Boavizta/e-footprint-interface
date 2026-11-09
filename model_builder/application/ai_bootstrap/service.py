"""Build a library graph without persistence or presentation concerns."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from efootprint.core.system import System

from .catalogs import Resolution
from .dsl import build_system, parse_json, validate_tolerating_extras


@dataclass
class Completion:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    latency_s: float = 0.0
    stop_reason: str | None = None


@dataclass
class GeneratedModel:
    system: System
    resolutions: list[Resolution]
    ignored_fields: list[str]


def system_prompt() -> str:
    return Path(__file__).with_name("system_prompt.md").read_text()


def build_answer(text: str) -> GeneratedModel:
    data, _, error = parse_json(text)
    if data is None:
        raise ValueError("Invalid JSON answer")
    spec, ignored = validate_tolerating_extras(data)
    system, resolutions = build_system(spec)
    return GeneratedModel(system, resolutions, ignored)


def generate(description: str, complete: Callable[[str, str], Completion]) -> tuple[GeneratedModel, Completion]:
    completion = complete(system_prompt(), description)
    return build_answer(completion.text), completion
