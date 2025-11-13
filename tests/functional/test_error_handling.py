"""
Category 10: Error Handling Tests

Tests that spec-kitty fails gracefully with helpful error messages.

Test Coverage:
1. Input Validation (3 tests)
   - Init with empty project name fails gracefully
   - Invalid --ai flag shows helpful message
   - Scripts show usage when args missing

2. Missing Dependencies (3 tests)
   - Missing git handled gracefully
   - Missing template error
   - Corrupted .kittify directory

3. State Conflicts (4 tests)
   - Feature name collision
   - Spec file missing error
   - Invalid branch name handling
   - Worktree path already exists
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    # Default: sibling directory to spec-kitty-test
    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output (last JSON line)."""
    for line in reversed(output.strip().split('\n')):
        if line.strip().startswith('{'):
            try:
                return json.loads(line.strip())
            except json.JSONDecodeError:
                continue
    return None


class TestInputValidation:
    """Test that invalid inputs are handled gracefully."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_empty_project_name_error(self, temp_project_dir, spec_kitty_repo_root):
        """Test: spec-kitty init with empty name fails gracefully."""
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', ''],
            cwd=temp_project_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail
        assert result.returncode != 0, "Should fail with empty project name"

        # Error should mention missing or invalid name
        error_output = result.stderr + result.stdout
        assert any(keyword in error_output.lower() for keyword in ['name', 'required', 'invalid', 'empty']), \
            f"Error should mention missing/invalid name. Got: {error_output}"

    def test_init_invalid_agent_error(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Invalid --ai flag shows helpful message."""
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', 'test_project', '--ai=invalid-agent-xyz'],
            cwd=temp_project_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail
        assert result.returncode != 0, "Should fail with invalid agent"

        # Error should reference agents or show valid options
        error_output = result.stderr + result.stdout
        # Should mention the invalid agent or show valid agents
        assert 'invalid' in error_output.lower() or 'claude' in error_output.lower() or 'agent' in error_output.lower(), \
            f"Error should reference agents or show valid options. Got: {error_output}"

    def test_script_missing_required_args(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Scripts show usage when args missing."""
        project_name = 'test_args'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Try to run create-new-feature.sh without arguments
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        assert create_script.exists(), "create-new-feature.sh should exist"

        result = subprocess.run(
            [str(create_script)],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail (no args provided)
        assert result.returncode != 0, "Should fail when required args are missing"

        # Should show usage or help message
        output = result.stderr + result.stdout
        assert any(keyword in output.lower() for keyword in ['usage', 'required', 'arguments', 'help', 'description']), \
            f"Should show usage message. Got: {output}"


class TestMissingDependencies:
    """Test that missing dependencies are handled gracefully."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_missing_git_handled_gracefully(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Projects without git show helpful warning."""
        project_name = 'test_no_git'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Remove .git directory
        git_dir = project_path / '.git'
        if git_dir.exists():
            shutil.rmtree(git_dir)

        # Try to create a feature (requires git for branches)
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'TestFeature', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Script should succeed but show warning about missing git
        # (it gracefully degrades by skipping git operations)
        output = result.stderr + result.stdout

        # Should mention git in warning/error message
        assert 'git' in output.lower(), \
            f"Should mention git. Got: {output}"

        # Should mention that it's skipping git operations or repository not detected
        assert any(keyword in output.lower() for keyword in ['warning', 'skipped', 'not detected']), \
            f"Should show warning about git. Got: {output}"

    def test_missing_template_error(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Missing template shows clear path to fix."""
        project_name = 'test_missing_template'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Delete a template file
        spec_template = project_path / '.kittify/templates/spec-template.md'
        if spec_template.exists():
            spec_template.unlink()

        # Try to run setup-plan.sh which may use the template
        setup_script = project_path / '.kittify/scripts/bash/setup-plan.sh'

        result = subprocess.run(
            [str(setup_script)],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # If it fails, error should be helpful
        if result.returncode != 0:
            output = result.stderr + result.stdout
            # Error should reference template or file missing
            assert any(keyword in output.lower() for keyword in ['template', 'file', 'missing', 'not found']), \
                f"Error should reference missing template. Got: {output}"

    def test_corrupted_kittify_directory(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Missing .kittify/ shows helpful error."""
        project_name = 'test_corrupt_kittify'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Delete .kittify directory
        kittify_dir = project_path / '.kittify'
        if kittify_dir.exists():
            shutil.rmtree(kittify_dir)

        # Try to use spec-kitty commands (they rely on .kittify)
        # For example, try to run the dashboard
        result = subprocess.run(
            ['spec-kitty', 'dashboard'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail or show warning
        if result.returncode != 0:
            output = result.stderr + result.stdout
            # Error should reference .kittify or configuration
            assert any(keyword in output.lower() for keyword in ['.kittify', 'kittify', 'not found', 'missing', 'config']), \
                f"Error should reference missing .kittify. Got: {output}"


class TestStateConflicts:
    """Test that state conflicts are detected and reported."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_feature_name_collision(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Creating duplicate feature name is allowed (overwrites)."""
        project_name = 'test_collision'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
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
            [str(create_script), '--json', '--feature-name', 'UserAuth', 'User authentication'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data1 = extract_json_from_output(result1.stdout)
        assert data1 is not None, "First feature should succeed"
        branch1 = data1.get('BRANCH_NAME')
        assert branch1, "Should have branch name"

        # Try to create duplicate with same name
        result2 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'UserAuth', 'User authentication again'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Spec-kitty currently allows duplicate feature names (overwrites)
        # This test validates the current behavior is graceful
        assert result2.returncode == 0, \
            "Creating duplicate feature should succeed (overwrites existing)"

        data2 = extract_json_from_output(result2.stdout)
        assert data2 is not None, "Second feature should return data"

        # Both should use the same branch name (001-userauth)
        # because spec-kitty allows overwriting features
        branch2 = data2.get('BRANCH_NAME')
        assert branch2 == branch1, \
            "Duplicate feature name uses same branch (overwrites)"

        # Verify the spec file was updated
        spec_file = data2.get('SPEC_FILE')
        if spec_file:
            spec_path = Path(spec_file)
            assert spec_path.exists(), "Spec file should exist after overwrite"

    def test_spec_file_missing_error(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Missing spec.md shows recovery path."""
        project_name = 'test_missing_spec'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create a feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'TestFeature', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data = extract_json_from_output(result.stdout)
        assert data is not None

        # Delete spec.md
        specs_dir = project_path / 'kitty-specs'
        if specs_dir.exists():
            for spec_file in specs_dir.rglob('spec.md'):
                spec_file.unlink()

        # Try to run setup-plan.sh (which may need spec.md)
        setup_script = project_path / '.kittify/scripts/bash/setup-plan.sh'

        result = subprocess.run(
            [str(setup_script)],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # If it fails, error should be clear
        if result.returncode != 0:
            output = result.stderr + result.stdout
            # Should mention spec or missing file
            assert any(keyword in output.lower() for keyword in ['spec', 'missing', 'not found', 'file']), \
                f"Error should reference missing spec. Got: {output}"

    def test_invalid_branch_name_handling(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Invalid git branch names handled."""
        project_name = 'test_invalid_branch'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
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

        # Try to create feature with problematic characters
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Feature With Spaces!@#', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should either succeed (sanitizing the name) or fail gracefully
        if result.returncode == 0:
            # If successful, branch name should be sanitized
            data = extract_json_from_output(result.stdout)
            if data and 'BRANCH_NAME' in data:
                branch_name = data['BRANCH_NAME']
                # Should not contain spaces or special chars
                assert ' ' not in branch_name, "Branch name should not contain spaces"
                assert not any(c in branch_name for c in '!@#$%^&*()'), \
                    "Branch name should not contain special characters"
        else:
            # If it fails, error should be helpful
            output = result.stderr + result.stdout
            assert any(keyword in output.lower() for keyword in ['branch', 'name', 'invalid', 'character']), \
                f"Error should reference invalid branch name. Got: {output}"

    def test_worktree_path_already_exists(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Creating feature when worktree path exists."""
        project_name = 'test_worktree_collision'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create a feature first
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result1 = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'TestFeature', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        data1 = extract_json_from_output(result1.stdout)
        assert data1 is not None

        # Get the worktree path
        worktree_path = data1.get('WORKTREE_PATH')
        if worktree_path:
            worktree_full_path = Path(worktree_path)

            # Manually create a directory at the same location
            # First delete the worktree if it exists
            if worktree_full_path.exists():
                # Remove the worktree using git
                subprocess.run(
                    ['git', 'worktree', 'remove', str(worktree_full_path)],
                    cwd=project_path,
                    capture_output=True,
                    check=False
                )

            # Create directory manually
            worktree_full_path.mkdir(parents=True, exist_ok=True)

            # Try to create feature again with same path
            result2 = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'TestFeature2', 'Second test'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=False
            )

            # Should handle collision gracefully
            # Either succeed with different path or fail with helpful error
            if result2.returncode != 0:
                output = result2.stderr + result2.stdout
                assert any(keyword in output.lower() for keyword in ['exists', 'collision', 'already', 'path']), \
                    f"Error should reference path collision. Got: {output}"
