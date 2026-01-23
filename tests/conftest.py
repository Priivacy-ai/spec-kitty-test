"""
Shared pytest fixtures for spec-kitty functional tests
"""
import os
import shutil
import subprocess
from pathlib import Path
import pytest


# =============================================================================
# Pytest Hooks for Markers and Auto-Skip (T001, T003, T004)
# =============================================================================

def pytest_configure(config):
    """Register custom markers for jj and distribution tests."""
    # Hardcode all markers from contracts/markers.py
    # (Don't try to import - sparse-checkout excludes kitty-specs/ in worktrees)
    MARKERS = {
        # Test tier markers
        "functional": "Fast functional tests with mocked dependencies (<10 min)",
        "integration": "Integration tests using real orchestration (adaptive timing)",
        "distribution": "Distribution tests validating PyPI user experience (no bypasses, <45 min)",

        # Feature area markers
        "orchestrator": "Tests for orchestrator system (state machine, agents, execution)",
        "vcs": "Tests for VCS abstraction (git/jj isolation, detection, factory)",
        "data_loss": "Tests for data loss prevention (cleanup, corruption, conflicts)",
        "templates": "Tests for template bundling and resolution",
        "migrations": "Tests for migration execution and registry",

        # Agent requirement markers
        "requires_agent": "Test requires specific agent to be installed (parametrized)",
        "requires_claude": "Test requires Claude Code agent",
        "requires_opencode": "Test requires OpenCode agent",
        "requires_codex": "Test requires GitHub Codex agent",
        "requires_copilot": "Test requires GitHub Copilot agent",
        "requires_gemini": "Test requires Google Gemini agent",

        # Test philosophy markers
        "adversarial": "Adversarial test designed to break spec-kitty with edge cases",
        "regression": "Regression test for previously discovered bugs",

        # Special requirement markers
        "jj": "Test requires jujutsu VCS (auto-skip if not installed)",
        "upgrade": "Test validates upgrade paths between versions",

        # Performance markers
        "slow": "Test takes >30 seconds (may be skipped for quick test runs)",
        "very_slow": "Test takes >2 minutes (skipped by default)",
    }

    for marker_name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{marker_name}: {description}")


def pytest_collection_modifyitems(config, items):
    """Auto-skip @pytest.mark.jj tests when jj is not installed (T003)."""
    if not _jj_is_available():
        skip_jj = pytest.mark.skip(reason="jj (jujutsu) not installed")
        for item in items:
            if "jj" in item.keywords:
                item.add_marker(skip_jj)


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
        # Default: prefer sibling to spec-kitty-test, with worktree awareness.
        # When running from a worktree, __file__ is under .worktrees/<wp>/...
        file_path = Path(__file__).resolve()
        worktrees_parent = next(
            (parent for parent in file_path.parents if parent.name == ".worktrees"),
            None
        )
        if worktrees_parent is not None:
            spec_kitty_test_root = worktrees_parent.parent
        else:
            spec_kitty_test_root = file_path.parent.parent.parent

        candidates = [
            spec_kitty_test_root / "spec-kitty",
            spec_kitty_test_root.parent / "spec-kitty",
        ]
        repo_path = next((path for path in candidates if path.exists()), candidates[0])

    # Validate path exists
    if not repo_path.exists():
        raise FileNotFoundError(
            f"spec-kitty repository not found at {repo_path}\n\n"
            f"Please either:\n"
            f"  1. Set SPEC_KITTY_REPO environment variable:\n"
            f"     export SPEC_KITTY_REPO=/path/to/spec-kitty\n"
            f"  2. Clone spec-kitty to default location (sibling to spec-kitty-test):\n"
            f"     git clone <repo-url> {repo_path}\n"
        )

    # Validate it's actually a spec-kitty repo
    if not (repo_path / 'src' / 'specify_cli').exists():
        raise ValueError(
            f"Directory {repo_path} exists but doesn't appear to be spec-kitty repository.\n"
            f"Expected to find src/specify_cli/ directory."
        )

    return repo_path


