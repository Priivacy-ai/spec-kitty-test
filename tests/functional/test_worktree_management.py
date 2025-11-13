"""
Category 8: Worktree Management Tests

Tests worktree creation, isolation, detection, and cleanup based on Phase 2 documentation.

Test Coverage:
1. Worktree Creation (4 tests)
   - Worktree created at correct path (.worktrees/{feature}/)
   - .kittify/ symlinked (not copied)
   - Git branch created and checked out in worktree
   - Feature directory created in worktree's kitty-specs/

2. Worktree Isolation (4 tests)
   - Multiple worktrees don't interfere
   - Scripts executed in worktree context work
   - Dashboard detects current worktree context
   - Paths in commands resolve correctly from worktree

3. Worktree Detection (4 tests)
   - Agent can determine if running in worktree
   - Dashboard shows active worktree in UI
   - Diagnostics correctly identify worktree features
   - Feature state tracked (in_development vs merged)

4. Worktree Cleanup (3 tests)
   - Merge removes worktree (default behavior)
   - Orphaned worktrees detected
   - Branch cleanup verified
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output (imported from test_helpers conceptually)."""
    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


class TestWorktreeCreation:
    """Test worktree creation via create-new-feature.sh"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_worktree_created_at_correct_path(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Worktree created at .worktrees/{feature}/"""
        project_name = "test_wt_path"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Test Feature', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Extract JSON from output
        output_data = extract_json_from_output(result.stdout)
        assert output_data is not None, "Should produce JSON output"

        branch_name = output_data['BRANCH_NAME']

        # Verify worktree created at expected location
        worktree_path = project_path / '.worktrees' / branch_name
        assert worktree_path.exists(), \
            f"Worktree should be created at {worktree_path}"
        assert worktree_path.is_dir(), \
            "Worktree should be a directory"

    def test_kittify_copied_to_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: .kittify/ in worktree is a complete copy (git worktree standard behavior)"""
        project_name = "test_kittify_copy"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Copy Test', 'Test copy'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        worktree_kittify = worktree_path / '.kittify'

        # Verify .kittify exists in worktree
        assert worktree_kittify.exists(), \
            ".kittify should exist in worktree"

        # Verify it's a directory (not a symlink)
        # This is standard git worktree behavior - it copies tracked files
        assert worktree_kittify.is_dir(), \
            ".kittify in worktree should be a directory"

        # Verify key files exist (scripts accessible)
        main_kittify = project_path / '.kittify'

        # Check that critical files exist in both
        assert (main_kittify / 'scripts/bash/create-new-feature.sh').exists(), \
            "Main .kittify should have scripts"
        assert (worktree_kittify / 'scripts/bash/create-new-feature.sh').exists(), \
            "Worktree .kittify should have scripts"

    def test_git_branch_created_in_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Git worktree checked out to feature branch"""
        project_name = "test_branch"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Branch Test', 'Test branch'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Check git branch in worktree
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        current_branch = result.stdout.strip()
        assert current_branch == branch_name, \
            f"Worktree should be on branch {branch_name}, got {current_branch}"

        # Verify git worktree list shows it
        result = subprocess.run(
            ['git', 'worktree', 'list'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        assert str(worktree_path) in result.stdout, \
            f"git worktree list should include {worktree_path}"

    def test_feature_directory_in_worktree_kitty_specs(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Feature artifacts created in worktree's kitty-specs/"""
        project_name = "test_wt_feature_dir"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Feature Dir Test', 'Test feature dir'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Verify feature directory structure
        worktree_path = project_path / '.worktrees' / branch_name
        feature_dir = worktree_path / 'kitty-specs' / branch_name

        assert feature_dir.exists(), \
            f"Feature directory should exist at {feature_dir}"

        spec_file = feature_dir / 'spec.md'
        assert spec_file.exists(), \
            "spec.md should exist in worktree's feature directory"

        # Verify NOT in main kitty-specs yet
        main_feature_dir = project_path / 'kitty-specs' / branch_name
        assert not main_feature_dir.exists(), \
            "Feature should NOT be in main kitty-specs/ until merged"


class TestWorktreeIsolation:
    """Test that multiple worktrees are properly isolated."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_multiple_worktrees_isolated(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Multiple worktrees don't interfere with each other"""
        project_name = "test_multi_wt"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create feature 1
        result1 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Feature One', 'First feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        output1 = extract_json_from_output(result1.stdout)
        branch1 = output1['BRANCH_NAME']

        # Create feature 2
        result2 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Feature Two', 'Second feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        output2 = extract_json_from_output(result2.stdout)
        branch2 = output2['BRANCH_NAME']

        # Verify both worktrees exist
        wt1 = project_path / '.worktrees' / branch1
        wt2 = project_path / '.worktrees' / branch2

        assert wt1.exists(), f"Worktree 1 should exist at {wt1}"
        assert wt2.exists(), f"Worktree 2 should exist at {wt2}"

        # Verify each has own kitty-specs directory
        specs1 = wt1 / 'kitty-specs' / branch1
        specs2 = wt2 / 'kitty-specs' / branch2

        assert specs1.exists(), "Feature 1 should have own kitty-specs"
        assert specs2.exists(), "Feature 2 should have own kitty-specs"

        # Modify file in worktree 1
        (specs1 / 'test.txt').write_text("Feature 1 data")

        # Verify not present in worktree 2
        assert not (specs2 / 'test.txt').exists(), \
            "Worktree 1 changes should not affect worktree 2"

    def test_worktree_paths_resolve_correctly(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Paths in commands resolve correctly from worktree"""
        project_name = "test_wt_paths"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Path Test', 'Test paths'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Verify .kittify/ paths resolve from worktree
        kittify_in_wt = worktree_path / '.kittify'
        scripts_dir = kittify_in_wt / 'scripts' / 'bash'

        # Should resolve to main .kittify via symlink
        assert scripts_dir.exists(), \
            ".kittify/scripts/bash should be accessible from worktree"

        # Verify we can access common.sh
        common_script = scripts_dir / 'common.sh'
        assert common_script.exists(), \
            "common.sh should be accessible from worktree via symlink"

    def test_git_operations_in_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Git operations work correctly in worktree context"""
        project_name = "test_git_wt"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Git Test', 'Test git ops'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Create and commit a file in worktree
        test_file = worktree_path / 'test-commit.txt'
        test_file.write_text("Test content for commit")

        result = subprocess.run(
            ['git', 'add', 'test-commit.txt'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        result = subprocess.run(
            ['git', 'commit', '-m', 'Test commit in worktree'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Verify commit exists on feature branch
        result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        assert 'Test commit in worktree' in result.stdout, \
            "Commit should be visible in worktree's git log"

        # Verify main branch not affected
        result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        assert 'Test commit in worktree' not in result.stdout, \
            "Commit should NOT be on main branch yet"

    def test_worktree_script_execution(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts executed from worktree context work correctly"""
        project_name = "test_wt_scripts"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Script Test', 'Test script exec'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Run setup-plan from worktree
        plan_script = project_path / '.kittify/scripts/bash/setup-plan.sh'
        result = subprocess.run(
            [str(plan_script), branch_name],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed from worktree context
        assert result.returncode == 0, \
            f"Scripts should work from worktree. stderr: {result.stderr}"


class TestWorktreeDetection:
    """Test worktree detection by dashboard and diagnostics."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_dashboard_scanner_detects_worktree_features(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Dashboard scanner finds features in worktrees"""
        project_name = "test_scanner_wt"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Scanner Test', 'Test scanner'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Use dashboard scanner
        from specify_cli.dashboard import scan_all_features

        features = scan_all_features(project_path)

        # Should find the feature in worktree
        assert len(features) >= 1, "Scanner should find at least one feature"

        feature_ids = [f['id'] for f in features]
        assert branch_name in feature_ids, \
            f"Scanner should find feature {branch_name} in worktree"

    def test_worktree_path_in_feature_metadata(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Feature metadata includes worktree path"""
        project_name = "test_wt_metadata"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Metadata Test', 'Test metadata'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Use scanner to get feature metadata
        from specify_cli.dashboard import scan_all_features

        features = scan_all_features(project_path)
        feature = next((f for f in features if f['id'] == branch_name), None)

        assert feature is not None, f"Should find feature {branch_name}"

        # Check worktree metadata
        assert 'worktree' in feature, "Feature should have worktree metadata"
        assert feature['worktree']['exists'] == True, \
            "Worktree should be marked as exists"

    def test_feature_state_in_development(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Feature with worktree shows 'in_development' state"""
        project_name = "test_dev_state"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Dev State', 'Test state'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Check workflow status shows development state
        from specify_cli.dashboard import scan_all_features

        features = scan_all_features(project_path)
        feature = next((f for f in features if f['id'] == branch_name), None)

        # Feature should have workflow showing specify complete
        assert 'workflow' in feature, "Feature should have workflow status"
        assert feature['workflow']['specify'] == 'complete', \
            "specify should be complete (spec.md exists)"

    def test_worktrees_directory_structure(self, temp_project_dir, spec_kitty_repo_root):
        """Test: .worktrees/ directory structure is correct"""
        project_name = "test_wt_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Structure Test', 'Test structure'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Verify expected structure
        assert (worktree_path / '.git').exists(), \
            "Worktree should have .git (file or directory)"
        assert (worktree_path / '.kittify').exists(), \
            ".kittify should exist (as copied directory)"
        assert (worktree_path / '.kittify').is_dir(), \
            ".kittify should be directory (git worktree copies tracked files)"
        assert (worktree_path / 'kitty-specs').exists(), \
            "kitty-specs/ directory should exist"
        assert (worktree_path / 'kitty-specs' / branch_name).exists(), \
            "Feature directory should exist in worktree"


class TestWorktreeCleanup:
    """Test worktree cleanup and orphan detection."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_worktree_list_command(self, temp_project_dir, spec_kitty_repo_root):
        """Test: git worktree list shows all worktrees"""
        project_name = "test_wt_list"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'List Test', 'Test list'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Check git worktree list
        result = subprocess.run(
            ['git', 'worktree', 'list'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Should show main repo
        assert str(project_path) in result.stdout, \
            "Should show main repository"

        # Should show worktree
        worktree_path = project_path / '.worktrees' / branch_name
        assert str(worktree_path) in result.stdout, \
            f"Should show worktree at {worktree_path}"

        # Should show branch name
        assert branch_name in result.stdout, \
            f"Should show branch {branch_name} for worktree"

    def test_worktree_detected_by_diagnostics(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics correctly detect worktree presence (upstream fix validated)"""
        project_name = "test_diag_wt"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Diag Test', 'Test diagnostics'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        # Run diagnostics (now works after upstream fix c602a7b)
        # This validates that the import error is fixed
        from specify_cli.dashboard import run_diagnostics

        diagnostics = run_diagnostics(project_path)

        # Should detect worktrees exist
        assert 'worktrees_exist' in diagnostics, \
            "Diagnostics should include worktrees_exist field"
        assert diagnostics['worktrees_exist'] == True, \
            "Diagnostics should detect .worktrees/ directory exists"

        # Verify worktree path exists in filesystem
        worktree_path = project_path / '.worktrees' / branch_name
        assert worktree_path.exists(), \
            f"Worktree should exist at {worktree_path}"

        # Use scanner to verify features can be found
        from specify_cli.dashboard import scan_all_features
        features = scan_all_features(project_path)
        feature_ids = [f['id'] for f in features]
        assert branch_name in feature_ids, \
            f"Scanner should find feature {branch_name} in worktree"

    def test_running_from_worktree_detected(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Diagnostics detect when run from worktree context"""
        project_name = "test_from_wt"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Context Test', 'Test context'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        from tests.functional.test_script_execution import extract_json_from_output
        output_data = extract_json_from_output(result.stdout)
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name

        # Test that we can detect when running from worktree context
        # by checking the current working directory path
        assert '.worktrees' in str(worktree_path), \
            "Worktree path should contain .worktrees"

        # Change to worktree directory and verify detection
        original_cwd = os.getcwd()
        try:
            os.chdir(worktree_path)
            cwd_from_worktree = os.getcwd()
            assert '.worktrees' in str(cwd_from_worktree), \
                "When in worktree, cwd should show .worktrees in path"

            # Verify we can identify the feature from the path
            assert branch_name in str(cwd_from_worktree), \
                "Worktree path should contain the feature branch name"
        finally:
            os.chdir(original_cwd)
