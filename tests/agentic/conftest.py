"""Pytest configuration and fixtures for agentic E2E testing.

This module provides the pytest fixtures required for running agentic
end-to-end tests against spec-kitty's multi-agent orchestrator.

Fixture Scopes:
- Session: Expensive operations like container image builds, agent registry,
           AgentInvoker, WorktreeManager, AgentDiscovery
- Function: Test isolation (individual containers, worktrees)

Key Fixtures:
- container_factory: Creates isolated Docker containers for agent execution
- agent_registry: Loads and validates agent configurations
- available_agents: List of agents that are installed and authenticated
- test_container: Function-scoped container for a single test
- tmp_worktree: Git-initialized temporary directory for testing
- workflow_validator: Validates WP lane transitions
- output_logger: Captures agent stdout/stderr
- transition_logger: Logs WP status transitions

Host-based Invocation Fixtures (WP06):
- worktree_manager: Session-scoped WorktreeManager for git isolation
- agent_invoker: Session-scoped AgentInvoker for subprocess management
- agent_discovery: Session-scoped AgentDiscovery with all registered configs
- host_available_agents: Available agents for host-based execution

Usage:
    pytest tests/agentic/ -v  # Run all agentic tests
    pytest tests/agentic/ -v -k "claude"  # Run tests for Claude agent
    pytest tests/agentic/ -v -m "single_agent"  # Run single-agent tests only

Note: These tests are excluded from default pytest runs because they:
- Require Docker (container-based) or agent CLIs (host-based)
- Make real API calls (costs money)
- Take significant time to complete
"""

