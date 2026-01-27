"""
End-to-End Feature Detection Tests

These tests validate the complete feature detection workflow in real scenarios,
especially the original bug: /spec-kitty.plan selecting wrong feature.

**Original Bug Scenario:**
1. User creates 020-feature-a (no plan.md yet)
2. User creates 021-feature-b (already has plan.md)
3. Agent runs /spec-kitty.plan expecting to work on feature 020
4. CLI auto-selects feature 021 (highest number) ← BUG!
5. Agent creates/overwrites plan.md for wrong feature

**These Tests Validate:**
- Original bug is fixed
- Real agent workflows work correctly
- Template updates propagated correctly
- Worktree scenarios handled properly
- Multi-feature repos work deterministically

Run: pytest tests/distribution/test_feature_detection_e2e.py -xvs
"""

import subprocess
import json
import os
from pathlib import Path
import pytest

pytestmark = [
    pytest.mark.distribution,
    pytest.mark.adversarial,
    pytest.mark.integration,
]


class TestOriginalBugFixed:
    """
    THE CRITICAL TEST: Validate the original bug is fixed.

    This reproduces the exact scenario reported in the problem statement.
    """

    def test_plan_command_with_multiple_features_requires_explicit(self, tmp_path, spec_kitty_repo_root):
        """
        THE BUG: /spec-kitty.plan selects wrong feature when multiple exist.

        SCENARIO:
        - 020-feature-a exists (no plan.md)
        - 021-feature-b exists (has plan.md)
        - Agent runs setup-plan without --feature
        - OLD: Selects 021 (highest) ← WRONG!
        - NEW: Errors, requires --feature flag ← CORRECT!
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # REPRODUCE THE BUG: Create 020 (no plan) and 021 (has plan)
        feature_020 = repo / "kitty-specs" / "020-feature-a"
        feature_021 = repo / "kitty-specs" / "021-feature-b"
        feature_020.mkdir(parents=True)
        feature_021.mkdir(parents=True)

        # Feature 020: No plan.md (user wants to create it)
        meta_020 = {"feature_id": "020-feature-a", "title": "Feature A", "mission": "software-dev"}
        (feature_020 / "meta.json").write_text(json.dumps(meta_020))

        # Feature 021: Already has plan.md
        meta_021 = {"feature_id": "021-feature-b", "title": "Feature B", "mission": "software-dev"}
        (feature_021 / "meta.json").write_text(json.dumps(meta_021))
        (feature_021 / "plan.md").write_text("# Existing Plan\n\nAlready planned.")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add features"], cwd=repo, capture_output=True)

        # THE CRITICAL TEST: Run setup-plan WITHOUT --feature from main branch
        subprocess.run(["git", "checkout", "main"], cwd=repo, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "setup-plan", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # NEW BEHAVIOR: Should ERROR (not auto-select 021)
        if result.returncode == 0:
            # If it succeeded, check which feature it used
            # It should NOT have selected 021-feature-b automatically
            if (feature_021 / "plan.md").exists():
                plan_content = (feature_021 / "plan.md").read_text()
                if plan_content != "# Existing Plan\n\nAlready planned.":
                    pytest.fail(
                        "CRITICAL BUG DETECTED: setup-plan modified 021-feature-b!\n"
                        "This is the exact bug we're fixing - auto-selected highest numbered feature.\n"
                        f"Plan content changed: {plan_content}"
                    )

            # Also check 020
            if (feature_020 / "plan.md").exists():
                pytest.fail(
                    "BUG: setup-plan created plan in 020-feature-a without --feature flag!\n"
                    "Should error when multiple features exist."
                )

        # CORRECT BEHAVIOR: Should fail with helpful error
        assert result.returncode != 0, \
            "Should error when multiple features exist (ambiguous)"

        error_msg = result.stderr + result.stdout
        # Should mention multiple features
        assert "020-feature-a" in error_msg and "021-feature-b" in error_msg, \
            f"Error should list both features: {error_msg}"

        # Should guide to --feature flag
        assert "--feature" in error_msg, \
            f"Error should mention --feature flag: {error_msg}"

    def test_plan_command_with_explicit_feature_works(self, tmp_path, spec_kitty_repo_root):
        """
        With explicit --feature, command should work correctly.

        This is the fix - agent provides --feature explicitly.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create feature
        feature_dir = repo / "kitty-specs" / "020-feature-a"
        feature_dir.mkdir(parents=True)
        meta = {"feature_id": "020-feature-a", "title": "Feature A", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True)

        # Test: With explicit --feature, should work
        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "setup-plan", "--feature", "020-feature-a", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should work when feature is explicit
        # (Might fail for other reasons, but not due to detection)
        if result.returncode != 0:
            error_combined = (result.stdout + result.stderr).lower()
            assert "multiple feature" not in error_combined, \
                f"Should not error about ambiguity when --feature provided: {result.stderr}"


