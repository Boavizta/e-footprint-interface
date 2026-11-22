"""The three calls where no collector is installed, which is production: they do nothing, and importing them
brings nothing but the standard library."""
import subprocess
import sys
import textwrap

from comprehension_harness.python.tests.conftest import ROOT


def run_python(script: str) -> subprocess.CompletedProcess:
    """A fresh interpreter at the repository root: this process has the collector installed, a server has not."""
    return subprocess.run([sys.executable, "-c", textwrap.dedent(script)], cwd=ROOT, capture_output=True, text=True)


def test_without_a_collector_a_call_returns_nothing_and_its_watch_is_never_called():
    done = run_python("""
        from comprehension_harness.python import event, narrate, planned

        def watch():
            raise AssertionError("the watch was called")

        assert narrate("A step.", watch) is None
        assert event("A cause.", watch) is None
        assert planned("gift-cards#deduct-the-card", "A change.", watch) is None
        assert planned.remove("gift-cards#deduct-the-card", "A function that goes.") is None
    """)

    assert done.returncode == 0, done.stderr


def test_importing_the_calls_loads_the_standard_library_and_no_other_module_of_the_harness():
    done = run_python("""
        import sys

        before = set(sys.modules)
        import comprehension_harness.python
        loaded = set(sys.modules) - before

        print(sorted(name for name in loaded if name.split(".")[0] not in sys.stdlib_module_names))
    """)

    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "['comprehension_harness', 'comprehension_harness.python']"