# =============================================================================
# jj (Jujutsu) VCS Fixtures (T002)
# =============================================================================

def _jj_is_available():
    """Return True if jj is installed and `jj --version` succeeds."""
    if shutil.which("jj") is None:
        return False
    try:
        result = subprocess.run(
            ["jj", "--version"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


@pytest.fixture(scope="session")
def jj_available():
    """Check if jj (jujutsu) is installed and functional.

    Returns:
        bool: True if jj is installed and `jj --version` succeeds, False otherwise.

    This is session-scoped for performance - jj availability is checked once per test run.

    Example:
        def test_something(jj_available):
            if not jj_available:
                pytest.skip("Test requires jj")
            # or use @pytest.mark.jj for automatic skipping
    """
    return _jj_is_available()


@pytest.fixture(scope="session")
def jj_version():
    """Get the installed jj version as a string, or None if not installed.

    Returns:
        str | None: Version string like "0.20.0", or None if jj not available.

    Example:
        def test_something(jj_version):
            if jj_version and jj_version >= "0.20.0":
                # Test jj 0.20+ feature
    """
    if shutil.which("jj") is None:
        return None
    try:
        result = subprocess.run(
            ["jj", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return None
        # Parse "jj 0.20.0" -> "0.20.0"
        output = result.stdout.strip()
        parts = output.split()
        return parts[-1] if parts else None
    except (subprocess.TimeoutExpired, OSError):
        return None


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


@pytest.fixture
def requires_v011(spec_kitty_version):
    """Skip test if spec-kitty < 0.11.0

    Use for tests that require workspace-per-WP features (v0.11.0+).

    Example:
        def test_implement_command(requires_v011):
            # This test only runs on v0.11.0+
    """
    if spec_kitty_version < (0, 11, 0):
        pytest.skip("Requires spec-kitty >= 0.11.0 (workspace-per-WP)")


@pytest.fixture
def requires_pre_v011(spec_kitty_version):
    """Skip test if spec-kitty >= 0.11.0

    Use for legacy tests that test single worktree per feature (< v0.11.0).

    Example:
        def test_legacy_worktree_creation(requires_pre_v011):
            # This test only runs on < v0.11.0
    """
    if spec_kitty_version >= (0, 11, 0):
        pytest.skip("Legacy test for spec-kitty < 0.11.0 (single worktree per feature)")


@pytest.fixture
def workspace_is_per_wp(spec_kitty_version):
    """Returns True if workspace-per-WP (v0.11.0+), False if legacy.

    Use for adaptive tests that need to test both versions.

    Example:
        def test_worktree_creation(workspace_is_per_wp):
            if workspace_is_per_wp:
                # Test spec-kitty implement WP01
            else:
                # Test legacy /spec-kitty.specify creates worktree
    """
    return spec_kitty_version >= (0, 11, 0)


@pytest.fixture
def requires_v010_12(spec_kitty_version):
    """Skip test if spec-kitty < 0.10.12

    Use for tests requiring Feature 011 (constitution packaging safety).

    Example:
        def test_packaging_safety(requires_v010_12):
            # This test only runs on v0.10.12+
    """
    if spec_kitty_version < (0, 10, 12):
        pytest.skip("Requires spec-kitty >= 0.10.12 (Feature 011: constitution packaging safety)")


# =============================================================================
# Version-Gating Utilities (T054 - TR-013)
# =============================================================================

def get_spec_kitty_version_string():
    """Get installed spec-kitty version as a string.

    Returns:
        str | None: Version string like "0.12.0", or None if not installed.
    """
    try:
        result = subprocess.run(
            ["spec-kitty", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return None
        # Parse "spec-kitty-cli version 0.12.0" or "spec-kitty 0.12.0" -> "0.12.0"
        output = result.stdout.strip()
        parts = output.split()
        return parts[-1] if parts else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def requires_spec_kitty_version(min_version):
    """Create a pytest marker that skips if spec-kitty version is below minimum.

    This is a function that returns a pytest marker, to be used as a decorator.

    Args:
        min_version: Minimum version string, e.g., "0.12.0"

    Returns:
        pytest marker that will skip the test if version requirement not met.

    Example:
        @requires_spec_kitty_version("0.12.0")
        @pytest.mark.jj
        def test_jj_feature_only_in_v012(spec_kitty_project):
            # This test only runs on spec-kitty 0.12.0+
            ...
    """
    from packaging import version

    current = get_spec_kitty_version_string()
    if current is None:
        return pytest.mark.skip(reason="spec-kitty not installed")
    try:
        if version.parse(current) < version.parse(min_version):
            return pytest.mark.skip(
                reason=f"Requires spec-kitty >= {min_version}, got {current}"
            )
    except version.InvalidVersion:
        return pytest.mark.skip(reason=f"Cannot parse spec-kitty version: {current}")

    # Version requirement met - return a no-op decorator
    # Using identity decorator pattern
    return lambda fn: fn


# Convenience markers for common versions (evaluated at import time)
requires_v0_11 = requires_spec_kitty_version("0.11.0")
requires_v0_12 = requires_spec_kitty_version("0.12.0")
requires_v0_13 = requires_spec_kitty_version("0.13.0")


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure clean environment for each test"""
    # Save original env
    original_env = os.environ.copy()

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Test Project Fixtures (T005, T006)
# =============================================================================

@pytest.fixture
def spec_kitty_project(tmp_path):
    """Create an isolated, initialized spec-kitty project for testing.

    This fixture creates a fresh git repository and initializes spec-kitty in it.
    Use this for tests that need a complete spec-kitty project environment.

    Returns:
        Path: Path to the initialized project directory.

    The project is automatically cleaned up after the test (via tmp_path).

    Example:
        def test_feature_creation(spec_kitty_project):
            result = subprocess.run(
                ["spec-kitty", "specify", "test-feature"],
                cwd=spec_kitty_project,
                capture_output=True
            )
            assert result.returncode == 0
    """
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Initialize git repository
    subprocess.run(
        ["git", "init"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Configure git user (required for commits)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Initialize spec-kitty (--here --force --ai for non-interactive mode)
    subprocess.run(
        ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    return project_dir


@pytest.fixture
def no_template_bypass(monkeypatch):
    """Ensure distribution tests run without SPEC_KITTY_TEMPLATE_ROOT bypass.

    CRITICAL: This fixture is essential for distribution tests. The 0.10.8
    catastrophe happened because tests used TEMPLATE_ROOT bypass while
    100% of PyPI users failed.

    Use this fixture for all tests in tests/distribution/ to validate
    the real user experience.

    Example:
        @pytest.mark.distribution
        def test_pypi_user_experience(no_template_bypass, tmp_path):
            # SPEC_KITTY_TEMPLATE_ROOT is NOT set
            # Test behaves like a real PyPI user
            ...
    """
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_REPO", raising=False)
    yield
    # Environment automatically restored by monkeypatch


@pytest.fixture(autouse=True)
def cleanup_dashboard_processes():
    """Kill any orphaned dashboard server processes after each test.

    This prevents zombie processes from accumulating during test runs.
    Dashboard servers spawned by tests should clean up, but if tests fail
    or are interrupted, we ensure cleanup happens regardless.
    """
    import subprocess
    import signal

    yield  # Run the test

    # After test, kill any dashboard server processes
    try:
        # Find and kill processes matching run_dashboard_server
        result = subprocess.run(
            ['pgrep', '-f', 'run_dashboard_server'],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass  # Process already dead or invalid PID
    except FileNotFoundError:
        pass  # pgrep not available on this system


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
