"""Tests for the HTML placeholder handler builder."""
import pytest

from model_builder.adapters.ui_config.interface_placeholder_handlers import build_html_handlers


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


def test_html_doc_handler_can_use_custom_label():
    out = HTML["doc"]("Server|Custom server")
    assert "https://docs.example/Server" in out
    assert ">Custom server</a>" in out
    assert "Server|Custom server" not in out


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


# ---- Failure modes ---------------------------------------------------------

def test_unknown_class_raises():
    with pytest.raises(ValueError):
        HTML["class"]("NotAClass")


def test_unknown_param_raises():
    with pytest.raises(ValueError):
        HTML["param"]("Server.not_a_param")


def test_unknown_calc_raises():
    with pytest.raises(ValueError):
        HTML["calc"]("Server.not_a_calc")


def test_unknown_ui_token_raises():
    with pytest.raises(ValueError):
        HTML["ui"]("not_a_token")


def test_unknown_doc_slug_does_not_raise():
    HTML["doc"]("any-slug-the-mkdocs-build-validates")
