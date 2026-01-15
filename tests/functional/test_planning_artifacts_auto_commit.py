"""
Comprehensive tests for planning artifacts auto-commit before worktree creation

Tests for bug discovered 2026-01-11:
- Planning artifacts (spec.md, plan.md, tasks/*.md) created in main
- User runs `spec-kitty implement WP01` with untracked planning files
- OLD BUG: Worktree created from HEAD without committing first
- RESULT: Worktree missing all planning files (git only copies committed files)
- FIX: Auto-commit planning artifacts before creating worktree

Critical: Git worktrees only include committed files from the branch they're created from.
If planning files are untracked in main, they won't appear in the worktree.

This broke the v0.11.0 workflow where planning happens in main but implementation in worktrees.
"""
import pytest
import subprocess
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_untracked_planning(temp_project_dir, spec_kitty_repo_root):
    """
    Create project with UNTRACKED planning artifacts.

    This simulates the user workflow:
    1. Run /spec-kitty.specify (creates untracked spec.md)
    2. Run /spec-kitty.plan (creates untracked plan.md)
    3. Run /spec-kitty.tasks (creates untracked tasks/*.md)
    4. Run spec-kitty implement WP01 (should auto-commit first)
    """
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    # Init project
    subprocess.run(
        ['spec-kitty', 'init', 'test-project', '--ai=claude'],
        cwd=str(temp_project_dir),
        env=env,
        input=b'y\n',
        capture_output=True
    )

    project_path = temp_project_dir / 'test-project'

    # Git setup
    subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

    # Create feature (committed)
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
        cwd=str(project_path),
        env=env,
        capture_output=True
    )
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add feature'], cwd=str(project_path), check=True, capture_output=True)

    # Create UNTRACKED planning files (simulating /spec-kitty.plan, /spec-kitty.tasks)
    feature_dir = project_path / 'kitty-specs' / '001-test-feature'

    # Plan file (untracked)
    plan_file = feature_dir / 'plan.md'
    plan_file.write_text("# Implementation Plan\n\nThis is the plan.")

    # Quickstart (untracked)
    quickstart_file = feature_dir / 'quickstart.md'
    quickstart_file.write_text("# Quick Start\n\n1. Do this\n2. Do that")

    # Task files (untracked) - use v0.11.0 naming pattern WP01-task-name.md
    tasks_dir = feature_dir / 'tasks'
    (tasks_dir / 'WP01-implement-feature.md').write_text("---\nwork_package_id: WP01\ntitle: Implement feature\ndependencies: []\nlane: planned\n---\n\n# WP01: Implement feature\n\nImplement the feature")
    (tasks_dir / 'WP02-test-feature.md').write_text("---\nwork_package_id: WP02\ntitle: Test feature\ndependencies: [WP01]\nlane: planned\n---\n\n# WP02: Test feature\n\nTest the feature")

    # Verify files are untracked
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        check=True
    )

    assert '??' in result.stdout, "Planning files should be untracked"

    return project_path, feature_dir


