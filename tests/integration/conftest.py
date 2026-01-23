"""
Integration test fixtures for real orchestration testing.

These fixtures provide access to the spec-kitty-git-test harness
and handle auto-skipping when the harness is not available.

T067: Integration test infrastructure setup.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest


# Harness path (external to test repo)
HARNESS_PATH = Path("/Users/robert/Code/spec-kitty-git-test")


def _harness_available() -> bool:
    """Check if spec-kitty-git-test harness is available."""
    return HARNESS_PATH.exists() and HARNESS_PATH.is_dir()


def _agent_available(agent: str) -> bool:
    """Check if specific agent is installed and available."""
    agent_commands = {
        "claude": ["claude", "--version"],
        "opencode": ["opencode", "--version"],
        "aider": ["aider", "--version"],
        "copilot": ["github-copilot-cli", "--version"],
    }

    cmd = agent_commands.get(agent)
    if not cmd:
        return False

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def spec_kitty_git_test():
    """
    Fixture providing access to spec-kitty-git-test harness.

    Auto-skips all tests if harness not available.
    """
    if not _harness_available():
        pytest.skip("spec-kitty-git-test harness not available")

    return HARNESS_PATH


@pytest.fixture
def reset_test_harness(spec_kitty_git_test):
    """
    Reset spec-kitty-git-test harness before test.

    Runs cleanup-bookmarks.sh to reset state.
    """
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"

    if not cleanup_script.exists():
        pytest.skip("cleanup-bookmarks.sh not found in harness")

    # Run cleanup
    result = subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.skip(f"Harness cleanup failed: {result.stderr}")

    yield spec_kitty_git_test

    # Optionally cleanup after test as well
    # subprocess.run(["bash", str(cleanup_script)], cwd=spec_kitty_git_test)


@pytest.fixture
def orchestration_state(spec_kitty_git_test):
    """
    Helper to read orchestration-state.json from harness.

    Returns parsed state or None if file doesn't exist.
    """
    state_file = spec_kitty_git_test / ".kittify" / "orchestration-state.json"

    def _read_state() -> Optional[dict]:
        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    return _read_state


@pytest.fixture
def harness_worktrees(spec_kitty_git_test):
    """
    Helper to list worktrees in harness.

    Returns list of worktree paths.
    """
    worktrees_dir = spec_kitty_git_test / ".worktrees"

    def _list_worktrees() -> list[Path]:
        if not worktrees_dir.exists():
            return []

        # Find all WP worktrees (feature/WPxx format)
        worktrees = []
        for feature_dir in worktrees_dir.iterdir():
            if feature_dir.is_dir():
                for wp_dir in feature_dir.iterdir():
                    if wp_dir.is_dir():
                        worktrees.append(wp_dir)

        return worktrees

    return _list_worktrees


@pytest.fixture
def run_orchestration(spec_kitty_git_test):
    """
    Helper to run orchestration in harness.

    Returns function that runs spec-kitty orchestrate command.
    """
    def _orchestrate(feature: str, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
        """
        Run orchestration for feature.

        Args:
            feature: Feature slug or number
            *args: Additional arguments to orchestrate command
            timeout: Timeout in seconds (default 5 minutes)

        Returns:
            CompletedProcess with result
        """
        cmd = ["spec-kitty", "orchestrate", feature] + list(args)

        try:
            result = subprocess.run(
                cmd,
                cwd=spec_kitty_git_test,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            # Return a fake completed process for timeout
            result = subprocess.CompletedProcess(
                cmd,
                returncode=-1,
                stdout="",
                stderr="Orchestration timed out"
            )

        return result

    return _orchestrate


@pytest.fixture
def validate_wp_commits(spec_kitty_git_test):
    """
    Helper to validate commits in WP worktree.

    Returns function that checks if WP has commits.
    """
    def _validate_commits(feature: str, wp_id: str) -> bool:
        """
        Check if WP worktree has commits.

        Args:
            feature: Feature slug
            wp_id: Work package ID (e.g., "WP01")

        Returns:
            True if commits exist, False otherwise
        """
        worktree_path = (
            spec_kitty_git_test / ".worktrees" / feature / wp_id
        )

        if not worktree_path.exists():
            return False

        # Check git log
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        # Has commits if log has output
        return len(result.stdout.strip()) > 0

    return _validate_commits


@pytest.fixture
def create_test_feature(spec_kitty_git_test, reset_test_harness):
    """
    Helper to create minimal test feature in harness.

    Returns function that creates feature structure.
    """
    created_features = []

    def _create_feature(
        feature_number: str,
        feature_slug: str,
        wp_count: int = 3
    ) -> Path:
        """
        Create test feature with specified WPs.

        Args:
            feature_number: Feature number (e.g., "001")
            feature_slug: Feature slug (e.g., "001-test-feature")
            wp_count: Number of work packages to create

        Returns:
            Path to created feature directory
        """
        feature_dir = (
            spec_kitty_git_test / "kitty-specs" / feature_slug
        )
        feature_dir.mkdir(parents=True, exist_ok=True)
        created_features.append(feature_dir)

        # Create meta.json
        meta = {
            "feature_number": feature_number,
            "slug": feature_slug,
            "vcs": "git",
            "created_at": "2026-01-23T00:00:00Z"
        }

        (feature_dir / "meta.json").write_text(
            json.dumps(meta, indent=2)
        )

        # Create spec.md
        (feature_dir / "spec.md").write_text(f"""# Test Feature: {feature_slug}

## User Story
Test feature for integration testing.

## Requirements
- FR-001: Basic functionality
""")

        # Create plan.md
        (feature_dir / "plan.md").write_text("""# Implementation Plan

Basic test plan.
""")

        # Create tasks directory and prompts
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        for i in range(1, wp_count + 1):
            wp_id = f"WP{i:02d}"
            prompt_file = tasks_dir / f"{wp_id}-test-wp.md"

            prompt_file.write_text(f"""---
work_package_id: "{wp_id}"
subtasks: ["T{i:03d}"]
lane: "planned"
---

# Test Work Package {wp_id}

Simple test implementation task.

## Objective
Create test file for validation.

## Steps
1. Create test file
2. Add basic content
3. Commit changes
""")

        return feature_dir

    yield _create_feature

    # Cleanup created features after tests
    for feature_dir in created_features:
        if feature_dir.exists():
            shutil.rmtree(feature_dir, ignore_errors=True)


@pytest.fixture
def detect_available_agents():
    """
    Detect which agents are installed on the system.

    Returns function that returns list of available agent names.
    """
    def _detect() -> list[str]:
        """
        Detect available agents.

        Returns:
            List of agent names (e.g., ["claude", "opencode"])
        """
        agents = []
        for agent in ["claude", "opencode", "aider", "copilot"]:
            if _agent_available(agent):
                agents.append(agent)
        return agents

    return _detect


# Custom markers for agent-specific tests
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "orchestrator: mark test as orchestrator-specific"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (>30s)"
    )
    config.addinivalue_line(
        "markers", "requires_agent(agent): mark test as requiring specific agent"
    )


def pytest_runtest_setup(item):
    """Skip tests that require agents not installed."""
    for marker in item.iter_markers(name="requires_agent"):
        agent = marker.args[0]
        if not _agent_available(agent):
            pytest.skip(f"Agent '{agent}' not installed")
