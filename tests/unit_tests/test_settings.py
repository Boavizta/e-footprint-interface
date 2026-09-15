"""Settings invariants for session and cache retention."""

import pytest
from django.conf import settings

from e_footprint_interface.settings import clever_cloud_privacy_default, optional_env_bool
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository


def test_session_cookie_age_is_explicitly_fourteen_days():
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60


def test_only_system_model_hot_cache_default_is_one_hour():
    assert SessionSystemRepository.REDIS_CACHE_TIMEOUT_SECONDS == 60 * 60
    assert CacheBackend.REDIS_CACHE_TIMEOUT_SECONDS == 10 * 60


def test_self_hosted_privacy_facts_are_not_assumed():
    assert settings.DATA_PRIVACY_PUBLIC_SHARED_INSTANCE is False
    assert settings.DATA_PRIVACY_OPERATOR_NAME == ""
    assert settings.DATA_PRIVACY_HOSTING_PROVIDER_NAME == ""
    assert settings.DATA_PRIVACY_HOSTING_REGION == ""
    assert settings.DATA_PRIVACY_REDIS_TLS_SETUP_IN_PROGRESS is False
    assert settings.DATA_PRIVACY_REDIS_BACKUP_DISABLE_IN_PROGRESS is False
    assert settings.DATA_PRIVACY_POSTGRES_BACKUP_ENCRYPTION_IN_PROGRESS is False


def test_clever_cloud_deployments_use_the_verified_public_privacy_facts_by_default(monkeypatch):
    monkeypatch.setenv("DJANGO_CLEVER_CLOUD", "True")
    assert clever_cloud_privacy_default() is True
    monkeypatch.setenv("DJANGO_CLEVER_CLOUD", "False")
    assert clever_cloud_privacy_default() is False


def test_optional_privacy_boolean_preserves_unknown_and_rejects_invalid_values(monkeypatch):
    monkeypatch.delenv("TEST_PRIVACY_BOOLEAN", raising=False)
    assert optional_env_bool("TEST_PRIVACY_BOOLEAN") is None
    monkeypatch.setenv("TEST_PRIVACY_BOOLEAN", "yes")
    assert optional_env_bool("TEST_PRIVACY_BOOLEAN") is True
    monkeypatch.setenv("TEST_PRIVACY_BOOLEAN", "off")
    assert optional_env_bool("TEST_PRIVACY_BOOLEAN") is False
    monkeypatch.setenv("TEST_PRIVACY_BOOLEAN", "sometimes")
    with pytest.raises(ValueError):
        optional_env_bool("TEST_PRIVACY_BOOLEAN")
