"""One bounded Mistral request; the application owns answer construction."""
import os
import time

from efootprint.logger import logger

from model_builder.application.ai_bootstrap.service import Completion

MODEL = "zai-glm-5-3-flash"
# The finish reasons the SDK knows: any other string the provider sends is logged as "unrecognized".
FINISH_REASONS = {"length", "model_length", "error", "tool_calls", None}


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


def _failure_kind(error: Exception) -> str:
    """The failure's kind, never its text: the SDK's errors can carry the response body."""
    from httpx2 import TimeoutException
    from mistralai.client.errors import MistralError, ResponseValidationError
    if isinstance(error, TimeoutException):
        return "timeout"
    if isinstance(error, ResponseValidationError):  # a response the SDK could not read, often a 200
        return f"ResponseValidationError (HTTP {error.status_code})"
    if isinstance(error, MistralError):
        return f"HTTP {error.status_code}"
    return type(error).__name__


def complete_mistral(system_prompt: str, description: str) -> Completion:
    from mistralai.client import Mistral
    from mistralai.client.utils.logger import NoOpLogger

    start = time.perf_counter()
    try:
        with Mistral(api_key=_api_key(), debug_logger=NoOpLogger()) as client:
            response = client.chat.complete(
                model=MODEL, max_tokens=16000, response_format={"type": "json_object"}, reasoning_effort="low",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": description}],
                timeout_ms=45000, retries=None,
            )
        latency = time.perf_counter() - start
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            reason = choice.finish_reason if choice.finish_reason in FINISH_REASONS else "unrecognized"
            logger.warning("AI provider failure: unfinished (%s) after %.1f s", reason, latency)
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
    except Exception as error:
        logger.warning("AI provider failure: %s after %.1f s", _failure_kind(error), time.perf_counter() - start)
        raise ProviderError("Generation provider unavailable") from None