import subprocess

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


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests for unavailable agents.

    T038: Add pytest markers for manual test triggering

    This hook runs after test collection and adds skip markers to tests
    that require agents which are not installed or authenticated.
    """
    from pathlib import Path
    from tests.agentic.fixtures.agent_fixtures import AgentRegistry

    # Load registry once for all items
    config_path = Path(__file__).parent / "config" / "agents.yaml"
    if config_path.exists():
        try:
            registry = AgentRegistry(config_path)
            available = {a.agent_id for a in registry.get_available_agents()}
        except Exception:
            available = set()
    else:
        available = set()

    # Mapping of marker names to agent IDs
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


# Fixtures from WP03, WP05, WP06, WP08, and WP09 are imported above


# =============================================================================
# Host-based Invocation Fixtures (WP06)
# =============================================================================


@pytest.fixture(scope="session")
def worktree_manager():
    """Session-scoped WorktreeManager that cleans up all worktrees.

    Provides git worktree isolation for host-based agent invocations.
    All worktrees are automatically cleaned up at end of session.

    Yields:
        WorktreeManager instance
    """
    import subprocess
    from tests.agentic.invoker.worktree_manager import WorktreeManager

    # Get repo root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    repo_root = result.stdout.strip()

    manager = WorktreeManager(repo_path=repo_root)
    yield manager
    # Cleanup all worktrees at end of session
    manager.remove_all()


@pytest.fixture(scope="session")
def agent_invoker(worktree_manager):
    """Session-scoped AgentInvoker for host-based execution.

    Provides subprocess management for invoking AI coding agents
    directly on the host machine without Docker containers.

    Args:
        worktree_manager: Session-scoped WorktreeManager

    Yields:
        AgentInvoker instance
    """
    from tests.agentic.invoker.agent_invoker import AgentInvoker

    invoker = AgentInvoker(
        worktree_manager=worktree_manager,
        default_timeout=1800.0,  # 30 minutes
        cleanup_on_exit=True,
    )
    yield invoker
    # Cleanup any remaining processes
    invoker.kill_all()


@pytest.fixture(scope="session")
def agent_discovery():
    """Session-scoped AgentDiscovery with all registered configs.

    Discovers which AI coding agents are installed and authenticated
    on the current machine, with caching for performance.

    Returns:
        AgentDiscovery instance with all 5 standard agent configs
    """
    from tests.agentic.invoker.discovery import AgentDiscovery
    from tests.agentic.agents import ALL_AGENT_CONFIGS

    discovery = AgentDiscovery(agent_configs=ALL_AGENT_CONFIGS)
    return discovery


@pytest.fixture
def host_available_agents(agent_discovery):
    """Return list of agent configs available for host-based execution.

    Uses AgentDiscovery to check which agents are installed
    and authenticated on this machine.

    Args:
        agent_discovery: Session-scoped AgentDiscovery

    Returns:
        List of BaseAgentConfig for available agents
    """
    discovered = agent_discovery.get_available()
    return [d.config for d in discovered]


@pytest.fixture
def host_available_agent_count(host_available_agents):
    """Return count of available agents for skip conditions.

    Args:
        host_available_agents: List of available agent configs

    Returns:
        Number of available agents
    """
    return len(host_available_agents)


# =============================================================================
# User Agent Config Fixtures (WP09)
# =============================================================================


@pytest.fixture
def agent_selection_config(host_available_agents, tmp_path):
    """Create AgentSelectionConfig for user-configurable agent selection.

    This fixture provides the user-configurable agent selection functionality.
    It uses the host_available_agents to populate available agents.

    Args:
        host_available_agents: List of available BaseAgentConfig
        tmp_path: pytest tmp_path for config file storage

    Returns:
        AgentSelectionConfig instance
    """
    from tests.agentic.agent_config import (
        AgentConfig,
        AgentSelectionConfig,
        STRATEGY_PREFERRED,
    )

    available_ids = [cfg.agent_id for cfg in host_available_agents]
    config_map = {cfg.agent_id: cfg for cfg in host_available_agents}

    user_config = AgentConfig(
        available_agents=available_ids,
        selection_strategy=STRATEGY_PREFERRED,
        preferred_implementer=available_ids[0] if available_ids else None,
        preferred_reviewer=available_ids[0] if available_ids else None,
    )

    return AgentSelectionConfig(
        config=user_config,
        agent_configs=config_map,
    )


@pytest.fixture
def saved_agent_config(host_available_agents, tmp_path):
    """Create and save AgentConfig to .kittify/config.yaml.

    This fixture simulates having run `spec-kitty init` with agent
    selection preferences.

    Args:
        host_available_agents: List of available BaseAgentConfig
        tmp_path: pytest tmp_path for config file storage

    Returns:
        Tuple of (AgentConfig, config_file_path)
    """
    from tests.agentic.agent_config import (
        AgentConfig,
        save_agent_config,
        STRATEGY_PREFERRED,
    )

    available_ids = [cfg.agent_id for cfg in host_available_agents]

    config = AgentConfig(
        available_agents=available_ids,
        selection_strategy=STRATEGY_PREFERRED,
        preferred_implementer=available_ids[0] if available_ids else None,
        preferred_reviewer=available_ids[1] if len(available_ids) > 1 else (available_ids[0] if available_ids else None),
    )

    config_path = save_agent_config(config, tmp_path)
    return config, config_path


def pytest_addoption(parser):
    """Add CLI options for agent selection overrides."""
    parser.addoption(
        "--impl-agent",
        action="store",
        default=None,
        help="Override implementation agent (e.g., --impl-agent claude-code)",
    )
    parser.addoption(
        "--implementer",
        action="store",
        default=None,
        help="Alias for --impl-agent",
    )
    parser.addoption(
        "--review-agent",
        action="store",
        default=None,
        help="Override review agent (e.g., --review-agent codex)",
    )
    parser.addoption(
        "--reviewer",
        action="store",
        default=None,
        help="Alias for --review-agent",
    )


@pytest.fixture
def impl_agent_override(request):
    """Get CLI override for implementation agent.

    Returns:
        Agent ID string or None if not specified
    """
    return request.config.getoption("--impl-agent") or request.config.getoption("--implementer")


@pytest.fixture
def review_agent_override(request):
    """Get CLI override for review agent.

    Returns:
        Agent ID string or None if not specified
    """
    return request.config.getoption("--review-agent") or request.config.getoption("--reviewer")


@pytest.fixture
def selected_implementer(agent_selection_config, impl_agent_override):
    """Get selected implementation agent respecting CLI overrides.

    This is the main fixture for tests that need an implementation agent.
    It respects both user config and CLI overrides.

    Args:
        agent_selection_config: AgentSelectionConfig fixture
        impl_agent_override: CLI override if specified

    Returns:
        Selected agent ID or None
    """
    return agent_selection_config.select_implementer(override=impl_agent_override)


@pytest.fixture
def selected_reviewer(agent_selection_config, review_agent_override, selected_implementer):
    """Get selected review agent respecting CLI overrides.

    This is the main fixture for tests that need a review agent.
    It respects both user config and CLI overrides, and handles
    the DIFFERENT_FROM constraint for cross-review tests.

    Args:
        agent_selection_config: AgentSelectionConfig fixture
        review_agent_override: CLI override if specified
        selected_implementer: Implementation agent ID (for DIFFERENT_FROM)

    Returns:
        Selected agent ID or None
    """
    return agent_selection_config.select_reviewer(
        override=review_agent_override,
        different_from=selected_implementer,
    )


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
