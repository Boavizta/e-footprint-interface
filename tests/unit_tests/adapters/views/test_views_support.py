from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from django.template.loader import render_to_string

from model_builder.adapters.repositories import SessionSystemRepository
from model_builder.adapters.views.exception_handling import build_feedback_email_url, build_github_feedback_url


@pytest.mark.django_db
def test_support_route_is_standalone_and_feedback_is_globally_linked(client, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    response = client.get("/support/")
    content = response.content.decode()

    assert response.status_code == 200
    assert "Report or give feedback" in content
    assert 'href="/support/"' in content
    assert 'data-action="open-feedback"' in content
    assert "<textarea" not in content
    assert 'type="checkbox"' not in content


@pytest.mark.django_db
def test_support_htmx_response_is_a_builder_partial_with_explicit_download(client, minimal_system_data):
    SessionSystemRepository(client.session).save_data(minimal_system_data)

    response = client.get("/model_builder/support/", HTTP_HX_REQUEST="true")
    content = response.content.decode()

    assert response.status_code == 200
    assert "<html" not in content
    assert 'id="sidePanelContent"' in content
    assert 'href="/model_builder/download-json/"' in content
    assert "Download my current modeling to include" in content
    assert "attach it manually" in content


def test_mobile_builder_menu_contains_feedback_entry(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

    content = render_to_string(
        "model_builder/upload_download_reboot_model_tooltips.html",
        {
            "workspace_slots": [],
            "model_web": SimpleNamespace(
                system=SimpleNamespace(name="Example"),
                has_edge_objects=False,
                creation_constraints={"__results__": {"enabled": False, "reason": "Incomplete"}},
            ),
        },
    )

    assert 'class="nav-item d-lg-none"' in content
    assert 'data-action="open-feedback"' in content
    assert ">Feedback<" in content


def test_help_menu_links_data_privacy_as_a_normal_route_and_side_panel_partial():
    content = render_to_string("model_builder/components/help_menu.html")

    assert 'href="/model_builder/data-privacy/"' in content
    assert 'hx-boost="true"' in content
    assert 'hx-target="#sidePanel"' in content
    assert "Data &amp; privacy" in content


@pytest.mark.parametrize("kind", ["bug", "feedback"])
def test_github_feedback_urls_contain_prompts_only(kind):
    url = build_github_feedback_url(kind)
    query = parse_qs(urlparse(url).query)

    assert urlparse(url).netloc == "github.com"
    assert set(query) == {"title", "body"}
    assert "optional" in query["body"][0].lower()
    assert "attach it manually" in query["body"][0].lower()


@pytest.mark.parametrize("kind", ["bug", "feedback"])
def test_email_feedback_urls_contain_prompts_and_manual_attachment_guidance_only(kind):
    url = build_feedback_email_url(kind)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "mailto"
    assert parsed.path == "vincent.villet@publicissapient.com"
    assert set(query) == {"subject", "body"}
    assert "attach it manually" in query["body"][0].lower()


def test_feedback_url_builders_reject_unknown_kinds():
    with pytest.raises(ValueError, match="Unsupported feedback kind"):
        build_github_feedback_url("question")
