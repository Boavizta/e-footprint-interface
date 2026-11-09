"""One bounded Mistral request; the application owns answer construction."""
import os
import time

from model_builder.application.ai_bootstrap.service import Completion

MODEL = "zai-glm-5-3-flash"


class ProviderError(Exception):
    """Fixed, content-free failure suitable for response handling."""


def _api_key() -> str:
    from django.conf import settings
    if settings.configured:
        return getattr(settings, "MISTRAL_API_KEY", "")
    return os.environ.get("MISTRAL_API_KEY", "")


def is_available() -> bool:
    from django.conf import settings
    return bool(getattr(settings, "AI_BOOTSTRAP_ENABLED", False) and _api_key())


def complete_mistral(system_prompt: str, description: str) -> Completion:
    from mistralai.client import Mistral
    from mistralai.client.utils.logger import NoOpLogger

    try:
        start = time.perf_counter()
        with Mistral(api_key=_api_key(), debug_logger=NoOpLogger()) as client:
            response = client.chat.complete(
                model=MODEL, max_tokens=16000, response_format={"type": "json_object"}, reasoning_effort="low",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
                timeout_ms=45000, retries=None,
            )
        latency = time.perf_counter() - start
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise ProviderError("Generation did not complete")
        content = choice.message.content
        if not isinstance(content, str):
            content = "".join(chunk.text for chunk in content or [] if getattr(chunk, "type", None) == "text")
        usage = response.usage
        return Completion(
            text=content, input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None), cached_input_tokens=None,
            latency_s=latency, stop_reason=choice.finish_reason,
        )
    except ProviderError:
        raise
    except Exception:
        raise ProviderError("Generation provider unavailable") from None
