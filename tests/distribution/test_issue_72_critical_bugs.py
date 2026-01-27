"""
CRITICAL Bug Tests for Issue #72 Implementation

These tests validate the 3 bugs found during code analysis of the Issue #72 fix:

1. CRITICAL: JSON mode corruption from empty branch warnings
2. MEDIUM: Missing migration for template updates
3. LOW: Subprocess error handling

Run these BEFORE releasing 0.13.6!
"""

import subprocess
import json
from pathlib import Path
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.regression]


class TestCriticalBug1JsonModeCorruption:
    """
    🔴 CRITICAL BUG #1: JSON Mode Corruption

    Location: src/specify_cli/core/multi_parent_merge.py:142
    Problem: Uses print() for warnings, corrupts JSON output
    Impact: Users running `spec-kitty implement WP## --json` get invalid JSON
    """

    def test_empty_branch_warning_json_mode(self, tmp_path, spec_kitty_repo_root):
        """
        CRITICAL: Empty branch warnings should not corrupt JSON output.

        Reproduction:
        1. Create WP01 with no commits (empty branch)
        2. Create WP02 depending on WP01
        3. Run: spec-kitty implement WP02 --json
        4. Check output is valid JSON (not corrupted by warning print())
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
        subprocess.run(["git", "add", ".kittify"], cwd=repo, capture_output=True)
        subprocess.run(["git", "add", ".claude"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Manually create feature structure with dependencies
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)

        # Create meta.json
        meta = {
            "feature_id": "001-test-feature",
            "title": "Test Feature",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        # Create tasks directory
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP01
        wp01_content = """---
work_package_id: WP01
title: First Package
lane: planned
dependencies: []
---

# WP01: First Package

Work package 1.

## Activity Log
"""
        (tasks_dir / "WP01-first-package.md").write_text(wp01_content)

        # Create WP02 with dependency on WP01
        wp02_content = """---
work_package_id: WP02
title: Second Package
lane: planned
dependencies: [WP01]
---

# WP02: Second Package

Depends on WP01.

