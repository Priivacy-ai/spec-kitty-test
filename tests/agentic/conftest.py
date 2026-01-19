"""Pytest configuration and fixtures for agentic E2E testing.

This module provides the pytest fixtures required for running agentic
end-to-end tests against spec-kitty's multi-agent orchestrator.

Fixture Scopes:
- Session: Expensive operations like container image builds, agent registry
- Function: Test isolation (individual containers, worktrees)

Key Fixtures (implemented in subsequent WPs):
- container_factory: Creates isolated Docker containers for agent execution
- agent_registry: Loads and validates agent configurations
- available_agents: List of agents that are installed and authenticated
- test_container: Function-scoped container for a single test
- tmp_worktree: Git-initialized temporary directory for testing
- workflow_validator: Validates WP lane transitions
- output_logger: Captures agent stdout/stderr
- transition_logger: Logs WP status transitions

Usage:
    pytest tests/agentic/ -v  # Run all agentic tests
    pytest tests/agentic/ -v -k "claude"  # Run tests for Claude agent
    pytest tests/agentic/ -v -m "single_agent"  # Run single-agent tests only

Note: These tests are excluded from default pytest runs because they:
- Require Docker
- Make real API calls (costs money)
- Take significant time to complete
"""

import pytest

# Import fixtures from fixtures module (WP03)
# These become available to all tests in tests/agentic/
from tests.agentic.fixtures.container_fixtures import (
    container_factory,
    test_container,
    tmp_worktree,
)
from tests.agentic.fixtures.agent_fixtures import (
    agent_config,
    agent_registry,
    available_agents,
    require_agent,
)

# Workflow fixtures (WP05)
from tests.agentic.fixtures.workflow_fixtures import (
    lane_monitor_factory,
    rejection_handler,
    test_feature_scaffold,
    test_run_factory,
    workflow_engine,
    workflow_validator,
)

# Observability fixtures (WP06)
from tests.agentic.fixtures.observability import (
    container_metrics_collector,
    git_state_capture,
    output_logger,
    post_mortem_exporter,
    transition_logger,
)

# Fault injection fixtures (WP08)
from tests.agentic.faults import (
    # Process faults
    ProcessFaultInjector,
    TimeoutFaultInjector,
    ProcessCrashInjector,
    # File faults
    FileFaultInjector,
    GitFaultInjector,
    PermissionFaultInjector,
    CorruptionType,
    # Auth faults
    AuthFaultInjector,
    AuthFaultType,
    CredentialType,
    # Resource faults
    ResourceFaultInjector,
    ResourceType,
    ExhaustionLevel,
    # Common types
    TriggerCondition,
)


def pytest_configure(config):
    """Register custom markers for agentic tests."""
    # Test categories
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

    # Test path markers
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


# Fixtures from WP03, WP05, WP06, and WP08 are imported above


# =============================================================================
# Fault Injection Fixtures (WP08)
# =============================================================================


@pytest.fixture
def process_fault_injector():
    """Create a ProcessFaultInjector for signal-based faults.

    Yields:
        ProcessFaultInjector instance

    Cleanup:
        Restores any stopped processes (SIGSTOP -> SIGCONT)
    """
    import signal

    injector = ProcessFaultInjector(signal_type=signal.SIGTERM)
    yield injector
    injector.restore()


@pytest.fixture
def timeout_fault_injector():
    """Create a TimeoutFaultInjector for delay simulation.

    Yields:
        TimeoutFaultInjector instance

    Cleanup:
        Unpauses any paused containers
    """
    injector = TimeoutFaultInjector(delay_type="artificial", delay_seconds=30.0)
    yield injector
    injector.restore()


@pytest.fixture
def crash_fault_injector():
    """Create a ProcessCrashInjector for crash simulation.

    Yields:
        ProcessCrashInjector instance
    """
    injector = ProcessCrashInjector(crash_type="exit_error", exit_code=1)
    yield injector


@pytest.fixture
def file_fault_injector(tmp_path):
    """Create a FileFaultInjector with temp backup directory.

    Args:
        tmp_path: pytest tmp_path fixture

    Yields:
        FileFaultInjector instance

    Cleanup:
        Restores corrupted files and cleans up backups
    """
    injector = FileFaultInjector(
        corruption_type=CorruptionType.RANDOM_BYTES,
        corruption_ratio=0.1,
        backup_dir=tmp_path / "fault_backups",
    )
    yield injector
    injector.restore()
    injector.cleanup()


@pytest.fixture
def git_fault_injector():
    """Create a GitFaultInjector for git-related faults.

    Yields:
        GitFaultInjector instance

    Cleanup:
        Restores git repository state
    """
    injector = GitFaultInjector(fault_type="merge_conflict")
    yield injector
    injector.restore()


@pytest.fixture
def permission_fault_injector():
    """Create a PermissionFaultInjector.

    Yields:
        PermissionFaultInjector instance

    Cleanup:
        Restores original file permissions
    """
    from tests.agentic.faults.file_faults import PermissionFault

    injector = PermissionFaultInjector(permission_fault=PermissionFault.READ_ONLY)
    yield injector
    injector.restore()


@pytest.fixture
def auth_fault_injector():
    """Create an AuthFaultInjector for credential faults.

    Yields:
        AuthFaultInjector instance

    Cleanup:
        Restores credentials from backup
    """
    injector = AuthFaultInjector(
        fault_type=AuthFaultType.CREDENTIAL_REMOVAL,
        credential_type=CredentialType.ANTHROPIC_API_KEY,
    )
    yield injector
    injector.restore()
    injector.cleanup()


@pytest.fixture
def resource_fault_injector(tmp_path):
    """Create a ResourceFaultInjector for resource exhaustion.

    Args:
        tmp_path: pytest tmp_path fixture

    Yields:
        ResourceFaultInjector instance

    Cleanup:
        Cleans up fill files and stops stress threads
    """
    injector = ResourceFaultInjector(
        resource_type=ResourceType.DISK,
        exhaustion_level=ExhaustionLevel.MODERATE,
    )
    yield injector
    injector.restore()


@pytest.fixture
def fault_injection_suite(
    process_fault_injector,
    timeout_fault_injector,
    file_fault_injector,
    git_fault_injector,
    auth_fault_injector,
    resource_fault_injector,
):
    """Provide all fault injectors as a combined fixture.

    This fixture is useful for tests that need access to multiple
    fault injection capabilities.

    Yields:
        Dict containing all fault injectors

    Cleanup:
        All individual injectors handle their own cleanup
    """
    return {
        "process": process_fault_injector,
        "timeout": timeout_fault_injector,
        "file": file_fault_injector,
        "git": git_fault_injector,
        "auth": auth_fault_injector,
        "resource": resource_fault_injector,
    }