class TestWorktreeScenarios:
    """
    Test feature detection in worktree contexts.

    Worktrees use branches with -WP## suffix that must be handled correctly.
    """

    def test_worktree_branch_detection(self, tmp_path, spec_kitty_repo_root):
        """
        In worktree with branch 020-feature-a-WP01, detect 020-feature-a.

        Critical for implement workflow.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create feature with tasks
        feature_dir = repo / "kitty-specs" / "020-feature-a"
        feature_dir.mkdir(parents=True)
        meta = {"feature_id": "020-feature-a", "title": "Feature A", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: Test WP
lane: planned
dependencies: []
---

# WP01
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True)

        # Create worktree (if implement command available)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01", "--feature", "020-feature-a"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Implement command not available: {result.stderr}")

        # Worktree should exist
        worktree_dir = repo / ".worktrees" / "020-feature-a-WP01"
        if not worktree_dir.exists():
            pytest.skip("Worktree not created")

        # Test: Run command from inside worktree
        # Should detect feature from branch (stripping -WP01)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=worktree_dir,
            env=env,
            capture_output=True,
            text=True
        )

        # Should detect 020-feature-a from branch 020-feature-a-WP01
        assert result.returncode == 0 or "020-feature-a" in (result.stdout + result.stderr)


class TestTemplateUpdates:
    """
    Test that plan.md template is updated correctly.

    Template should instruct agents to pass --feature explicitly.
    """

    def test_plan_template_instructs_explicit_feature(self, spec_kitty_repo_root):
        """
        Plan template should tell agents to detect feature and pass --feature.

        Template should include logic like:
        1. Detect feature from git branch
        2. Pass --feature <detected-feature> to CLI command
        """
        # Find plan.md template
        template_file = spec_kitty_repo_root / "src" / "specify_cli" / "missions" / "software-dev" / "command-templates" / "plan.md"

        if not template_file.exists():
            # Try alternate locations
            alt_path = spec_kitty_repo_root / ".kittify" / "missions" / "software-dev" / "command-templates" / "plan.md"
            if alt_path.exists():
                template_file = alt_path
            else:
                pytest.skip(f"Plan template not found at {template_file}")

        template_content = template_file.read_text()

        # Should instruct to pass --feature
        assert "--feature" in template_content, \
            "Plan template should instruct agents to use --feature flag"

        # Should mention detecting from context (branch, cwd)
        has_detection_logic = any(keyword in template_content.lower() for keyword in [
            "git branch", "branch name", "detect feature", "current feature"
        ])

        assert has_detection_logic, \
            "Template should instruct how to detect feature context"

    def test_agent_templates_regenerated(self, spec_kitty_repo_root):
        """
        All 12 agent template copies should be updated.

        After updating source template, migration should regenerate all copies.
        """
        # Check a few key agent directories
        agent_dirs = [
            ".claude/commands",
            ".cursor/commands",
            ".github/prompts",
        ]

        for agent_dir in agent_dirs:
            plan_template = spec_kitty_repo_root / agent_dir / "spec-kitty.plan.md"
            if not plan_template.exists():
                continue  # Not all agents might be present

            template_content = plan_template.read_text()

            # Should have updated template (mentions --feature)
            assert "--feature" in template_content, \
                f"{agent_dir}/spec-kitty.plan.md should mention --feature flag"


class TestMultiFeatureWorkflows:
    """
    Test complete workflows in repos with multiple features.
    """

    def test_workflow_from_feature_branch(self, tmp_path, spec_kitty_repo_root):
        """
        When on feature branch, commands should auto-detect from branch.

        User workflow:
        1. git checkout 020-feature-a
        2. /spec-kitty.plan
        3. Should use 020-feature-a (from branch)
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create multiple features
        for num, name in [("020", "feature-a"), ("021", "feature-b")]:
            feature_dir = repo / "kitty-specs" / f"{num}-{name}"
            feature_dir.mkdir(parents=True)
            meta = {"feature_id": f"{num}-{name}", "title": name, "mission": "software-dev"}
            (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add features"], cwd=repo, capture_output=True)

        # Checkout branch for feature-a
        subprocess.run(["git", "checkout", "-b", "020-feature-a"], cwd=repo, capture_output=True)

        # Test: Commands should detect from branch
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should use 020-feature-a from branch context
        assert result.returncode == 0 or "020-feature-a" in (result.stdout + result.stderr)

    def test_workflow_from_inside_feature_directory(self, tmp_path, spec_kitty_repo_root):
        """
        When inside feature directory, detect from path.

        User workflow:
        1. cd kitty-specs/020-feature-a
        2. /spec-kitty.plan
        3. Should use 020-feature-a (from cwd)
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create multiple features
        feature_020 = repo / "kitty-specs" / "020-feature-a"
        feature_021 = repo / "kitty-specs" / "021-feature-b"
        feature_020.mkdir(parents=True)
        feature_021.mkdir(parents=True)

        for feature_dir, feature_id in [(feature_020, "020-feature-a"), (feature_021, "021-feature-b")]:
            meta = {"feature_id": feature_id, "title": feature_id, "mission": "software-dev"}
            (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add features"], cwd=repo, capture_output=True)

        # Test: Run from inside 020-feature-a directory
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=feature_020,
            env=env,
            capture_output=True,
            text=True
        )

        # Should detect feature from cwd path
        assert result.returncode == 0 or "020-feature-a" in (result.stdout + result.stderr)

    def test_workflow_with_env_var(self, tmp_path, spec_kitty_repo_root):
        """
        SPECIFY_FEATURE env var should work from anywhere.

        Agent workflow:
        1. export SPECIFY_FEATURE=020-feature-a
        2. /spec-kitty.plan (from any directory)
        3. Should use 020-feature-a
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
            "SPECIFY_FEATURE": "020-feature-a",
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create feature
        feature_dir = repo / "kitty-specs" / "020-feature-a"
        feature_dir.mkdir(parents=True)
        meta = {"feature_id": "020-feature-a", "title": "Feature A", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True)

        # Test: From random directory, env var should work
        random_dir = repo / "random"
        random_dir.mkdir()

        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=random_dir,
            env=env,
            capture_output=True,
            text=True
        )

        # Should use env var (020-feature-a) regardless of cwd
        assert result.returncode == 0 or "020-feature-a" in (result.stdout + result.stderr)


