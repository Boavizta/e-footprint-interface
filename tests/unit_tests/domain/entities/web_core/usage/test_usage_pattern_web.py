"""Unit tests for UsagePatternWeb entity."""
from model_builder.domain.entities.web_core.usage.usage_pattern_web import UsagePatternWeb
from tests.unit_tests.domain.entities.snapshot_utils import assert_creation_context_matches_snapshot
from tests.unit_tests.domain.entities.web_core.usage.snapshot_model_webs import build_usage_pattern_model_web


class TestUsagePatternWeb:
    """Tests for UsagePatternWeb-specific behavior."""

    # --- generate_object_creation_context (snapshot test) ---

    def test_generate_object_creation_context_matches_snapshot(self):
        """Creation context form structure matches reference snapshot."""
        model_web = build_usage_pattern_model_web()
        assert_creation_context_matches_snapshot(UsagePatternWeb, model_web=model_web)
