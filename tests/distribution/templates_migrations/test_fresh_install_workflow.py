"""Tests for fresh install workflow from distribution package.

This module tests the complete end-to-end workflow that a PyPI user
would experience: install spec-kitty, init, create feature, etc.

CRITICAL: These tests replicate the exact PyPI user experience without
any developer bypasses. They would have caught the 0.10.8 catastrophe.
"""

import pytest
from pathlib import Path
import subprocess
import json


@pytest.mark.distribution
@pytest.mark.slow
def test_fresh_install_init_workflow(installed_spec_kitty, tmp_path):
    """Test complete init workflow from fresh install.

    This test validates the most critical path: a user installs spec-kitty
    from PyPI and runs `spec-kitty init` for the first time.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    test_project = tmp_path / "fresh_project"
    test_project.mkdir()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=test_project, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=test_project,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=test_project,
        capture_output=True
    )

    # Clean environment - NO BYPASSES
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }
    # Explicitly verify no template bypass
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in env

    # Step 1: Init
    result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Fresh install init failed: {result.stderr}\n"
        "This is the PRIMARY failure mode from 0.10.8!"
    )

    # Verify .kittify directory created
    assert (test_project / ".kittify").exists(), (
        ".kittify directory not created"
    )

    # Verify mission selected (default or explicit)
    config_file = test_project / ".kittify" / "config.json"
    assert config_file.exists(), "config.json not created"

    config = json.loads(config_file.read_text())
    assert "mission" in config or "default_mission" in config, (
        "Mission not configured"
    )


@pytest.mark.distribution
@pytest.mark.slow
def test_fresh_install_create_feature(installed_spec_kitty, tmp_path):
    """Test creating a feature after fresh install."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    test_project = tmp_path / "feature_test_project"
    test_project.mkdir()

    # Setup git
    subprocess.run(["git", "init"], cwd=test_project, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=test_project,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=test_project,
        capture_output=True
    )

    # Clean environment
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }

    # Init first
    subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    # Create feature
    result = subprocess.run(
        [str(spec_kitty), "agent", "feature", "create-feature",
         "--mission", "software-dev", "test-feature"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Feature creation failed: {result.stderr}"
    )

    # Verify feature directory created
    feature_dir = test_project / "kitty-specs" / "001-test-feature"
    assert feature_dir.exists(), "Feature directory not created"

    # Verify spec.md created from template
    spec_file = feature_dir / "spec.md"
    assert spec_file.exists(), "spec.md not created"

    spec_content = spec_file.read_text()
    # Should have basic spec structure
    assert len(spec_content) > 100, "spec.md appears empty"
    # Should not have template placeholders
    assert "{{TEMPLATE_" not in spec_content, (
        "spec.md contains unreplaced template placeholders"
    )


@pytest.mark.distribution
def test_no_template_root_required(installed_spec_kitty, tmp_path):
    """Verify SPEC_KITTY_TEMPLATE_ROOT not required for operation.

    CRITICAL TEST: This is the EXACT failure from 0.10.8.
    All operations must work without the environment variable bypass.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    test_project = tmp_path / "no_bypass_project"
    test_project.mkdir()

    # Setup git
    subprocess.run(["git", "init"], cwd=test_project, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=test_project,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=test_project,
        capture_output=True
    )

    # Environment with NO bypass
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }
    # Double-check bypass NOT present
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in env, (
        "Test setup error: SPEC_KITTY_TEMPLATE_ROOT should not be set"
    )

    # Init should work without bypass
    result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"CRITICAL: Init failed without SPEC_KITTY_TEMPLATE_ROOT!\n"
        f"This is the 0.10.8 catastrophic failure.\n"
        f"Error: {result.stderr}"
    )

    # Verify init actually worked
    assert (test_project / ".kittify").exists(), (
        "Init claimed success but .kittify not created"
    )


@pytest.mark.distribution
@pytest.mark.slow
def test_version_command_works(installed_spec_kitty):
    """Verify --version command works from installed package."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"

    result = subprocess.run(
        [str(spec_kitty), "--version"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"--version command failed: {result.stderr}"
    )
    assert "spec-kitty" in result.stdout.lower(), (
        "Version output doesn't mention spec-kitty"
    )


@pytest.mark.distribution
@pytest.mark.slow
@pytest.mark.regression
def test_0_10_8_complete_workflow_regression(installed_spec_kitty, tmp_path):
    """Complete regression test for 0.10.8 catastrophic failure.

    This test replicates the EXACT workflow that 100% of PyPI users
    attempted and failed during 0.10.8-0.10.15:

    1. Install spec-kitty from PyPI (simulated by installed_spec_kitty)
    2. Initialize a new project
    3. Create a feature
    4. Verify templates accessible

    ALL steps must work without SPEC_KITTY_TEMPLATE_ROOT bypass.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    user_project = tmp_path / "real_user_project"
    user_project.mkdir()

    # Setup git (users would do this)
    subprocess.run(["git", "init"], cwd=user_project, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "realuser@example.com"],
        cwd=user_project,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Real User"],
        cwd=user_project,
        capture_output=True
    )

    # Exact PyPI user environment
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "user_home"),
    }

    # Step 1: Init (THIS FAILED IN 0.10.8)
    init_result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=user_project,
        env=env,
        capture_output=True,
        text=True
    )

    assert init_result.returncode == 0, (
        f"0.10.8 REGRESSION: Init failed!\n"
        f"Error: {init_result.stderr}\n"
        f"This is the catastrophic failure that affected 100% of PyPI users."
    )

    # Step 2: Create feature (also failed in 0.10.8)
    feature_result = subprocess.run(
        [str(spec_kitty), "agent", "feature", "create-feature",
         "--mission", "software-dev", "my-feature"],
        cwd=user_project,
        env=env,
        capture_output=True,
        text=True
    )

    assert feature_result.returncode == 0, (
        f"0.10.8 REGRESSION: Feature creation failed!\n"
        f"Error: {feature_result.stderr}"
    )

    # Step 3: Verify spec.md has content
    spec_file = user_project / "kitty-specs" / "001-my-feature" / "spec.md"
    assert spec_file.exists(), "spec.md not created"

    spec_content = spec_file.read_text()
    assert len(spec_content) > 500, (
        "spec.md too small - template may not have loaded"
    )

    # Step 4: Verify no placeholder leaks
    assert "{{" not in spec_content[:200], (
        "Template placeholders not replaced"
    )

    print("✅ Complete 0.10.8 regression test PASSED")
    print("   All PyPI user workflows function correctly")


@pytest.mark.distribution
def test_cli_accessible_in_path(installed_spec_kitty):
    """Verify spec-kitty command is in PATH after install."""
    venv_path, wheel_path, site_packages = installed_spec_kitty

    # Check spec-kitty binary exists
    spec_kitty_bin = venv_path / "bin" / "spec-kitty"
    assert spec_kitty_bin.exists(), (
        "spec-kitty command not installed in venv/bin"
    )
    assert spec_kitty_bin.is_file(), (
        "spec-kitty is not a file"
    )


@pytest.mark.distribution
def test_package_metadata_accessible(installed_spec_kitty):
    """Verify package metadata is accessible."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Check package can be imported
    result = subprocess.run(
        [str(python), "-c",
         "import specify_cli; print(specify_cli.__version__)"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to import specify_cli: {result.stderr}"
    )
    # Should have version string
    assert len(result.stdout.strip()) > 0, "No version string"
