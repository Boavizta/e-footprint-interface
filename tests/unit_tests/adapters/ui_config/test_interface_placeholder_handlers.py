"""Tests for the HTML and text placeholder handler builders."""
import pytest

from model_builder.adapters.ui_config.interface_placeholder_handlers import (
    build_html_handlers,
    build_text_handlers,
)


UI_TOKENS = {
    "infra_panel_add_button": {
        "display": "the Add button in the Infrastructure section",
        "selector": "#add_server",
    },
    "fancy_token": {
        "display": "weird <button> & button",
        "selector": "#fancy",
    },
}
HTML = build_html_handlers(UI_TOKENS, mkdocs_base_url="https://docs.example/")
TEXT = build_text_handlers(UI_TOKENS)


# ---- HTML handlers ---------------------------------------------------------

def test_html_class_handler_emits_anchor_with_label():
    out = HTML["class"]("Server")
    assert "/model_builder/open-help-drawer/Server/" in out
    assert "Custom server" in out
    assert 'class="help-drawer-trigger"' in out


def test_html_param_handler_emits_span_with_label():
    out = HTML["param"]("Server.power")
    assert '<span class="ssot-param-ref">' in out
    assert "power" in out


def test_html_calc_handler_emits_span_with_humanized_attr():
    out = HTML["calc"]("Server.instances_energy")
    assert '<span class="ssot-calc-ref">' in out
    assert "instances energy" in out


def test_html_doc_handler_emits_anchor_with_mkdocs_url():
    out = HTML["doc"]("methodology")
    assert "https://docs.example/methodology" in out
    assert "methodology" in out


def test_html_ui_handler_emits_span_with_display_text():
    out = HTML["ui"]("infra_panel_add_button")
    assert '<span class="ssot-ui-ref"' in out
    assert "data-ui-token=\"infra_panel_add_button\"" in out
    assert "the Add button in the Infrastructure section" in out


def test_html_handlers_escape_variable_parts():
    out = HTML["ui"]("fancy_token")
    assert "&lt;button&gt;" in out
    assert "&amp;" in out
    assert "<button>" not in out


# ---- Text handlers ---------------------------------------------------------

def test_text_class_handler_returns_label():
    assert TEXT["class"]("Server") == "Custom server"


def test_text_param_handler_returns_label():
    assert TEXT["param"]("Server.power") == "power"


def test_text_calc_handler_returns_humanized_attr():
    assert TEXT["calc"]("Server.instances_energy") == "instances energy"


def test_text_doc_handler_returns_slug():
    assert TEXT["doc"]("methodology") == "methodology"


def test_text_ui_handler_returns_display():
    assert TEXT["ui"]("infra_panel_add_button") == "the Add button in the Infrastructure section"


# ---- Failure modes ---------------------------------------------------------

@pytest.mark.parametrize("handlers", [HTML, TEXT])
def test_unknown_class_raises(handlers):
    with pytest.raises(ValueError):
        handlers["class"]("NotAClass")


@pytest.mark.parametrize("handlers", [HTML, TEXT])
def test_unknown_param_raises(handlers):
    with pytest.raises(ValueError):
        handlers["param"]("Server.not_a_param")


@pytest.mark.parametrize("handlers", [HTML, TEXT])
def test_unknown_calc_raises(handlers):
    with pytest.raises(ValueError):
        handlers["calc"]("Server.not_a_calc")


@pytest.mark.parametrize("handlers", [HTML, TEXT])
def test_unknown_ui_token_raises(handlers):
    with pytest.raises(ValueError):
        handlers["ui"]("not_a_token")


@pytest.mark.parametrize("handlers", [HTML, TEXT])
def test_unknown_doc_slug_does_not_raise(handlers):
    handlers["doc"]("any-slug-the-mkdocs-build-validates")
