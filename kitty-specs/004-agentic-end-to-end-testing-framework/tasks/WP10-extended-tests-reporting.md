---
work_package_id: WP10
title: Extended Tests and Reporting
lane: "doing"
dependencies: []
subtasks:
- T011
- T038
- T039
- T040
- T041
- T043
- T044
- T046
- T047
- T049
phase: Phase 4 - Test Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "85695"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 – Extended Tests and Reporting

## Objective

Complete the test suite with extended tests (cross-review, parallel, fault injection, natural failures, agent config) and implement test execution controls (markers, filtering, JUnit XML, human-readable reports).

## Context

**Depends On**: WP07 (multi-agent paths), WP08 (fault injection), WP09 (core tests)
**User Stories Addressed**: US2, US3, US5, US6, US8
**Functional Requirements**: FR-011, FR-016, FR-035, FR-036, FR-037, FR-038

This is the largest work package, completing all remaining tests. It may be split during implementation if needed.

## Subtasks

### T011: Support dynamic agent configuration loading

Enhance agent_fixtures.py to support runtime config updates:

```python
# In tests/agentic/fixtures/agent_fixtures.py

class DynamicAgentRegistry(AgentRegistry):
    """Agent registry that supports runtime updates."""

    def add_agent(self, agent_config: AgentConfig) -> None:
        """Add a new agent at runtime."""
        self._agents[agent_config.agent_id] = agent_config

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def update_agent(self, agent_id: str, **kwargs) -> bool:
        """Update agent configuration."""
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        return True

    def reload_config(self) -> None:
        """Reload configuration from YAML file."""
        self._agents.clear()
        self._load_config()
```

**Acceptance Criteria**:
- Agents can be added at runtime
- Agents can be removed at runtime
- Configuration can be reloaded
- Changes don't affect other tests (isolation)

### T038: Add pytest markers for manual test triggering

Create marker definitions in `tests/agentic/conftest.py`:

```python
# In tests/agentic/conftest.py

import pytest

def pytest_configure(config):
    """Register custom markers for agentic tests."""
    config.addinivalue_line(
        "markers", "agentic: mark test as agentic E2E test (requires Docker)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (real agent invocations)"
    )
    config.addinivalue_line(
        "markers", "distribution: mark as distribution test (PyPI validation)"
    )
    config.addinivalue_line(
        "markers", "isolation: mark as container isolation test"
    )
    config.addinivalue_line(
        "markers", "security: mark as security-related test"
    )
    config.addinivalue_line(
        "markers", "single_agent: mark as single-agent workflow test"
    )
    config.addinivalue_line(
        "markers", "cross_review: mark as cross-review workflow test"
    )
    config.addinivalue_line(
        "markers", "parallel: mark as parallel execution test"
    )
    config.addinivalue_line(
        "markers", "fault_injection: mark as fault injection test"
    )
    config.addinivalue_line(
        "markers", "natural_failure: mark as natural failure observation test"
    )
    # Agent-specific markers
    config.addinivalue_line("markers", "claude: requires Claude Code agent")
    config.addinivalue_line("markers", "copilot: requires GitHub Copilot agent")
    config.addinivalue_line("markers", "codex: requires GitHub Codex agent")
    config.addinivalue_line("markers", "gemini: requires Google Gemini agent")
    config.addinivalue_line("markers", "cursor: requires Cursor agent")
    config.addinivalue_line("markers", "qwen: requires Qwen Code agent")
    config.addinivalue_line("markers", "opencode: requires OpenCode agent")
    config.addinivalue_line("markers", "kilocode: requires Kilocode agent")
    config.addinivalue_line("markers", "augment: requires Augment Code agent")

def pytest_collection_modifyitems(config, items):
    """Auto-skip tests for unavailable agents."""
    # Get available agents
    from .fixtures.agent_fixtures import AgentRegistry
    from pathlib import Path

    config_path = Path(__file__).parent / "config" / "agents.yaml"
    if config_path.exists():
        registry = AgentRegistry(config_path)
        available = {a.agent_id for a in registry.get_available_agents()}
    else:
        available = set()

    agent_markers = {
        "claude": "claude-code",
        "copilot": "github-copilot",
        "codex": "github-codex",
        "gemini": "google-gemini",
        "cursor": "cursor",
        "qwen": "qwen-code",
        "opencode": "opencode",
        "kilocode": "kilocode",
        "augment": "augment-code",
    }

    for item in items:
        for marker_name, agent_id in agent_markers.items():
            if marker_name in item.keywords:
                if agent_id not in available:
                    item.add_marker(pytest.mark.skip(
                        reason=f"Agent {agent_id} not available"
                    ))
```