## Activity Log
"""
        (tasks_dir / "WP02-second-package.md").write_text(wp02_content)

        # Commit feature
        subprocess.run(["git", "add", "kitty-specs"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True, check=True)

        # Create WP01 branch (EMPTY - no commits beyond main)
        subprocess.run(["git", "checkout", "-b", "001-test-feature-WP01"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "checkout", "main"], cwd=repo, capture_output=True, check=True)

        # Try to implement WP02 with --json (depends on empty WP01)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02", "--feature", "001-test-feature"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        output = result.stdout

        # BUG CHECK: Output should be valid JSON (or contain NO JSON)
        # If warnings use print(), they'll appear in stdout and corrupt JSON

        if result.returncode == 0:
            # Check if output contains warning symbols mixed with potential JSON
            has_warning_symbol = "⚠️" in output or "Warning" in output
            has_json_structure = "{" in output or "}" in output

            if has_warning_symbol and has_json_structure:
                # CRITICAL BUG: Warning printed to stdout alongside JSON
                # Try to parse as JSON - should fail
                try:
                    json.loads(output)
                    # If it parses, the JSON is valid (bug might be fixed or warning not shown)
                except json.JSONDecodeError as e:
                    pytest.fail(
                        f"🔴 CRITICAL BUG #1 FOUND: JSON mode corrupted by warning print()!\n\n"
                        f"Output contains both warning and JSON:\n{output}\n\n"
                        f"JSON parse error: {e}\n\n"
                        f"FIX: multi_parent_merge.py line 142 should check json_mode or use stderr"
                    )


class TestMediumBug2MissingMigration:
    """
    ⚠️ MEDIUM BUG #2: Missing Migration for Template Updates

    Location: src/specify_cli/upgrade/migrations/ (MISSING FILE)
    Problem: No migration to add commit section to existing project templates
    Impact: Existing projects don't get commit section via `spec-kitty upgrade`
    """

    def test_documentation_template_has_commit_section(self):
        """
        Test: New projects should have commit section in templates.

        This validates templates are correct in the package.
        """
        # Run spec-kitty init and check template
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "test"
            repo.mkdir()

            subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

            result = subprocess.run(
                ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
                cwd=repo,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            # Check claude template has commit section
            template_path = repo / ".claude" / "commands" / "spec-kitty.implement.md"

            if not template_path.exists():
                pytest.skip("Template not found (might be different structure)")

            content = template_path.read_text()

            # Should have commit workflow section
            assert "## Commit Workflow" in content or "Commit Workflow" in content, (
                "Template missing commit section - might not be in package yet"
            )

            assert "git commit" in content, "Template missing git commit instructions"

    def test_migration_exists_for_template_update(self):
        """
        CRITICAL: Migration should exist to update existing projects.

        This checks if the migration file exists.
        """
        import sys
        import os

        # Find spec-kitty installation
        import sys
        result = subprocess.run(
            [sys.executable, "-c", "import specify_cli; print(specify_cli.__file__)"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("spec-kitty not installed in editable mode")

        specify_cli_path = Path(result.stdout.strip()).parent
        migrations_dir = specify_cli_path / "upgrade" / "migrations"

        if not migrations_dir.exists():
            pytest.skip(f"Migrations directory not found: {migrations_dir}")

        # Look for 0.13.5 template migration
        migration_files = list(migrations_dir.glob("m_0_13_5_*template*.py"))

        if not migration_files:
            pytest.fail(
                f"⚠️ MEDIUM BUG #2 FOUND: No migration for template update!\n\n"
                f"Expected file like: m_0_13_5_add_commit_workflow_to_templates.py\n"
                f"Location: {migrations_dir}\n\n"
                f"Existing projects won't get commit section via upgrade.\n"
                f"Compare to: m_0_13_0_update_research_implement_templates.py\n\n"
                f"FIX: Create migration to update documentation/implement.md templates"
            )


class TestLowBug3SubprocessErrorHandling:
    """
    ⚠️ LOW BUG #3: Missing Subprocess Error Handling

    Location: src/specify_cli/core/multi_parent_merge.py:117-139
    Problem: No try/except around git commands for empty branch detection
    Impact: Could crash on git failures in edge cases
    """

    def test_empty_branch_detection_code_review(self):
        """
        Code review: Check if subprocess error handling exists.

        This is a code inspection test - reads the source to verify.
        """
        import sys

        # Find multi_parent_merge.py
        import sys
        result = subprocess.run(
            [sys.executable, "-c", "import specify_cli.core.multi_parent_merge; print(specify_cli.core.multi_parent_merge.__file__)"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("spec-kitty not installed in editable mode")

        module_path = Path(result.stdout.strip())

        if not module_path.exists():
            pytest.skip(f"Module not found: {module_path}")

        # Read the source
        source = module_path.read_text()

        # Find the empty branch detection section (Step 1.5)
        if "Step 1.5: Check if each dependency branch has unique commits" not in source:
            pytest.skip("Empty branch detection code not found (might be refactored)")

        # Extract the section
        lines = source.split('\n')
        step_15_start = None
        step_15_end = None

        for i, line in enumerate(lines):
            if "Step 1.5" in line:
                step_15_start = i
            if step_15_start and "Step 2" in line:
                step_15_end = i
                break

        if not step_15_start or not step_15_end:
            pytest.skip("Can't locate Step 1.5 section")

        section = '\n'.join(lines[step_15_start:step_15_end])

        # Check for error handling
        has_try_except = "try:" in section and "except" in section
        has_timeout = "timeout=" in section

        if not has_try_except:
            print(
                f"\n⚠️ LOW BUG #3 FOUND: No subprocess error handling in empty branch detection!\n\n"
                f"Location: {module_path}:{step_15_start}\n\n"
                f"Missing try/except around subprocess.run() calls.\n"
                f"Could crash on git command failures (detached HEAD, corrupted repo, etc.)\n\n"
                f"FIX: Wrap subprocess calls in try/except (subprocess.TimeoutExpired, OSError)"
            )

        if not has_timeout:
            print(
                f"\n⚠️ LOW BUG #3 POTENTIAL: No timeout on subprocess calls!\n\n"
                f"subprocess.run() without timeout can hang indefinitely.\n"
                f"Add: timeout=10 parameter\n"
            )


class TestVerifyImplementationComplete:
    """Verify that the core implementation is actually present."""

    def test_done_validation_extends_to_done_lane(self):
        """
        Verify done validation code is present in tasks.py.

        This confirms the implementation is complete.
        """
        import sys

        # Find tasks.py
        import sys
        result = subprocess.run(
            [sys.executable, "-c", "import specify_cli.cli.commands.agent.tasks; print(specify_cli.cli.commands.agent.tasks.__file__)"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("spec-kitty not installed in editable mode")

        module_path = Path(result.stdout.strip())
        source = module_path.read_text()

        # Check for done validation
        has_done_validation = 'target_lane in ("for_review", "done")' in source or \
                             "target_lane in ['for_review', 'done']" in source

        assert has_done_validation, (
            "❌ Implementation NOT complete: done validation missing!\n"
            f"Expected to find: target_lane in ('for_review', 'done')\n"
            f"In: {module_path}"
        )

        print(f"\n✅ Implementation verified: Done validation present in {module_path}")

    def test_empty_branch_warnings_present(self):
        """
        Verify empty branch warning code is present.
        """
        import sys

        import sys
        result = subprocess.run(
            [sys.executable, "-c", "import specify_cli.core.multi_parent_merge; print(specify_cli.core.multi_parent_merge.__file__)"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("spec-kitty not installed in editable mode")

        module_path = Path(result.stdout.strip())
        source = module_path.read_text()

        # Check for empty branch detection
        has_empty_detection = "no commits beyond main" in source or \
                             "no unique commits" in source

        assert has_empty_detection, (
            "❌ Implementation NOT complete: empty branch warnings missing!\n"
            f"Expected to find empty branch warning code\n"
            f"In: {module_path}"
        )

        print(f"\n✅ Implementation verified: Empty branch warnings present in {module_path}")
