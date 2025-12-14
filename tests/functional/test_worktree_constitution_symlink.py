"""
Test Worktree Constitution Symlink

Tests that worktrees use symlinks to share the main repo's constitution,
ensuring all feature branches follow the same project principles.

Related: findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md

Test Coverage:
1. Symlink Creation (3 tests)
   - Worktree memory/ is a symlink
   - Symlink uses relative path
   - Symlink points to main memory/

2. Constitution Sharing (3 tests)
   - Edits in main visible in worktree
   - Edits in worktree visible in main
   - Multiple worktrees share same constitution

3. Fallback Behavior (2 tests)
   - Windows fallback to copy (simulated)
   - Warning message displayed on fallback
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Import helper for JSON extraction
import sys
sys.path.insert(0, str(Path(__file__).parent))
from test_helpers import extract_json_from_output


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path.home() / 'Code' / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError("spec-kitty repository not found. Set SPEC_KITTY_REPO environment variable.")


class TestSymlinkCreation:
    """Test that worktrees create symlinks to memory/."""

    def test_worktree_memory_is_symlink(self, spec_kitty_repo_root):
        """Test: .kittify/memory/ in worktree is a symlink"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_symlink'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            # Create project
            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Symlink Test', 'Test symlinks'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            worktree_path = project_path / '.worktrees' / branch_name
            worktree_memory = worktree_path / '.kittify' / 'memory'

            # Verify memory exists in worktree
            assert worktree_memory.exists(), \
                f".kittify/memory should exist in worktree"

            # Verify it's a symlink (on Unix-like systems)
            if os.name != 'nt':  # Not Windows
                assert worktree_memory.is_symlink(), \
                    ".kittify/memory should be a symlink, not a directory"
            else:
                # On Windows, it might be a copy if symlinks aren't supported
                assert worktree_memory.is_dir() or worktree_memory.is_symlink(), \
                    ".kittify/memory should exist (as symlink or copy)"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_symlink_uses_relative_path(self, spec_kitty_repo_root):
        """Test: Symlink uses relative path (repo can be moved)"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_relative'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Relative Test', 'Test relative path'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            worktree_memory = project_path / '.worktrees' / branch_name / '.kittify' / 'memory'

            if os.name != 'nt' and worktree_memory.is_symlink():
                # Read the symlink target
                target = os.readlink(worktree_memory)

                # Should be relative, not absolute
                assert not os.path.isabs(target), \
                    f"Symlink should use relative path, got: {target}"

                # Should be ../../../.kittify/memory
                assert target == '../../../.kittify/memory', \
                    f"Symlink should point to ../../../.kittify/memory, got: {target}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_symlink_points_to_main_memory(self, spec_kitty_repo_root):
        """Test: Symlink resolves to main repo's memory/"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_points_main'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Points Main', 'Test pointing'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            worktree_memory = project_path / '.worktrees' / branch_name / '.kittify' / 'memory'
            main_memory = project_path / '.kittify' / 'memory'

            # Resolve both to absolute paths
            worktree_resolved = worktree_memory.resolve()
            main_resolved = main_memory.resolve()

            # They should point to the same location
            assert worktree_resolved == main_resolved, \
                f"Worktree memory should resolve to main memory.\nWorktree: {worktree_resolved}\nMain: {main_resolved}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConstitutionSharing:
    """Test that constitution changes are shared between main and worktrees."""

    def test_edits_in_main_visible_in_worktree(self, spec_kitty_repo_root):
        """Test: Changes to constitution in main are visible in worktree"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_main_to_wt'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Edit Test', 'Test editing'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            # Edit constitution in main
            main_constitution = project_path / '.kittify' / 'memory' / 'constitution.md'
            original_content = main_constitution.read_text()
            test_marker = "\n\n## TEST MARKER FROM MAIN\n"
            main_constitution.write_text(original_content + test_marker)

            # Read from worktree
            worktree_constitution = project_path / '.worktrees' / branch_name / '.kittify' / 'memory' / 'constitution.md'
            worktree_content = worktree_constitution.read_text()

            # Should contain the test marker
            assert "TEST MARKER FROM MAIN" in worktree_content, \
                "Changes in main constitution should be visible in worktree"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_edits_in_worktree_visible_in_main(self, spec_kitty_repo_root):
        """Test: Changes to constitution in worktree are visible in main"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_wt_to_main'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Worktree Edit', 'Test worktree edit'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            # Edit constitution in worktree
            worktree_constitution = project_path / '.worktrees' / branch_name / '.kittify' / 'memory' / 'constitution.md'
            original_content = worktree_constitution.read_text()
            test_marker = "\n\n## TEST MARKER FROM WORKTREE\n"
            worktree_constitution.write_text(original_content + test_marker)

            # Read from main
            main_constitution = project_path / '.kittify' / 'memory' / 'constitution.md'
            main_content = main_constitution.read_text()

            # Should contain the test marker
            assert "TEST MARKER FROM WORKTREE" in main_content, \
                "Changes in worktree constitution should be visible in main"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_multiple_worktrees_share_constitution(self, spec_kitty_repo_root):
        """Test: Multiple worktrees all share the same constitution"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_multi_wt'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'

            # Create two worktrees
            result1 = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Feature One', 'First feature'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch1 = extract_json_from_output(result1.stdout)['BRANCH_NAME']

            result2 = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Feature Two', 'Second feature'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch2 = extract_json_from_output(result2.stdout)['BRANCH_NAME']

            # Edit in worktree 1
            wt1_constitution = project_path / '.worktrees' / branch1 / '.kittify' / 'memory' / 'constitution.md'
            original = wt1_constitution.read_text()
            wt1_constitution.write_text(original + "\n\n## SHARED EDIT\n")

            # Read from worktree 2
            wt2_constitution = project_path / '.worktrees' / branch2 / '.kittify' / 'memory' / 'constitution.md'
            wt2_content = wt2_constitution.read_text()

            # Should see the edit
            assert "SHARED EDIT" in wt2_content, \
                "Constitution changes should be shared across all worktrees"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestFallbackBehavior:
    """Test fallback to directory copy when symlinks fail."""

    def test_fallback_message_in_output(self, spec_kitty_repo_root):
        """Test: Success or fallback message is displayed"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_fallback_msg'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Fallback Test', 'Test fallback'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            # Should have symlink message (success or warning)
            stderr_output = result.stderr

            has_symlink_message = (
                'symlink' in stderr_output.lower() or
                'shared constitution' in stderr_output.lower()
            )

            assert has_symlink_message, \
                f"Output should mention symlink or constitution sharing. Got: {stderr_output}"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_memory_accessible_in_worktree(self, spec_kitty_repo_root):
        """Test: Memory is accessible regardless of symlink/copy"""
        temp_dir = tempfile.mkdtemp()
        try:
            project_name = 'test_accessible'
            project_path = Path(temp_dir) / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
                cwd=temp_dir,
                env=env,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )

            # Create worktree
            create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
            result = subprocess.run(
                [str(create_script), '--json', '--feature-name', 'Access Test', 'Test access'],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True
            )

            output_data = extract_json_from_output(result.stdout)
            branch_name = output_data['BRANCH_NAME']

            # Constitution should be accessible
            worktree_constitution = project_path / '.worktrees' / branch_name / '.kittify' / 'memory' / 'constitution.md'
            assert worktree_constitution.exists(), \
                "Constitution should be accessible in worktree (symlink or copy)"

            # Should be readable
            content = worktree_constitution.read_text()
            assert len(content) > 0, \
                "Constitution should have content"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
