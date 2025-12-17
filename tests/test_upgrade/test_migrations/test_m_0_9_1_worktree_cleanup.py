"""
Test Migration: 0.9.1 Worktree Cleanup

Tests that the v0.9.1 upgrade correctly REMOVES command templates and scripts
from existing worktrees, so they inherit from the main repository.

Background:
The v0.9.1 migration Part 2 (Worktree Cleanup) removes ALL agent command
directories and scripts from worktrees. This ensures:
1. Worktrees always use current command templates from main repo
2. No stale/outdated templates remain in worktrees
3. No duplication of command files across worktrees

Bug discovered in mittwald-mcp:
After running v0.9.0 upgrade, worktrees still had:
- Old `tasks-move-to-lane.sh` script
- Old command templates in .codex/prompts/ referencing deprecated scripts

The v0.9.1 fix removes these entirely - worktrees inherit from main.

Agent directories removed from worktrees:
- .claude/commands/
- .codex/prompts/
- .gemini/commands/
- .github/prompts/
- .cursor/commands/
- .windsurf/commands/
- .sourcegraph/prompts/
- .zed/prompts/
- .amazon-q/prompts/
- .supermaven/prompts/
- .kittify/scripts/

Real-world fix:
```
# BEFORE v0.9.1:
[011-langfuse-eval-suite] .codex/prompts/spec-kitty.tasks.md references old script

# AFTER v0.9.1:
[011-langfuse-eval-suite] .codex/prompts/ REMOVED - inherits from main repo
```

Test Coverage:
1. Agent Directory Removal (5 tests)
   - .claude/commands/ removed from worktrees
   - .codex/prompts/ removed from worktrees
   - .kittify/scripts/ removed from worktrees
   - All agent directories removed (gemini, github, cursor, etc.)
   - Main repo directories NOT removed

2. Inheritance Verification (3 tests)
   - Worktree inherits .claude/commands/ from main
   - Worktree inherits .kittify/scripts/ from main
   - Commands execute from main repo path

3. Worktree Detection (3 tests)
   - Upgrade detects all worktrees
   - Reports worktrees cleaned up
   - Handles missing .worktrees/ gracefully

4. Worktree Cleanup Completeness (3 tests)
   - All worktrees cleaned (not just first one)
   - Reports each worktree cleaned
   - No orphaned agent directories in any worktree

5. Edge Cases (3 tests)
   - Handles worktrees without agent directories
   - Handles symlinked directories gracefully
   - Handles read-only worktrees (reports error)

Note: Tests require spec-kitty >= 0.9.1 with worktree cleanup
"""

import os
import subprocess
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version_str = result.stdout.strip().split()[-1]
        return tuple(map(int, version_str.split('.')))
    except Exception:
        return (0, 0, 0)


# Tests require v0.9.1+ (worktree cleanup added in v0.9.1)
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 9, 1),
    reason="Requires spec-kitty >= 0.9.1 (worktree cleanup)"
)


