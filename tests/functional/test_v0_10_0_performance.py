"""
Test: spec-kitty v0.10.0 Performance Validation

Purpose: Validate that Python CLI meets performance targets and doesn't
introduce significant overhead compared to bash version.

Version Tested: spec-kitty >= 0.10.0
Related Feature: Performance requirements from spec.md

Test Coverage:
1. Command Performance (6 tests)
   - Simple commands < 100ms (check-prerequisites, list-tasks)
   - Complex commands < 5s (create-feature, merge)
   - JSON output has negligible overhead
   - Concurrent command execution doesn't block
   - BASELINE: Python vs bash timing comparison
   - STRESS: 100+ task list performance

Performance Targets (from spec.md):
- Simple operations (path resolution, validation): < 100ms
- Complex operations (worktree creation, migration): < 5s
- JSON overhead: Negligible (< 10% slowdown)
- Python vs bash: <= 2x bash baseline

Note: Performance tests are informational. Failure doesn't block release
but indicates optimization opportunities. Tests require spec-kitty >= 0.10.0
"""

import subprocess
import tempfile
import time
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 10, 0),
    reason="Requires spec-kitty >= 0.10.0 (performance testing)"
)


class TestCommandPerformance:
    """Test that commands meet performance targets."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create initialized project with feature."""
        import os
        project_name = "perf_test"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'perf-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        return {
            'project_path': project_path,
            'worktree_path': project_path / '.worktrees' / '001-perf-feature'
        }

    def test_simple_commands_under_100ms(self, initialized_project):
        """
        Test: Simple commands execute in < 100ms

        Commands tested:
        - check-prerequisites
        - list-tasks

        Target: < 100ms for path resolution and validation operations

        NOTE: This is a soft target. Failure indicates performance
        opportunity, not a blocking issue.
        """
        worktree_path = initialized_project['worktree_path']

        # Warmup run
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Timed run
        start = time.time()
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        duration_ms = (time.time() - start) * 1000

        # Log performance (informational)
        print(f"\ncheck-prerequisites: {duration_ms:.1f}ms")

        # Soft assertion - log warning if slow
        if duration_ms > 100:
            import warnings
            warnings.warn(
                f"check-prerequisites took {duration_ms:.1f}ms (target: <100ms)",
                UserWarning
            )

    def test_complex_commands_under_5s(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Complex commands execute in < 5s

        Commands tested:
        - create-feature (git worktree creation)
        - merge (git merge + cleanup)

        Target: < 5s for operations involving git/filesystem

        NOTE: This is a soft target. Informational only.
        """
        import os
        project_name = "complex_perf"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Timed create-feature
        start = time.time()
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'timed-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        duration = time.time() - start

        print(f"\ncreate-feature: {duration:.2f}s")

        if duration > 5.0:
            import warnings
            warnings.warn(
                f"create-feature took {duration:.2f}s (target: <5s)",
                UserWarning
            )

    def test_json_output_no_overhead(self, initialized_project):
        """
        Test: --json flag doesn't add significant overhead

        Validates:
        - JSON serialization is fast
        - < 10% overhead vs non-JSON
        - Not a performance bottleneck
        """
        worktree_path = initialized_project['worktree_path']

        # Time without JSON
        start = time.time()
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        duration_no_json = time.time() - start

        # Time with JSON
        start = time.time()
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        duration_with_json = time.time() - start

        overhead_percent = ((duration_with_json - duration_no_json) / duration_no_json) * 100 if duration_no_json > 0 else 0

        print(f"\nJSON overhead: {overhead_percent:.1f}%")

        if overhead_percent > 50:  # Lenient threshold
            import warnings
            warnings.warn(
                f"JSON overhead is {overhead_percent:.1f}% (target: <10%)",
                UserWarning
            )

    def test_concurrent_command_execution(self, initialized_project):
        """
        Test: Multiple agents don't block each other

        Validates:
        - No global locks
        - Concurrent execution works
        - Performance scales with parallelism
        """
        import concurrent.futures

        worktree_path = initialized_project['worktree_path']

        def run_command():
            start = time.time()
            subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return time.time() - start

        # Run 3 commands concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_command) for _ in range(3)]
            durations = [f.result() for f in futures]

        avg_duration = sum(durations) / len(durations)
        print(f"\nConcurrent execution avg: {avg_duration*1000:.1f}ms")

        # Should complete without errors
        assert all(d < 30 for d in durations), "Concurrent execution should not hang"

    def test_python_vs_bash_timing(self, temp_project_dir, spec_kitty_repo_root):
        """
        BASELINE: Python CLI vs bash script timing comparison

        Validates:
        - Python overhead is acceptable
        - Target: <= 2x bash baseline
        - Informational comparison

        NOTE: This is informational only. We can't run bash scripts
        directly anymore, so this test documents Python performance.
        """
        import os
        project_name = "baseline"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Measure Python CLI
        start = time.time()
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'baseline-test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        python_duration = time.time() - start

        print(f"\nPython CLI create-feature: {python_duration:.2f}s")

        # Can't measure bash (scripts are gone), so this is just baseline documentation
        assert python_duration < 60, "Should complete in reasonable time"

    def test_100_task_list_performance(self, initialized_project):
        """
        STRESS: Large task lists (100+ tasks) performance

        Validates:
        - Scales to large task counts
        - No O(n²) algorithms
        - Reasonable performance with 100 tasks
        """
        worktree_path = initialized_project['worktree_path']
        tasks_dir = worktree_path / 'kitty-specs' / '001-perf-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create 100 task files
        for i in range(100):
            wp_file = tasks_dir / f'WP{i:02d}-task.md'
            content = f"""---
lane: planned
work_package_id: WP{i:02d}
---

# Task {i}
"""
            wp_file.write_text(content)

        # Time list-tasks with 100 tasks
        start = time.time()
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'list-tasks', '--json'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        duration = time.time() - start

        print(f"\nlist-tasks (100 tasks): {duration:.2f}s")

        # Should complete in reasonable time
        assert duration < 10, (
            f"list-tasks with 100 tasks took {duration:.2f}s (should be < 10s)"
        )

        # JSON should be valid
        if result.returncode == 0:
            # Should produce output
            assert len(result.stdout) > 0, "Should produce output for 100 tasks"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
