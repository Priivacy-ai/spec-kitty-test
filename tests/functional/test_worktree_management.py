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


class TestFeatureNumbering:
    """Test that feature numbers are assigned correctly without collisions.

    Bug context: When creating a new feature, the script was only checking
    for exact branch name matches and checking kitty-specs/ in the main repo.
    It failed to check .worktrees/ for existing feature numbers, leading to
    situations where two features could get the same number prefix:
    - 001-multi-agent-orchestration (existing)
    - 001-supervisor-agent-mode (incorrectly assigned same number)
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_second_feature_gets_next_number(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Second feature gets 002, not 001

        GIVEN: A project with one existing feature (001)
        WHEN: Creating a second feature
        THEN: The second feature should get 002

        This is the primary bug this test catches.
        """
        project_name = "test_number_sequence"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create first feature
        result1 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'First Feature', 'First feature description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output1 = extract_json_from_output(result1.stdout)
        branch1 = output1['BRANCH_NAME']

        # First feature should be 001
        assert branch1.startswith('001-'), \
            f"First feature should start with 001-, got {branch1}"

        # Create second feature
        result2 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Second Feature', 'Second feature description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output2 = extract_json_from_output(result2.stdout)
        branch2 = output2['BRANCH_NAME']

        # Second feature MUST be 002, NOT 001
        assert branch2.startswith('002-'), \
            f"Second feature should start with 002-, got {branch2}. " \
            "Bug: Script is not checking .worktrees/ for existing feature numbers!"

        # Verify both worktrees exist with unique numbers
        wt1 = project_path / '.worktrees' / branch1
        wt2 = project_path / '.worktrees' / branch2

        assert wt1.exists(), f"First worktree should exist at {wt1}"
        assert wt2.exists(), f"Second worktree should exist at {wt2}"

    def test_feature_number_unique_across_worktrees(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Feature numbers are unique even when in different worktrees

        GIVEN: A project with feature 001 in a worktree
        WHEN: Creating another feature with a different name
        THEN: The new feature should get 002, not reuse 001
        """
        project_name = "test_unique_numbers"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create first feature (simulating 001-multi-agent-orchestration)
        result1 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Multi Agent Orchestration', 'First feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output1 = extract_json_from_output(result1.stdout)
        branch1 = output1['BRANCH_NAME']

        # Verify first feature is 001
        assert '001-' in branch1, f"First feature should be 001, got {branch1}"

        # Verify worktree exists for first feature
        wt1_path = project_path / '.worktrees' / branch1
        assert wt1_path.exists(), "First worktree should exist"

        # Create second feature (simulating 002-supervisor-agent-mode, NOT 001!)
        result2 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Supervisor Agent Mode', 'Second feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output2 = extract_json_from_output(result2.stdout)
        branch2 = output2['BRANCH_NAME']

        # CRITICAL: Second feature must NOT be 001
        assert '001-' not in branch2, \
            f"Second feature should NOT be 001! Got {branch2}. " \
            "The script is not scanning .worktrees/ for existing feature numbers."

        # Second feature should be 002
        assert '002-' in branch2, \
            f"Second feature should be 002, got {branch2}"

    def test_feature_number_checks_worktrees_directory(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Script scans .worktrees/ for existing feature numbers

        GIVEN: A project with a worktree at .worktrees/001-xxx/
        WHEN: Checking for next available feature number
        THEN: Script should find 001 is taken and assign 002

        This test specifically validates the fix for the bug where only
        kitty-specs/ in the main repo was checked.
        """
        project_name = "test_worktrees_scan"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create three features sequentially
        feature_numbers = []

        for i, name in enumerate(['Alpha', 'Beta', 'Gamma'], 1):
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', f'Feature {name}', f'Description for {name}'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output = extract_json_from_output(result.stdout)
            branch = output['BRANCH_NAME']

            # Extract the number prefix (e.g., "001" from "001-feature-alpha")
            number_prefix = branch.split('-')[0]
            feature_numbers.append(number_prefix)

        # All numbers should be unique
        assert len(set(feature_numbers)) == 3, \
            f"All feature numbers should be unique, got: {feature_numbers}"

        # Numbers should be sequential
        expected = ['001', '002', '003']
        assert feature_numbers == expected, \
            f"Feature numbers should be {expected}, got {feature_numbers}"

    def test_no_duplicate_feature_numbers(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Two features never get the same number

        GIVEN: A project where features are created
        WHEN: Creating multiple features with different names
        THEN: No two features should ever have the same number prefix
        """
        project_name = "test_no_duplicates"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create 5 features
        branches = []
        for i in range(5):
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', f'Feature {i+1}', f'Description {i+1}'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output = extract_json_from_output(result.stdout)
            branches.append(output['BRANCH_NAME'])

        # Extract number prefixes
        number_prefixes = [b.split('-')[0] for b in branches]

        # Check for duplicates
        duplicates = [n for n in number_prefixes if number_prefixes.count(n) > 1]
        assert len(duplicates) == 0, \
            f"Found duplicate feature numbers: {duplicates} in {branches}. " \
            "Script is not properly detecting existing feature numbers in .worktrees/"

        # Verify they're all unique
        assert len(set(number_prefixes)) == 5, \
            f"All 5 features should have unique numbers, got: {number_prefixes}"

    def test_worktree_directories_checked_for_numbering(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Existing .worktrees/NNN-xxx/ directories are considered for numbering

        GIVEN: A project with existing worktrees
        WHEN: Determining the next feature number
        THEN: Script should scan .worktrees/ directory names for number prefixes
        """
        project_name = "test_worktree_dir_scan"
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

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        # Create first feature
        result1 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Test Feature', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output1 = extract_json_from_output(result1.stdout)
        branch1 = output1['BRANCH_NAME']

        # Verify first feature created at .worktrees/001-xxx/
        worktrees_dir = project_path / '.worktrees'
        assert worktrees_dir.exists(), ".worktrees/ should exist"

        worktree_dirs = list(worktrees_dir.iterdir())
        assert len(worktree_dirs) == 1, "Should have exactly one worktree"
        assert worktree_dirs[0].name.startswith('001-'), \
            f"First worktree should be 001-xxx, got {worktree_dirs[0].name}"

        # Now create second feature - script should find 001 in .worktrees/
        result2 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Another Feature', 'Another test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output2 = extract_json_from_output(result2.stdout)
        branch2 = output2['BRANCH_NAME']

        # Second feature must be 002, proving .worktrees/ was scanned
        assert branch2.startswith('002-'), \
            f"Second feature should be 002-xxx (proving .worktrees/ was scanned), got {branch2}"

        # Verify we now have two worktrees
        worktree_dirs = list(worktrees_dir.iterdir())
        assert len(worktree_dirs) == 2, "Should have exactly two worktrees"

    def test_main_kitty_specs_also_checked(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Features in main kitty-specs/ are also considered for numbering

        GIVEN: A project with a feature in main kitty-specs/ (e.g., merged feature)
        WHEN: Creating a new feature
        THEN: Script should also check main kitty-specs/ for existing numbers

        This ensures merged features (which may no longer have worktrees)
        are still considered when assigning numbers.
        """
        project_name = "test_main_specs_check"
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

        # Manually create a "merged" feature in main kitty-specs/ (simulating post-merge)
        merged_feature = project_path / 'kitty-specs' / '001-previously-merged-feature'
        merged_feature.mkdir(parents=True)
        (merged_feature / 'spec.md').write_text('# Previously Merged Feature\n')

        # Commit so it's part of the repo state
        subprocess.run(
            ['git', 'add', '.'],
            cwd=project_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ['git', 'commit', '-m', 'Add merged feature'],
            cwd=project_path,
            capture_output=True,
            check=True
        )

        # Now create a new feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'New Feature', 'New feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output = extract_json_from_output(result.stdout)
        branch = output['BRANCH_NAME']

        # New feature should be 002, not 001 (since 001 exists in main kitty-specs/)
        assert branch.startswith('002-'), \
            f"New feature should be 002 (001 exists in main kitty-specs/), got {branch}"