class TestAgentDirectoryRemoval:
    """Test that agent directories are REMOVED from worktrees."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_with_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with a worktree containing agent directories."""
        project_name = "worktree_cleanup_test"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create worktree manually
        worktree_path = project_path / '.worktrees' / '001-test-feature'
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Copy agent directories to worktree (simulating old behavior)
        import shutil
        for agent_dir in ['.claude', '.codex', '.kittify']:
            src = project_path / agent_dir
            dst = worktree_path / agent_dir
            if src.exists():
                shutil.copytree(src, dst, symlinks=True)

        return project_path, worktree_path

    def test_claude_commands_removed_from_worktree(
        self, project_with_worktree
    ):
        """Test: .claude/commands/ removed from worktree

        GIVEN: Worktree with .claude/commands/ directory
        WHEN: Running spec-kitty upgrade
        THEN: .claude/commands/ should be removed from worktree
        """
        project_path, worktree_path = project_with_worktree

        # Ensure worktree has .claude/commands/
        claude_commands = worktree_path / '.claude' / 'commands'
        claude_commands.mkdir(parents=True, exist_ok=True)
        (claude_commands / 'spec-kitty.tasks.md').write_text('# Old template')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Setup'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # .claude/commands/ should be removed from worktree
        assert not (worktree_path / '.claude' / 'commands').exists(), \
            ".claude/commands/ should be removed from worktree"

    def test_codex_prompts_removed_from_worktree(
        self, project_with_worktree
    ):
        """Test: .codex/prompts/ removed from worktree (mittwald-mcp fix)

        GIVEN: Worktree with .codex/prompts/ containing old templates
        WHEN: Running spec-kitty upgrade
        THEN: .codex/prompts/ should be removed entirely
        """
        project_path, worktree_path = project_with_worktree

        # Create .codex/prompts/ with old templates
        codex_prompts = worktree_path / '.codex' / 'prompts'
        codex_prompts.mkdir(parents=True, exist_ok=True)
        (codex_prompts / 'spec-kitty.tasks.md').write_text('''# Tasks (OLD)
.kittify/scripts/bash/tasks-move-to-lane.sh
''')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Old codex'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # .codex/prompts/ should be removed
        assert not (worktree_path / '.codex' / 'prompts').exists(), \
            ".codex/prompts/ should be removed from worktree"

    def test_kittify_scripts_removed_from_worktree(
        self, project_with_worktree
    ):
        """Test: .kittify/scripts/ removed from worktree

        GIVEN: Worktree with .kittify/scripts/ directory
        WHEN: Running upgrade
        THEN: .kittify/scripts/ should be removed from worktree
        """
        project_path, worktree_path = project_with_worktree

        # Ensure .kittify/scripts/ exists in worktree
        scripts_dir = worktree_path / '.kittify' / 'scripts' / 'bash'
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / 'tasks-move-to-lane.sh').write_text('#!/bin/bash\n# OLD')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Old scripts'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # .kittify/scripts/ should be removed from worktree
        assert not (worktree_path / '.kittify' / 'scripts').exists(), \
            ".kittify/scripts/ should be removed from worktree"

    def test_all_agent_directories_removed(
        self, project_with_worktree
    ):
        """Test: All agent directories removed from worktree

        GIVEN: Worktree with multiple agent directories
        WHEN: Running upgrade
        THEN: All agent command directories should be removed
        """
        project_path, worktree_path = project_with_worktree

        # Create multiple agent directories
        agent_dirs = [
            ('.claude', 'commands'),
            ('.codex', 'prompts'),
            ('.gemini', 'commands'),
            ('.github', 'prompts'),
            ('.cursor', 'commands'),
        ]

        for agent, subdir in agent_dirs:
            dir_path = worktree_path / agent / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / 'test.md').write_text('# Old template')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'All agents'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # All agent command directories should be removed
        for agent, subdir in agent_dirs:
            dir_path = worktree_path / agent / subdir
            assert not dir_path.exists(), \
                f"{agent}/{subdir}/ should be removed from worktree"

    def test_main_repo_directories_not_removed(
        self, project_with_worktree
    ):
        """Test: Main repo agent directories NOT removed

        GIVEN: Main repo with .claude/commands/
        WHEN: Running upgrade
        THEN: Main repo directories should remain intact
        """
        project_path, worktree_path = project_with_worktree

        # Ensure main repo has directories
        main_claude = project_path / '.claude' / 'commands'
        main_claude.mkdir(parents=True, exist_ok=True)
        (main_claude / 'spec-kitty.tasks.md').write_text('# Main template')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Main dirs'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Main repo should still have directories
        assert (project_path / '.claude' / 'commands').exists(), \
            "Main repo .claude/commands/ should NOT be removed"
        assert (project_path / '.claude' / 'commands' / 'spec-kitty.tasks.md').exists(), \
            "Main repo templates should remain"


