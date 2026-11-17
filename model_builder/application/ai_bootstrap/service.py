"""Build a library graph without persistence or presentation concerns."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from efootprint.core.system import System

from model_builder.narrate import narrate, planned

from .catalogs import Resolution
from .dsl import ModelSpec, build_system, parse_json, validate_tolerating_extras


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
    planned("ai-bootstrap-edge#edge-instructions", "For Web + edge, its own prompt file is read: the sandbox's, moved here and edited for the new format.")
    return Path(__file__).with_name("system_prompt.md").read_text()


def build_answer(text: str) -> GeneratedModel:
    data, _, error = parse_json(text)
    if data is None:
        raise ValueError("Invalid JSON answer")
    planned("ai-bootstrap-edge#scope-selects-format", "The answer is held to the schema of the scope it was asked in.")
    spec, ignored = validate_tolerating_extras(data, ModelSpec)
    narrate("The answer is read as JSON and **held to the bootstrap schema** by `validate_tolerating_extras`: a "
            "field the schema does not know is dropped and listed, anything else wrong refuses the answer.",
            lambda: {"ignored_fields": ignored})
    system, resolutions = build_system(spec)
    return GeneratedModel(system, resolutions, ignored)


def generate(description: str, complete: Callable[[str, str], Completion]) -> tuple[GeneratedModel, Completion]:
    narrate("**One request** carries the shared `system_prompt` and the description to the provider.",
            lambda: {"description_characters": len(description)})
    planned("ai-bootstrap-edge#scope-selects-format", "The scope picks the instructions and the schema; its callers and tests pass it.")
    completion = complete(system_prompt(), description)
    return build_answer(completion.text), completion