**Acceptance Criteria**:
- All markers registered
- Agent markers auto-skip when unavailable
- Tests filterable by marker

### T039: Implement test filtering (by agent, path, scenario)

The pytest markers above enable filtering. Add pytest.ini configuration:

```ini
# pytest.ini or in pyproject.toml
[pytest]
markers =
    agentic: agentic E2E tests
    slow: slow tests
    distribution: distribution tests
    # ... etc

# Default: exclude agentic tests from regular test runs
addopts = --ignore=tests/agentic

# To run agentic tests manually:
# pytest tests/agentic/ -v
```

Also add helper scripts:

```bash
#!/bin/bash
# scripts/run-agentic-tests.sh

# Run all agentic tests
pytest tests/agentic/ -v "$@"

# Examples:
# ./scripts/run-agentic-tests.sh -k "claude"  # Claude only
# ./scripts/run-agentic-tests.sh -m "single_agent"  # Single-agent only
# ./scripts/run-agentic-tests.sh -m "not slow"  # Fast tests only
```

**Acceptance Criteria**:
- Tests excluded from default pytest run
- Filter by agent: `-k claude`
- Filter by path: `-m single_agent`
- Filter by scenario: `-m fault_injection`
- Helper script for common filters

### T040: Generate JUnit XML test reports

Add JUnit XML output:

```python
# In conftest.py

@pytest.fixture(scope="session", autouse=True)
def configure_reporting(request):
    """Configure test reporting."""
    # JUnit XML is built into pytest: pytest --junitxml=report.xml
    pass

# Add to pytest.ini or pyproject.toml:
# [pytest]
# junit_family = xunit2
# junit_suite_name = agentic-e2e-tests
```

Create wrapper script:

```bash
#!/bin/bash
# scripts/run-with-reports.sh

OUTPUT_DIR="tests/agentic/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

pytest tests/agentic/ \
    --junitxml="$OUTPUT_DIR/junit-$TIMESTAMP.xml" \
    --tb=short \
    -v \
    "$@"
```

**Acceptance Criteria**:
- JUnit XML generated automatically
- Timestamped report files
- Compatible with CI systems

### T041: Generate human-readable summary reports

Create summary report generator:

