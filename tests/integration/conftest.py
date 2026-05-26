"""Shared fixtures for tests/integration/."""
import pytest


@pytest.fixture(autouse=True)
def disable_staticfiles_manifest(settings):
    """Templates rendered by view tests use {% static %}, which fails under
    ManifestStaticFilesStorage without a prior collectstatic. Tests don't run
    collectstatic, so swap to the plain backend that returns raw paths.
    """
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
