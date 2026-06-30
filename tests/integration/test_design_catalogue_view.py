"""The contributor design catalogue: GET /design.

A live, intentionally-unlinked page. Tokens render from the app's real compiled CSS
custom properties; components are rendered live from a real sample ModelWeb (built from
the maintained ecommerce intro template, in memory) through the real canvas and form
pipeline — so the catalogue can't drift from what ships. A 500 here means the canvas or
the edit-panel pipeline broke against the sample model.
"""
import pytest


@pytest.mark.django_db
def test_design_catalogue_renders_tokens_and_live_components(client):
    response = client.get("/design/")
    assert response.status_code == 200
    content = response.content
    # The page itself.
    assert b"Design catalogue" in content
    # Live token swatches reference the real CSS custom properties.
    assert b"var(--new-primary)" in content
    assert b"var(--edge-paradigm-accent)" in content
    # The live canvas rendered from the sample model (a real object card is present).
    assert b'data-canvas-id="usage-journey-container"' in content
    assert b"model-builder-card" in content
    # The live edit side panel section rendered (a 200 already proves the form pipeline
    # built it; this pins the section is wired in).
    assert b"The edit side panel" in content
    # Real partials: confidence badge + the Results bar, with the locked validation copy.
    assert b"confidence-badge" in content
    assert b'id="btn-open-panel-result"' in content
    assert b"the modeling is incomplete" in content