```python
# tests/agentic/reporting.py

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TestSummary:
    """Summary of a test run."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    agents_used: List[str]
    paths_tested: List[str]
    failures: List[Dict[str, Any]]

class ReportGenerator:
    """Generates human-readable test reports."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def generate_summary(self, test_runs: List['TestRun']) -> TestSummary:
        """Generate summary from test runs."""
        passed = sum(1 for r in test_runs if r.status.value == "passed")
        failed = sum(1 for r in test_runs if r.status.value == "failed")
        skipped = sum(1 for r in test_runs if r.status.value == "skipped")
        errors = sum(1 for r in test_runs if r.status.value == "error")

        agents = set()
        paths = set()
        failures = []

        for run in test_runs:
            for agent_id in run.agent_assignments.values():
                agents.add(agent_id)
            paths.add(run.path_id)

            if run.status.value in ("failed", "error"):
                failures.append({
                    "run_id": run.run_id,
                    "path_id": run.path_id,
                    "reason": run.failure_reason,
                    "agents": list(run.agent_assignments.values())
                })

        total_duration = sum(
            (r.completed_at - r.started_at).total_seconds()
            for r in test_runs
            if r.completed_at
        )

        return TestSummary(
            timestamp=datetime.utcnow().isoformat(),
            total_tests=len(test_runs),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=total_duration,
            agents_used=sorted(agents),
            paths_tested=sorted(paths),
            failures=failures
        )

    def write_markdown_report(
        self,
        summary: TestSummary,
        output_path: Path
    ) -> None:
        """Write summary as Markdown."""
        with open(output_path, 'w') as f:
            f.write(f"# Agentic E2E Test Report\n\n")
            f.write(f"**Generated**: {summary.timestamp}\n\n")

            f.write("## Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Total Tests | {summary.total_tests} |\n")
            f.write(f"| Passed | {summary.passed} |\n")
            f.write(f"| Failed | {summary.failed} |\n")
            f.write(f"| Skipped | {summary.skipped} |\n")
            f.write(f"| Errors | {summary.errors} |\n")
            f.write(f"| Duration | {summary.duration_seconds:.1f}s |\n")
            f.write(f"\n")

            f.write("## Agents Tested\n\n")
            for agent in summary.agents_used:
                f.write(f"- {agent}\n")
            f.write("\n")

            f.write("## Test Paths\n\n")
            for path in summary.paths_tested:
                f.write(f"- {path}\n")
            f.write("\n")

            if summary.failures:
                f.write("## Failures\n\n")
                for failure in summary.failures:
                    f.write(f"### {failure['run_id']}\n\n")
                    f.write(f"- **Path**: {failure['path_id']}\n")
                    f.write(f"- **Agents**: {', '.join(failure['agents'])}\n")
                    f.write(f"- **Reason**: {failure['reason']}\n\n")

    def write_json_report(
        self,
        summary: TestSummary,
        output_path: Path
    ) -> None:
        """Write summary as JSON."""
        with open(output_path, 'w') as f:
            json.dump({
                "timestamp": summary.timestamp,
                "total_tests": summary.total_tests,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "errors": summary.errors,
                "duration_seconds": summary.duration_seconds,
                "agents_used": summary.agents_used,
                "paths_tested": summary.paths_tested,
                "failures": summary.failures
            }, f, indent=2)
```

**Acceptance Criteria**:
- Markdown report generated
- JSON report generated
- Includes pass/fail counts
- Lists agents and paths tested
- Details failures

### T043: Write test_cross_review.py test cases

Create `tests/agentic/tests/test_cross_review.py`:

```python
"""Cross-review workflow tests - US2 validation.

Tests two-agent workflows where different agents
implement and review.
"""

import pytest
import asyncio

from ..paths.cross_review import CrossReviewPath
from ..fixtures.workflow_fixtures import TestStatus

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.cross_review,
]


class TestCrossReviewWorkflow:
    """US2: Two-Agent Cross-Review Validation"""

    @pytest.mark.parametrize("implementer,reviewer", [
        pytest.param("claude-code", "github-copilot", marks=[pytest.mark.claude, pytest.mark.copilot]),
        pytest.param("claude-code", "google-gemini", marks=[pytest.mark.claude, pytest.mark.gemini]),
        pytest.param("github-copilot", "github-codex", marks=[pytest.mark.copilot, pytest.mark.codex]),
        pytest.param("google-gemini", "qwen-code", marks=[pytest.mark.gemini, pytest.mark.qwen]),
    ])
    def test_cross_review_with_different_agents(
        self,
        implementer,
        reviewer,
        require_agent,
        cross_review_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 1:
        Given a feature with one WP and two configured agents,
        When the two-agent test runs,
        Then one agent implements and a different agent reviews.
        """
        # Require both agents
        impl_config = require_agent(implementer)
        review_config = require_agent(reviewer)

        feature = test_feature_scaffold.create_test_feature(
            feature_name="cross-review-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": implementer,
            "reviewer": reviewer
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify different agents used
        impl_obs = [o for o in run.observations if o.data.get("role") == "implementer"]
        review_obs = [o for o in run.observations if o.data.get("role") == "reviewer"]

        assert impl_obs, "No implementation observations"
        assert review_obs, "No review observations"

        impl_agents = {o.agent_id for o in impl_obs}
        review_agents = {o.agent_id for o in review_obs}

        assert impl_agents == {implementer}, f"Wrong implementer: {impl_agents}"
        assert review_agents == {reviewer}, f"Wrong reviewer: {review_agents}"
        assert impl_agents.isdisjoint(review_agents), "Same agent did both roles"

    def test_rejection_rework_by_original_implementer(
        self,
        available_agents,
        cross_review_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 2:
        Given the review agent rejects the implementation,
        When the WP returns to "planned",
        Then the original implementation agent performs the rework.
        """
        if len(available_agents) < 2:
            pytest.skip("Need at least 2 agents for cross-review")

        impl_id = available_agents[0].agent_id
        review_id = available_agents[1].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="rejection-rework-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": impl_id,
            "reviewer": review_id
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # If there was a rework, verify implementer did it
        rework_obs = [o for o in run.observations if "rework" in o.step]
        for obs in rework_obs:
            assert obs.agent_id == impl_id, \
                f"Wrong agent did rework: {obs.agent_id}, expected {impl_id}"

    def test_logs_attribute_actions_to_correct_agents(
        self,
        available_agents,
        cross_review_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 4:
        Given a two-agent workflow completes successfully,
        When analyzing the logs,
        Then the implementation and review phases are clearly attributed.
        """
        if len(available_agents) < 2:
            pytest.skip("Need at least 2 agents")

        impl_id = available_agents[0].agent_id
        review_id = available_agents[1].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="attribution-test",
            num_wps=1
        )

        cross_review_path.assign_agents({
            "implementer": impl_id,
            "reviewer": review_id
        })

        run = asyncio.run(cross_review_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify all observations have agent_id set
        action_obs = [o for o in run.observations if o.agent_id]
        assert action_obs, "No agent-attributed observations"

        for obs in action_obs:
            assert obs.agent_id in (impl_id, review_id), \
                f"Unknown agent in observation: {obs.agent_id}"


@pytest.fixture
def cross_review_path():
    """Create a CrossReviewPath for testing."""
    from ..paths.cross_review import CrossReviewPath
    from ..paths.base_path import TestPathConfig, AgentSlot, AgentRole

    config = TestPathConfig(
        path_id="cross-review",
        description="Cross-review test path",
        agent_slots=[
            AgentSlot(
                slot_id="implementer",
                role=AgentRole.IMPLEMENTATION,
                required=True
            ),
            AgentSlot(
                slot_id="reviewer",
                role=AgentRole.REVIEW,
                required=True,
                different_from="implementer"
            )
        ],
        max_iterations=3,
        timeout_seconds=2400
    )

    return CrossReviewPath(config)
```

**Acceptance Criteria**:
- Tests US2 acceptance scenarios
- Parameterized for agent combinations
- Verifies agent attribution

### T044: Write test_parallel.py test cases

Create `tests/agentic/tests/test_parallel.py`:

```python
"""Parallel execution tests - US3 validation."""

import pytest
import asyncio
import time

from ..paths.parallel_three import ParallelThreePath
from ..fixtures.workflow_fixtures import TestStatus

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.parallel,
]


class TestParallelExecution:
    """US3: Three-Agent Parallel Execution"""

    def test_three_wps_execute_in_parallel(
        self,
        available_agents,
        parallel_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 1:
        Given a feature with 3 independent WPs and 3 available agents,
        When the three-agent test runs,
        Then all 3 WPs execute in parallel (not sequentially).
        """
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents for parallel test")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="parallel-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        start_time = time.time()
        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))
        total_time = time.time() - start_time

        # Get individual timings
        timings = parallel_path.get_parallel_timing()

        if len(timings) >= 3:
            # If all completed, total should be less than sum
            sum_individual = sum(timings.values())
            assert total_time < sum_individual, \
                f"Execution appears sequential: total={total_time:.1f}s, sum={sum_individual:.1f}s"

    def test_parallel_execution_less_than_2x_slowest(
        self,
        available_agents,
        parallel_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 4:
        Given all 3 WPs complete successfully,
        When the test finishes,
        Then execution time is significantly less than 3x single-WP time.
        """
        if len(available_agents) < 3:
            pytest.skip("Need 3 agents")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="timing-test",
            num_wps=3
        )

        parallel_path.assign_agents({
            "worker_1": available_agents[0].agent_id,
            "worker_2": available_agents[1].agent_id,
            "worker_3": available_agents[2].agent_id,
        })

        parallel_path.assign_work_items(
            wp_ids=feature["wp_ids"],
            agent_assignments=parallel_path._agent_assignments
        )

        run = asyncio.run(parallel_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        timings = parallel_path.get_parallel_timing()

        if timings:
            slowest = max(timings.values())
            total = (run.completed_at - run.started_at).total_seconds()

            # SC-003: Less than 2x slowest single-agent execution
            assert total < 2 * slowest, \
                f"Parallel too slow: {total:.1f}s vs 2x{slowest:.1f}s"

    def test_one_failure_doesnt_block_others(
        self,
        available_agents,
        parallel_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 3:
        Given one agent fails during parallel execution,
        When the failure is detected,
        Then other agents continue their work.
        """
        # This test is harder to force - we rely on natural behavior
        # or inject a fault on one agent
        pytest.skip("Requires fault injection - see test_fault_injection.py")
```

