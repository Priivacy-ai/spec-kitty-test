"""
Adversarial Edge Case Tests for 0.13.7 Release

These tests cover edge cases and ensure the three bugs fixed in 0.13.7
don't regress in future releases.

**Bugs Covered:**
1. PR #111 - Hyphenated agent names
2. PR #104 - Workflow git commits
3. PR #99 - Dashboard command template

**Edge Cases:**
- Migration paths for users upgrading
- Interaction between multiple bugs
- Boundary conditions
- Unusual agent names and workflows

**Related Issues:**
- Issue #112 - Migration from legacy bash scripts (not a bug, but users
  upgrading from old versions might encounter issues)

Run: pytest tests/distribution/test_0_13_7_edge_cases.py -xvs
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
    pytest.mark.edge_cases,
]


class TestRegressionPrevention:
    """
    Comprehensive regression tests for all three bugs.

    These tests ensure that if someone accidentally reverts the fixes,
    the tests will catch it immediately.
    """

    def test_hyphenated_agent_names_comprehensive(self, tmp_path, spec_kitty_repo_root):
        """
        REGRESSION TEST: Comprehensive check for hyphenated agent parsing.

        Tests multiple hyphenated name formats to ensure parser handles
        all cases correctly. If PR #111 is reverted, this MUST fail.
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature with comprehensive agent name test
        feature_dir = repo / "kitty-specs" / "001-regression"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "001-regression",
            "title": "Regression Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Test ALL edge case agent names
        wp_content = """---
work_package_id: WP01
title: Comprehensive Agent Test
lane: doing
dependencies: []
---

# WP01: Comprehensive Agent Test

Testing all hyphenated agent name formats.

## Activity Log

- 2025-01-27T10:00:00Z – cursor-agent – shell_pid=11111 – lane=doing – Single hyphen
- 2025-01-27T10:05:00Z – gpt-4-turbo – shell_pid=22222 – lane=doing – Two hyphens
- 2025-01-27T10:10:00Z – claude-3-5-sonnet – shell_pid=33333 – lane=doing – Three hyphens
- 2025-01-27T10:15:00Z – my-custom-ai-agent – shell_pid=44444 – lane=doing – Four hyphens
- 2025-01-27T10:20:00Z – claude – shell_pid=55555 – lane=doing – No hyphens (control)
"""
        (tasks_dir / "WP01-comprehensive.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add comprehensive test"], cwd=repo, capture_output=True)

        # Run status - should parse all agent names without error
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # REGRESSION CHECK: Must succeed with all hyphenated names
        assert result.returncode == 0, \
            f"REGRESSION DETECTED: Hyphenated agent parsing failed!\n" \
            f"Error: {result.stderr}\n" \
            f"This means PR #111 fix was reverted!"

        # Verify JSON is valid
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"REGRESSION DETECTED: JSON parsing failed with hyphenated agents!\n"
                f"Error: {e}\n"
                f"PR #111 fix may have been reverted!"
            )

    def test_empty_branch_validation_comprehensive(self, tmp_path, spec_kitty_repo_root):
        """
        REGRESSION TEST: Ensure empty branch validation is active.

        If PR #104 validation is removed, this MUST fail.
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature
        feature_dir = repo / "kitty-specs" / "002-validation"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "002-validation",
            "title": "Validation Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: Validation Test
lane: doing
dependencies: []
---

# WP01: Validation Test

## Activity Log
"""
        (tasks_dir / "WP01-validation.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP"], cwd=repo, capture_output=True)

        # Implement WP01 (creates worktree)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement failed: {result.stderr}")

        worktree = repo / ".worktrees" / "002-validation-WP01"
        if not worktree.exists():
            pytest.skip("Worktree not created")

        # Create uncommitted file
        (worktree / "test.txt").write_text("uncommitted")

        # Try to mark done - MUST be blocked
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # REGRESSION CHECK: Must fail with uncommitted work
        if result.returncode == 0:
            pytest.fail(
                "REGRESSION DETECTED: Empty branch validation bypassed!\n"
                "Uncommitted work was allowed through to 'done' state.\n"
                "PR #104 validation was likely removed or broken!"
            )

    def test_dashboard_template_simplicity_comprehensive(self, spec_kitty_repo_root):
        """
        REGRESSION TEST: Dashboard templates must stay simple.

        If someone re-adds embedded Python, this MUST fail.
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

            # REGRESSION CHECK: Must use CLI command
            has_cli_command = "spec-kitty dashboard" in template_content

            # REGRESSION CHECK: Must not have excessive Python
            python_blocks = re.findall(r'```python\n(.*?)```', template_content, re.DOTALL)
            total_python_lines = sum(len(block.strip().split('\n')) for block in python_blocks)

            if not has_cli_command or total_python_lines > 30:
                pytest.fail(
                    f"REGRESSION DETECTED: Dashboard template complexity!\n"
                    f"Template: {template_path.name}\n"
                    f"Has CLI command: {has_cli_command}\n"
                    f"Python lines: {total_python_lines}\n"
                    f"PR #99 simplification was likely reverted!"
                )


class TestEdgeCaseBoundaries:
    """
    Test boundary conditions and unusual inputs.
    """

    def test_agent_name_with_special_characters(self, tmp_path, spec_kitty_repo_root):
        """
        Agent names with underscores, numbers, etc.

        While hyphens are the main concern, test other special chars.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        feature_dir = repo / "kitty-specs" / "003-special-chars"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "003-special-chars",
            "title": "Special Characters Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Agent names with underscores, numbers
        wp_content = """---
work_package_id: WP01
title: Special Chars
lane: doing
dependencies: []
---

# WP01: Special Chars

## Activity Log

- 2025-01-27T11:00:00Z – agent_123 – shell_pid=11111 – lane=doing – Underscores
- 2025-01-27T11:05:00Z – gpt4 – shell_pid=22222 – lane=doing – Numbers
- 2025-01-27T11:10:00Z – claude-3_5 – shell_pid=33333 – lane=doing – Mixed
"""
        (tasks_dir / "WP01-special.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add special chars test"], cwd=repo, capture_output=True)

        # Should handle various special characters
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # EDGE CASE: Parser should be robust to various characters
        assert result.returncode == 0, \
            f"Parser failed with special characters: {result.stderr}"

    def test_very_long_agent_name(self, tmp_path, spec_kitty_repo_root):
        """
        Agent name with many hyphens (boundary test).

        Ensure parser doesn't have issues with long names.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        feature_dir = repo / "kitty-specs" / "004-long-name"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "004-long-name",
            "title": "Long Name Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Very long agent name with many hyphens
        long_agent = "my-very-long-agent-name-with-many-hyphens-for-testing"
        wp_content = f"""---
