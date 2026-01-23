"""
Fixtures for orchestrator tests (WP05).

Provides fixtures for dependency graph testing, parallel execution validation,
and mock agents for orchestration testing.
"""
import pytest
import tempfile
import json
import time
from pathlib import Path
from typing import Callable, Any
from unittest.mock import Mock, patch, MagicMock
import yaml


# =============================================================================
# T028: Dependency Graph Fixtures
# =============================================================================

@pytest.fixture
def temp_feature_dir():
    """Create temporary directory for feature with tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        feature_dir = Path(tmpdir) / "001-test-feature"
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        yield feature_dir


@pytest.fixture
def create_wp_file():
    """Factory fixture to create WP files with frontmatter."""
    def _create_wp(
        feature_dir: Path,
        wp_id: str,
        dependencies: list | None = None,
        lane: str = "planned",
        extra_fields: dict | None = None
    ) -> Path:
        """
        Create a WP markdown file with frontmatter.

        Args:
            feature_dir: Path to feature directory (with tasks/ subdirectory)
            wp_id: Work package ID (e.g., "WP01")
            dependencies: List of dependency WP IDs
            lane: Lane status (planned/doing/for_review/done)
            extra_fields: Additional frontmatter fields

        Returns:
            Path to created WP file
        """
        if dependencies is None:
            dependencies = []

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        wp_file = tasks_dir / f"{wp_id}-test.md"

        frontmatter = {
            "work_package_id": wp_id,
            "title": f"Test {wp_id}",
            "dependencies": dependencies,
            "lane": lane,
        }

        if extra_fields:
            frontmatter.update(extra_fields)

        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n# {wp_id} Test\n\nWork package content for testing.\n"
        wp_file.write_text(content)

        return wp_file

    return _create_wp


@pytest.fixture
def diamond_dependency_graph(temp_feature_dir, create_wp_file):
    """
    Create a diamond dependency graph for testing.

    Structure:
        WP01 (root, no dependencies)
          ├── WP02 (depends on WP01)
          └── WP03 (depends on WP01)
               └── WP04 (depends on WP02 and WP03)
    """
    create_wp_file(temp_feature_dir, "WP01", [])
    create_wp_file(temp_feature_dir, "WP02", ["WP01"])
    create_wp_file(temp_feature_dir, "WP03", ["WP01"])
    create_wp_file(temp_feature_dir, "WP04", ["WP02", "WP03"])

    return temp_feature_dir


@pytest.fixture
def linear_dependency_chain(temp_feature_dir, create_wp_file):
    """
    Create a linear dependency chain for testing.

    Structure:
        WP01 → WP02 → WP03 → WP04 → WP05
    """
    create_wp_file(temp_feature_dir, "WP01", [])
    create_wp_file(temp_feature_dir, "WP02", ["WP01"])
    create_wp_file(temp_feature_dir, "WP03", ["WP02"])
    create_wp_file(temp_feature_dir, "WP04", ["WP03"])
    create_wp_file(temp_feature_dir, "WP05", ["WP04"])

    return temp_feature_dir


@pytest.fixture
def circular_dependency_graph(temp_feature_dir, create_wp_file):
    """
    Create a graph with circular dependencies.

    Structure:
        WP01 → WP02 → WP03 → WP01 (cycle!)
    """
    create_wp_file(temp_feature_dir, "WP01", ["WP03"])
    create_wp_file(temp_feature_dir, "WP02", ["WP01"])
    create_wp_file(temp_feature_dir, "WP03", ["WP02"])

    return temp_feature_dir


# =============================================================================
# T031/T032: Parallel Execution Fixtures
# =============================================================================

@pytest.fixture
def execution_tracker():
    """Track execution order and timing for parallel tests."""
    class ExecutionTracker:
        def __init__(self):
            self.execution_log = []
            self.execution_times = {}
            self.start_time = None

        def record_start(self, wp_id: str):
            """Record when a WP starts execution."""
            now = time.time()
            if self.start_time is None:
                self.start_time = now
            self.execution_log.append((wp_id, "start", now - (self.start_time or now)))
            if wp_id not in self.execution_times:
                self.execution_times[wp_id] = {"start": now}

        def record_end(self, wp_id: str):
            """Record when a WP finishes execution."""
            now = time.time()
            self.execution_log.append((wp_id, "end", now - (self.start_time or now)))
            if wp_id in self.execution_times:
                self.execution_times[wp_id]["end"] = now

        def get_execution_order(self) -> list[str]:
            """Get list of WPs in order they completed."""
            return [wp_id for wp_id, event, _ in self.execution_log if event == "end"]

        def get_concurrent_count(self) -> int:
            """Count maximum concurrent executions (overlapping time windows)."""
            events = []
            for wp_id, times in self.execution_times.items():
                if "start" in times and "end" in times:
                    events.append((times["start"], 1))  # +1 for start
                    events.append((times["end"], -1))   # -1 for end

            events.sort(key=lambda x: x[0])

            max_concurrent = 0
            current = 0
            for _, delta in events:
                current += delta
                max_concurrent = max(max_concurrent, current)

            return max_concurrent

        def assert_executed_before(self, first_wp: str, second_wp: str):
            """Assert first_wp completed before second_wp started."""
            first_end = self.execution_times.get(first_wp, {}).get("end", float("inf"))
            second_start = self.execution_times.get(second_wp, {}).get("start", 0)

            assert first_end <= second_start, (
                f"{first_wp} (ended {first_end}) should complete before "
                f"{second_wp} (started {second_start})"
            )

    return ExecutionTracker()


@pytest.fixture
def mock_agent_executor(execution_tracker):
    """
    Create a mock agent executor for testing parallel execution.

    Returns a factory that creates mock executors with configurable behavior.
    """
    def create_executor(
        delay: float = 0.1,
        fail_wps: list[str] | None = None,
        custom_delays: dict[str, float] | None = None
    ) -> Callable:
        """
        Create a mock executor function.

        Args:
            delay: Default execution delay in seconds
            fail_wps: List of WP IDs that should fail (return non-zero)
            custom_delays: Dict mapping WP IDs to custom delays
        """
        fail_wps = fail_wps or []
        custom_delays = custom_delays or {}

        def execute(wp_id: str) -> int:
            execution_tracker.record_start(wp_id)

            # Apply delay
            wp_delay = custom_delays.get(wp_id, delay)
            time.sleep(wp_delay)

            execution_tracker.record_end(wp_id)

            # Return failure code if in fail list
            if wp_id in fail_wps:
                return 1
            return 0

        return execute

    return create_executor


@pytest.fixture
def independent_wps_graph(temp_feature_dir, create_wp_file):
    """
    Create a graph with independent WPs (no dependencies).

    Structure:
        WP01, WP02, WP03 (all independent)
    """
    create_wp_file(temp_feature_dir, "WP01", [])
    create_wp_file(temp_feature_dir, "WP02", [])
    create_wp_file(temp_feature_dir, "WP03", [])

    return temp_feature_dir


@pytest.fixture
def convergent_dependency_graph(temp_feature_dir, create_wp_file):
    """
    Create a graph where multiple independent WPs converge to one.

    Structure:
        WP01, WP02, WP03 (independent)
           └──────┴──────┘
                  │
                WP04 (depends on all three)
    """
    create_wp_file(temp_feature_dir, "WP01", [])
    create_wp_file(temp_feature_dir, "WP02", [])
    create_wp_file(temp_feature_dir, "WP03", [])
    create_wp_file(temp_feature_dir, "WP04", ["WP01", "WP02", "WP03"])

    return temp_feature_dir
