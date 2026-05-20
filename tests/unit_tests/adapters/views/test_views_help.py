import pytest


@pytest.mark.django_db
class TestOpenHelpDrawer:

    def test_returns_200_with_class_label_and_no_raw_placeholders(self, client):
        response = client.get("/model_builder/open-help-drawer/Server/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "About Custom server" in body
        # The HTML resolver must consume every `{kind:target}` token before it
        # reaches the template.
        assert "{class:" not in body
        assert "{param:" not in body
        assert "{calc:" not in body
        assert "{ui:" not in body
        assert "{doc:" not in body

    def test_omits_interactions_section_when_class_has_no_interactions(self, client):
        # ``UsageJourneyStep`` is a real efootprint class but has no
        # ``interactions`` entry in ``class_ui_config.json``; the corresponding
        # <h6> heading therefore must not be in the body.
        response = client.get("/model_builder/open-help-drawer/UsageJourneyStep/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "<h6 class=\"text-uppercase text-muted small mb-1\">Interactions</h6>" not in body

    def test_renders_interactions_section_when_class_has_interactions(self, client):
        # ``Server`` inherits its interactions text from ``ServerBase`` via MRO.
        response = client.get("/model_builder/open-help-drawer/Server/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "<h6 class=\"text-uppercase text-muted small mb-1\">Interactions</h6>" in body

    def test_works_for_interface_only_abstract_base(self, client):
        # ``EdgeDeviceBase`` is not in ``ALL_EFOOTPRINT_CLASSES_DICT`` but has a
        # JSON-authored description, so the drawer must render rather than 404.
        response = client.get("/model_builder/open-help-drawer/EdgeDeviceBase/")

        body = response.content.decode()
        assert response.status_code == 200
        assert "About Edge device" in body

    @pytest.mark.parametrize(
        ("class_name", "expected_urls", "abstract_url"),
        [
            ("ServerBase", ["/GPUServer", "/BoaviztaCloudServer", "/Server"], "/ServerBase"),
            ("EdgeDeviceBase", ["/EdgeComputer", "/EdgeAppliance", "/EdgeDevice"], "/EdgeDeviceBase"),
            ("ExternalAPI", ["/EcoLogitsGenAIExternalAPI"], "/ExternalAPI"),
        ],
    )
    def test_abstract_base_docs_section_links_to_concrete_docs(
        self, client, class_name, expected_urls, abstract_url
    ):
        response = client.get(f"/model_builder/open-help-drawer/{class_name}/")

        body = response.content.decode()
        assert response.status_code == 200
        for expected_url in expected_urls:
            assert expected_url in body
        assert abstract_url not in body

    def test_abstract_base_docs_section_uses_ui_labels(self, client):
        response = client.get("/model_builder/open-help-drawer/ServerBase/")

        body = response.content.decode()
        assert response.status_code == 200
        assert ">AI server</a>" in body
        assert ">Cloud server</a>" in body
        assert ">Custom server</a>" in body

    def test_unknown_class_returns_404(self, client):
        response = client.get("/model_builder/open-help-drawer/NotARealClass/")

        assert response.status_code == 404