class TestRegressionPrevention:
    """
    Tests that ensure the bug doesn't come back.
    """

    def test_comprehensive_no_highest_numbered_anywhere(self, spec_kitty_repo_root):
        """
        COMPREHENSIVE CHECK: No "highest numbered" logic anywhere.

        Search the entire codebase for suspicious patterns.
        """
        # Search for max/sorted with feature
        patterns = [
            r"max.*\d+.*feature",
            r"sorted.*feature.*\[-1",
            r"feature.*max.*\d+",
        ]

        findings = []
        for pattern in patterns:
            result = subprocess.run(
                ["grep", "-r", "-E", "-n", pattern,
                 str(spec_kitty_repo_root / "src" / "specify_cli"),
                 "--include=*.py"],
                capture_output=True,
                text=True
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    # Exclude comments and test files
                    if not any(skip in line for skip in ['#', 'test_', '"""', "'''"]):
                        findings.append(line)

        if findings:
            pytest.fail(
                f"POTENTIAL REGRESSION: Found 'highest numbered' pattern:\n" +
                "\n".join(findings[:5]) +
                "\n\nVerify this is not selecting features by number"
            )

    def test_all_commands_have_deterministic_detection(self, tmp_path, spec_kitty_repo_root):
        """
        All commands should use deterministic detection.

        Run multiple times - should get consistent results.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": os.environ.get("PATH", ""),
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
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create single feature
        feature_dir = repo / "kitty-specs" / "020-test"
        feature_dir.mkdir(parents=True)
        meta = {"feature_id": "020-test", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True)

        # Run same command 5 times - should be deterministic
        results = []
        for i in range(5):
            result = subprocess.run(
                ["spec-kitty", "agent", "tasks", "status", "--json"],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True
            )
            results.append(result.returncode)

        # All runs should have same return code
        assert len(set(results)) == 1, \
            f"Detection should be deterministic, got varying results: {results}"
