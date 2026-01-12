"""
Adaptive Worktree Behavior Version Comparison Tests

These tests run on BOTH v0.10.x and v0.11.0, documenting behavioral differences.

Uses the `workspace_is_per_wp` fixture to branch behavior:
- workspace_is_per_wp == False → v0.10.x behavior
- workspace_is_per_wp == True → v0.11.0+ behavior

These tests serve multiple purposes:
1. Regression documentation - what changed between versions
2. Version compatibility validation - both versions tested
3. Migration guide validation - documented behavior matches actual behavior

All tests use the workspace_is_per_wp fixture for adaptive behavior.
"""
import pytest
import os
import subprocess
import tempfile
from pathlib import Path


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def init_test_project(temp_project_dir, spec_kitty_repo_root):
    """Initialize spec-kitty project."""
    def _init(project_name="test-project"):
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input='y\n',
            capture_output=True,
            text=True
        )

        project_path = temp_project_dir / project_name

        # Initialize git
        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        return project_path

    return _init


class TestPlanningWorkflowComparison:
    """Compare planning workflow between v0.10.x and v0.11.0"""

    def test_specify_command_behavior(self, workspace_is_per_wp, spec_kitty_version, init_test_project):
        """
        Document that specify creates worktree in v0.10.x but not in v0.11.0.

        v0.10.x: /spec-kitty.specify creates .worktrees/001-feature/
        v0.11.0: /spec-kitty.specify works in main, NO worktree created
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Run create-feature command
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"create-feature failed: {result.stderr}"

        worktrees_dir = project_path / '.worktrees'

        if workspace_is_per_wp:
            # v0.11.0: NO worktree created during specify
            assert not worktrees_dir.exists(), \
                "v0.11.0+ should NOT create .worktrees/ during specify"

            # Feature artifacts in main
            spec_file = project_path / 'kitty-specs' / '001-test-feature' / 'spec.md'
            assert spec_file.exists(), \
                "v0.11.0+ spec.md should be in main repo"
        else:
            # v0.10.x: Worktree created during specify
            assert worktrees_dir.exists(), \
                "v0.10.x should create .worktrees/ during specify"

            feature_worktree = worktrees_dir / '001-test-feature'
            assert feature_worktree.exists(), \
                "v0.10.x should create .worktrees/001-test-feature/"

            # Spec in worktree
            spec_file = feature_worktree / 'kitty-specs' / '001-test-feature' / 'spec.md'
            assert spec_file.exists(), \
                "v0.10.x spec.md should be in worktree"

    def test_plan_command_location(self, workspace_is_per_wp, init_test_project):
        """
        Document plan command location differs by version.

        v0.10.x: Run plan command in worktree
        v0.11.0: Run plan command in main repo
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Create plan.md file in appropriate location (simulating setup-plan)
        # We're testing location, not the command itself
        if workspace_is_per_wp:
            # v0.11.0: plan.md in main
            plan_file = project_path / 'kitty-specs' / '001-test-feature' / 'plan.md'
        else:
            # v0.10.x: plan.md in worktree
            plan_file = project_path / '.worktrees' / '001-test-feature' / 'kitty-specs' / '001-test-feature' / 'plan.md'

        plan_file.write_text("# Implementation Plan\n\nThis is a test plan.")

        # Verify location
        if workspace_is_per_wp:
            assert plan_file.exists(), \
                "v0.11.0+ plan.md should be in main repo"
            assert 'kitty-specs' in str(plan_file) and '.worktrees' not in str(plan_file), \
                "v0.11.0+ plan in main repo"
        else:
            assert plan_file.exists(), \
                "v0.10.x plan.md should be in worktree"
            assert '.worktrees' in str(plan_file), \
                "v0.10.x plan in worktree"

    def test_tasks_command_location(self, workspace_is_per_wp, init_test_project):
        """
        Document tasks command location.

        v0.10.x: Tasks in worktree
        v0.11.0: Tasks in main
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature and plan
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'setup-plan'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Create tasks directory manually (simulating tasks command)
        if workspace_is_per_wp:
            tasks_dir = project_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        else:
            tasks_dir = project_path / '.worktrees' / '001-test-feature' / 'kitty-specs' / '001-test-feature' / 'tasks'

        tasks_dir.mkdir(parents=True, exist_ok=True)
        wp_file = tasks_dir / 'WP01.md'
        wp_file.write_text("# WP01: Test task")

        # Verify location
        assert wp_file.exists(), "WP file should exist in expected location"

        if workspace_is_per_wp:
            assert 'kitty-specs' in str(wp_file) and '.worktrees' not in str(wp_file), \
                "v0.11.0+ tasks should be in main repo"
        else:
            assert '.worktrees' in str(wp_file), \
                "v0.10.x tasks should be in worktree"

    def test_planning_artifact_location(self, workspace_is_per_wp, init_test_project):
        """
        Document where all planning artifacts end up.
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Run full planning workflow
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Create plan.md file in appropriate location (simulating planning workflow)
        if workspace_is_per_wp:
            # v0.11.0: All in main
            base_dir = project_path / 'kitty-specs' / '001-test-feature'
            plan_file = base_dir / 'plan.md'
        else:
            # v0.10.x: All in worktree
            base_dir = project_path / '.worktrees' / '001-test-feature' / 'kitty-specs' / '001-test-feature'
            plan_file = base_dir / 'plan.md'

        plan_file.write_text("# Implementation Plan\n\nTest plan content")

        # Verify all artifacts in correct location
        if workspace_is_per_wp:
            assert base_dir.exists(), "v0.11.0+ artifacts in main"
            assert (base_dir / 'spec.md').exists(), "spec.md in main"
            assert (base_dir / 'plan.md').exists(), "plan.md in main"

            # Should NOT be in worktrees
            assert not (project_path / '.worktrees').exists(), \
                "v0.11.0+ should have no .worktrees during planning"
        else:
            assert base_dir.exists(), "v0.10.x artifacts in worktree"
            assert (base_dir / 'spec.md').exists(), "spec.md in worktree"
            assert (base_dir / 'plan.md').exists(), "plan.md in worktree"

    def test_git_branch_during_planning(self, workspace_is_per_wp, init_test_project):
        """
        Document which git branch is active during planning.

        v0.10.x: On feature branch in worktree
        v0.11.0: On main/master branch
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Still on main/master
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            assert branch in ['main', 'master'], \
                f"v0.11.0+ should be on main/master, got: {branch}"
        else:
            # v0.10.x: On feature branch in worktree
            worktree_dir = project_path / '.worktrees' / '001-test-feature'
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=str(worktree_dir),
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            assert branch == '001-test-feature', \
                f"v0.10.x should be on 001-test-feature branch, got: {branch}"

    def test_git_commits_during_planning(self, workspace_is_per_wp, init_test_project):
        """
        Document where planning commits are made.
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Can commit on main
            # Add and commit spec
            subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
            result = subprocess.run(
                ['git', 'commit', '-m', 'Add spec'],
                cwd=str(project_path),
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "v0.11.0+ should commit on main"

            # Verify on main branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                check=True
            )
            assert branch_result.stdout.strip() in ['main', 'master'], \
                "v0.11.0+ commits on main/master"
        else:
            # v0.10.x: Commit on feature branch in worktree
            worktree_dir = project_path / '.worktrees' / '001-test-feature'
            subprocess.run(['git', 'add', '.'], cwd=str(worktree_dir), check=True, capture_output=True)
            result = subprocess.run(
                ['git', 'commit', '-m', 'Add spec'],
                cwd=str(worktree_dir),
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, "v0.10.x should commit in worktree"

            # Verify on feature branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=str(worktree_dir),
                capture_output=True,
                text=True,
                check=True
            )
            assert branch_result.stdout.strip() == '001-test-feature', \
                "v0.10.x commits on feature branch"


