"""
Orchestrator distribution test fixtures (WP11: T062).

Provides fixtures for testing orchestrator from installed package.
"""
import pytest
import subprocess
from pathlib import Path
from typing import Generator
import json


@pytest.fixture
def mock_agent_binary(tmp_path) -> Path:
    """
    Create a mock agent binary for testing detection.

    Returns path to mock-bin directory to prepend to PATH.
    """
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()

    # Create mock claude-code that succeeds
    claude_binary = mock_bin / "claude"
    claude_binary.write_text("""#!/bin/bash
echo "Claude Code Mock Agent"
exit 0
""")
    claude_binary.chmod(0o755)

    return mock_bin


@pytest.fixture
def broken_agent_binary(tmp_path) -> Path:
    """
    Create a broken agent binary for testing graceful handling.

    Returns path to mock-bin directory.
    """
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()

    # Create broken claude that crashes
    claude_binary = mock_bin / "claude"
    claude_binary.write_text("#!/bin/bash\nexit 1\n")
    claude_binary.chmod(0o755)

    return mock_bin


@pytest.fixture
def git_project_with_kitty_specs(tmp_path) -> Path:
    """
    Create a git project with kitty-specs for orchestration testing.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Initialize git
    subprocess.run(
        ["git", "init"],
        cwd=project_dir,
        capture_output=True,
        check=True
    )

    # Git config
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project_dir,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        capture_output=True
    )

    # Create kitty-specs structure
    kitty_specs = project_dir / "kitty-specs"
    kitty_specs.mkdir()

    # Create a feature
    feature_dir = kitty_specs / "001-test-feature"
    feature_dir.mkdir()

    (feature_dir / "spec.md").write_text("# Test Feature\n")
    (feature_dir / "meta.json").write_text(json.dumps({
        "vcs": "git",
        "feature_number": "001"
    }))

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    # Create a WP
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text("""---
work_package_id: WP01
title: Test WP
lane: planned
dependencies: []
---

# Test WP
""")

    # Initial commit
    subprocess.run(
        ["git", "add", "-A"],
        cwd=project_dir,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        capture_output=True
    )

    return project_dir


@pytest.fixture
def agents_config(tmp_path) -> Path:
    """
    Create an agents config file for testing.
    """
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir()

    agents_file = config_dir / "agents.yaml"
    agents_file.write_text("""agents:
  priorities:
    - claude-code
    - opencode
    - codex
  timeout: 300
""")

    return agents_file
