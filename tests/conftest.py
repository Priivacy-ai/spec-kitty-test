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
def spec_kitty_git_hash(spec_kitty_repo_root):
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


@pytest.fixture(scope="session")
def spec_kitty_version():
    """Get the installed spec-kitty semantic version as a tuple.

    Returns:
        tuple: Version as (major, minor, patch), e.g., (0, 8, 0)

    Example:
        def test_something(spec_kitty_version):
            if spec_kitty_version >= (0, 8, 0):
                # v0.8.0+ behavior
            else:
                # legacy behavior
    """
    import subprocess
    result = subprocess.run(
        ['spec-kitty', '--version'],
        capture_output=True,
        text=True,
        check=True
    )
    # Parse "spec-kitty-cli version 0.8.0" -> (0, 8, 0)
    version_str = result.stdout.strip().split()[-1]
    return tuple(map(int, version_str.split('.')))


@pytest.fixture
def requires_v08(spec_kitty_version):
    """Skip test if spec-kitty < 0.8.0

    Use for tests that require per-feature missions (v0.8.0+).

    Example:
        def test_per_feature_mission(requires_v08, temp_project_dir):
            # This test only runs on v0.8.0+
    """
    if spec_kitty_version < (0, 8, 0):
        pytest.skip("Requires spec-kitty >= 0.8.0 (per-feature missions)")


@pytest.fixture
def requires_pre_v08(spec_kitty_version):
    """Skip test if spec-kitty >= 0.8.0

    Use for legacy tests that test project-level missions (< v0.8.0).

    Example:
        def test_active_mission_symlink(requires_pre_v08, temp_project_dir):
            # This test only runs on < v0.8.0 (active-mission was removed)
    """
    if spec_kitty_version >= (0, 8, 0):
        pytest.skip("Legacy test for spec-kitty < 0.8.0 (active-mission removed)")


@pytest.fixture
def mission_is_per_feature(spec_kitty_version):
    """Returns True if missions are per-feature (v0.8.0+), False if per-project.

    Use for tests that need to adapt behavior based on version.

    Example:
        def test_mission_works(mission_is_per_feature, temp_project_dir):
            if mission_is_per_feature:
                # Check meta.json for mission
            else:
                # Check active-mission symlink
    """
    return spec_kitty_version >= (0, 8, 0)


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment for each test"""
    # Save original env
    original_env = os.environ.copy()

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


# Playwright Configuration
@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure Playwright browser launch options."""
    return {
        **browser_type_launch_args,
        "headless": True,  # Run headless for CI/CD
        "args": [
            "--disable-dev-shm-usage",  # Overcome limited resource problems
            "--no-sandbox",  # For containerized environments
            "--new-window",  # Open new windows instead of tabs
        ]
    }


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure Playwright browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.fixture
def isolated_page(browser):
    """
    Create a new browser context (window) for each test.

    This ensures:
    1. Each test gets a fresh window (not a tab in an existing window)
    2. The window is automatically closed when the test ends
    3. Complete isolation between tests (cookies, storage, etc.)

    Usage:
        def test_something(isolated_page):
            isolated_page.goto("http://localhost:8000")
            # Test runs in isolated window
        # Window automatically closed after test
    """
    context = browser.new_context()
    page = context.new_page()
    yield page
    # Cleanup: close page and context (window) after test
    page.close()
    context.close()
