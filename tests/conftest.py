"""
Shared pytest fixtures for spec-kitty functional tests
"""
import os
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def spec_kitty_repo_root():
    """
    Path to the spec-kitty repository being tested.

    Configuration precedence:
    1. SPEC_KITTY_REPO environment variable (absolute path)
    2. Default: ../spec-kitty relative to test directory

    Examples:
        export SPEC_KITTY_REPO=/absolute/path/to/spec-kitty
        export SPEC_KITTY_REPO=~/Code/spec-kitty
        export SPEC_KITTY_REPO=/tmp/spec-kitty-checkout
    """
    # Check environment variable first
    env_path = os.environ.get('SPEC_KITTY_REPO')

    if env_path:
        repo_path = Path(env_path).expanduser().resolve()
    else:
        # Default: sibling directory to spec-kitty-test
        repo_path = Path(__file__).parent.parent.parent / "spec-kitty"

    # Validate path exists
    if not repo_path.exists():
        raise FileNotFoundError(
            f"spec-kitty repository not found at {repo_path}\n\n"
            f"Please either:\n"
            f"  1. Set SPEC_KITTY_REPO environment variable:\n"
            f"     export SPEC_KITTY_REPO=/path/to/spec-kitty\n"
            f"  2. Clone spec-kitty to default location:\n"
            f"     git clone <repo-url> {repo_path}\n"
        )

    # Validate it's actually a spec-kitty repo
    if not (repo_path / 'src' / 'specify_cli').exists():
        raise ValueError(
            f"Directory {repo_path} exists but doesn't appear to be spec-kitty repository.\n"
            f"Expected to find src/specify_cli/ directory."
        )

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