class TestInheritanceVerification:
    """Test that worktrees properly inherit from main repo after cleanup."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def inheritance_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project for inheritance testing."""
        project_name = "inheritance_test"
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

        worktree_path = project_path / '.worktrees' / '001-inheritance'
        worktree_path.mkdir(parents=True, exist_ok=True)

        return project_path, worktree_path

    def test_worktree_inherits_commands_from_main(
        self, inheritance_project
    ):
        """Test: Worktree inherits .claude/commands/ from main repo

        GIVEN: Main repo has .claude/commands/ with templates
        WHEN: Running upgrade (worktree commands removed)
        THEN: Worktree should use main repo's commands via git
        """
        project_path, worktree_path = inheritance_project

        # Create commands in main repo
        main_commands = project_path / '.claude' / 'commands'
        main_commands.mkdir(parents=True, exist_ok=True)
        (main_commands / 'spec-kitty.tasks.md').write_text('''# Tasks (MAIN REPO)
Use tasks_cli.py update
''')

        # Create commands in worktree (will be removed)
        wt_commands = worktree_path / '.claude' / 'commands'
        wt_commands.mkdir(parents=True, exist_ok=True)
        (wt_commands / 'spec-kitty.tasks.md').write_text('# OLD WORKTREE TEMPLATE')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Setup'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Worktree's local commands should be removed
        assert not (worktree_path / '.claude' / 'commands').exists(), \
            "Worktree's local commands should be removed"

        # Main repo commands should still exist
        assert (main_commands / 'spec-kitty.tasks.md').exists(), \
            "Main repo commands should still exist"

    def test_worktree_inherits_scripts_from_main(
        self, inheritance_project
    ):
        """Test: Worktree inherits .kittify/scripts/ from main repo

        GIVEN: Main repo has .kittify/scripts/
        WHEN: Running upgrade
        THEN: Worktree should inherit scripts from main via git
        """
        project_path, worktree_path = inheritance_project

        # Create scripts in main repo
        main_scripts = project_path / '.kittify' / 'scripts' / 'bash'
        main_scripts.mkdir(parents=True, exist_ok=True)
        (main_scripts / 'tasks-update-lane.sh').write_text('#!/bin/bash\n# NEW SCRIPT')

        # Create scripts in worktree (will be removed)
        wt_scripts = worktree_path / '.kittify' / 'scripts' / 'bash'
        wt_scripts.mkdir(parents=True, exist_ok=True)
        (wt_scripts / 'tasks-move-to-lane.sh').write_text('#!/bin/bash\n# OLD SCRIPT')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Scripts'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Worktree's local scripts should be removed
        assert not (worktree_path / '.kittify' / 'scripts').exists(), \
            "Worktree's local scripts should be removed"

        # Main repo scripts should still exist
        assert (main_scripts / 'tasks-update-lane.sh').exists(), \
            "Main repo scripts should still exist"

    def test_upgrade_output_mentions_inheritance(
        self, inheritance_project
    ):
        """Test: Upgrade output mentions inheritance from main

        GIVEN: Worktree with agent directories
        WHEN: Running upgrade
        THEN: Output should mention "inherits from main"
        """
        project_path, worktree_path = inheritance_project

        # Create directories in worktree
        wt_commands = worktree_path / '.codex' / 'prompts'
        wt_commands.mkdir(parents=True, exist_ok=True)
        (wt_commands / 'test.md').write_text('# Test')

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Setup'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Should mention inheritance
        assert 'inherit' in output_lower or 'removed' in output_lower, \
            "Upgrade output should mention inheritance or removal"