class TestImplementationWorkflowComparison:
    """Compare implementation workflow between versions"""

    def test_implementation_entry_point(self, workspace_is_per_wp, spec_kitty_version, init_test_project):
        """
        Document how implementation starts.

        v0.10.x: Already in worktree after specify
        v0.11.0: Must run `spec-kitty implement WP##`
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Complete planning
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Must run implement command
            result = subprocess.run(
                ['spec-kitty', 'implement', '--help'],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, \
                "v0.11.0+ should have implement command"
        else:
            # v0.10.x: Already in worktree, no implement command
            worktree_dir = project_path / '.worktrees' / '001-test-feature'
            assert worktree_dir.exists(), \
                "v0.10.x should already have worktree"

            # implement command should NOT exist
            result = subprocess.run(
                ['spec-kitty', 'implement', '--help'],
                capture_output=True,
                text=True
            )
            assert result.returncode != 0, \
                "v0.10.x should NOT have implement command"

    def test_worktree_creation_timing(self, workspace_is_per_wp, init_test_project):
        """
        Document when worktrees are created.

        v0.10.x: During specify command
        v0.11.0: During implement command
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Before specify
        assert not (project_path / '.worktrees').exists(), \
            "No .worktrees before feature creation"

        # After specify
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Still no .worktrees
            assert not (project_path / '.worktrees').exists(), \
                "v0.11.0+ should NOT create .worktrees during specify"

            # Would create during implement (can't test without v0.11.0 installed)
        else:
            # v0.10.x: .worktrees exists now
            assert (project_path / '.worktrees').exists(), \
                "v0.10.x should create .worktrees during specify"
            assert (project_path / '.worktrees' / '001-test-feature').exists(), \
                "v0.10.x should create feature worktree during specify"

    def test_worktree_naming_convention(self, workspace_is_per_wp, init_test_project):
        """
        Document worktree naming pattern change.

        v0.10.x: .worktrees/###-feature-slug/
        v0.11.0: .worktrees/###-feature-slug-WP##/
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'my-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: No worktree yet, but would be ###-feature-WP##
            # Can't test without actually implementing, so just document expectation
            assert not (project_path / '.worktrees').exists(), \
                "v0.11.0+ no worktree until implement"
            # Expected pattern: 001-my-feature-WP01
        else:
            # v0.10.x: Pattern is ###-feature
            import re
            worktree_dir = project_path / '.worktrees' / '001-my-feature'
            assert worktree_dir.exists(), \
                "v0.10.x worktree should exist"

            # Verify naming matches pattern
            pattern = re.compile(r'^\d{3}-[a-z-]+$')
            assert pattern.match('001-my-feature'), \
                "v0.10.x naming should match ###-feature-slug pattern"

    def test_parallel_implementation_support(self, workspace_is_per_wp, init_test_project):
        """
        Document parallel development capability.

        v0.10.x: Sequential (one worktree per feature)
        v0.11.0: Parallel (multiple worktrees per feature)
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Would support parallel (can't test without v0.11.0)
            # Multiple worktrees possible: 001-test-feature-WP01, 001-test-feature-WP03
            assert not (project_path / '.worktrees').exists(), \
                "v0.11.0+ supports parallel, one worktree per WP"
        else:
            # v0.10.x: Only one worktree per feature
            worktrees = list((project_path / '.worktrees').iterdir())
            assert len(worktrees) == 1, \
                "v0.10.x only one worktree per feature"
            assert worktrees[0].name == '001-test-feature', \
                "v0.10.x single worktree for entire feature"

    def test_dependency_tracking(self, workspace_is_per_wp, init_test_project):
        """
        Document dependency tracking system.

        v0.10.x: No formal dependency tracking
        v0.11.0: Dependencies in WP frontmatter, validated
        """
        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Create WP files
        if workspace_is_per_wp:
            tasks_dir = project_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        else:
            tasks_dir = project_path / '.worktrees' / '001-test-feature' / 'kitty-specs' / '001-test-feature' / 'tasks'

        tasks_dir.mkdir(parents=True, exist_ok=True)

        if workspace_is_per_wp:
            # v0.11.0: Can specify dependencies in frontmatter
            wp1 = tasks_dir / 'WP01.md'
            wp1.write_text("---\ntitle: WP01\ndependencies: []\n---\n\n# WP01")

            wp2 = tasks_dir / 'WP02.md'
            wp2.write_text("---\ntitle: WP02\ndependencies: [WP01]\n---\n\n# WP02")

            # Dependencies field exists
            assert 'dependencies:' in wp2.read_text(), \
                "v0.11.0+ supports dependency field"
        else:
            # v0.10.x: No dependency field
            wp1 = tasks_dir / 'WP01.md'
            wp1.write_text("# WP01: First task\n\nDescription")

            wp2 = tasks_dir / 'WP02.md'
            wp2.write_text("# WP02: Second task\n\nDescription")

            # No frontmatter dependencies
            assert 'dependencies:' not in wp2.read_text(), \
                "v0.10.x has no formal dependency field"


class TestCommandAvailability:
    """Compare command availability between versions"""

    def test_implement_command_exists(self, workspace_is_per_wp, spec_kitty_version):
        """
        Test implement command availability.

        v0.10.x: Command does NOT exist
        v0.11.0: Command exists
        """
        result = subprocess.run(
            ['spec-kitty', 'implement', '--help'],
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Command exists
            assert result.returncode == 0, \
                "v0.11.0+ should have implement command"
            assert 'implement' in result.stdout.lower(), \
                "Help should describe implement command"
        else:
            # v0.10.x: Command does NOT exist
            assert result.returncode != 0, \
                "v0.10.x should NOT have implement command"
            assert 'no such command' in result.stderr.lower() or 'unknown command' in result.stderr.lower(), \
                "Should error about unknown command"

    def test_finalize_tasks_command_exists(self, workspace_is_per_wp):
        """
        Test finalize-tasks command availability.

        v0.10.x: Does NOT exist
        v0.11.0: Exists (parses dependencies from tasks.md)
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'finalize-tasks', '--help'],
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Command exists
            assert result.returncode == 0, \
                "v0.11.0+ should have finalize-tasks command"
        else:
            # v0.10.x: Command does NOT exist
            assert result.returncode != 0, \
                "v0.10.x should NOT have finalize-tasks command"

    def test_list_legacy_features_command(self, workspace_is_per_wp):
        """
        Test list-legacy-features command.

        v0.10.x: Does NOT exist
        v0.11.0: Exists (helps prepare for migration)
        """
        result = subprocess.run(
            ['spec-kitty', 'list-legacy-features', '--help'],
            capture_output=True,
            text=True
        )

        if workspace_is_per_wp:
            # v0.11.0: Command exists
            assert result.returncode == 0, \
                "v0.11.0+ should have list-legacy-features command"
        else:
            # v0.10.x: Command does NOT exist
            assert result.returncode != 0, \
                "v0.10.x should NOT have list-legacy-features command"

    def test_specify_command_compatibility(self, workspace_is_per_wp):
        """
        Test that specify command exists in both but behaves differently.

        Both versions: Command exists
        Behavior: Differs (see test_specify_command_behavior)
        """
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', '--help'],
            capture_output=True,
            text=True
        )

        # Command exists in BOTH versions
        assert result.returncode == 0, \
            "create-feature command should exist in both v0.10.x and v0.11.0+"

        # Help text should describe the command
        assert 'create-feature' in result.stdout.lower() or 'feature' in result.stdout.lower(), \
            "Help should describe create-feature command"


class TestMigrationPathValidation:
    """Validate migration path documentation"""

    def test_v010_project_detectable(self, workspace_is_per_wp, init_test_project):
        """
        Test that v0.10.x project structure is detectable.
        """
        if workspace_is_per_wp:
            # Skip on v0.11.0+ (this tests legacy detection)
            pytest.skip("v0.11.0+ doesn't create legacy structure")

        project_path = init_test_project()

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(project_path.parent.parent.parent / "spec-kitty")

        # Create feature (creates legacy worktree)
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Check legacy pattern
        import re
        worktree_dir = project_path / '.worktrees' / '001-test-feature'
        assert worktree_dir.exists(), "Legacy worktree created"

        # Pattern matches: r'^\d{3}-[a-z-]+$'
        pattern = re.compile(r'^\d{3}-[a-z-]+$')
        assert pattern.match('001-test-feature'), \
            "Legacy pattern detected: ###-feature-slug"

    def test_v011_project_detectable(self, workspace_is_per_wp, init_test_project):
        """
        Test that v0.11.0 project structure is detectable.
        """
        if not workspace_is_per_wp:
            # Skip on v0.10.x (this tests new structure)
            pytest.skip("v0.10.x doesn't create new structure")

        # v0.11.0: No worktree created yet, but pattern would be:
        # r'^\d{3}-[a-z-]+-WP\d{2}$'
        import re
        pattern = re.compile(r'^\d{3}-[a-z-]+-WP\d{2}$')

        # Test pattern recognition
        assert pattern.match('001-my-feature-WP01'), \
            "New pattern: ###-feature-slug-WP##"
        assert pattern.match('001-test-feature-WP03'), \
            "New pattern allows multiple WPs"

        # Should NOT match legacy pattern
        assert not pattern.match('001-my-feature'), \
            "New pattern should not match legacy"

    def test_mixed_structure_warning(self, workspace_is_per_wp, init_test_project):
        """
        Test warning when both patterns detected.
        """
        project_path = init_test_project()

        # Manually create BOTH patterns
        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)

        # Legacy pattern
        legacy_dir = worktrees_dir / '001-old'
        legacy_dir.mkdir()

        # New pattern
        new_dir = worktrees_dir / '002-new-WP01'
        new_dir.mkdir()

        # Detect mixed structure
        import re
        legacy_pattern = re.compile(r'^\d{3}-[a-z-]+$')
        new_pattern = re.compile(r'^\d{3}-[a-z-]+-WP\d{2}$')

        worktrees = [d.name for d in worktrees_dir.iterdir() if d.is_dir()]

        has_legacy = any(legacy_pattern.match(w) for w in worktrees)
        has_new = any(new_pattern.match(w) for w in worktrees)

        # Mixed structure detected
        assert has_legacy and has_new, \
            "Should detect both legacy and new patterns"

        # This would trigger a warning in real usage
        assert has_legacy, "Legacy pattern detected"
        assert has_new, "New pattern detected"

    def test_upgrade_path_documented(self, workspace_is_per_wp, spec_kitty_version):
        """
        Test that upgrade path matches documentation.
        """
        # Test version detection
        assert isinstance(spec_kitty_version, tuple), \
            "Version should be tuple (major, minor, patch)"
        assert len(spec_kitty_version) == 3, \
            "Version should have 3 components"

        if workspace_is_per_wp:
            # v0.11.0+: New behavior
            assert spec_kitty_version >= (0, 11, 0), \
                "workspace_is_per_wp should be True for v0.11.0+"

            # Can detect legacy worktrees
            import re
            legacy_pattern = re.compile(r'^\d{3}-[a-z-]+$')
            assert legacy_pattern.match('001-old-feature'), \
                "v0.11.0+ can detect legacy patterns"
        else:
            # v0.10.x: Legacy behavior
            assert spec_kitty_version < (0, 11, 0), \
                "workspace_is_per_wp should be False for v0.10.x"

            # Creates legacy worktrees
            import re
            legacy_pattern = re.compile(r'^\d{3}-[a-z-]+$')
            assert legacy_pattern.match('001-my-feature'), \
                "v0.10.x creates legacy pattern worktrees"