**Acceptance Criteria**:
- Tests US3 scenarios
- Verifies parallel (not sequential) execution
- Checks timing constraint (< 2x slowest)

### T046: Write test_fault_injection.py test cases

Create `tests/agentic/tests/test_fault_injection.py`:

```python
"""Fault injection tests - US5 validation."""

import pytest
import asyncio

from ..faults.process_faults import ProcessFaultInjector, ProcessSignal
from ..faults.file_faults import FileFaultInjector, CorruptionType
from ..faults.auth_faults import AuthFaultInjector
from ..fixtures.workflow_fixtures import TestStatus

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.fault_injection,
]


class TestProcessCrashRecovery:
    """US5 Scenario 1: Process crash handling."""

    def test_agent_crash_detected_and_handled(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Given a running agent process,
        When the test kills the process mid-task,
        Then the orchestrator detects the failure and applies fallback.
        """
        if not available_agents:
            pytest.skip("No agents available")

        # Set up fault injector
        injector = ProcessFaultInjector()

        # This test needs to inject fault during execution
        # Implementation depends on how we hook into the execution


class TestTimeoutHandling:
    """US5 Scenario 2: Timeout handling."""

    def test_timeout_terminates_and_retries(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry
    ):
        """
        Given an agent execution,
        When the test injects a timeout,
        Then the orchestrator terminates the agent and retries.
        """
        pytest.skip("Requires integration with timeout injection")


class TestStateFileCorruption:
    """US5 Scenario 3: State file corruption handling."""

    def test_corrupted_json_detected(
        self,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Given a merge state file,
        When the test corrupts the JSON structure,
        Then the orchestrator detects corruption and reports clearly.
        """
        feature = test_feature_scaffold.create_test_feature(
            feature_name="corruption-test",
            num_wps=1
        )

        injector = FileFaultInjector()

        # Corrupt the WP file
        result = injector.corrupt_wp_state(
            worktree_path=tmp_worktree,
            wp_id=feature["wp_ids"][0]
        )

        if not result.success:
            pytest.skip(f"Could not corrupt file: {result.error}")

        # Now try to read the corrupted file
        import yaml
        from pathlib import Path

        wp_files = list(Path(tmp_worktree).rglob(f"**/{feature['wp_ids'][0]}*.md"))
        if wp_files:
            with pytest.raises((yaml.YAMLError, ValueError)):
                content = wp_files[0].read_text()
                # Try to parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    yaml.safe_load(parts[1])


class TestGitConflictHandling:
    """US5 Scenario 4: Git conflict handling."""

    def test_git_conflict_detected(
        self,
        tmp_worktree
    ):
        """
        Given two WPs modifying the same file,
        When the test creates a git conflict,
        Then the orchestrator pauses or auto-resolves.
        """
        from ..faults.file_faults import GitFaultInjector

        injector = GitFaultInjector(tmp_worktree)
        result = injector.create_merge_conflict(
            file_path="test_file.txt",
            content_a="Version A",
            content_b="Version B"
        )

        assert result.success, f"Failed to create conflict: {result.error}"
        assert result.conflict_markers, "No conflict markers found"

        # Cleanup
        injector.abort_merge()


class TestAuthFailureHandling:
    """US5 Scenario 5: Authentication failure handling."""

    def test_auth_failure_triggers_fallback(
        self,
        available_agents,
        tmp_path
    ):
        """
        Given the test simulates authentication failure,
        When an agent cannot authenticate,
        Then the fallback strategy activates.
        """
        if not available_agents:
            pytest.skip("No agents available")

        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()

        # Create a fake credential
        cred_file = secrets_dir / "test_api_key.txt"
        cred_file.write_text("valid_key_123")

        injector = AuthFaultInjector(secrets_dir)

        with injector.temporary_auth_failure("test-agent", "test_api_key.txt"):
            # Credential should be invalid now
            content = cred_file.read_text()
            assert content == "INVALID_API_KEY_FOR_TESTING"

        # After context, should be restored
        content = cred_file.read_text()
        assert content == "valid_key_123"
```

