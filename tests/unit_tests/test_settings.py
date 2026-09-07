"""Settings invariants for session and cache retention."""

import pytest
from django.conf import settings

from e_footprint_interface.settings import optional_env_bool
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository


def test_session_cookie_age_is_explicitly_fourteen_days():
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60


def test_only_system_model_hot_cache_default_is_one_hour():
    assert SessionSystemRepository.REDIS_CACHE_TIMEOUT_SECONDS == 60 * 60
    assert CacheBackend.REDIS_CACHE_TIMEOUT_SECONDS == 10 * 60


def test_public_privacy_claims_are_not_inferred_from_the_hosting_platform():
    assert settings.DATA_PRIVACY_PUBLIC_SHARED_INSTANCE is False
    assert settings.DATA_PRIVACY_OPERATOR_NAME == ""
    assert settings.DATA_PRIVACY_HOSTING_PROVIDER_NAME == ""
    assert settings.DATA_PRIVACY_HOSTING_REGION == ""


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