work_package_id: WP01
title: Long Name
lane: doing
dependencies: []
---

# WP01: Long Name

## Activity Log

- 2025-01-27T12:00:00Z – {long_agent} – shell_pid=99999 – lane=doing – Long name test
"""
        (tasks_dir / "WP01-long.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add long name test"], cwd=repo, capture_output=True)

        # Should handle very long names
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # EDGE CASE: Long names should work
        assert result.returncode == 0, \
            f"Parser failed with long agent name: {result.stderr}"


class TestMultipleBugInteraction:
    """
    Test interactions between multiple bugs.

    What happens when multiple edge cases occur together?
    """

    def test_hyphenated_agent_with_uncommitted_work(self, tmp_path, spec_kitty_repo_root):
        """
        Hyphenated agent name + uncommitted work validation.

        Both PR #111 and PR #104 fixes must work together.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        feature_dir = repo / "kitty-specs" / "005-interaction"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "005-interaction",
            "title": "Bug Interaction Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with hyphenated agent in activity log
        wp_content = """---
work_package_id: WP01
title: Interaction Test
lane: doing
dependencies: []
---

# WP01: Interaction Test

## Activity Log

- 2025-01-27T13:00:00Z – cursor-agent – shell_pid=12345 – lane=doing – Hyphenated agent started work
"""
        (tasks_dir / "WP01-interaction.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP"], cwd=repo, capture_output=True)

        # Implement (creates worktree)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "implement", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement failed: {result.stderr}")

        worktree = repo / ".worktrees" / "005-interaction-WP01"
        if not worktree.exists():
            pytest.skip("Worktree not created")

        # Create uncommitted work
        (worktree / "code.py").write_text("# by cursor-agent")

        # Try to move to done
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # INTERACTION CHECK: Validation should work even with hyphenated agent
        # Should fail due to uncommitted work, NOT due to parsing hyphenated name
        if result.returncode == 0:
            pytest.fail(
                "BUG INTERACTION: Uncommitted work allowed through!\n"
                "Validation may be failing when hyphenated agent present."
            )

        # Error should be about uncommitted work, not parsing
        error = result.stderr.lower()
        assert "cursor-agent" not in error or "parse" not in error, \
            f"Should not fail due to parsing hyphenated agent: {result.stderr}"


class TestMigrationScenarios:
    """
    Test upgrade scenarios for users migrating from older versions.

    Related to Issue #112 - not a bug, but users need smooth migrations.
    """

    def test_fresh_install_has_no_legacy_artifacts(self, tmp_path, spec_kitty_repo_root):
        """
        Fresh spec-kitty init should not create legacy artifacts.

        Legacy: .kittify/scripts/bash/*.sh files
        New: Built-in CLI commands
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Check for legacy bash scripts
        legacy_scripts = repo / ".kittify" / "scripts" / "bash"
        if legacy_scripts.exists():
            bash_files = list(legacy_scripts.glob("*.sh"))
            assert len(bash_files) == 0, \
                f"Fresh install should not create legacy bash scripts: {bash_files}"

    def test_all_commands_use_python_cli(self, tmp_path, spec_kitty_repo_root):
        """
        All commands should use Python CLI, not bash scripts.

        Ensures we're not reverting to old bash-based architecture.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Test that key commands work via Python CLI
        commands_to_test = [
            ["spec-kitty", "agent", "tasks", "status"],
            ["spec-kitty", "--version"],
        ]

        for cmd in commands_to_test:
            result = subprocess.run(
                cmd,
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Commands should work (or fail gracefully, but not with bash errors)
            if result.returncode != 0:
                assert ".sh" not in result.stderr, \
                    f"Command {' '.join(cmd)} is calling bash scripts: {result.stderr}"
                assert "bash" not in result.stderr.lower() or "command not found" not in result.stderr.lower(), \
                    f"Command {' '.join(cmd)} has bash errors: {result.stderr}"