**Acceptance Criteria**:
- Tests US5 scenarios
- Process crash injection
- File corruption injection
- Git conflict injection
- Auth failure injection

### T047: Write test_natural_failures.py test cases

Create `tests/agentic/tests/test_natural_failures.py`:

```python
"""Natural failure observation tests - US6 validation.

These tests run extended sessions to observe real agent failures.
"""

import pytest
import asyncio

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.natural_failure,
]


class TestNaturalFailureObservation:
    """US6: Natural Failure Observation"""

    @pytest.mark.timeout(3600)  # 1 hour max
    def test_extended_run_captures_failures(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree,
        output_logger
    ):
        """
        Acceptance Scenario 1-2:
        Given real agents executing complex WPs,
        When agents produce invalid output or unexpected decisions,
        Then the test captures all actions for post-mortem.
        """
        if not available_agents:
            pytest.skip("No agents available")

        # Run multiple iterations
        results = []
        for i in range(5):  # Run 5 workflows
            feature = test_feature_scaffold.create_test_feature(
                feature_name=f"natural-{i}",
                num_wps=1
            )

            single_agent_path.assign_agents({
                "implementer": available_agents[0].agent_id,
                "reviewer": available_agents[0].agent_id
            })

            run = asyncio.run(single_agent_path.execute(
                container_factory=container_factory,
                agent_registry=agent_registry,
                worktree_path=tmp_worktree
            ))
            results.append(run)

        # Analyze results
        failures = [r for r in results if r.status != "passed"]

        # Log files should exist
        log_files = output_logger.get_log_files()
        assert len(log_files) > 0, "No log files captured"

    def test_comprehensive_log_capture(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree,
        output_logger,
        transition_logger,
        git_state_capture
    ):
        """
        Acceptance Scenario 3:
        Given any agent failure,
        When reviewing test results,
        Then logs include stdout/stderr, git state, WP status, timing, metrics.
        """
        if not available_agents:
            pytest.skip("No agents available")

        feature = test_feature_scaffold.create_test_feature(
            feature_name="log-capture-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": available_agents[0].agent_id,
            "reviewer": available_agents[0].agent_id
        })

        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify comprehensive capture
        assert run.observations, "No observations captured"

        # Check for required data types
        has_stdout = any(
            "stdout" in o.data or "output" in o.data
            for o in run.observations
        )

        # Capture git state
        git_state = git_state_capture.capture()
        assert git_state.branch, "Git branch not captured"

        # Capture transitions
        transitions = transition_logger.get_transitions()
        # May be empty if no lane changes occurred
```

**Acceptance Criteria**:
- Extended run test (multiple workflows)
- Comprehensive log capture verification
- All data types captured

### T049: Write test_agent_config.py test cases

Create `tests/agentic/tests/test_agent_config.py`:

```python
"""Agent configuration tests - US8 validation."""

import pytest
from pathlib import Path

pytestmark = [
    pytest.mark.agentic,
]


class TestAgentConfiguration:
    """US8: Modular Agent Configuration"""

    def test_only_configured_agents_used(
        self,
        agent_registry
    ):
        """
        Acceptance Scenario 1:
        Given a YAML configuration file listing available agents,
        When tests run,
        Then only configured agents are used.
        """
        agents = agent_registry.get_available_agents()

        # All returned agents should be enabled in config
        for agent in agents:
            assert agent.enabled, f"Disabled agent returned: {agent.agent_id}"

    def test_new_agent_auto_discovered(
        self,
        tmp_path
    ):
        """
        Acceptance Scenario 2:
        Given a new agent is added to configuration,
        When tests run,
        Then the new agent is automatically included.
        """
        from ..fixtures.agent_fixtures import AgentRegistry, AgentConfig

        # Create temp config with new agent
        config_content = """
version: "1.0"
agents:
  test-new-agent:
    enabled: true
    command: "echo"
    invocation_pattern: "stdin"
    timeout_seconds: 30
    credentials_secret: "test_key"
    resource_limits:
      cpu_cores: 1.0
      memory_mb: 512
      disk_mb: 1024
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = AgentRegistry(config_path)
        agent = registry.get_agent("test-new-agent")

        assert agent is not None, "New agent not discovered"
        assert agent.agent_id == "test-new-agent"

    def test_removed_agent_tests_skipped(
        self,
        agent_registry
    ):
        """
        Acceptance Scenario 3:
        Given an agent is removed from configuration,
        When tests run,
        Then tests requiring that agent are skipped.
        """
        # Try to get a non-existent agent
        agent = agent_registry.get_agent("definitely-not-real-agent")
        assert agent is None, "Non-existent agent should return None"

    def test_agent_specific_config_applied(
        self,
        agent_registry
    ):
        """
        Acceptance Scenario 4:
        Given agent-specific configuration,
        When that agent runs,
        Then the specific configuration is applied.
        """
        agents = agent_registry.get_available_agents()

        for agent in agents:
            # Each agent should have its own limits
            assert agent.timeout_seconds > 0
            assert agent.resource_limits.cpu_cores > 0
            assert agent.resource_limits.memory_mb > 0

            # Cursor should have timeout wrapper
            if agent.agent_id == "cursor":
                assert agent.requires_timeout_wrapper, \
                    "Cursor should require timeout wrapper"
```

**Acceptance Criteria**:
- Tests US8 scenarios
- Config loading verified
- Agent discovery verified
- Skip behavior verified

## Technical Notes

- This is the largest WP - consider splitting if needed
- Some tests require multiple agents
- Natural failure tests are time-consuming
- Fault injection tests may require Docker privileges

## Files to Create/Modify

1. `tests/agentic/fixtures/agent_fixtures.py` (update T011)
2. `tests/agentic/conftest.py` (update T038)
3. `tests/agentic/reporting.py` (create T041)
4. `tests/agentic/tests/test_cross_review.py` (create T043)
5. `tests/agentic/tests/test_parallel.py` (create T044)
6. `tests/agentic/tests/test_fault_injection.py` (create T046)
7. `tests/agentic/tests/test_natural_failures.py` (create T047)
8. `tests/agentic/tests/test_agent_config.py` (create T049)
9. `pytest.ini` or `pyproject.toml` (update T039)
10. `scripts/run-agentic-tests.sh` (create T039)
11. `scripts/run-with-reports.sh` (create T040)

## Verification

```bash
# Run all extended tests
pytest tests/agentic/tests/ -v --tb=short

# Generate reports
./scripts/run-with-reports.sh

# Filter by marker
pytest tests/agentic/ -v -m "cross_review"
pytest tests/agentic/ -v -m "fault_injection"
```

## Definition of Done

- [ ] DynamicAgentRegistry implemented
- [ ] All pytest markers registered
- [ ] Test filtering working
- [ ] JUnit XML reports generated
- [ ] Markdown summary reports generated
- [ ] test_cross_review.py complete
- [ ] test_parallel.py complete
- [ ] test_fault_injection.py complete
- [ ] test_natural_failures.py complete
- [ ] test_agent_config.py complete
- [ ] Helper scripts created

## Activity Log

- 2026-01-19T16:11:25Z – claude-opus – shell_pid=85695 – lane=doing – Started implementation via workflow command
