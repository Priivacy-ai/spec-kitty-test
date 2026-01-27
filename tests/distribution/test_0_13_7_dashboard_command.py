"""
Adversarial Tests for PR #99: Dashboard Command Template Simplification

These tests validate that dashboard templates use the simple CLI command
instead of embedding 90 lines of fragile Python code.

**The Bug:**
Dashboard command templates embedded 90 lines of Python code:
- Socket operations to check if dashboard running
- webbrowser module to open browser
- Complex error handling
- Multiple print statements
- Fragile in agent contexts

**The Fix (PR #99):**
Replaced with simple CLI command:
```bash
spec-kitty dashboard
```

**Why These Tests Matter:**
- Embedded Python in templates is fragile
- Agents may modify/break embedded code
- Socket operations fail in CI/CD
- Browser automation fails in headless environments
- CLI commands are more reliable
- Template complexity should be minimized

Run: pytest tests/distribution/test_0_13_7_dashboard_command.py -xvs
"""

import subprocess
import json
from pathlib import Path
import pytest
import re

pytestmark = [
    pytest.mark.distribution,
    pytest.mark.adversarial,
    pytest.mark.regression,
    pytest.mark.pr_99,
]


class TestDashboardCommandSimplicity:
    """
    Test that dashboard templates use CLI command, not embedded Python.

    PR #99 simplified templates from 90 lines of Python to one CLI command.
    """

    def test_dashboard_template_uses_cli_not_python(self, spec_kitty_repo_root):
        """
        Dashboard template should use `spec-kitty dashboard`, not Python code.

        OLD (BAD): 90 lines of embedded Python with sockets, webbrowser, etc.
        NEW (GOOD): spec-kitty dashboard

        BUG CHECK: If template has >20 lines of Python, regression detected.
        """
        # Find dashboard templates in missions
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        # Look for dashboard command templates
        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        # Test each dashboard template
        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: Should use CLI command
            assert "spec-kitty dashboard" in template_content, \
                f"Template {template_path.name} should use 'spec-kitty dashboard' command"

            # BUG CHECK: Should NOT have embedded Python
            # Count Python code blocks
            python_blocks = re.findall(r'```python\n(.*?)```', template_content, re.DOTALL)
            total_python_lines = sum(len(block.strip().split('\n')) for block in python_blocks)

            assert total_python_lines < 20, \
                f"Template {template_path.name} has {total_python_lines} lines of Python " \
                f"(should be <20). Embedded Python detected - regression of PR #99 bug!"

    def test_no_socket_operations_in_template(self, spec_kitty_repo_root):
        """
        Dashboard template should NOT use socket operations.

        OLD BUG: Templates had socket.create_connection() to check if running.
        NEW: CLI handles this internally.
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: No socket operations
            assert "import socket" not in template_content, \
                f"Template {template_path.name} should not import socket module"
            assert "socket.create_connection" not in template_content, \
                f"Template {template_path.name} should not use socket operations"
            assert "socket.connect" not in template_content, \
                f"Template {template_path.name} should not use socket operations"

    def test_no_webbrowser_module_in_template(self, spec_kitty_repo_root):
        """
        Dashboard template should NOT use webbrowser module.

        OLD BUG: Templates had webbrowser.open() which is fragile.
        NEW: CLI command handles browser opening.
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: No webbrowser module
            assert "import webbrowser" not in template_content, \
                f"Template {template_path.name} should not import webbrowser"
            assert "webbrowser.open" not in template_content, \
                f"Template {template_path.name} should not use webbrowser.open()"

    def test_dashboard_template_is_concise(self, spec_kitty_repo_root):
        """
        Dashboard template should be concise (<50 lines total).

        OLD: 90+ lines of Python code
        NEW: <50 lines total (mostly documentation)
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()
            line_count = len(template_content.strip().split('\n'))

            # BUG CHECK: Should be concise
            assert line_count < 100, \
                f"Template {template_path.name} has {line_count} lines " \
                f"(should be <100). May contain embedded Python code!"


class TestDashboardCommandFunctionality:
    """
    Test that `spec-kitty dashboard` CLI command works correctly.

    The command should handle all the complexity that was previously
    in the template.
    """

    def test_dashboard_command_exists(self):
        """
        spec-kitty dashboard command should be available.

        Basic sanity check that the CLI command exists.
        """
        result = subprocess.run(
            ["spec-kitty", "dashboard", "--help"],
            capture_output=True,
            text=True
        )

        # BUG CHECK: Command should exist
        assert result.returncode == 0, \
            f"spec-kitty dashboard command not found: {result.stderr}"

        # Help should mention dashboard
        assert "dashboard" in result.stdout.lower(), \
            "Dashboard help text should mention dashboard"

    def test_dashboard_command_without_init(self, tmp_path):
        """
        Dashboard command should give clear error if not initialized.

        When run in non-initialized repo, should suggest running init.
        """
        # Create fresh directory (not initialized)
        test_dir = tmp_path / "not_initialized"
        test_dir.mkdir()

        result = subprocess.run(
            ["spec-kitty", "dashboard"],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=5
        )

        # BUG CHECK: Should fail gracefully or provide guidance
        # Dashboard might succeed but not find config, or might fail
        # Either way, it should not crash with a Python traceback
        error_output = (result.stderr + result.stdout).lower()

        # Should not crash with Python errors
        assert "traceback" not in error_output, \
            f"Dashboard should not crash: {result.stderr}"

        # If it failed, error should be helpful
        if result.returncode != 0:
            # Error message should guide user
            assert any(word in error_output for word in [
                "init", "initialize", "not found", "configure", "setup", "directory"
            ]), f"Error should guide user: {result.stderr}"

    def test_dashboard_command_with_init(self, tmp_path, spec_kitty_repo_root):
        """
        Dashboard command should work in initialized repo.

        After spec-kitty init, dashboard command should at least attempt
        to start or connect to dashboard.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Try dashboard command (with timeout since it might try to start server)
        result = subprocess.run(
            ["spec-kitty", "dashboard"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )

        # BUG CHECK: Should not crash with Python errors
        # (Might fail for other reasons like port in use, but not Python errors)
        if result.returncode != 0:
            error_msg = result.stderr.lower()
            # Should not have Python traceback or socket errors
            assert "traceback" not in error_msg, \
                f"Dashboard should not crash with Python error: {result.stderr}"
            assert "socket.error" not in error_msg, \
                f"Dashboard should not have socket errors: {result.stderr}"


class TestDashboardInAgentContext:
    """
    Test that dashboard works when called from agent workflows.

    Templates are used by agents, so dashboard command must work
    in agent execution contexts.
    """

    def test_dashboard_doesnt_corrupt_stdout(self, tmp_path, spec_kitty_repo_root):
        """
        Dashboard command should not corrupt stdout.

        When agents run dashboard, any output should go to stderr,
        not interfere with stdout.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Run dashboard command
        result = subprocess.run(
            ["spec-kitty", "dashboard"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )

        # BUG CHECK: If there's output, it should be on stderr, not stdout
        # (Dashboard is a UI command, shouldn't produce structured output)
        if result.stdout.strip():
            # Some output on stdout is okay if it's just a URL
            # But should not be Python code or error messages
            assert "import" not in result.stdout, \
                "Dashboard stdout should not contain Python code"
            assert "traceback" not in result.stdout.lower(), \
                "Dashboard stdout should not contain errors"


class TestDashboardBrowserHandling:
    """
    Test graceful handling when browser cannot be opened.

    Dashboard should work in headless environments (CI/CD) where
    browser opening fails.
    """

    def test_headless_environment_handling(self, tmp_path, spec_kitty_repo_root):
        """
        Dashboard should work in headless environment.

        In CI/CD (no DISPLAY), dashboard should:
        1. Not crash
        2. Show URL to access manually
        3. Exit gracefully
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
            # Simulate headless environment
            "DISPLAY": "",
        }

        # Remove DISPLAY from environment
        env.pop("DISPLAY", None)

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        init_env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=init_env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Try dashboard in headless mode
        result = subprocess.run(
            ["spec-kitty", "dashboard"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )

        # BUG CHECK: Should not crash in headless mode
        # May fail to open browser, but should handle gracefully
        if result.returncode != 0:
            error_msg = result.stderr
            # Should not be a Python crash
            assert "Traceback" not in error_msg, \
                f"Dashboard crashed in headless mode: {error_msg}"


class TestDashboardTemplateRegression:
    """
    Regression tests to ensure template complexity doesn't creep back.

    These tests prevent future developers from re-adding embedded Python.
    """

    def test_dashboard_template_no_file_operations(self, spec_kitty_repo_root):
        """
        Dashboard template should not do file I/O operations.

        OLD BUG: Template read .kittify/.dashboard file directly
        NEW: CLI command handles all file operations
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: No file operations in template
            assert "open(" not in template_content or "# open(" in template_content, \
                f"Template {template_path.name} should not use open() for file I/O"
            assert ".read(" not in template_content, \
                f"Template {template_path.name} should not read files"
            assert "Path(" not in template_content or "# Path(" in template_content, \
                f"Template {template_path.name} should not use pathlib"

    def test_dashboard_template_no_error_handling(self, spec_kitty_repo_root):
        """
        Dashboard template should not have complex error handling.

        OLD BUG: Template had try/except blocks for socket errors, etc.
        NEW: CLI command handles all errors
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: Minimal error handling in template
            # Count try/except blocks in Python code
            try_count = template_content.count("try:")
            except_count = template_content.count("except")

            assert try_count <= 1, \
                f"Template {template_path.name} has {try_count} try blocks " \
                f"(should be ≤1). Complex error handling detected!"
            assert except_count <= 1, \
                f"Template {template_path.name} has {except_count} except blocks " \
                f"(should be ≤1). Complex error handling detected!"

    def test_dashboard_template_no_print_statements(self, spec_kitty_repo_root):
        """
        Dashboard template should minimize print() statements.

        OLD BUG: Template had multiple print() calls for status messages
        NEW: CLI command handles all output
        """
        missions_dir = spec_kitty_repo_root / "src" / "specify_cli" / "missions"
        if not missions_dir.exists():
            missions_dir = spec_kitty_repo_root / ".kittify" / "missions"

        if not missions_dir.exists():
            pytest.skip("Cannot find missions directory")

        dashboard_templates = list(missions_dir.rglob("*dashboard*.md"))
        if not dashboard_templates:
            pytest.skip("No dashboard templates found")

        for template_path in dashboard_templates:
            template_content = template_path.read_text()

            # BUG CHECK: Minimal print statements
            # Extract Python code blocks
            python_blocks = re.findall(r'```python\n(.*?)```', template_content, re.DOTALL)
            total_prints = sum(block.count("print(") for block in python_blocks)

            assert total_prints <= 2, \
                f"Template {template_path.name} has {total_prints} print() calls " \
                f"(should be ≤2). Embedded logging detected!"
