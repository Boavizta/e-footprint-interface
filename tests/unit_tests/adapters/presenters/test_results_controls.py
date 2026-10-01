from django.utils.html import strip_tags

from model_builder.adapters.presenters.oob_regions import _render_results_buttons
from model_builder.domain.entities.web_core.model_web import ModelWeb


def test_unavailable_results_keep_reason_in_tooltips_and_not_button_text(default_system_repository):
    model_web = ModelWeb(default_system_repository)
    reason = model_web.creation_constraints["__results__"]["reason"]
    assert not model_web.creation_constraints["__results__"]["enabled"]

    html = _render_results_buttons(model_web, {})
    toolbar = html.split('id="show-results-toolbar-btn"', 1)[1].split(">", 1)[1]

    assert " ".join(strip_tags(toolbar).split()) == "Show results"
    assert html.count("data-quick-total></small>") == 2
    assert html.count(f'title="{reason}"') == 2
