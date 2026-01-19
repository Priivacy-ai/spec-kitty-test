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


# Fixtures will be implemented in WP03 (container_fixtures, agent_fixtures)
# and WP05 (workflow_fixtures)
