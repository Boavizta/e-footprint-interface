"""Unit tests for payload size limit enforcement in repositories."""
import pytest
from unittest.mock import MagicMock, patch

from e_footprint_interface.json_payload_utils import compute_json_size, JsonSizeResult
from model_builder.adapters.repositories.in_memory_system_repository import InMemorySystemRepository
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.cache_backend import CacheBackend
from model_builder.domain.exceptions import PayloadSizeLimitExceeded


class TestJsonPayloadUtils:
    """Tests for json_payload_utils module."""

    def test_compute_json_size_returns_correct_structure(self):
        """Should return JsonSizeResult with size and timing info."""
        data = {"test": "value"}
        result = compute_json_size(data)

        assert isinstance(result, JsonSizeResult)
        assert result.size_bytes > 0
        assert result.size_mb == result.size_bytes / (1024 * 1024)
        assert result.computation_time_ms >= 0

    def test_compute_json_size_measures_correctly(self):
        """Should correctly measure JSON payload size."""
        data = {"key": "x" * 1000}  # 1000 x's plus JSON structure
        result = compute_json_size(data)

        # JSON will be {"key": "xxx..."} so slightly more than 1000 bytes
        assert result.size_bytes > 1000
        assert result.size_bytes < 1100  # Reasonable overhead


class TestInMemorySystemRepositorySizeLimit:
    """Tests for size limit enforcement in InMemorySystemRepository."""

    def test_save_within_limit_succeeds(self):
        """Should save data when within the size limit."""
        repository = InMemorySystemRepository(max_payload_size_mb=1.0)
        small_data = {"System": {"test": "small data"}}

        repository.save_system_data(small_data)

        assert repository.get_system_data() == small_data

    def test_save_exceeding_limit_raises_exception(self):
        """Should raise PayloadSizeLimitExceeded when data exceeds limit."""
        repository = InMemorySystemRepository(max_payload_size_mb=0.001)  # 1 KB limit
        large_data = {"System": {"data": "x" * 2000}}  # ~2 KB

        with pytest.raises(PayloadSizeLimitExceeded) as exc_info:
            repository.save_system_data(large_data)

        assert exc_info.value.current_size_mb > 0.001
        assert exc_info.value.limit_mb == 0.001

    def test_save_without_limit_allows_any_size(self):
        """Should allow any size when no limit is configured."""
        repository = InMemorySystemRepository()  # No limit
        large_data = {"System": {"data": "x" * 100000}}

        repository.save_system_data(large_data)

        assert repository.get_system_data() == large_data

    def test_data_not_saved_when_limit_exceeded(self):
        """Should not modify stored data when limit is exceeded."""
        initial_data = {"System": {"initial": True}}
        repository = InMemorySystemRepository(initial_data=initial_data, max_payload_size_mb=0.001)
        large_data = {"System": {"data": "x" * 2000}}

        with pytest.raises(PayloadSizeLimitExceeded):
            repository.save_system_data(large_data)

        # Original data should still be there
        assert repository.get_system_data() == initial_data


class TestSessionSystemRepositorySizeLimit:
    """Tests for size limit enforcement in SessionSystemRepository."""

    def test_save_within_limit_succeeds(self):
        """Should save data when within the size limit."""
        mock_session = MagicMock()
        mock_session.session_key = "session-key"
        mock_session.__contains__.return_value = False
        repository = SessionSystemRepository(mock_session)

        redis_cache = MagicMock()
        postgres_cache = MagicMock()

        def get_cache(alias):
            if alias == SessionSystemRepository.REDIS_CACHE_ALIAS:
                return redis_cache
            return postgres_cache

        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 1.0):
            small_data = {"System": {"test": "small data"}}
            with patch.object(CacheBackend, "_get_cache", side_effect=get_cache):
                repository.save_system_data(small_data)

        cache_key = f"{SessionSystemRepository.SYSTEM_DATA_KEY}:{mock_session.session_key}"
        redis_cache.set.assert_called_once_with(
            cache_key, small_data, timeout=SessionSystemRepository.REDIS_CACHE_TIMEOUT_SECONDS
        )
        postgres_cache.set.assert_called_once_with(
            cache_key, small_data, timeout=SessionSystemRepository.POSTGRES_CACHE_TIMEOUT_SECONDS
        )

    def test_save_exceeding_limit_raises_exception(self):
        """Should raise PayloadSizeLimitExceeded when data exceeds limit."""
        mock_session = MagicMock()
        mock_session.session_key = "session-key"
        mock_session.__contains__.return_value = False
        repository = SessionSystemRepository(mock_session)
        redis_cache = MagicMock()
        postgres_cache = MagicMock()

        def get_cache(alias):
            if alias == SessionSystemRepository.REDIS_CACHE_ALIAS:
                return redis_cache
            return postgres_cache

        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 0.001):
            large_data = {"System": {"data": "x" * 2000}}

            with pytest.raises(PayloadSizeLimitExceeded) as exc_info:
                with patch.object(CacheBackend, "_get_cache", side_effect=get_cache):
                    repository.save_system_data(large_data)

            assert exc_info.value.limit_mb == 0.001
            redis_cache.set.assert_not_called()
            postgres_cache.set.assert_not_called()

    def test_cache_not_written_when_limit_exceeded(self):
        """Should not write to caches when limit is exceeded."""
        mock_session = MagicMock()
        mock_session.session_key = "session-key"
        mock_session.__contains__.return_value = False
        repository = SessionSystemRepository(mock_session)
        redis_cache = MagicMock()
        postgres_cache = MagicMock()

        def get_cache(alias):
            if alias == SessionSystemRepository.REDIS_CACHE_ALIAS:
                return redis_cache
            return postgres_cache

        with patch.object(SessionSystemRepository, "MAX_PAYLOAD_SIZE_MB", 0.001):
            large_data = {"System": {"data": "x" * 2000}}

            with pytest.raises(PayloadSizeLimitExceeded):
                with patch.object(CacheBackend, "_get_cache", side_effect=get_cache):
                    repository.save_system_data(large_data)

        redis_cache.set.assert_not_called()
        postgres_cache.set.assert_not_called()

    def test_limit_from_environment_variable(self):
        """Should use MAX_PAYLOAD_SIZE_MB class attribute (set from env)."""
        # Default is 30.0 MB from environment or default
        assert SessionSystemRepository.MAX_PAYLOAD_SIZE_MB == 30.0