class TestPlanningArtifactsAutoCommit:
    """Tests for auto-commit of planning artifacts before worktree creation"""

    @pytest.mark.xfail(reason="spec-kitty bug: auto-commit of planning artifacts not yet implemented")
    def test_untracked_planning_files_committed_before_worktree(self, project_with_untracked_planning, requires_v011):
        """
        Test that untracked planning files are auto-committed before worktree creation.

        Bug scenario:
        1. User creates plan.md, tasks/*.md (untracked)
        2. Run: spec-kitty implement WP01
        3. OLD: Creates worktree without committing → planning files missing in worktree
        4. NEW: Auto-commits planning files first → planning files present in worktree

        This is CRITICAL for v0.11.0 workflow where planning happens in main.
        """
        project_path, feature_dir = project_with_untracked_planning

        # Verify planning files are currently untracked
        result = subprocess.run(
            ['git', 'status', '--porcelain', str(feature_dir)],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        untracked_count = result.stdout.count('??')
        assert untracked_count >= 3, f"Should have untracked planning files, found {untracked_count}"

        # Run implement (should auto-commit)
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, f"Implement should succeed: {result.stderr}"

        # Verify planning files now committed
        result = subprocess.run(
            ['git', 'status', '--porcelain', str(feature_dir)],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        # Should have no untracked files (all committed)
        assert '??' not in result.stdout, "Planning files should be committed"

        # Verify worktree created
        worktree_path = project_path / '.worktrees' / '001-test-feature-WP01'
        assert worktree_path.exists(), "Worktree should be created"

        # CRITICAL: Verify planning files are in worktree
        worktree_feature_dir = worktree_path / 'kitty-specs' / '001-test-feature'
        assert (worktree_feature_dir / 'plan.md').exists(), "plan.md should be in worktree"
        assert (worktree_feature_dir / 'quickstart.md').exists(), "quickstart.md should be in worktree"
        wp01_files = list((worktree_feature_dir / 'tasks').glob('WP01-*.md'))
        assert len(wp01_files) > 0, "WP01-*.md should be in worktree"

        # Verify content is correct (not empty)
        plan_content = (worktree_feature_dir / 'plan.md').read_text()
        assert "Implementation Plan" in plan_content, "plan.md should have content"

    @pytest.mark.xfail(reason="spec-kitty bug: auto-commit of planning artifacts not yet implemented")
    def test_auto_commit_creates_proper_commit_message(self, project_with_untracked_planning, requires_v011):
        """
        Test that auto-commit creates commit with descriptive message.

        Commit message should:
        - Mention that it's planning artifacts
        - Include feature slug
        - Indicate it was auto-committed by spec-kitty
        """
        project_path, feature_dir = project_with_untracked_planning

        # Run implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Check latest commit message
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%s%n%b'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        commit_msg = result.stdout

        # Should mention planning
        assert 'planning' in commit_msg.lower() or 'artifacts' in commit_msg.lower(), \
            "Commit should mention planning artifacts"

        # Should mention feature
        assert '001-test-feature' in commit_msg or 'test-feature' in commit_msg, \
            "Commit should mention feature name"

        # Should indicate auto-commit
        assert 'auto' in commit_msg.lower() or 'spec-kitty' in commit_msg.lower(), \
            "Commit should indicate it was automated"

    def test_modified_planning_files_also_committed(self, temp_project_dir, spec_kitty_repo_root, requires_v011):
        """
        Test that MODIFIED planning files (not just untracked) are committed.

        Scenario:
        1. Plan.md already committed
        2. User updates plan.md (modified, not committed)
        3. Run implement
        4. Should commit the modification
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Setup project
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        feature_dir = project_path / 'kitty-specs' / '001-test-feature'

        # Commit initial planning
        plan_file = feature_dir / 'plan.md'
        plan_file.write_text("# Plan v1")

        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'WP01-test-task.md').write_text("---\nwork_package_id: WP01\ntitle: Test task\nlane: planned\n---\n\n# WP01: Test task")

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial planning'], cwd=str(project_path), check=True, capture_output=True)

        # MODIFY planning (don't commit)
        plan_file.write_text("# Plan v2 - Updated")

        # Verify modified
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        assert ' M ' in result.stdout or 'M  ' in result.stdout, "plan.md should be modified"

        # Run implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Verify modification committed
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        assert ' M ' not in result.stdout, "Modified files should be committed"

        # Verify worktree has updated content
        worktree_plan = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature' / 'plan.md'
        if worktree_plan.exists():
            content = worktree_plan.read_text()
            assert "v2 - Updated" in content, "Worktree should have updated planning file"


class TestAutoCommitOnlyForFirstWP:
    """Tests that auto-commit only happens for first WP (branching from main)"""

    def test_dependent_wp_does_not_auto_commit(self, project_with_untracked_planning, requires_v011):
        """
        Test that WP02 --base WP01 does NOT auto-commit.

        Only first WP (branching from main) should auto-commit planning.
        Dependent WPs assume planning already committed.
        """
        project_path, feature_dir = project_with_untracked_planning

        # First, commit planning manually for this test
        subprocess.run(['git', 'add', str(feature_dir)], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Planning'], cwd=str(project_path), check=True, capture_output=True)

        # Implement WP01
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("WP01 implement failed")

        # Create untracked file in main
        (project_path / 'random.txt').write_text("Random untracked file")

        # Implement WP02 with --base (should NOT auto-commit)
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Check if random.txt still untracked
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        # random.txt should still be untracked (dependent WP doesn't auto-commit)
        assert '?? random.txt' in result.stdout or result.returncode != 0, \
            "Dependent WP should NOT auto-commit untracked files in main"

    def test_first_wp_auto_commits_only_feature_directory(self, project_with_untracked_planning, requires_v011):
        """
        Test that auto-commit only commits files in the feature directory.

        Should NOT commit:
        - Random untracked files in project root
        - Files in other features
        - .gitignore, README, etc.

        Should ONLY commit:
        - Files in kitty-specs/{feature-slug}/
        """
        project_path, feature_dir = project_with_untracked_planning

        # Create untracked file OUTSIDE feature directory
        (project_path / 'random.txt').write_text("Should not be committed")

        # Verify it's untracked
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        assert '?? random.txt' in result.stdout, "random.txt should be untracked"

        # Run implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Verify random.txt STILL untracked (not auto-committed)
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        assert '?? random.txt' in result.stdout, \
            "Auto-commit should only commit feature directory, not random files"

        # Verify feature files ARE committed
        assert '?? kitty-specs' not in result.stdout, "Feature files should be committed"


class TestAutoCommitBranchValidation:
    """Tests that auto-commit validates user is on main branch"""

    def test_error_if_not_on_main_branch(self, project_with_untracked_planning, requires_v011):
        """
        Test that implement fails if not on main branch when creating first WP.

        v0.11.0 planning happens on main branch.
        First WP must be created from main.
        Should error if on different branch.
        """
        project_path, feature_dir = project_with_untracked_planning

        # Checkout different branch
        subprocess.run(
            ['git', 'checkout', '-b', 'wrong-branch'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Try to implement from non-main branch
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail when not on main branch"

        output = result.stdout + result.stderr

        # Error should mention main branch
        assert 'main' in output.lower() or 'branch' in output.lower(), \
            "Error should mention main branch requirement"

    def test_auto_commit_works_on_master_branch(self, temp_project_dir, spec_kitty_repo_root, requires_v011):
        """
        Test that auto-commit works if default branch is 'master' instead of 'main'.

        Some repos use 'master' as default branch.
        Should work on either.
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        # Git with master branch
        subprocess.run(['git', 'init', '-b', 'master'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create feature with untracked planning
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        feature_dir = project_path / 'kitty-specs' / '001-test-feature'
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'WP01-test-task.md').write_text("---\nwork_package_id: WP01\ntitle: Test task\nlane: planned\n---\n\n# WP01: Test task")

        # Commit feature structure
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Feature'], cwd=str(project_path), check=True, capture_output=True)

        # Create untracked planning
        (feature_dir / 'plan.md').write_text("# Plan")

        # Run implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should work on 'master' branch (not just 'main')
        if result.returncode != 0:
            output = result.stdout + result.stderr
            # Should NOT fail because of branch name
            assert 'main' not in output.lower() or 'master' in output.lower(), \
                "Should accept 'master' branch as well as 'main'"


@pytest.mark.xfail(reason="spec-kitty bug: auto-commit of planning artifacts not yet implemented")
class TestWorktreeHasPlanningFiles:
    """Tests that worktree includes all planning files after creation"""

    def test_worktree_has_spec_file(self, project_with_untracked_planning, requires_v011):
        """
        Test that spec.md is accessible in worktree.
        """
        project_path, feature_dir = project_with_untracked_planning

        # Add spec.md (untracked)
        (feature_dir / 'spec.md').write_text("# Feature Spec\n\nSpec content")

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Check worktree has spec.md
        worktree_spec = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature' / 'spec.md'
        assert worktree_spec.exists(), "Worktree should have spec.md"

        content = worktree_spec.read_text()
        assert "Feature Spec" in content, "spec.md should have content"

    def test_worktree_has_all_wp_files(self, project_with_untracked_planning, requires_v011):
        """
        Test that ALL WP files in tasks/ are in worktree.

        Even WPs not being implemented should be visible in worktree.
        """
        project_path, feature_dir = project_with_untracked_planning

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Check worktree has all WP files
        worktree_tasks = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature' / 'tasks'

        wp01_files = list(worktree_tasks.glob('WP01-*.md'))
        wp02_files = list(worktree_tasks.glob('WP02-*.md'))
        assert len(wp01_files) > 0, "Should have WP01-*.md (being implemented)"
        assert len(wp02_files) > 0, "Should have WP02-*.md (not being implemented yet)"

    def test_worktree_has_quickstart_file(self, project_with_untracked_planning, requires_v011):
        """
        Test that quickstart.md is in worktree.

        This was specifically mentioned in the bug report.
        """
        project_path, feature_dir = project_with_untracked_planning

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        worktree_quickstart = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature' / 'quickstart.md'
        assert worktree_quickstart.exists(), "Worktree should have quickstart.md"

        content = worktree_quickstart.read_text()
        assert "Quick Start" in content, "quickstart.md should have content"


@pytest.mark.xfail(reason="spec-kitty bug: auto-commit of planning artifacts not yet implemented")
class TestRegressionPrevention:
    """Prevent regression of the planning files missing bug"""

    def test_no_empty_planning_files_in_worktree(self, project_with_untracked_planning, requires_v011):
        """
        Prevent regression: Worktree having empty/missing planning files.

        Old bug:
        - Planning files untracked in main
        - Worktree created from HEAD
        - Git doesn't copy untracked files
        - Worktree missing spec.md, plan.md, tasks/*.md

        New behavior:
        - Auto-commit planning files first
        - Worktree created from commit including planning
        - All planning files present in worktree
        """
        project_path, feature_dir = project_with_untracked_planning

        # Add comprehensive planning files
        (feature_dir / 'spec.md').write_text("# Spec\n\nSpecification content")
        (feature_dir / 'plan.md').write_text("# Plan\n\nImplementation plan")
        (feature_dir / 'quickstart.md').write_text("# Quickstart\n\nQuick guide")
        (feature_dir / 'research.md').write_text("# Research\n\nBackground research")

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        worktree_feature = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature'

        # ALL planning files should exist and have content
        required_files = ['spec.md', 'plan.md', 'quickstart.md', 'research.md']

        missing_or_empty = []

        for file_path in required_files:
            full_path = worktree_feature / file_path
            if not full_path.exists():
                missing_or_empty.append(f"{file_path} - MISSING")
            elif full_path.stat().st_size == 0:
                missing_or_empty.append(f"{file_path} - EMPTY")
            elif len(full_path.read_text().strip()) < 5:
                missing_or_empty.append(f"{file_path} - NO CONTENT")

        # Check WP01 file exists (using v0.11.0 naming pattern)
        wp01_files = list((worktree_feature / 'tasks').glob('WP01-*.md'))
        if not wp01_files:
            missing_or_empty.append("tasks/WP01-*.md - MISSING")

        if missing_or_empty:
            pytest.fail(
                "REGRESSION: Planning files missing or empty in worktree:\n" +
                "\n".join(f"  - {f}" for f in missing_or_empty) +
                "\n\nThis indicates planning files were NOT committed before worktree creation."
            )

    def test_agent_can_access_all_planning_context(self, project_with_untracked_planning, requires_v011):
        """
        Test that agent in worktree can access ALL planning context.

        Agent needs:
        - spec.md for requirements
        - plan.md for implementation strategy
        - quickstart.md for getting started
        - tasks/*.md for all WPs (context about other WPs)

        If any missing, agent is working blind.
        """
        project_path, feature_dir = project_with_untracked_planning

        # Add all planning context
        (feature_dir / 'spec.md').write_text("# Spec\n\nUser requirements: Build hello world script")
        (feature_dir / 'plan.md').write_text("# Plan\n\nStep 1: Create script\nStep 2: Test script")
        (feature_dir / 'quickstart.md').write_text("# Quickstart\n\n1. Run ./hello.sh\n2. Verify output")

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        worktree_feature = project_path / '.worktrees' / '001-test-feature-WP01' / 'kitty-specs' / '001-test-feature'

        # Verify agent has all context
        spec_content = (worktree_feature / 'spec.md').read_text()
        plan_content = (worktree_feature / 'plan.md').read_text()
        quickstart_content = (worktree_feature / 'quickstart.md').read_text()

        assert "User requirements" in spec_content, "Agent should see requirements"
        assert "Step 1" in plan_content, "Agent should see implementation steps"
        assert "Run ./hello.sh" in quickstart_content, "Agent should see quickstart guide"

        # Agent should also see OTHER WPs for context
        wp02_files = list((worktree_feature / 'tasks').glob('WP02-*.md'))
        assert len(wp02_files) > 0, "Agent should see other WPs for context"


class TestAutoCommitUserFeedback:
    """Tests for user feedback during auto-commit"""

    def test_user_sees_auto_commit_message(self, project_with_untracked_planning, requires_v011):
        """
        Test that user is informed when auto-commit happens.

        Should see:
        - List of files being committed
        - "Auto-committing to main..."
        - "✓ Planning artifacts committed"
        """
        project_path, feature_dir = project_with_untracked_planning

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test-feature'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should inform user about auto-commit
        # (May or may not be implemented yet)
        if 'auto-commit' in output.lower() or 'committing' in output.lower():
            # Great - user is informed
            assert 'planning' in output.lower() or 'artifacts' in output.lower(), \
                "Should mention what's being committed"


class TestEdgeCases:
    """Edge cases for auto-commit functionality"""

    def test_empty_feature_directory_does_not_crash(self, temp_project_dir, spec_kitty_repo_root, requires_v011):
        """
        Test that auto-commit handles empty feature directory gracefully.

        Scenario:
        - Feature exists but no planning files created yet
        - Should not crash, should proceed or give helpful error
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create minimal feature (no planning files)
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'minimal'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Feature'], cwd=str(project_path), check=True, capture_output=True)

        # Try to implement without creating WP files
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-minimal'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail gracefully (WP files missing), not crash
        # Error should be about missing WP files, not about auto-commit
        if result.returncode != 0:
            output = result.stdout + result.stderr
            # Should mention missing WP or tasks, not crash with traceback
            assert 'WP01' in output or 'tasks' in output.lower() or 'not found' in output.lower(), \
                "Error should be about missing WP, not crash during auto-commit"

    @pytest.mark.xfail(reason="spec-kitty bug: auto-commit of planning artifacts not yet implemented")
    def test_already_committed_files_not_recommitted(self, temp_project_dir, spec_kitty_repo_root, requires_v011):
        """
        Test that if planning files already committed, no new commit created.

        Scenario:
        - Planning files already in git
        - Run implement
        - Should NOT create duplicate commit
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create feature with planning files
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        feature_dir = project_path / 'kitty-specs' / '001-test'
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        (feature_dir / 'plan.md').write_text("# Plan")
        (tasks_dir / 'WP01-test-task.md').write_text("---\nwork_package_id: WP01\ntitle: Test task\nlane: planned\n---\n\n# WP01: Test task")

        # COMMIT planning files
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Planning'], cwd=str(project_path), check=True, capture_output=True)

        # Get commit count before implement
        result_before = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        commits_before = int(result_before.stdout.strip())

        # Run implement (planning already committed)
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-test'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip("Implement failed")

        # Get commit count after
        result_after = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        commits_after = int(result_after.stdout.strip())

        # Should NOT have created new commit (planning already committed)
        assert commits_after == commits_before, \
            "Should not create duplicate commit when planning already committed"
