"""
VCS abstraction distribution test fixtures (WP11: T062).

Provides fixtures for testing VCS abstraction from installed package.
"""
import pytest
import subprocess
from pathlib import Path
from typing import Generator, List
import os


class CommandLogger:
    """Logs all subprocess commands to detect VCS invocations."""

    def __init__(self):
        self.commands: List[str] = []
        self._original_run = subprocess.run

    def log_command(self, args, **kwargs):
        """Log command and pass through to real subprocess.run."""
        if args:
            cmd = args[0] if isinstance(args, list) else args
            self.commands.append(cmd)
        return self._original_run(args, **kwargs)

    def get_jj_invocations(self) -> List[str]:
        """Return all jj command invocations."""
        return [cmd for cmd in self.commands if 'jj' in str(cmd)]

    def has_jj_invocations(self) -> bool:
        """Check if any jj commands were invoked."""
        return len(self.get_jj_invocations()) > 0

    def clear(self):
        """Clear command log."""
        self.commands.clear()


@pytest.fixture
def command_logger(monkeypatch) -> Generator[CommandLogger, None, None]:
    """
    Fixture that logs all subprocess commands.

    Useful for verifying jj is never invoked during VCS operations.
    """
    logger = CommandLogger()

    # Patch subprocess.run to log commands
    def patched_run(*args, **kwargs):
        return logger.log_command(*args, **kwargs)

    monkeypatch.setattr(subprocess, 'run', patched_run)

    yield logger

    # Cleanup handled automatically by monkeypatch


@pytest.fixture
def broken_jj_binary(tmp_path) -> Path:
    """
    Create a broken jj binary for testing detection.

    Returns path to mock-bin directory to prepend to PATH.
    """
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()

    # Create jj that exits with error
    jj_binary = mock_bin / "jj"
    jj_binary.write_text("#!/bin/bash\nexit 1\n")
    jj_binary.chmod(0o755)

    return mock_bin


@pytest.fixture
def legacy_jj_feature(tmp_path) -> Path:
    """
    Create a feature directory with jj in meta.json.

    Simulates a feature created before jj rollback.
    """
    feature_dir = tmp_path / "kitty-specs" / "001-legacy-feature"
    feature_dir.mkdir(parents=True)

    # Create spec.md
    (feature_dir / "spec.md").write_text("# Legacy Feature\n")

    # Create meta.json with jj VCS
    meta_file = feature_dir / "meta.json"
    meta_file.write_text('{"vcs": "jj", "feature_number": "001"}')

    # Create tasks directory
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    return feature_dir


@pytest.fixture
def git_initialized_project(tmp_path) -> Path:
    """
    Create a git-initialized project directory.

    Returns path to project ready for spec-kitty init.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=project_dir,
        capture_output=True,
        check=True
    )

    # Set git config for commits
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

    return project_dir