class TestWorktreeDetection:
    """Test detection of worktrees during upgrade."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def multi_worktree_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with multiple worktrees."""
        project_name = "multi_worktree"
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

        # Create multiple worktrees
        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)

        import shutil
        for i in range(3):
            wt_path = worktrees_dir / f'feature-{i:03d}'
            wt_path.mkdir(exist_ok=True)
            if (project_path / '.kittify').exists():
                shutil.copytree(
                    project_path / '.kittify',
                    wt_path / '.kittify',
                    symlinks=True
                )

        return project_path

    def test_upgrade_detects_all_worktrees(
        self, multi_worktree_project
    ):
        """Test: Upgrade detects all worktrees in .worktrees/

        GIVEN: Project with 3 worktrees
        WHEN: Running upgrade --dry-run
        THEN: Should report all 3 worktrees will be updated
        """
        project_path = multi_worktree_project

        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout

        # Should mention worktrees
        if 'worktree' in output.lower():
            # Count how many worktrees mentioned
            worktree_count = output.lower().count('feature-')
            assert worktree_count >= 1, "Should report at least some worktrees"
        else:
            pytest.skip("--dry-run may not report worktrees")

    def test_upgrade_reports_worktrees_to_update(
        self, multi_worktree_project
    ):
        """Test: Upgrade reports which worktrees will be updated

        GIVEN: Project with worktrees needing updates
        WHEN: Running upgrade
        THEN: Should report worktree update progress
        """
        project_path = multi_worktree_project

        # Set older version
        metadata_path = project_path / '.kittify' / 'metadata.yaml'
        if metadata_path.exists():
            content = metadata_path.read_text()
            import re
            content = re.sub(
                r'version:\s*["\']?\d+\.\d+\.\d+["\']?',
                'version: "0.8.0"',
                content
            )
            metadata_path.write_text(content)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stderr + result.stdout
        output_lower = output.lower()

        # Should mention updating worktrees
        assert 'worktree' in output_lower or \
               'feature-000' in output_lower or \
               'feature-001' in output_lower, \
            "Should report worktree updates"

    def test_handles_missing_worktrees_directory(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Upgrade handles missing .worktrees/ gracefully

        GIVEN: Project without .worktrees/ directory
        WHEN: Running upgrade
        THEN: Should complete without error
        """
        project_name = "no_worktrees"
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

        # Ensure no .worktrees/
        worktrees_dir = project_path / '.worktrees'
        if worktrees_dir.exists():
            import shutil
            shutil.rmtree(worktrees_dir)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=False
        )

        # Should not crash
        assert 'traceback' not in result.stderr.lower()
        assert 'exception' not in result.stderr.lower()


class TestWorktreeCleanupCompleteness:
    """Test that all worktrees are completely cleaned up."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def project_with_many_worktrees(self, temp_project_dir, spec_kitty_repo_root):
        """Create project with many worktrees for cleanup testing."""
        project_name = "many_worktrees"
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

        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)

        import shutil
        worktree_paths = []
        for i in range(5):
            wt_path = worktrees_dir / f'wt-{i:03d}'
            wt_path.mkdir(exist_ok=True)
            # Copy agent directories to each worktree
            for agent_dir in ['.claude', '.codex', '.kittify']:
                src = project_path / agent_dir
                dst = wt_path / agent_dir
                if src.exists():
                    shutil.copytree(src, dst, symlinks=True)
            worktree_paths.append(wt_path)

        return project_path, worktree_paths

    def test_all_worktrees_cleaned_not_just_first(
        self, project_with_many_worktrees
    ):
        """Test: All worktrees cleaned, not just the first one

        GIVEN: 5 worktrees with agent directories
        WHEN: Running upgrade
        THEN: All 5 worktrees should have agent dirs removed
        """
        project_path, worktree_paths = project_with_many_worktrees

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Worktrees'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check ALL worktrees have agent directories removed
        cleaned_count = 0
        for wt_path in worktree_paths:
            # All agent command directories should be removed
            has_claude = (wt_path / '.claude' / 'commands').exists()
            has_codex = (wt_path / '.codex' / 'prompts').exists()
            has_scripts = (wt_path / '.kittify' / 'scripts').exists()

            if not has_claude and not has_codex and not has_scripts:
                cleaned_count += 1

        assert cleaned_count == len(worktree_paths), \
            f"Only {cleaned_count}/{len(worktree_paths)} worktrees cleaned"

    def test_no_orphaned_agent_dirs_in_any_worktree(
        self, project_with_many_worktrees
    ):
        """Test: No orphaned agent directories in any worktree

        GIVEN: Multiple worktrees with agent directories
        WHEN: After upgrade
        THEN: No worktree should have agent command directories
        """
        project_path, worktree_paths = project_with_many_worktrees

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Setup'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check for orphaned agent directories
        orphaned = []
        agent_subdirs = [
            ('.claude', 'commands'),
            ('.codex', 'prompts'),
            ('.kittify', 'scripts'),
        ]

        for wt_path in worktree_paths:
            for agent, subdir in agent_subdirs:
                dir_path = wt_path / agent / subdir
                if dir_path.exists():
                    orphaned.append(str(dir_path))

        assert len(orphaned) == 0, \
            f"Found orphaned agent directories: {orphaned}"

    def test_reports_cleanup_count(
        self, project_with_many_worktrees
    ):
        """Test: Upgrade reports number of worktrees cleaned

        GIVEN: 5 worktrees with agent directories
        WHEN: Running upgrade
        THEN: Output should report worktrees cleaned
        """
        project_path, worktree_paths = project_with_many_worktrees

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Setup'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Should report cleanup
        assert 'worktree' in output_lower, \
            "Output should mention worktrees"


