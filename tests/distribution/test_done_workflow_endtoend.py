"""
Distribution tests for complete done workflow end-to-end.

CRITICAL: These tests validate the COMPLETE workflow from specify to done,
testing how all the pieces (template, validation, empty branch warnings) work
together in real scenarios.

Tests validate that:
1. Full WP lifecycle with commits works
2. Full WP lifecycle without commits fails appropriately
3. Dependent WPs receive committed work
4. Multiple WPs with empty branches produce expected warnings
5. Real Feature 017 scenario is handled correctly
"""

import subprocess
from pathlib import Path
import pytest
import json

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.regression]


class TestCompleteWorkflow:
    """Test complete WP lifecycle scenarios."""

    def test_full_wp_lifecycle_with_commits(
        self, tmp_path
    ):
        """
        Complete workflow: specify → implement → commit → done.

        All steps should succeed.

        BUG CHECK:
        - Some step might break the flow
        - Validation might be too strict
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # 1. Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        # 2. Specify feature
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # 3. Create tasks
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # 4. Implement WP01
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Extract worktree path
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        assert worktree_path and worktree_path.exists(), "Worktree should be created"

        # 5. Create and commit files
        (worktree_path / "feature.py").write_text("""
# Feature implementation
def hello():
    return "world"
""")
        subprocess.run(["git", "add", "feature.py"], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): Add hello function"],
            cwd=worktree_path,
            check=True
        )

        # 6. Move to for_review
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "for_review"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should move to for_review. Error: {result.stderr}"

        # 7. Move to done
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should move to done. Error: {result.stderr}"

        # 8. Verify final state
        wp_file = list((feature_dir / "tasks").glob("WP01*.md"))[0]
        wp_content = wp_file.read_text()
        assert 'lane: "done"' in wp_content or "lane: done" in wp_content, \
            "WP should be in done lane"

    def test_full_wp_lifecycle_without_commits_fails(
        self, tmp_path
    ):
        """
        Same workflow but WITHOUT committing should fail.

        BUG CHECK:
        - Validation might not catch it
        - Might allow done without commits
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test Work Package

- [x] T001: Create test file
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Extract worktree path
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        # Create files but DON'T commit
        (worktree_path / "feature.py").write_text("# Feature\n")

        # Try: move to for_review (should fail)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "for_review"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail to move to for_review without commits"

        # Try: move to done (should also fail)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Should fail to move to done without commits"

    def test_dependent_wp_receives_committed_work(
        self, tmp_path
    ):
        """
        WP02 depending on WP01 should get WP01's commits.

        BUG CHECK:
        - Empty branch warning doesn't mean empty merge
        - Dependency resolution might be broken
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create WP01 and WP02 (WP02 depends on WP01)
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Foundation

- [x] T001: Create foundation

## WP02: Feature

Depends on: WP01

- [x] T002: Build feature
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement WP01 and commit
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        wp01_worktree = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line and 'WP01' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        wp01_worktree = project_root / part.strip('`')
                        break

        # Create foundation file
        (wp01_worktree / "foundation.py").write_text("""
# Foundation
class Base:
    def __init__(self):
        self.name = "base"
