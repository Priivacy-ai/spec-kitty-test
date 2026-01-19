"""Pytest fixtures for agentic E2E testing.

This module exports fixtures for:
- Container lifecycle management (container_fixtures.py - WP03)
- Agent configuration and detection (agent_fixtures.py - WP03)
- Workflow validation and scaffolding (workflow_fixtures.py - WP05)
- Fault injection utilities (fault_fixtures.py - WP08)
- Observability and logging (observability.py - WP06)

Fixtures are registered in conftest.py and available to all tests.
"""

# Container fixtures (WP03)
from .container_fixtures import (
    AgentContainerFactory,
    ContainerTimeoutError,
    ResourceLimits,
    TestContainer,
    container_factory,
    container_timeout,
    test_container,
    tmp_worktree,
)

# Agent fixtures (WP03)
from .agent_fixtures import (
    AgentConfig,
    AgentRegistry,
    InvocationPattern,
    agent_config,
    agent_registry,
    available_agents,
    require_agent,
    require_agents,
    skip_if_agent_unavailable,
)

__all__ = [
    # Container fixtures
    "AgentContainerFactory",
    "ContainerTimeoutError",
    "ResourceLimits",
    "TestContainer",
    "container_factory",
    "container_timeout",
    "test_container",
    "tmp_worktree",
    # Agent fixtures
    "AgentConfig",
    "AgentRegistry",
    "InvocationPattern",
    "agent_config",
    "agent_registry",
    "available_agents",
    "require_agent",
    "require_agents",
    "skip_if_agent_unavailable",
]