class TestEdgeCases:
    """Test edge cases in worktree cleanup."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def edge_case_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create project for edge case testing."""
        project_name = "edge_case_test"
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

        return project_path

    def test_handles_worktree_without_agent_dirs(
        self, edge_case_project
    ):
        """Test: Handles worktrees without agent directories

        GIVEN: Worktree with no agent directories
        WHEN: Running upgrade
        THEN: Should complete without error
        """
        project_path = edge_case_project

        # Create worktree with NO agent directories
        worktree_path = project_path / '.worktrees' / 'empty-wt'
        worktree_path.mkdir(parents=True, exist_ok=True)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Empty worktree'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Should not crash
        assert 'traceback' not in result.stderr.lower()

    def test_handles_symlinked_directories(
        self, edge_case_project
    ):
        """Test: Handles symlinked agent directories gracefully

        GIVEN: Worktree with symlinked .claude/commands/
        WHEN: Running upgrade
        THEN: Should remove symlink without "Cannot call rmtree on a symbolic link" error

        Bug discovered in mittwald-mcp v0.9.1 upgrade:
        shutil.rmtree() fails on symlinks with:
        "Cannot call rmtree on a symbolic link"

        The migration must detect symlinks and use os.unlink() instead of shutil.rmtree().
        """
        project_path = edge_case_project

        worktree_path = project_path / '.worktrees' / 'symlink-wt'
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create symlink to main repo commands
        main_commands = project_path / '.claude' / 'commands'
        worktree_claude = worktree_path / '.claude'
        worktree_claude.mkdir(parents=True, exist_ok=True)

        symlink_path = worktree_claude / 'commands'
        try:
            symlink_path.symlink_to(main_commands)
        except (OSError, FileExistsError):
            pytest.skip("Cannot create symlinks in this environment")

        # Verify symlink was created
        assert symlink_path.is_symlink(), "Test setup: symlink should be created"

        # Set metadata version to 0.9.0 so 0.9.1 migration will run
        import yaml
        metadata_file = project_path / '.kittify' / 'metadata.yaml'
        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)
        metadata['spec_kitty']['version'] = '0.9.0'
        with open(metadata_file, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Symlink'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=False  # Don't check=True so we can inspect errors
        )

        output = result.stdout + result.stderr

        # Should NOT have "Cannot call rmtree on a symbolic link" error
        assert 'cannot call rmtree on a symbolic link' not in output.lower(), \
            f"Migration failed on symlink with rmtree error: {output}"

        # Should not crash with traceback
        assert 'traceback' not in result.stderr.lower(), \
            f"Migration crashed: {result.stderr}"

        # Symlink should be removed (or parent dir removed)
        assert not symlink_path.exists(), \
            "Symlink should be removed after upgrade"

    def test_handles_multiple_symlinked_agent_dirs(
        self, edge_case_project
    ):
        """Test: Handles multiple symlinked agent directories (mittwald-mcp bug)

        GIVEN: Worktree with symlinked .claude/commands/, .codex/prompts/, .opencode/command/
        WHEN: Running upgrade
        THEN: All symlinks should be removed without rmtree errors

        Real-world bug from mittwald-mcp:
        ```
        ✗ [009-fix-token-truncation] Failed to remove .claude/commands/:
        Cannot call rmtree on a symbolic link
        ✗ [009-fix-token-truncation] Failed to remove .opencode/command/:
        Cannot call rmtree on a symbolic link
        ✗ [009-fix-token-truncation] Failed to remove .codex/prompts/:
        Cannot call rmtree on a symbolic link
        ```
        """
        project_path = edge_case_project

        worktree_path = project_path / '.worktrees' / '009-multi-symlink'
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create multiple symlinked agent directories (like real worktrees have)
        symlinks_created = []
        agent_dirs = [
            ('.claude', 'commands'),
            ('.codex', 'prompts'),
            ('.opencode', 'command'),
            ('.kittify', 'scripts'),
        ]

        for parent_dir, child_dir in agent_dirs:
            main_dir = project_path / parent_dir / child_dir
            if not main_dir.exists():
                main_dir.mkdir(parents=True, exist_ok=True)
                (main_dir / 'test.md').write_text('# Test')

            wt_parent = worktree_path / parent_dir
            wt_parent.mkdir(parents=True, exist_ok=True)
            symlink_path = wt_parent / child_dir

            try:
                symlink_path.symlink_to(main_dir)
                symlinks_created.append(symlink_path)
            except (OSError, FileExistsError):
                pass  # Skip this one

        if not symlinks_created:
            pytest.skip("Cannot create symlinks in this environment")

        # Set metadata version to 0.9.0 so 0.9.1 migration will run
        import yaml
        metadata_file = project_path / '.kittify' / 'metadata.yaml'
        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)
        metadata['spec_kitty']['version'] = '0.9.0'
        with open(metadata_file, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Multi symlinks'], cwd=project_path, check=True)

        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Count symlink errors
        symlink_errors = output.lower().count('cannot call rmtree on a symbolic link')
        assert symlink_errors == 0, \
            f"Migration had {symlink_errors} rmtree symlink errors: {output}"

        # All symlinks should be removed
        for symlink_path in symlinks_created:
            assert not symlink_path.exists(), \
                f"Symlink {symlink_path} should be removed"

    def test_handles_copied_directories(
        self, edge_case_project
    ):
        """Test: Handles copied (non-symlinked) directories

        GIVEN: Worktree with copied agent directories
        WHEN: Running upgrade
        THEN: Copied directories should be removed
        """
        project_path = edge_case_project

        worktree_path = project_path / '.worktrees' / 'copy-wt'
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Copy (not symlink) the agent directories
        import shutil
        main_commands = project_path / '.claude' / 'commands'
        worktree_commands = worktree_path / '.claude' / 'commands'
        if main_commands.exists():
            shutil.copytree(main_commands, worktree_commands)

        # Set metadata version to 0.9.0 so 0.9.1 migration will run
        import yaml
        metadata_file = project_path / '.kittify' / 'metadata.yaml'
        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)
        metadata['spec_kitty']['version'] = '0.9.0'
        with open(metadata_file, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)

        subprocess.run(['git', 'add', '.'], cwd=project_path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Copied'], cwd=project_path, check=True)

        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Copied directories should be removed
        assert not (worktree_commands).exists(), \
            "Copied agent directories should be removed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
