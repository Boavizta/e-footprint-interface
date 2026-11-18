import logging
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import httpx2
import pytest
from mistralai.client.errors import ResponseValidationError, SDKError

from model_builder.adapters.ai_provider import ProviderError, complete_mistral, is_available


def sdk(monkeypatch, content='{"system_name":"Example"}', usage=NS(prompt_tokens=20, completion_tokens=30),
        stop="stop"):
    client = MagicMock()
    client.__enter__.return_value = client
    client.chat.complete.return_value = NS(choices=[NS(finish_reason=stop, message=NS(content=content))], usage=usage)
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr("mistralai.client.Mistral", constructor)
    monkeypatch.setenv("MISTRAL_API_KEY", "dummy")
    monkeypatch.setattr("django.conf.settings.MISTRAL_API_KEY", "dummy")
    return client, constructor


def test_fixed_request_and_usage(monkeypatch, caplog):
    client, constructor = sdk(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        completion = complete_mistral("System", "Description")
    assert not caplog.records
    constructor.assert_called_once()
    assert constructor.call_args.kwargs["api_key"] == "dummy"
    from mistralai.client.utils.logger import NoOpLogger
    assert isinstance(constructor.call_args.kwargs["debug_logger"], NoOpLogger)
    client.chat.complete.assert_called_once_with(
        model="zai-glm-5-3-flash", max_tokens=16000, response_format={"type": "json_object"},
        reasoning_effort="low", timeout_ms=45000, retries=None,
        messages=[{"role": "system", "content": "System"}, {"role": "user", "content": "Description"}],
    )
    assert (completion.input_tokens, completion.output_tokens, completion.cached_input_tokens) == (20, 30, None)
    assert completion.stop_reason == "stop" and completion.latency_s >= 0


def test_text_chunks_exclude_thinking_and_missing_usage(monkeypatch):
    sdk(monkeypatch, [NS(type="thinking", text="private"), NS(type="text", text="{}")], usage=None)
    result = complete_mistral("System", "Description")
    assert result.text == "{}"
    assert result.input_tokens is result.output_tokens is result.cached_input_tokens is None


@pytest.mark.parametrize("reason", ["length", "error", None])
def test_unsuccessful_output_is_rejected(monkeypatch, reason):
    sdk(monkeypatch, stop=reason)
    with pytest.raises(ProviderError, match="^Generation did not complete$"):
        complete_mistral("System", "Description")


def test_provider_error_is_content_free_and_never_retried(monkeypatch):
    client, _ = sdk(monkeypatch)
    client.chat.complete.side_effect = RuntimeError("SENTINEL secret request body")
    with pytest.raises(ProviderError) as raised:
        complete_mistral("SENTINEL prompt", "SENTINEL description")
    assert str(raised.value) == "Generation provider unavailable"
    assert raised.value.__suppress_context__
    client.chat.complete.assert_called_once()


@pytest.mark.parametrize("error, stop, kind", [
    (httpx2.ReadTimeout("SENTINEL timeout"), "stop", "timeout"),
    (SDKError("SENTINEL message", httpx2.Response(503, text="SENTINEL body")), "stop", "HTTP 503"),
    (ResponseValidationError("SENTINEL message", httpx2.Response(200, text="SENTINEL body"), ValueError("SENTINEL")),
     "stop", "ResponseValidationError (HTTP 200)"),
    (RuntimeError("SENTINEL other"), "stop", "RuntimeError"),
    (None, "length", "unfinished (length)"),
    (None, "SENTINEL reason", "unfinished (unrecognized)"),
])
def test_failure_logs_its_kind_and_latency_only(monkeypatch, caplog, error, stop, kind):
    client, _ = sdk(monkeypatch, content="SENTINEL answer", stop=stop)
    client.chat.complete.side_effect = error
    with pytest.raises(ProviderError), caplog.at_level(logging.DEBUG):
        complete_mistral("SENTINEL prompt", "SENTINEL description")
    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.getMessage().startswith(f"AI provider failure: {kind} after ") and record.getMessage().endswith(" s")
    assert "SENTINEL" not in caplog.text


def test_availability_requires_flag_and_key(settings, monkeypatch):
    settings.AI_BOOTSTRAP_ENABLED = True
    settings.MISTRAL_API_KEY = ""
    monkeypatch.setenv("MISTRAL_API_KEY", "ignored-process-key")
    assert not is_available()
    settings.MISTRAL_API_KEY = "dummy"
    assert is_available()
    settings.AI_BOOTSTRAP_ENABLED = False
    assert not is_available()


def test_evaluation_flash_delegates_to_bounded_adapter_unless_an_effort_is_given(monkeypatch):
    from ai_sandbox.providers import complete
    client, _ = sdk(monkeypatch)
    completion = complete("zai-glm-5-3-flash", "System", "Description")
    pinned = client.chat.complete.call_args.kwargs
    assert (pinned["reasoning_effort"], pinned["max_tokens"]) == ("low", 16000)
    assert completion.cached_input_tokens is completion.reasoning_tokens is None
    assert completion.cost_usd("zai-glm-5-3-flash") == pytest.approx((20 * 0.15 + 30 * 0.50) / 1e6)
    complete("zai-glm-5-3-flash", "System", "Description", effort="high")
    assert client.chat.complete.call_args.kwargs["reasoning_effort"] == "high"
