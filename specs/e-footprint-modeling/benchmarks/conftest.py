"""Pytest wiring kept beside the usage-journey benchmark."""

from tests.e2e.conftest import model_builder_page


def pytest_addoption(parser):
    """Register the opt-in usage-journey benchmark controls."""
    group = parser.getgroup("usage journey benchmark")
    group.addoption(
        "--run-usage-benchmark",
        action="store_true",
        default=False,
        help="Run the sequential browser usage-journey benchmark.",
    )
    group.addoption(
        "--usage-benchmark-output",
        default="specs/e-footprint-modeling/benchmarks/results",
        help="Directory receiving benchmark JSON and CSV files.",
    )


__all__ = ["model_builder_page"]
