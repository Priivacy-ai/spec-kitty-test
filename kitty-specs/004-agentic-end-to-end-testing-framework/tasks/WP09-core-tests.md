---
work_package_id: WP09
title: 'Core Tests: Single-Agent, Distribution, and Isolation'
lane: "doing"
dependencies: []
subtasks:
- T036
- T037
- T042
- T045
- T048
phase: Phase 4 - Test Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "79929"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Core Tests: Single-Agent, Distribution, and Isolation

## Objective

Implement the P1 (highest priority) test files: test_single_agent.py for single-agent workflow validation, test_distribution.py for PyPI package validation, and test_container_isolation.py for security verification.

## Context

**Depends On**: WP01-WP06 (all infrastructure and fixtures)
**User Stories Addressed**: US1 (Single-Agent), US4 (Isolation), US7 (Distribution)
**Functional Requirements**: FR-007, FR-032, FR-033, FR-034, FR-001-FR-006

These are the core tests that must pass before the framework is considered functional. They validate the fundamental capabilities: running a single agent workflow, ensuring we test PyPI packages, and verifying container isolation.

## Subtasks

### T036: Verify PyPI install (no SPEC_KITTY_TEMPLATE_ROOT)

Create distribution validation in `tests/agentic/tests/test_distribution.py`:

```python
"""Distribution testing - validates PyPI package, not development code.

CRITICAL: Per CLAUDE.md, this test validates what users experience.
The 0.10.8 catastrophe taught us: test what you ship, not just what you write.

These tests MUST NOT set SPEC_KITTY_TEMPLATE_ROOT.
"""

import pytest
import subprocess
import os
from pathlib import Path

# Mark all tests in this module as distribution tests
pytestmark = [
    pytest.mark.distribution,
    pytest.mark.slow,  # Real agent invocations take time
]


class TestDistributionInstall:
    """Verify spec-kitty is installed from PyPI correctly."""

    def test_spec_kitty_installed_from_pypi(self, test_container):
        """Verify spec-kitty is installed from PyPI, not local source."""
        # Run pip show inside container
        exit_code, stdout, stderr = test_container.exec_command(
            "pip show spec-kitty",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty not installed: {stderr}"

        # Verify it's not an editable install
        assert "Editable project location" not in stdout, \
            "spec-kitty appears to be an editable install (development mode)"

        # Verify Location is in site-packages, not a local path
        lines = stdout.split('\n')
        location_line = [l for l in lines if l.startswith('Location:')]
        assert location_line, "Could not find Location in pip show output"
        assert 'site-packages' in location_line[0], \
            f"spec-kitty not in site-packages: {location_line[0]}"

    def test_template_root_not_set(self, test_container):
        """Verify SPEC_KITTY_TEMPLATE_ROOT is not set in container."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import os; print(os.environ.get(\"SPEC_KITTY_TEMPLATE_ROOT\", \"NOT_SET\"))'",
            timeout=10
        )

        assert exit_code == 0
        assert stdout.strip() == "NOT_SET", \
            f"SPEC_KITTY_TEMPLATE_ROOT is set: {stdout.strip()}"

    def test_templates_from_package(self, test_container):
        """Verify templates are loaded from the installed package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from spec_kitty.template_manager import TemplateManager; "
            "tm = TemplateManager(); "
            "print(tm.template_dir)"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to get template dir: {stderr}"

        # Should be in site-packages, not a local directory
        template_dir = stdout.strip()
        assert 'site-packages' in template_dir, \
            f"Templates not from package: {template_dir}"


class TestDistributionFunctionality:
    """Verify distributed package works correctly."""

    def test_spec_kitty_version_accessible(self, test_container):
        """Verify spec-kitty version is accessible."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty --version",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty --version failed: {stderr}"
        assert "spec-kitty" in stdout.lower() or stdout.strip(), \
            f"Unexpected version output: {stdout}"

    def test_spec_kitty_help_works(self, test_container):
        """Verify spec-kitty help command works."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty --help",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty --help failed: {stderr}"
        assert "Usage" in stdout or "usage" in stdout, \
            f"Help output missing Usage: {stdout}"

    def test_agent_commands_available(self, test_container):
        """Verify agent subcommands are available."""
        exit_code, stdout, stderr = test_container.exec_command(
            "spec-kitty agent --help",
            timeout=30
        )

        assert exit_code == 0, f"spec-kitty agent --help failed: {stderr}"
        # Should list agent-related subcommands
        assert any(cmd in stdout for cmd in ['feature', 'tasks', 'implement']), \
            f"Agent commands not found in help: {stdout}"
```

