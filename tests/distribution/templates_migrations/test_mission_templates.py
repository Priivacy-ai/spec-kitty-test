"""Tests for mission template loading from distribution package.

This module validates that templates can be loaded using importlib.resources
from an installed package, without requiring SPEC_KITTY_TEMPLATE_ROOT bypass.

CRITICAL: The 0.10.8 failure occurred because templates were not accessible
via importlib.resources after installation. These tests prevent regression.
"""

import pytest
import subprocess
from pathlib import Path


@pytest.mark.distribution
@pytest.mark.templates
@pytest.mark.parametrize("mission", [
    "software-dev",
    "research",
    "documentation"
])
def test_mission_can_be_loaded(installed_spec_kitty, mission):
    """Verify mission object can be instantiated from installed package."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Try to load mission
    result = subprocess.run(
        [str(python), "-c",
         f"from specify_cli.mission import Mission; "
         f"m = Mission('{mission}'); "
         f"print(m.name)"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to load {mission} mission: {result.stderr}"
    )
    assert mission in result.stdout


@pytest.mark.distribution
@pytest.mark.templates
@pytest.mark.parametrize("mission,template", [
    ("software-dev", "spec-template.md"),
    ("software-dev", "plan-template.md"),
    ("software-dev", "tasks-template.md"),
    ("software-dev", "task-prompt-template.md"),
    ("research", "spec-template.md"),
    ("research", "plan-template.md"),
    ("research", "research-template.md"),
    ("documentation", "spec-template.md"),
    ("documentation", "plan-template.md"),
])
def test_mission_template_loading(installed_spec_kitty, mission, template):
    """Verify specific templates load from package."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Try to get template path
    result = subprocess.run(
        [str(python), "-c",
         f"from specify_cli.mission import Mission; "
         f"m = Mission('{mission}'); "
         f"template_path = m.get_template('{template}'); "
         f"print(template_path.exists())"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to load {mission}/{template}: {result.stderr}"
    )
    assert "True" in result.stdout, (
        f"Template {mission}/{template} does not exist"
    )


@pytest.mark.distribution
@pytest.mark.templates
def test_templates_have_actual_content(installed_spec_kitty):
    """Verify templates contain actual content, not just exist."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Load a template and check content
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.mission import Mission; "
         "m = Mission('software-dev'); "
         "template_path = m.get_template('spec-template.md'); "
         "content = template_path.read_text(); "
         "print(len(content))"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to read template content: {result.stderr}"
    )

    # Template should have substantial content
    content_length = int(result.stdout.strip())
    assert content_length > 100, (
        f"Template appears empty or too small: {content_length} bytes"
    )


@pytest.mark.distribution
@pytest.mark.templates
def test_templates_no_placeholder_leaks(installed_spec_kitty):
    """Verify templates don't have unreplaced placeholders.

    Templates should be processed during packaging, not contain raw
    placeholder strings that would confuse users.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Load spec template and check for placeholders
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.mission import Mission; "
         "m = Mission('software-dev'); "
         "template_path = m.get_template('spec-template.md'); "
         "content = template_path.read_text(); "
         "print(content)"],
        capture_output=True,
        text=True
    )

    template_content = result.stdout

    # These placeholder patterns should NOT appear in final templates
    bad_patterns = [
        "{{UNPROCESSED_",
        "${TEMPLATE_VAR}",
    ]

    for pattern in bad_patterns:
        assert pattern not in template_content, (
            f"Template contains unreplaced placeholder: {pattern}"
        )


@pytest.mark.distribution
@pytest.mark.templates
def test_no_template_root_required_for_loading(installed_spec_kitty, tmp_path):
    """Verify SPEC_KITTY_TEMPLATE_ROOT not required to load templates.

    CRITICAL: This is the exact failure mode from 0.10.8. Templates must
    be accessible via importlib.resources without environment bypasses.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Create clean environment WITHOUT template root bypass
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "fake_home"),
    }
    # Explicitly verify bypass variable NOT set
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in env

    # Try to load template
    result = subprocess.run(
        [str(python), "-c",
         "from specify_cli.mission import Mission; "
         "m = Mission('software-dev'); "
         "template_path = m.get_template('spec-template.md'); "
         "print('SUCCESS' if template_path.exists() else 'FAIL')"],
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"Failed to load template without SPEC_KITTY_TEMPLATE_ROOT: {result.stderr}\n"
        "This is the 0.10.8 catastrophic failure - templates not accessible from package!"
    )
    assert "SUCCESS" in result.stdout, (
        "Template loading failed without SPEC_KITTY_TEMPLATE_ROOT bypass"
    )


@pytest.mark.distribution
@pytest.mark.templates
@pytest.mark.regression
def test_0_10_8_regression_template_loading(installed_spec_kitty, tmp_path):
    """Regression test for 0.10.8 template loading failure.

    Context: Issues #62, #63, #64
    - 100% of PyPI users affected
    - 8+ releases (0.10.8-0.10.15) shipped with this bug
    - Templates were bundled but not accessible via importlib.resources

    This test validates the exact failure scenario is fixed.
    """
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    # Replicate exact PyPI user experience
    env = {
        "PATH": str(venv_path / "bin") + ":/usr/bin:/bin",
        "HOME": str(tmp_path / "test_home"),
    }

    # Try to use spec-kitty to load templates (as users would)
    test_project = tmp_path / "user_project"
    test_project.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=test_project, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "user@example.com"],
        cwd=test_project,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=test_project,
        capture_output=True
    )

    # Attempt init (which requires template loading)
    spec_kitty = venv_path / "bin" / "spec-kitty"
    result = subprocess.run(
        [str(spec_kitty), "init", "--here", "--force", "--ai", "claude"],
        cwd=test_project,
        env=env,
        capture_output=True,
        text=True
    )

    # This is what failed in 0.10.8 - templates not found
    assert result.returncode == 0, (
        f"CRITICAL REGRESSION: Init failed (0.10.8 behavior)!\n"
        f"Templates not accessible from installed package.\n"
        f"Error: {result.stderr}"
    )

    # Verify templates were actually used
    assert (test_project / ".kittify").exists(), (
        "Init succeeded but .kittify directory not created"
    )


@pytest.mark.distribution
@pytest.mark.templates
def test_divio_templates_accessible(installed_spec_kitty):
    """Verify documentation mission's divio subdirectory templates load."""
    venv_path, wheel_path, site_packages = installed_spec_kitty
    python = venv_path / "bin" / "python"

    divio_templates = [
        "divio/tutorial-template.md",
        "divio/howto-template.md",
        "divio/reference-template.md",
        "divio/explanation-template.md",
    ]

    for template in divio_templates:
        result = subprocess.run(
            [str(python), "-c",
             f"from specify_cli.mission import Mission; "
             f"m = Mission('documentation'); "
             f"template_path = m.get_template('{template}'); "
             f"print(template_path.exists())"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"Failed to load documentation/{template}: {result.stderr}"
        )
        assert "True" in result.stdout, (
            f"Template documentation/{template} not accessible"
        )
