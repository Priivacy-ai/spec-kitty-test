"""
Pytest Fixture Protocols for Comprehensive Test Suite

This module defines the protocols (interfaces) for pytest fixtures used throughout
the test suite. These are contracts that fixture implementations must follow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Callable
from datetime import datetime


class TestEnvironmentProtocol(Protocol):
    """Protocol for test environment fixtures.

    Implementations: tests/conftest.py (base), tests/functional/conftest.py,
                     tests/distribution/conftest.py
    """

    env_type: str  # "functional" | "distribution" | "integration"
    spec_kitty_path: Path
    test_repo_path: Path
    env_vars: dict[str, str]

    def run_command(self, *args: str, input_text: str | None = None) -> tuple[int, str, str]:
        """Run spec-kitty command in this environment.

        Returns: (exit_code, stdout, stderr)
        """
        ...


class MockAgentProtocol(Protocol):
    """Protocol for mock agent fixtures.

    Implementation: tests/functional/orchestrator/conftest.py
    """

    agent_id: str
    success_probability: float
    execution_delay: float
    output_pattern: str
    exit_code: int

    def invoke(self, prompt: str, workspace: Path) -> tuple[int, str, str]:
        """Simulate agent invocation.

        Returns: (exit_code, stdout, stderr)
        """
        ...


class TestFeatureProtocol(Protocol):
    """Protocol for test feature fixtures.

    Implementation: tests/conftest.py or tests/functional/conftest.py
    """

    feature_number: str
    slug: str
    mission: str
    wp_count: int
    dependency_graph: dict[str, list[str]]
    expected_artifacts: list[str]

    def create(self, project_path: Path) -> Path:
        """Create feature structure in project.

        Returns: Path to feature directory
        """
        ...


class StateSnapshotProtocol(Protocol):
    """Protocol for orchestration state snapshot fixtures.

    Implementation: tests/functional/orchestrator/conftest.py
    """

    timestamp: datetime
    wp_states: dict[str, str]
    agent_assignments: dict[str, str]
    execution_history: list[dict]

    def save(self, path: Path) -> None:
        """Save snapshot to orchestration-state.json"""
        ...

    def restore(self, path: Path) -> None:
        """Restore snapshot from orchestration-state.json"""
        ...


class VCSContextProtocol(Protocol):
    """Protocol for VCS testing context fixtures.

    Implementation: tests/functional/vcs_abstraction/conftest.py
    """

    vcs_type: str  # "git" | "jj" | "both"
    detection_override: dict[str, bool]
    command_log: list[tuple[str, list[str]]]
    feature_vcs_lock: str

    def start_logging(self) -> None:
        """Start logging subprocess commands"""
        ...

    def stop_logging(self) -> None:
        """Stop logging and return captured commands"""
        ...

    def assert_no_jj_commands(self) -> None:
        """Assert no jj commands were executed"""
        ...

    def assert_only_git_commands(self) -> None:
        """Assert only git commands were executed (no jj)"""
        ...


class DistributionPackageProtocol(Protocol):
    """Protocol for distribution package fixtures.

    Implementation: tests/distribution/conftest.py
    """

    package_path: Path
    version: str
    template_manifest: list[str]
    migration_list: list[str]
    installed_path: Path

    def install(self, venv_path: Path) -> None:
        """Install package in virtualenv"""
        ...

    def validate_templates(self) -> list[str]:
        """Validate all templates are present.

        Returns: List of missing templates (empty if valid)
        """
        ...

    def validate_migrations(self) -> list[str]:
        """Validate all migrations are registered.

        Returns: List of missing migrations (empty if valid)
        """
        ...


class ConflictScenarioProtocol(Protocol):
    """Protocol for merge conflict scenario fixtures.

    Implementation: tests/functional/data_loss/conftest.py
    """

    wp_modifications: dict[str, dict]
    conflict_type: str  # "code" | "status" | "frontmatter"
    expected_resolution: str | None
    auto_resolvable: bool

    def apply_to_feature(self, feature_path: Path) -> None:
        """Apply modifications to create conflict"""
        ...

    def validate_resolution(self, merged_content: str) -> bool:
        """Validate conflict was resolved correctly"""
        ...


class StalenessConfigProtocol(Protocol):
    """Protocol for staleness detection test config.

    Implementation: tests/functional/conftest.py
    """

    threshold_minutes: int
    wp_lane: str
    last_commit_time: datetime
    expected_stale_status: bool

    def create_wp_with_staleness(self, feature_path: Path, wp_id: str) -> Path:
        """Create WP with configured staleness.

        Returns: Path to WP worktree
        """
        ...


# Fixture factory type hints

TestEnvironmentFactory = Callable[[str], TestEnvironmentProtocol]
"""Factory that creates test environment with specified type."""

MockAgentFactory = Callable[[str, float], MockAgentProtocol]
"""Factory that creates mock agent with specified id and success probability."""

TestFeatureFactory = Callable[[int, dict[str, list[str]]], TestFeatureProtocol]
"""Factory that creates test feature with WP count and dependency graph."""

StateSnapshotFactory = Callable[[dict[str, str]], StateSnapshotProtocol]
"""Factory that creates state snapshot with specified WP states."""

VCSContextFactory = Callable[[str, dict[str, bool]], VCSContextProtocol]
"""Factory that creates VCS context with type and detection overrides."""

DistributionPackageFactory = Callable[[str], DistributionPackageProtocol]
"""Factory that builds distribution package for specified version."""

ConflictScenarioFactory = Callable[[str], ConflictScenarioProtocol]
"""Factory that creates conflict scenario of specified type."""

StalenessConfigFactory = Callable[[int, str, datetime], StalenessConfigProtocol]
"""Factory that creates staleness config with threshold, lane, and commit time."""


# Integration test specific protocols

class SpecKittyGitTestProtocol(Protocol):
    """Protocol for spec-kitty-git-test harness fixture.

    Implementation: tests/integration/conftest.py
    """

    harness_path: Path  # /Users/robert/Code/spec-kitty-git-test

    def reset(self) -> None:
        """Run cleanup-bookmarks.sh to reset state"""
        ...

    def orchestrate(self, feature: str) -> tuple[int, str, str]:
        """Run run-orchestrate.sh for feature.

        Returns: (exit_code, stdout, stderr)
        """
        ...

    def get_orchestration_state(self) -> dict:
        """Read .kittify/orchestration-state.json.

        Returns: Parsed orchestration state
        """
        ...

    def get_worktrees(self) -> list[Path]:
        """List all worktrees in .worktrees/.

        Returns: List of worktree paths
        """
        ...

    def validate_commits(self, wp_id: str) -> bool:
        """Validate WP worktree has commits.

        Returns: True if commits exist
        """
        ...


# Marker protocol (for type hints in tests)

class PytestMarkerProtocol(Protocol):
    """Protocol for pytest.mark decorators."""

    def __call__(self, func):
        """Decorate test function."""
        ...


# Export all protocols for type checking
__all__ = [
    "TestEnvironmentProtocol",
    "MockAgentProtocol",
    "TestFeatureProtocol",
    "StateSnapshotProtocol",
    "VCSContextProtocol",
    "DistributionPackageProtocol",
    "ConflictScenarioProtocol",
    "StalenessConfigProtocol",
    "SpecKittyGitTestProtocol",
    "TestEnvironmentFactory",
    "MockAgentFactory",
    "TestFeatureFactory",
    "StateSnapshotFactory",
    "VCSContextFactory",
    "DistributionPackageFactory",
    "ConflictScenarioFactory",
    "StalenessConfigFactory",
    "PytestMarkerProtocol",
]