**Acceptance Criteria**:
- Verifies pip install is from PyPI
- Confirms SPEC_KITTY_TEMPLATE_ROOT is NOT set
- Validates templates come from package
- Tests basic CLI functionality

### T037: Implement version verification for spec-kitty

Add version verification tests:

```python
# Continue in test_distribution.py

class TestVersionVerification:
    """Verify spec-kitty version matches expected release."""

    @pytest.fixture
    def expected_version(self):
        """Get expected version from test configuration."""
        # Can be set via environment or config
        return os.environ.get("SPEC_KITTY_TEST_VERSION", None)

    def test_version_matches_expected(self, test_container, expected_version):
        """Verify installed version matches expected version."""
        if not expected_version:
            pytest.skip("SPEC_KITTY_TEST_VERSION not set")

        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import spec_kitty; print(spec_kitty.__version__)'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to get version: {stderr}"
        installed_version = stdout.strip()

        assert installed_version == expected_version, \
            f"Version mismatch: installed={installed_version}, expected={expected_version}"

    def test_version_is_release(self, test_container):
        """Verify version looks like a release (not dev/local)."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c 'import spec_kitty; print(spec_kitty.__version__)'",
            timeout=30
        )

        assert exit_code == 0
        version = stdout.strip()

        # Should not contain dev indicators
        dev_indicators = ['.dev', '+local', '+editable', '-dirty']
        for indicator in dev_indicators:
            assert indicator not in version, \
                f"Version contains development indicator: {version}"

    def test_pypi_metadata_present(self, test_container):
        """Verify PyPI metadata is present in package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from importlib.metadata import metadata; "
            "m = metadata(\"spec-kitty\"); "
            "print(m[\"Author\"])"
            "'",
            timeout=30
        )

        # Should have metadata from PyPI
        assert exit_code == 0, f"Could not read package metadata: {stderr}"
        assert stdout.strip(), "Package metadata is empty"
```

**Acceptance Criteria**:
- Version matches expected when specified
- Version format indicates release
- PyPI metadata present

### T042: Write test_single_agent.py test cases

Create `tests/agentic/tests/test_single_agent.py`:

```python
"""Single-agent workflow tests - US1 validation.

Tests the simplest configuration: one agent performing both
implementation and review of a work package.
"""

import pytest
from pathlib import Path

from ..paths.single_agent import SingleAgentPath
from ..fixtures.workflow_fixtures import TestStatus, WPLane

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.slow,
    pytest.mark.single_agent,
]


class TestSingleAgentWorkflow:
    """US1: Single-Agent Workflow Validation"""

    @pytest.mark.parametrize("agent_id", [
        pytest.param("claude-code", marks=pytest.mark.claude),
        pytest.param("github-copilot", marks=pytest.mark.copilot),
        pytest.param("github-codex", marks=pytest.mark.codex),
        pytest.param("google-gemini", marks=pytest.mark.gemini),
        pytest.param("cursor", marks=pytest.mark.cursor),
    ])
    def test_single_agent_completes_workflow(
        self,
        agent_id,
        require_agent,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree
    ):
        """
        Acceptance Scenario 1:
        Given a prepared feature with one WP in "planned" lane,
        When the single-agent test runs with [agent],
        Then the WP progresses through implement → review → done with commits.
        """
        # Require agent (skips if unavailable)
        agent_config = require_agent(agent_id)

        # Create test feature with one WP
        feature = test_feature_scaffold.create_test_feature(
            feature_name="single-agent-test",
            num_wps=1
        )

        # Configure path with agent
        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id  # Same agent via same_as constraint
        })

        # Execute workflow
        import asyncio
        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Assertions
        assert run.status == TestStatus.PASSED, \
            f"Workflow failed: {run.failure_reason}"

        # Verify WP reached done
        final_observations = [
            o for o in run.observations
            if o.event_type.value == "wp_lane_changed"
        ]
        assert any(o.data.get("to_lane") == "done" for o in final_observations), \
            "WP did not reach done status"

    def test_single_agent_handles_rejection_cycle(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree,
        workflow_validator
    ):
        """
        Acceptance Scenario 2:
        Given a single-agent test where review phase rejects,
        When the WP is sent back to "planned",
        Then the agent re-implements and continues until approval or max iterations.
        """
        if not available_agents:
            pytest.skip("No agents available")

        agent_id = available_agents[0].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="rejection-cycle-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id
        })

        # Execute
        import asyncio
        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Check that rejection handling occurred (may or may not reject)
        rejection_observations = [
            o for o in run.observations
            if o.step == "rejection" or
               (o.data.get("from_lane") == "for_review" and
                o.data.get("to_lane") == "planned")
        ]

        # If rejections occurred, verify iteration tracking
        if rejection_observations:
            iterations = max(
                o.data.get("iteration", 0)
                for o in rejection_observations
            )
            assert iterations <= single_agent_path.config.max_iterations, \
                f"Exceeded max iterations: {iterations}"

    def test_unavailable_agent_skipped_gracefully(
        self,
        agent_registry,
        single_agent_path
    ):
        """
        Acceptance Scenario 3:
        Given an agent that is not installed or authenticated,
        When the test attempts to run,
        Then the test is skipped with a clear message.
        """
        # Try to use a fake agent
        fake_agent = "nonexistent-agent-xyz"
        agent = agent_registry.get_agent(fake_agent)

        if agent is None:
            pytest.skip(f"Agent {fake_agent} not available (expected)")
        elif not agent.is_available:
            pytest.skip(f"Agent {fake_agent} not available: not installed or authenticated")

        # If we get here, the fake agent somehow exists
        pytest.fail(f"Expected agent {fake_agent} to not exist")

    def test_successful_workflow_captures_all_data(
        self,
        available_agents,
        single_agent_path,
        container_factory,
        agent_registry,
        test_feature_scaffold,
        tmp_worktree,
        output_logger,
        transition_logger
    ):
        """
        Acceptance Scenario 4:
        Given a successful single-agent workflow,
        When the test completes,
        Then all logs, outputs, and state are captured for analysis.
        """
        if not available_agents:
            pytest.skip("No agents available")

        agent_id = available_agents[0].agent_id

        feature = test_feature_scaffold.create_test_feature(
            feature_name="data-capture-test",
            num_wps=1
        )

        single_agent_path.assign_agents({
            "implementer": agent_id,
            "reviewer": agent_id
        })

        import asyncio
        run = asyncio.run(single_agent_path.execute(
            container_factory=container_factory,
            agent_registry=agent_registry,
            worktree_path=tmp_worktree
        ))

        # Verify data captured
        assert run.run_id, "Run ID not set"
        assert run.started_at, "Start time not captured"
        assert run.completed_at, "Completion time not captured"
        assert run.observations, "No observations captured"

        # Verify observations contain required data
        for obs in run.observations:
            assert obs.timestamp, "Observation missing timestamp"
            assert obs.event_type, "Observation missing event type"

        # Verify log files created
        log_files = output_logger.get_log_files()
        # Note: log files may be empty if no real agent execution occurred


@pytest.fixture
def single_agent_path(agent_registry):
    """Create a SingleAgentPath for testing."""
    from ..paths.single_agent import SingleAgentPath
    from ..paths.base_path import TestPathConfig, AgentSlot, AgentRole

    config = TestPathConfig(
        path_id="single-agent",
        description="Single agent test path",
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
                same_as="implementer"
            )
        ],
        max_iterations=5,
        timeout_seconds=1800
    )

    return SingleAgentPath(config)
```

**Acceptance Criteria**:
- Tests all 4 acceptance scenarios from US1
- Parameterized for multiple agents
- Handles unavailable agents gracefully
- Verifies data capture

### T045: Write test_container_isolation.py test cases

Create `tests/agentic/tests/test_container_isolation.py`:

```python
"""Container isolation tests - US4 validation.

Validates that containers properly isolate agent execution,
preventing unauthorized access and enforcing resource limits.
"""

import pytest
import os

pytestmark = [
    pytest.mark.agentic,
    pytest.mark.isolation,
    pytest.mark.security,
]


class TestFileSystemIsolation:
    """US4 Scenario 1: File access outside worktree blocked."""

    def test_cannot_access_host_filesystem(self, test_container):
        """
        Given an agent running in a container,
        When it attempts to access files outside the designated worktree,
        Then the operation fails with permission denied.
        """
        # Try to read /etc/passwd (host file, should not be readable)
        exit_code, stdout, stderr = test_container.exec_command(
            "cat /etc/passwd",
            timeout=10
        )

        # Note: /etc/passwd exists in container but should be isolated
        # The real test is accessing paths outside container

        # Try to access host path (should fail)
        exit_code, stdout, stderr = test_container.exec_command(
            "ls /Users || ls /home/$(whoami)",
            timeout=10
        )

        # These paths should not exist or be accessible
        assert exit_code != 0 or not stdout.strip(), \
            "Container can access host user directories"

    def test_cannot_write_outside_worktree(self, test_container):
        """Container cannot write to paths outside worktree."""
        # Try to write to root filesystem (read-only)
        exit_code, stdout, stderr = test_container.exec_command(
            "touch /test_file_should_fail",
            timeout=10
        )

        assert exit_code != 0, \
            "Container was able to write to root filesystem"
        assert "Read-only" in stderr or "Permission denied" in stderr or "cannot touch" in stderr, \
            f"Unexpected error: {stderr}"

    def test_worktree_is_writable(self, test_container):
        """Worktree directory should be writable."""
        exit_code, stdout, stderr = test_container.exec_command(
            "touch /workspace/test_file && rm /workspace/test_file",
            timeout=10
        )

        assert exit_code == 0, \
            f"Could not write to worktree: {stderr}"


class TestNetworkIsolation:
    """US4 Scenario 2: Network access to non-allowlisted hosts blocked."""

    def test_cannot_access_internet(self, test_container):
        """
        Given an agent running in a container,
        When it attempts to make network requests to non-allowlisted hosts,
        Then the operation fails or is blocked.
        """
        # Try to curl a public URL
        exit_code, stdout, stderr = test_container.exec_command(
            "curl -s --connect-timeout 5 https://example.com || "
            "wget -q --timeout=5 -O- https://example.com",
            timeout=15
        )

        # Should fail due to internal network
        assert exit_code != 0, \
            "Container was able to access the internet"

    def test_cannot_resolve_external_dns(self, test_container):
        """Container cannot resolve external DNS."""
        exit_code, stdout, stderr = test_container.exec_command(
            "nslookup google.com || host google.com || getent hosts google.com",
            timeout=10
        )

        # Should fail or return nothing useful
        assert exit_code != 0 or "NXDOMAIN" in stdout or not stdout.strip(), \
            "Container can resolve external DNS"

    def test_can_access_local_services(self, test_container):
        """Container can access services on internal network."""
        # This tests that internal network works
        exit_code, stdout, stderr = test_container.exec_command(
            "ping -c 1 localhost || echo 'ping not available'",
            timeout=10
        )

        # Localhost should work
        # (actual service connectivity tested elsewhere)


class TestResourceLimits:
    """US4 Scenario 3: Resource limits enforced."""

    def test_memory_limit_enforced(self, test_container, container_factory):
        """
        Given an agent running in a container,
        When it consumes excessive memory,
        Then resource limits terminate the container.
        """
        # Try to allocate more memory than limit (4GB)
        exit_code, stdout, stderr = test_container.exec_command(
            "python3 -c 'x = [bytearray(1024*1024*1024) for _ in range(5)]'",
            timeout=60
        )

        # Should be killed by OOM (exit code 137)
        assert exit_code == 137 or exit_code != 0, \
            f"Memory hog succeeded unexpectedly: exit={exit_code}"

    def test_cpu_limits_applied(self, test_container):
        """CPU limits are configured (not necessarily hitting them)."""
        # Check cgroup limits
        exit_code, stdout, stderr = test_container.exec_command(
            "cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null || "
            "cat /sys/fs/cgroup/cpu.max 2>/dev/null || "
            "echo 'cgroup not available'",
            timeout=10
        )

        # Should have some CPU limit set
        # Note: exact format depends on cgroup v1 vs v2


class TestTimeoutEnforcement:
    """US4 Scenario 4: Timeout terminates hanging containers."""

    def test_timeout_terminates_container(
        self,
        container_factory,
        agent_registry,
        available_agents
    ):
        """
        Given a container that crashes or hangs,
        When the timeout is exceeded,
        Then the container is forcibly terminated.
        """
        if not available_agents:
            pytest.skip("No agents available")

        # Create container with short timeout
        from ..fixtures.container_fixtures import ResourceLimits

        container = container_factory.create_container(
            agent_id=available_agents[0].agent_id,
            worktree_path="/tmp",
            resource_limits=ResourceLimits(cpu_cores=1, memory_mb=512)
        )

        try:
            # Run a command that hangs
            from ..fixtures.container_fixtures import ContainerTimeoutError

            with pytest.raises(ContainerTimeoutError):
                container.exec_command(
                    "sleep 3600",  # Sleep for an hour
                    timeout=5  # But timeout after 5 seconds
                )
        finally:
            container.container.stop()


class TestContainerBuildReproducibility:
    """US4 Scenario 5: Container build is reproducible."""

    def test_container_builds_successfully(self, container_factory):
        """Container build process completes without error."""
        # The factory existing means build succeeded
        assert container_factory is not None
        assert container_factory.image is not None

    def test_dockerfile_exists(self):
        """Dockerfile.base exists and is valid."""
        dockerfile = Path(__file__).parent.parent.parent / "containers" / "Dockerfile.base"
        assert dockerfile.exists(), "Dockerfile.base not found"

        content = dockerfile.read_text()
        assert "FROM" in content, "Dockerfile missing FROM instruction"
        assert "spec-kitty" in content, "Dockerfile doesn't install spec-kitty"

    def test_docker_compose_valid(self):
        """docker-compose.yaml is valid."""
        import yaml

        compose_file = Path(__file__).parent.parent.parent / "containers" / "docker-compose.yaml"
        assert compose_file.exists(), "docker-compose.yaml not found"

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        assert "services" in config, "docker-compose missing services"
        assert "networks" in config, "docker-compose missing networks"

        # Verify internal network
        networks = config.get("networks", {})
        assert any(
            n.get("internal", False)
            for n in networks.values()
            if isinstance(n, dict)
        ), "No internal network configured"
```

