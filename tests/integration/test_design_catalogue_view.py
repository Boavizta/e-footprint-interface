"""The contributor design catalogue: GET /design.

A live, intentionally-unlinked page that renders the real tokens (the app's compiled
CSS custom properties) and a few real component partials with small sample context.
These tests pin that the route is wired in and that every embedded partial renders
without a template/context error (a 500 here means a partial's contract changed).
"""
import pytest


@pytest.mark.django_db
def test_design_catalogue_renders(client):
    response = client.get("/design/")
    assert response.status_code == 200
    content = response.content
    # The page itself.
    assert b"Design catalogue" in content
    # Live token swatches reference the real CSS custom properties.
    assert b"var(--new-primary)" in content
    assert b"var(--edge-paradigm-accent)" in content
    # The real component partials rendered with sample context (not just linked).
    assert b'id="dc-add-enabled"' in content          # add_object_button.html
    assert b'id="btn-open-panel-result"' in content   # results_bar_button.html
    assert b"confidence-badge" in content             # confidence_badge.html


@pytest.mark.django_db
def test_design_catalogue_shows_both_results_bar_states(client):
    """The locked Results bar carries the live validation reason as its tooltip."""
    content = client.get("/design/").content
    assert b"the modeling is incomplete" in content