""")
        subprocess.run(["git", "add", "foundation.py"], cwd=wp01_worktree, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): Add foundation"],
            cwd=wp01_worktree,
            check=True
        )

        # Mark WP01 as done
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Implement WP02 (depends on WP01)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP02"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        wp02_worktree = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line and 'WP02' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        wp02_worktree = project_root / part.strip('`')
                        break

        # BUG CHECK: WP02 workspace should have WP01's files
        foundation_file = wp02_worktree / "foundation.py"
        assert foundation_file.exists(), "WP02 should have foundation.py from WP01"

        # Verify content matches
        content = foundation_file.read_text()
        assert "class Base" in content, "Foundation code should be present"

    def test_multiple_wps_empty_branches_error(
        self, tmp_path
    ):
        """
        Multiple WPs with empty branches - real Feature 017 scenario.

        BUG CHECK:
        - Might crash with many empty branches
        - Should create warnings but still work
        - Merge-base might be invalid
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup documentation feature (like Feature 017)
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Documentation", "--mission", "documentation", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        # Create 8 empty WPs + 1 dependent
        (feature_dir / "tasks.md").write_text("""
# Documentation Tasks

## WP01: Structure
- [x] T001: Setup

## WP02: Tutorials
- [x] T002: Write

## WP03: How-To
- [x] T003: Write

## WP04: Reference
- [x] T004: Write

## WP05: Explanation
- [x] T005: Write

## WP06: Quality
- [x] T006: Validate

## WP07: Examples
- [x] T007: Add

## WP08: Integration
- [x] T008: Test

## WP09: Final Review

Depends on: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08

- [x] T009: Review all
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Mark all 8 as done WITHOUT commits (Issue #72)
        for i in range(1, 9):
            wp_id = f"WP{i:02d}"
            subprocess.run(
                ["spec-kitty", "implement", wp_id],
                cwd=project_root,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["spec-kitty", "agent", "tasks", "move-task", wp_id, "--to", "done", "--force"],
                cwd=project_root,
                check=True,
                capture_output=True
            )

        # Implement WP09 (should warn about all 8 empty branches)
        result = subprocess.run(
            ["spec-kitty", "implement", "WP09"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # BUG CHECK: Should have warnings but still succeed
        assert result.returncode == 0, "Should succeed despite empty branches"

        # Should warn about empty branches
        warning_count = output.count("⚠️") + output.count("warning") + output.count("Warning")
        assert warning_count >= 8, f"Should have at least 8 warnings, got {warning_count}"

        # Verify worktree created
        feature_slug = feature_dir.name
        wp09_worktree = project_root / ".worktrees" / f"{feature_slug}-WP09"
        assert wp09_worktree.exists(), "WP09 worktree should be created"


class TestResearchMissionWorkflow:
    """Test that research mission also has validation."""

    def test_research_mission_validates_commits(
        self, tmp_path
    ):
        """
        Research mission should also validate commits.

        Research artifacts go in main repo (kitty-specs/), not worktree.

        BUG CHECK:
        - Research validation might be different
        - Might not check main repo artifacts
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup research feature
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Research Feature", "--mission", "research", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]

        (feature_dir / "tasks.md").write_text("""
# Research Feature Tasks

## WP01: Data Collection

- [x] T001: Collect data
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement WP01
        subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Create research artifact in main repo (not worktree)
        research_dir = feature_dir / "research"
        research_dir.mkdir(exist_ok=True)
        (research_dir / "data.csv").write_text("name,value\ntest,123\n")

        # Try to move to done WITHOUT committing (should fail)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should block done with uncommitted research artifacts
        assert result.returncode != 0, "Should block done with uncommitted research files"
        error_output = result.stdout + result.stderr
        assert "data.csv" in error_output or "Uncommitted" in error_output, \
            "Should mention uncommitted research files"


class TestMultiMissionProject:
    """Test project with multiple mission types."""

    def test_mixed_missions_all_validated(
        self, tmp_path
    ):
        """
        Project with software-dev and documentation features.

        Both should have validation.

        BUG CHECK:
        - Validation might only work for one mission type
        - Template might not propagate correctly
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)

        # Create software-dev feature
        subprocess.run(
            ["spec-kitty", "specify", "Code Feature", "--mission", "software-dev", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        code_feature_dir = [d for d in (project_root / "kitty-specs").iterdir() if "code" in d.name.lower()][0]

        (code_feature_dir / "tasks.md").write_text("""
# Code Feature Tasks

## WP01: Implementation

- [x] T001: Write code
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement WP01
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Extract worktree
        worktree_path = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        worktree_path = project_root / part.strip('`')
                        break

        # Create file but don't commit
        (worktree_path / "code.py").write_text("# Code\n")

        # Try to move to done (should fail - validation works for software-dev)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        assert result.returncode != 0, "Software-dev validation should work"

        # Now test documentation mission
        subprocess.run(
            ["spec-kitty", "specify", "Docs Feature", "--mission", "documentation", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        docs_feature_dir = [d for d in (project_root / "kitty-specs").iterdir()
                           if "docs" in d.name.lower()][0]

        (docs_feature_dir / "tasks.md").write_text("""
# Docs Feature Tasks

## WP01: Write Docs

- [x] T001: Write
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement docs WP01
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01", "--feature", docs_feature_dir.name],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )

        # Extract worktree
        docs_worktree = None
        for line in result.stdout.split('\n'):
            if '.worktrees' in line and docs_feature_dir.name in line:
                parts = line.split()
                for part in parts:
                    if '.worktrees' in part:
                        docs_worktree = project_root / part.strip('`')
                        break

        if docs_worktree:
            # Create doc file but don't commit
            (docs_worktree / "doc.md").write_text("# Docs\n")

            # Try to move to done (should fail - validation works for documentation too)
            result = subprocess.run(
                ["spec-kitty", "agent", "tasks", "move-task", "WP01",
                 "--to", "done", "--feature", docs_feature_dir.name],
                cwd=project_root,
                capture_output=True,
                text=True
            )

            assert result.returncode != 0, "Documentation validation should also work"


class TestForceFlag:
    """Test --force flag behavior across workflow."""

    def test_force_allows_bypass_entire_workflow(
        self, tmp_path
    ):
        """
        --force should work consistently across all transitions.

        BUG CHECK:
        - --force might only work for some transitions
        - Might have inconsistent behavior
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Setup
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        feature_dir = list((project_root / "kitty-specs").glob("*"))[0]
        (feature_dir / "tasks.md").write_text("""
# Test Feature Tasks

## WP01: Test

- [x] T001: Work
""")

        subprocess.run(["spec-kitty", "tasks"], cwd=project_root, check=True, capture_output=True)

        # Implement but don't commit
        subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Move to for_review with --force (should work)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "for_review", "--force"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "--force should work for for_review"

        # Move back to doing
        subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "doing"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # Move to done with --force (should also work)
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "move-task", "WP01", "--to", "done", "--force"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "--force should work for done too"