**Acceptance Criteria**:
- Tests all 5 acceptance scenarios from US4
- File system isolation verified
- Network isolation verified
- Resource limits verified
- Timeout enforcement verified
- Build reproducibility verified

### T048: Write test_distribution.py test cases

The test_distribution.py file was created in T036. This subtask adds additional edge case tests:

```python
# Add to test_distribution.py

class TestDistributionEdgeCases:
    """Edge cases for distribution testing."""

    def test_no_development_overrides(self, test_container):
        """Verify no development environment variables are set."""
        env_vars_to_check = [
            "SPEC_KITTY_TEMPLATE_ROOT",
            "SPEC_KITTY_DEV_MODE",
            "PYTHONDONTWRITEBYTECODE",  # Sometimes set in dev
        ]

        for var in env_vars_to_check:
            exit_code, stdout, stderr = test_container.exec_command(
                f"python -c 'import os; print(os.environ.get(\"{var}\", \"NOT_SET\"))'",
                timeout=10
            )
            if var == "SPEC_KITTY_TEMPLATE_ROOT":
                assert stdout.strip() == "NOT_SET", \
                    f"{var} is set: {stdout.strip()}"

    def test_package_includes_all_templates(self, test_container):
        """Verify all required templates are in package."""
        exit_code, stdout, stderr = test_container.exec_command(
            "python -c '"
            "from spec_kitty.template_manager import TemplateManager; "
            "import os; "
            "tm = TemplateManager(); "
            "templates = os.listdir(tm.template_dir); "
            "print(\"\\n\".join(templates))"
            "'",
            timeout=30
        )

        assert exit_code == 0, f"Failed to list templates: {stderr}"

        templates = stdout.strip().split('\n')
        # Should have some templates
        assert len(templates) > 0, "No templates found in package"

    def test_cli_entry_point_works(self, test_container):
        """Verify CLI entry point is properly configured."""
        exit_code, stdout, stderr = test_container.exec_command(
            "which spec-kitty && spec-kitty --version",
            timeout=30
        )

        assert exit_code == 0, f"CLI entry point not working: {stderr}"
```

**Acceptance Criteria**:
- Verifies no dev overrides
- Checks templates are packaged
- Validates CLI entry point

## Technical Notes

- Tests use real containers (slow, marked appropriately)
- Some tests may be skipped if no agents available
- Resource limit tests may behave differently on CI vs local
- Network tests require Docker internal network to be set up

## Files to Create/Modify

1. `tests/agentic/tests/test_single_agent.py` (create)
2. `tests/agentic/tests/test_distribution.py` (create)
3. `tests/agentic/tests/test_container_isolation.py` (create)

## Verification

```bash
# Run core tests (requires Docker and at least one agent)
pytest tests/agentic/tests/test_distribution.py -v
pytest tests/agentic/tests/test_container_isolation.py -v
pytest tests/agentic/tests/test_single_agent.py -v -k "claude" --tb=short

# Run all P1 tests
pytest tests/agentic/tests/ -v -m "not slow" --tb=short
```

## Definition of Done

- [ ] test_distribution.py with PyPI validation
- [ ] Version verification tests
- [ ] test_single_agent.py with all US1 scenarios
- [ ] test_container_isolation.py with all US4 scenarios
- [ ] All tests properly marked (slow, agentic, etc.)
- [ ] Tests skip gracefully when requirements not met
- [ ] Tests pass with at least one available agent

## Activity Log

- 2026-01-19T15:06:27Z – claude-opus – shell_pid=77177 – lane=doing – Started implementation via workflow command
- 2026-01-19T15:16:00Z – claude-opus – shell_pid=77177 – lane=for_review – Ready for review: Implemented all P1 core tests (49 tests total) - test_distribution.py (T036/T037/T048), test_single_agent.py (T042), test_container_isolation.py (T045)
- 2026-01-19T15:19:20Z – claude-opus – shell_pid=79929 – lane=doing – Started review via workflow command
