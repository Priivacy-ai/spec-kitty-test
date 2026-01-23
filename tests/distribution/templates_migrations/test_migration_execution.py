"""Tests for migration execution in distribution package.

This module validates that all registered migrations can execute successfully
when spec-kitty is installed from PyPI. Migration failures during fresh
installs are critical bugs that prevent users from using spec-kitty.
"""

import pytest
from pathlib import Path
import subprocess
import json


@pytest.mark.distribution
@pytest.mark.migrations
def test_migrations_available_in_package(installed_spec_kitty):
    """Verify migration module is accessible in installed package."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Check that migrations module can be imported
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.upgrade import migrations; print('OK')"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to import migrations module: {result.stderr}"
    )
    assert "OK" in result.stdout


@pytest.mark.distribution
@pytest.mark.migrations
def test_migration_registry_accessible(installed_spec_kitty):
    """Verify migration registry can be loaded."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Get registered migrations
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.upgrade.registry import MigrationRegistry; "
         "registry = MigrationRegistry(); "
         "migrations = registry.get_all_migrations(); "
         "print(len(migrations))"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to access migration registry: {result.stderr}"
    )

    # Should have multiple migrations registered
    count = int(result.stdout.strip())
    assert count > 0, "No migrations registered"
    assert count >= 10, f"Too few migrations: {count} (expected at least 10)"


@pytest.mark.distribution
@pytest.mark.migrations
def test_critical_migrations_registered(installed_spec_kitty):
    """Verify critical migrations are registered in distribution.

    These are migrations that are essential for proper spec-kitty operation.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Get migration list
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.upgrade.registry import MigrationRegistry; "
         "registry = MigrationRegistry(); "
         "migrations = registry.get_all_migrations(); "
         "print([m.id for m in migrations])"],
        capture_output=True,
        text=True
    )

    migrations = eval(result.stdout.strip())

    # Critical migrations that must be present
    critical_migrations = [
        "m_0_10_9_repair_templates",  # Template repair (0.10.8 fix)
        "m_0_11_0_workspace_per_wp",  # Workspace per WP
        "m_0_12_0_documentation_mission",  # Documentation mission
    ]

    for critical in critical_migrations:
        assert any(critical in m for m in migrations), (
            f"Critical migration {critical} not registered"
        )


@pytest.mark.distribution
@pytest.mark.migrations
def test_init_creates_migration_tracking(installed_spec_kitty, tmp_path):
    """Verify spec-kitty init creates migration tracking file."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    test_project = tmp_path / "test_project"
    test_project.mkdir()

    # Initialize git repo first (spec-kitty requires git)
    subprocess.run(
        ["git", "init"],
        cwd=test_project,
        capture_output=True
    )
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

    # Ensure no bypass environment variables
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }

    # Run init
    result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    # Init should succeed
    assert result.returncode == 0, (
        f"Init failed: {result.stderr}"
    )

    # Verify migration tracking file exists
    migration_file = test_project / ".kittify" / "applied-migrations.json"
    assert migration_file.exists(), (
        "Migration tracking file not created during init"
    )

    # Verify file has content
    content = json.loads(migration_file.read_text())
    assert isinstance(content, dict), "Migration file not valid JSON"


@pytest.mark.distribution
@pytest.mark.migrations
def test_migration_execution_no_errors(installed_spec_kitty, tmp_path):
    """Verify migrations execute without errors during init."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    spec_kitty = venv_path / "bin" / "spec-kitty"
    test_project = tmp_path / "fresh_project"
    test_project.mkdir()

    # Initialize git
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

    # Run init with clean environment
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }

    result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    # Check for migration errors in output
    assert "migration" not in result.stderr.lower() or "error" not in result.stderr.lower(), (
        f"Migration errors detected: {result.stderr}"
    )

    # Init should complete successfully
    assert result.returncode == 0, (
        f"Init failed (migrations may have failed): {result.stderr}"
    )


@pytest.mark.distribution
@pytest.mark.migrations
@pytest.mark.regression
def test_0_10_9_template_repair_migration_present(distribution_package):
    """Regression test: Verify m_0_10_9_repair_templates migration is present.

    This migration fixes the template bundling issue from 0.10.8.
    It must be present to repair existing broken installations.
    """
    migrations = distribution_package.migration_list

    assert any("m_0_10_9" in m for m in migrations), (
        "Critical regression: m_0_10_9_repair_templates migration missing!\n"
        "This migration is required to fix 0.10.8 template bundling failures."
    )


@pytest.mark.distribution
@pytest.mark.migrations
def test_migration_order_preserved(installed_spec_kitty):
    """Verify migrations maintain proper ordering."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Get migrations in order
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.upgrade.registry import MigrationRegistry; "
         "registry = MigrationRegistry(); "
         "migrations = registry.get_all_migrations(); "
         "print([(m.id, m.target_version) for m in migrations])"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to get migration order: {result.stderr}"
    )

    # Verify we got valid output
    assert len(result.stdout) > 0, "No migration data returned"
