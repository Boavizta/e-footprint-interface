import pytest

from model_builder.application.ai_bootstrap.catalogs import resolve_genai


def _resolve(provider, model_name):
    resolutions = []
    resolved = resolve_genai(provider, model_name, resolutions)
    return resolved, [(r.kind, r.requested, r.resolved, r.how) for r in resolutions]


@pytest.mark.parametrize("model_name, expected", [("Fable 5.1", "claude-fable-5-1"), ("Opus 5.5", "claude-opus-5-5")])
def test_a_model_name_copied_from_the_description_resolves_in_its_provider_catalog(model_name, expected):
    assert _resolve("anthropic", model_name)[0] == ("anthropic", expected)


def test_a_wrong_provider_guess_gives_way_to_the_catalog_that_matches_the_model_name():
    resolved, resolutions = _resolve("openai", "Fable 5.1")
    assert resolved == ("anthropic", "claude-fable-5-1")
    assert resolutions == [("provider", "openai", "anthropic", "model_name"),
                           ("genai_model", "openai/Fable 5.1", "anthropic/claude-fable-5-1", "contains")]


def test_a_model_name_no_catalog_matches_falls_back_to_the_stated_provider_default():
    assert _resolve("Anthropic", "Zorblax 9") == (
        ("anthropic", "claude-sonnet-5-5"),
        [("provider", "Anthropic", "anthropic", "normalized"),
         ("genai_model", "Anthropic/Zorblax 9", "anthropic/claude-sonnet-5-5", "fallback")])


def test_an_unknown_provider_with_an_unknown_model_falls_back_to_openai():
    assert _resolve("Acme AI", "Zorblax 9")[0] == ("openai", "gpt-5-mini")
