"""Provider adapters. Each returns the raw text, a normalized usage dict and the USD cost.

Prices are USD per million tokens, captured on 2026-10-27 from:
- Anthropic: claude-api skill model table (first-party API rates)
- OpenAI: https://developers.openai.com/api/docs/pricing
- Mistral: https://docs.mistral.ai/inference/pricing (also hosts the open-weight GLM and DeepSeek models, 2026-10-28)
Cached-input discounts are applied only for Anthropic (cache read 0.1x, cache write 1.25x). OpenAI cached
tokens are recorded but priced at the full input rate, which overestimates slightly.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

SANDBOX_DIR = Path(__file__).parent


def load_dotenv(path: Path = SANDBOX_DIR.parent / ".env"):
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


MODELS = {
    # name: (provider, input $/M, output $/M)
    "claude-haiku-5-5": ("anthropic", 0.10, 0.50),
    "claude-sonnet-5-5": ("anthropic", 2.00, 10.00),
    "claude-opus-5-5": ("anthropic", 4.00, 20.00),
    "gpt-6-luna": ("openai", 0.10, 0.50),
    "gpt-6.1-terra": ("openai", 1.00, 5.00),
    "mistral-small-latest": ("mistral", 0.15, 0.60),
    "mistral-medium-latest": ("mistral", 1.50, 7.50),
    "mistral-large-4": ("mistral", 1.36, 4.18),
    # Open-weight models served on the Mistral platform (same key, same adapter).
    "zai-glm-5-3-flash": ("mistral", 0.15, 0.50),   # Z.ai, MIT; reasoning cannot be disabled
    "zai-glm-5-3": ("mistral", 1.40, 4.40),         # Z.ai, near-MIT custom license; reasoning cannot be disabled
    "deepseek-v4-1-flash-1017": ("mistral", 0.30, 1.20),  # DeepSeek, MIT; 2x the DeepSeek first-party off-peak price
}

# GLM models reason at effort "max" unless told otherwise, which is where their cost would go; start them low.
DEFAULT_EFFORT = {"zai-glm-5-3-flash": "low", "zai-glm-5-3": "low"}

# The first full run (2026-10-28, 3 cases x 7 models x 2 reps) kept these two: Haiku for quality per dollar, Luna as
# the cheap comparison point. Sonnet and Large 4 cost 10x for no structural gain, Medium and Small misread volumes.
# The three open-weight models joined them on 2026-10-29 for a second comparison; zai-glm-5-3-flash comes first
# because the interface's AI assistant preselects the first model of this list.
DEFAULT_MODELS = ["zai-glm-5-3-flash", "claude-haiku-5-5", "gpt-6-luna", "deepseek-v4-1-flash-1017", "zai-glm-5-3"]


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int | None = None  # included in output_tokens when the provider reports it
    latency_s: float = 0.0
    stop_reason: str | None = None
    request_params: dict = field(default_factory=dict)

    def cost_usd(self, model: str) -> float:
        _, price_in, price_out = MODELS[model]
        uncached = self.input_tokens - self.cached_input_tokens - self.cache_write_tokens
        return (uncached * price_in + self.cached_input_tokens * price_in * 0.1
                + self.cache_write_tokens * price_in * 1.25 + self.output_tokens * price_out) / 1e6


MAX_OUTPUT_TOKENS = 16000  # reasoning models spend most of it thinking; 8000 cut mistral-large-4 off


def _anthropic(model, system, prompt, effort) -> Completion:
    import anthropic
    client = anthropic.Anthropic()
    params = dict(
        model=model, max_tokens=MAX_OUTPUT_TOKENS,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}])
    if effort:
        params["output_config"] = {"effort": effort}
    start = time.perf_counter()
    response = client.messages.create(**params)
    latency = time.perf_counter() - start
    text = "".join(block.text for block in response.content if block.type == "text")
    usage = response.usage
    cache_read = usage.cache_read_input_tokens or 0
    cache_write = usage.cache_creation_input_tokens or 0
    return Completion(
        text=text, input_tokens=usage.input_tokens + cache_read + cache_write, output_tokens=usage.output_tokens,
        cached_input_tokens=cache_read, cache_write_tokens=cache_write, latency_s=latency,
        stop_reason=response.stop_reason, request_params={k: v for k, v in params.items() if k != "system"})


def _openai(model, system, prompt, effort) -> Completion:
    from openai import OpenAI
    client = OpenAI()
    # OpenAI's JSON mode requires the word "json" in the input itself, instructions do not count.
    params = dict(
        model=model, instructions=system, input=prompt + "\n\nRespond with the JSON object only.",
        max_output_tokens=MAX_OUTPUT_TOKENS, text={"format": {"type": "json_object"}})
    if effort:
        params["reasoning"] = {"effort": effort}
    start = time.perf_counter()
    response = client.responses.create(**params)
    latency = time.perf_counter() - start
    usage = response.usage
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    reasoning = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", None)
    return Completion(
        text=response.output_text, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        cached_input_tokens=cached, reasoning_tokens=reasoning, latency_s=latency,
        stop_reason=getattr(response, "status", None),
        request_params={k: v for k, v in params.items() if k not in ("instructions", "input")})


def _mistral(model, system, prompt, effort) -> Completion:
    from mistralai.client import Mistral
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    params = dict(
        model=model, max_tokens=MAX_OUTPUT_TOKENS, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
    if effort:
        params["reasoning_effort"] = effort
    start = time.perf_counter()
    response = client.chat.complete(**params)
    latency = time.perf_counter() - start
    choice = response.choices[0]
    content = choice.message.content
    thinking_chars = 0
    if not isinstance(content, str):  # list of chunks: TextChunk and, on reasoning models, ThinkChunk
        thinking_chars = sum(len(getattr(t, "text", "")) for chunk in content for t in getattr(chunk, "thinking", []) or [])
        content = "".join(getattr(chunk, "text", "") for chunk in content)
    usage = response.usage
    # Mistral reports no reasoning token split; approximate from the thinking text at 4 chars per token.
    return Completion(
        text=content, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens,
        reasoning_tokens=thinking_chars // 4 if thinking_chars else None,
        latency_s=latency, stop_reason=choice.finish_reason,
        request_params={k: v for k, v in params.items() if k != "messages"})


ADAPTERS = {"anthropic": _anthropic, "openai": _openai, "mistral": _mistral}


def complete(model: str, system: str, prompt: str, effort: str | None = None) -> Completion:
    provider = MODELS[model][0]
    effort = effort or DEFAULT_EFFORT.get(model)
    return ADAPTERS[provider](model, system, prompt, effort)


def list_models() -> dict[str, list[str]]:
    """Free calls: validates the API keys and lets us check the model ids in MODELS exist."""
    import anthropic
    from openai import OpenAI
    from mistralai.client import Mistral
    out = {"anthropic": sorted(m.id for m in anthropic.Anthropic().models.list(limit=100))}
    out["openai"] = sorted(m.id for m in OpenAI().models.list())
    out["mistral"] = sorted(m.id for m in Mistral(api_key=os.environ["MISTRAL_API_KEY"]).models.list().data)
    return out


if __name__ == "__main__":
    load_dotenv()
    for provider, ids in list_models().items():
        wanted = [m for m, (p, _, _) in MODELS.items() if p == provider]
        print(f"{provider}: {len(ids)} models; wanted {wanted}")
        for m in wanted:
            print("  ", "OK " if m in ids else "MISSING", m)
        print("   sample:", [i for i in ids if any(k in i for k in ("gpt-6", "gpt-5", "claude", "mistral", "ministral"))][:40])
