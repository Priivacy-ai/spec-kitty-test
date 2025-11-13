"""
Shared pytest fixtures for spec-kitty functional tests
"""
import os
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def spec_kitty_repo_root():
    """Path to the spec-kitty repository being tested"""
    repo_path = Path(__file__).parent.parent.parent / "spec-kitty"
    assert repo_path.exists(), f"spec-kitty repo not found at {repo_path}"
    return repo_path


@pytest.fixture(scope="session")
def spec_kitty_version(spec_kitty_repo_root):
    """Get the current git commit hash of spec-kitty repo"""
    import subprocess
    result = subprocess.run(
        ['git', 'log', '-1', '--format=%H'],
        cwd=spec_kitty_repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment for each test"""
    # Save original env
    original_env = os.environ.copy()

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)
