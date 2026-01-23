"""
Test parallel execution support with pytest-xdist (FR-055).

This module validates that the test suite can run successfully with
parallel workers using pytest-xdist.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.functional
class TestParallelExecutionSupport:
    """Tests for pytest-xdist parallel execution support."""

    def test_pytest_xdist_installed(self):
        """Verify pytest-xdist is available for parallel testing."""
        try:
            import xdist
            assert hasattr(xdist, '__version__'), "xdist should have version attribute"
        except ImportError:
            pytest.fail(
                "pytest-xdist not installed. Install with: pip install pytest-xdist"
            )

    def test_pytest_parallel_flag_accepted(self):
        """Verify pytest accepts -n flag for parallel execution."""
        # Run pytest --help and check for -n flag
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, "pytest --help should succeed"
        # Check for xdist-related help text
        assert "-n" in result.stdout or "numprocesses" in result.stdout.lower(), \
            "pytest should accept -n flag when xdist is installed"

    def test_parallel_execution_completes(self, tmp_path):
        """Test that parallel execution completes without errors."""
        # Create a minimal test file
        test_file = tmp_path / "test_sample.py"
        test_file.write_text('''
import pytest

@pytest.mark.functional
def test_one():
    assert 1 + 1 == 2

@pytest.mark.functional
def test_two():
    assert 2 + 2 == 4

@pytest.mark.functional
def test_three():
    assert 3 + 3 == 6
''')

        # Run with parallel workers
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-n", "2", "-v"],
            capture_output=True,
            text=True,
            timeout=60
        )

        assert result.returncode == 0, f"Parallel execution should succeed: {result.stderr}"
        # Verify tests ran
        assert "3 passed" in result.stdout or "passed" in result.stdout

    def test_no_worker_conflicts(self, tmp_path):
        """Test that parallel workers don't conflict on shared resources."""
        # Create tests that write to separate temp files
        test_file = tmp_path / "test_isolation.py"
        test_file.write_text('''
import os
import tempfile
import pytest

@pytest.mark.functional
def test_worker_isolation_a(tmp_path):
    """Each worker should get isolated tmp_path."""
    marker_file = tmp_path / "worker_a.txt"
    marker_file.write_text("worker_a")
    assert marker_file.read_text() == "worker_a"

@pytest.mark.functional
def test_worker_isolation_b(tmp_path):
    """Each worker should get isolated tmp_path."""
    marker_file = tmp_path / "worker_b.txt"
    marker_file.write_text("worker_b")
    assert marker_file.read_text() == "worker_b"

@pytest.mark.functional
def test_worker_isolation_c(tmp_path):
    """Each worker should get isolated tmp_path."""
    marker_file = tmp_path / "worker_c.txt"
    marker_file.write_text("worker_c")
    assert marker_file.read_text() == "worker_c"

@pytest.mark.functional
def test_worker_isolation_d(tmp_path):
    """Each worker should get isolated tmp_path."""
    marker_file = tmp_path / "worker_d.txt"
    marker_file.write_text("worker_d")
    assert marker_file.read_text() == "worker_d"
''')

        # Run with multiple workers
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-n", "4", "-v"],
            capture_output=True,
            text=True,
            timeout=60
        )

        assert result.returncode == 0, f"No worker conflicts: {result.stderr}"
        assert "4 passed" in result.stdout


@pytest.mark.functional
@pytest.mark.slow
class TestParallelPerformance:
    """Tests that verify parallel execution provides performance benefit."""

    def test_parallel_is_faster_than_sequential(self, tmp_path):
        """Verify parallel execution is faster than sequential for CPU-bound tests."""
        # Create test file with simulated work
        test_file = tmp_path / "test_perf.py"
        test_file.write_text('''
import time
import pytest

@pytest.mark.functional
def test_slow_1():
    """Simulate some work."""
    time.sleep(0.5)
    assert True

@pytest.mark.functional
def test_slow_2():
    """Simulate some work."""
    time.sleep(0.5)
    assert True

@pytest.mark.functional
def test_slow_3():
    """Simulate some work."""
    time.sleep(0.5)
    assert True

@pytest.mark.functional
def test_slow_4():
    """Simulate some work."""
    time.sleep(0.5)
    assert True
''')

        # Run sequentially
        start = time.time()
        result_seq = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v"],
            capture_output=True,
            text=True,
            timeout=30
        )
        sequential_time = time.time() - start

        assert result_seq.returncode == 0, "Sequential run should pass"

        # Run in parallel with 4 workers
        start = time.time()
        result_par = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-n", "4", "-v"],
            capture_output=True,
            text=True,
            timeout=30
        )
        parallel_time = time.time() - start

        assert result_par.returncode == 0, "Parallel run should pass"

        # Parallel should be meaningfully faster (at least 30% improvement)
        # Being lenient due to xdist overhead
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1

        # Log for debugging
        print(f"Sequential: {sequential_time:.2f}s, Parallel: {parallel_time:.2f}s, Speedup: {speedup:.2f}x")

        # Expect at least some speedup (>1.2x) with 4 workers on 4 sleep-bound tests
        assert speedup > 1.2, (
            f"Parallel ({parallel_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s). "
            f"Speedup: {speedup:.2f}x"
        )
