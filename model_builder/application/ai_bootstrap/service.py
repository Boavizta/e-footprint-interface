"""Build a library graph without persistence or presentation concerns."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from efootprint.core.system import System

from model_builder.narrate import narrate

from .catalogs import Resolution
from .dsl import ModelSpec, WebEdgeSpec, build_system, parse_json, validate_tolerating_extras


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


@dataclass(frozen=True)
class Scope:
    prompt_file: str
    schema: type[ModelSpec]


# Each scope pairs its instructions with the schema its answer is held to; everything after the answer is shared.
SCOPES = {"web": Scope("system_prompt.md", ModelSpec), "web_edge": Scope("system_prompt_web_edge.md", WebEdgeSpec)}


def system_prompt(scope: str) -> str:
    return Path(__file__).with_name(SCOPES[scope].prompt_file).read_text()


def build_answer(text: str, scope: str) -> GeneratedModel:
    data, _, error = parse_json(text)
    if data is None:
        raise ValueError("Invalid JSON answer")
    spec, ignored = validate_tolerating_extras(data, SCOPES[scope].schema)
    narrate("The answer is read as JSON and **held to the schema of its scope** by `validate_tolerating_extras`: a "
            "field the schema does not know is dropped and listed, anything else wrong refuses the answer.",
            lambda: {"scope": scope, "ignored_fields": ignored})
    system, resolutions = build_system(spec)
    return GeneratedModel(system, resolutions, ignored)


def generate(description: str, scope: str,
             complete: Callable[[str, str], Completion]) -> tuple[GeneratedModel, Completion]:
    narrate("**One request** carries the scope's `system_prompt` and the description to the provider.",
            lambda: {"scope": scope, "description_characters": len(description)})
    completion = complete(system_prompt(scope), description)
    return build_answer(completion.text, scope), completion
