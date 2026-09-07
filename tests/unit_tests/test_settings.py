"""Settings invariants for session and cache retention."""

from django.conf import settings

from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository


def test_session_cookie_age_is_explicitly_fourteen_days():
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60


def test_only_system_model_hot_cache_default_is_one_hour():
    assert SessionSystemRepository.REDIS_CACHE_TIMEOUT_SECONDS == 60 * 60
    assert CacheBackend.REDIS_CACHE_TIMEOUT_SECONDS == 10 * 60
