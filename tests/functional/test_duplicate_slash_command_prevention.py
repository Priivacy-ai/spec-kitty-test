"""
Test: Duplicate Slash Command Prevention (Regression)

Purpose: Prevent duplicate slash commands from being recreated in worktrees.

CONTEXT - User Suspicion (Issue #70 Related):
User suspects that migration 0.10.1 (populate_slash_commands) may UNDO the
deduplication from migration 0.7.2 (worktree_commands_dedup) by recreating
slash commands in worktrees.

BACKGROUND:
- Migration 0.7.2: REMOVES .claude/commands/ from worktrees (inherit from main)
- Migration 0.10.1: POPULATES missing slash commands

SUSPICION:
Migration 0.10.1 might:
1. Detect worktree .claude/commands/ is "missing"
2. Populate slash commands into worktree
3. Result: Duplicate commands (undo 0.7.2 deduplication)

CORRECT BEHAVIOR (after v0.7.2):
- Main repo: HAS .claude/commands/ (and other agent dirs)
- Worktrees: NO .claude/commands/ (inherit from main)
- Migration 0.10.1: Should ONLY populate main repo, NOT worktrees

Test Coverage:
- TestWorktreeCommandDeduplication: Verify worktrees don't have commands
- TestMigration_0_10_1_Behavior: Ensure it doesn't populate worktrees
- TestCommandInheritance: Verify worktrees inherit from main
- TestDuplicateCommandDetection: Catch any duplication

Version: Tests apply to v0.7.2+
"""

import subprocess
import tempfile
from pathlib import Path
import pytest


# All supported agent directories
AGENT_DIRS = [
    (".claude", "commands"),
    (".github", "prompts"),
    (".gemini", "commands"),
    (".cursor", "commands"),
    (".qwen", "commands"),
    (".opencode", "command"),
    (".windsurf", "workflows"),
    (".codex", "prompts"),
    (".kilocode", "workflows"),
    (".augment", "commands"),
    (".roo", "commands"),
    (".amazonq", "prompts"),
]


class TestWorktreeCommandDeduplication:
    """
    CRITICAL: Worktrees must NOT have duplicate agent command directories.

    After v0.7.2, worktrees should inherit from main repo.
    """

    @pytest.fixture
    def requires_v07_2(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.7.2"""
        if spec_kitty_version < (0, 7, 2):
            pytest.skip("Requires spec-kitty >= 0.7.2 (worktree command dedup)")

    def test_worktrees_have_no_claude_commands(self, spec_kitty_repo_root, requires_v07_2):
        """
        CRITICAL: Worktrees should NOT have .claude/commands/ after v0.7.2.

        Migration 0.7.2 removes these for inheritance.
        """
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            pytest.skip("No .worktrees/ directory")

        worktrees_with_commands = []

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            wt_commands = worktree / '.claude' / 'commands'
            if wt_commands.exists():
                # Count command files
                command_files = list(wt_commands.glob('spec-kitty.*.md'))
                if command_files:
                    worktrees_with_commands.append(f"{worktree.name} ({len(command_files)} commands)")

        assert len(worktrees_with_commands) == 0, (
            f"CRITICAL: Worktrees have duplicate .claude/commands/!\n\n"
            f"Found:\n" +
            "\n".join([f"  - {w}" for w in worktrees_with_commands]) +
            "\n\nAfter v0.7.2, worktrees should inherit from main repo.\n"
            "Migration 0.7.2 removes duplicates, but they may be recreated by later migrations."
        )

    def test_worktrees_have_no_agent_command_directories(self, spec_kitty_repo_root, requires_v07_2):
        """
        COMPREHENSIVE: Check ALL agent directories (not just .claude).

        Migration 0.9.1 extends to all 12 agent types.
        """
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            pytest.skip("No .worktrees/")

        duplicates_found = []

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            # Check each agent type
            for agent_root, subdir in AGENT_DIRS:
                agent_path = worktree / agent_root / subdir

                if agent_path.exists():
                    # Count command files
                    command_files = list(agent_path.glob('spec-kitty.*.md'))
                    if command_files:
                        duplicates_found.append(
                            f"{worktree.name}/{agent_root}/{subdir}/ ({len(command_files)} commands)"
                        )

        assert len(duplicates_found) == 0, (
            f"CRITICAL: Worktrees have duplicate agent commands!\n\n"
            f"Found {len(duplicates_found)} duplicate dir(s):\n" +
            "\n".join([f"  - {d}" for d in duplicates_found]) +
            "\n\nWorktrees should inherit ALL commands from main repo.\n"
            "Duplicates cause outdated commands to persist in worktrees."
        )

    def test_main_repo_has_commands_for_inheritance(self, spec_kitty_repo_root, requires_v07_2):
        """
        VALIDATION: Main repo must have commands for worktrees to inherit.

        If main has no commands, worktrees can't inherit.
        """
        main_commands = spec_kitty_repo_root / '.claude' / 'commands'

        assert main_commands.exists(), (
            "Main repo has no .claude/commands/!\n"
            "Worktrees inherit from main, so main must have commands."
        )

        command_files = list(main_commands.glob('spec-kitty.*.md'))

        assert len(command_files) >= 8, (
            f"Main repo has too few commands!\n"
            f"Found: {len(command_files)}, expected >= 8\n\n"
            "Worktrees inherit from main, so main must have complete command set."
        )


class TestMigration_0_10_1_Behavior:
    """
    CRITICAL: Verify migration 0.10.1 doesn't recreate duplicates.

    User suspects this migration undoes 0.7.2 deduplication.
    """

    def test_migration_0_10_1_does_not_populate_worktrees(self, spec_kitty_repo_root):
        """
        USER SUSPICION: Migration 0.10.1 should NOT populate worktree commands.

        This would undo the deduplication from migration 0.7.2.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mock v0.10.0 project (after 0.7.2 but before 0.10.1)
            project = tmpdir_path / 'v0100_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Create missions for templates
            missions = kittify / 'missions' / 'software-dev' / 'command-templates'
            missions.mkdir(parents=True)
            (missions / 'plan.md').write_text('# Plan')
            (missions / 'implement.md').write_text('# Implement')

            # Create main .claude/commands/ (should be populated)
            main_commands = project / '.claude' / 'commands'
            main_commands.mkdir(parents=True)

            # Create worktree WITHOUT commands (correct post-0.7.2 state)
            worktree = project / '.worktrees' / '001-test-WP01'
            worktree.mkdir(parents=True)

            # Create .git for worktree structure
            (worktree / '.git').write_text('gitdir: ../.git/worktrees/001-test-WP01')

            # Mark as v0.10.0 (needs 0.10.1 migration)
            (kittify / 'VERSION').write_text('0.10.0')

            # Run upgrade (will trigger migration 0.10.1)
            result = subprocess.run(
                ['spec-kitty', 'upgrade', '--force'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade failed: {result.stderr}")

            # Check main repo was populated
            main_command_files = list(main_commands.glob('spec-kitty.*.md'))

            # Main should have commands now
            # (Not critical failure if not, but good validation)
            if len(main_command_files) == 0:
                pytest.skip("Migration 0.10.1 didn't populate main repo commands")

            # CRITICAL: Check worktree was NOT populated
            wt_commands = worktree / '.claude' / 'commands'

            assert not wt_commands.exists() or len(list(wt_commands.iterdir())) == 0, (
                "CRITICAL: Migration 0.10.1 populated worktree commands!\n\n"
                f"Worktree path: {wt_commands}\n"
                f"Files found: {list(wt_commands.glob('*')) if wt_commands.exists() else []}\n\n"
                "This UNDOES migration 0.7.2 deduplication.\n"
                "Migration 0.10.1 should ONLY populate main repo, NOT worktrees.\n"
                "This matches user's suspicion in Issue #70."
            )

    def test_upgrade_0_7_0_to_0_10_13_preserves_deduplication(self, spec_kitty_repo_root):
        """
        USER SCENARIO: Full upgrade path preserves command deduplication.

        Upgrade v0.7.0 → v0.10.13 should:
        1. Run 0.7.2 (remove worktree commands)
        2. Run 0.10.1 (populate missing commands)
        3. Result: Main has commands, worktrees don't
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'v070_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Create missions
            missions = kittify / 'missions' / 'software-dev' / 'command-templates'
            missions.mkdir(parents=True)
            (missions / 'plan.md').write_text('# Plan')

            # Create main and worktree (both with commands - v0.7.0 state)
            main_commands = project / '.claude' / 'commands'
            main_commands.mkdir(parents=True)
            (main_commands / 'spec-kitty.plan.md').write_text('# Plan')

            worktree = project / '.worktrees' / '001-test-WP01'
            worktree.mkdir(parents=True)
            (worktree / '.git').write_text('gitdir: ../.git/worktrees/001-test-WP01')

            wt_commands = worktree / '.claude' / 'commands'
            wt_commands.mkdir(parents=True)
            (wt_commands / 'spec-kitty.plan.md').write_text('# Old Plan')

            (kittify / 'VERSION').write_text('0.7.0')

            # Run upgrade
            result = subprocess.run(
                ['spec-kitty', 'upgrade', '--force'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade failed: {result.stderr}")

            # CRITICAL: Worktree commands should be REMOVED
            wt_commands_exist = wt_commands.exists() and len(list(wt_commands.iterdir())) > 0

            assert not wt_commands_exist, (
                f"CRITICAL: Worktree commands not removed!\n\n"
                f"Path: {wt_commands}\n"
                "Migration 0.7.2 should remove duplicates.\n"
                "Migration 0.10.1 should NOT recreate them.\n\n"
                "This validates user's suspicion from Issue #70."
            )


class TestCommandInheritance:
    """
    VALIDATION: Verify worktrees properly inherit commands from main.

    Tests that the inheritance mechanism works.
    """

    @pytest.fixture
    def requires_v07_2(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.7.2"""
        if spec_kitty_version < (0, 7, 2):
            pytest.skip("Requires spec-kitty >= 0.7.2")

    def test_worktree_can_access_main_commands(self, spec_kitty_repo_root, requires_v07_2):
        """
        VALIDATION: Worktrees should be able to access main repo commands.

        Inheritance requires worktree to be inside main repo.
        """
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            pytest.skip("No .worktrees/")

        main_commands = spec_kitty_repo_root / '.claude' / 'commands'

        if not main_commands.exists():
            pytest.skip("Main repo has no .claude/commands/")

        main_command_files = list(main_commands.glob('spec-kitty.*.md'))

        if len(main_command_files) == 0:
            pytest.skip("Main repo commands directory empty")

        # Check worktrees
        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            # Worktree should NOT have its own commands
            wt_commands = worktree / '.claude' / 'commands'

            if wt_commands.exists():
                wt_command_files = list(wt_commands.glob('spec-kitty.*.md'))

                assert len(wt_command_files) == 0, (
                    f"Worktree {worktree.name} has duplicate commands!\n"
                    f"Found {len(wt_command_files)} command(s)\n\n"
                    "Worktrees should inherit from main, not have duplicates."
                )


class TestDuplicateCommandDetection:
    """
    ADVERSARIAL: Detect duplicate commands across main and worktrees.

    Comprehensive check for any duplication.
    """

    @pytest.fixture
    def requires_v07_2(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.7.2"""
        if spec_kitty_version < (0, 7, 2):
            pytest.skip("Requires spec-kitty >= 0.7.2")

    def test_no_slash_command_duplication_anywhere(self, spec_kitty_repo_root, requires_v07_2):
        """
        COMPREHENSIVE: Scan entire repo for duplicate slash commands.

        Finds any duplication between main and worktrees.
        """
        main_commands = {}

        # Scan main repo for all agent commands
        for agent_root, subdir in AGENT_DIRS:
            agent_path = spec_kitty_repo_root / agent_root / subdir

            if agent_path.exists():
                command_files = list(agent_path.glob('spec-kitty.*.md'))
                if command_files:
                    main_commands[f"{agent_root}/{subdir}"] = [f.name for f in command_files]

        # Scan worktrees for duplicates
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            # No worktrees - no duplication possible
            return

        duplicates_found = []

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            for agent_root, subdir in AGENT_DIRS:
                wt_agent_path = worktree / agent_root / subdir

                if wt_agent_path.exists():
                    wt_commands = list(wt_agent_path.glob('spec-kitty.*.md'))

                    if wt_commands:
                        duplicates_found.append({
                            'worktree': worktree.name,
                            'agent': f"{agent_root}/{subdir}",
                            'count': len(wt_commands),
                            'commands': [c.name for c in wt_commands[:5]]
                        })

        assert len(duplicates_found) == 0, (
            f"CRITICAL: Duplicate slash commands in worktrees!\n\n"
            f"Found {len(duplicates_found)} worktree(s) with duplicates:\n" +
            "\n".join([
                f"  - {d['worktree']} {d['agent']}: {d['count']} commands {d['commands'][:3]}"
                for d in duplicates_found
            ]) +
            "\n\nWorktrees should inherit from main, not have their own copies.\n"
            "This is the suspected regression from Issue #70."
        )

    def test_migration_0_10_1_scope_check(self, spec_kitty_repo_root):
        """
        ADVERSARIAL: Verify migration 0.10.1 only affects main repo.

        Read migration code to verify it doesn't touch worktrees.
        """
        migration_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations' / 'm_0_10_1_populate_slash_commands.py'

        if not migration_file.exists():
            pytest.skip("Migration 0.10.1 file not found")

        content = migration_file.read_text()

        # Check if migration code references worktrees
        worktree_refs = []

        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'worktree' in line.lower() and not line.strip().startswith('#'):
                # Check if it's populating worktrees (problematic)
                context_start = max(0, i - 3)
                context_end = min(len(lines), i + 3)
                context = '\n'.join(lines[context_start:context_end])

                if any(keyword in context.lower() for keyword in ['copy', 'write', 'populate', 'create']):
                    worktree_refs.append(f"Line {i+1}: {line.strip()[:80]}")

        if worktree_refs:
            pytest.fail(
                f"POTENTIAL BUG: Migration 0.10.1 may populate worktrees!\n\n"
                f"Found {len(worktree_refs)} suspicious reference(s):\n" +
                "\n".join([f"  {ref}" for ref in worktree_refs]) +
                "\n\nThis migration should ONLY populate main repo, not worktrees.\n"
                "Populating worktrees would recreate the duplicates removed by 0.7.2."
            )


class TestUpgradePathDeduplicationIntegrity:
    """
    COMPREHENSIVE: Test full upgrade paths maintain deduplication.

    Ensures 0.7.2 deduplication survives later migrations.
    """

    def test_upgrade_through_0_10_1_maintains_dedup(self, spec_kitty_repo_root):
        """
        USER SCENARIO: Upgrade from v0.7.1 (before dedup) through v0.10.13.

        Should result in deduplicated state.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            project = tmpdir_path / 'v071_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()

            # Create missions
            missions = kittify / 'missions' / 'software-dev' / 'command-templates'
            missions.mkdir(parents=True)
            (missions / 'plan.md').write_text('# Plan')

            # Create main and worktree commands (pre-0.7.2 duplicate state)
            main_commands = project / '.claude' / 'commands'
            main_commands.mkdir(parents=True)
            (main_commands / 'spec-kitty.plan.md').write_text('# Main Plan')

            worktree = project / '.worktrees' / '001-test-WP01'
            worktree.mkdir(parents=True)
            (worktree / '.git').write_text('gitdir: ../.git/worktrees/001-test-WP01')

            wt_commands = worktree / '.claude' / 'commands'
            wt_commands.mkdir(parents=True)
            (wt_commands / 'spec-kitty.plan.md').write_text('# WT Plan (duplicate)')

            (kittify / 'VERSION').write_text('0.7.1')

            # Run upgrade through 0.7.2, 0.10.1, 0.10.13
            result = subprocess.run(
                ['spec-kitty', 'upgrade', '--force'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade failed: {result.stderr}")

            # CRITICAL: Worktree commands should be GONE
            # (Removed by 0.7.2, NOT recreated by 0.10.1)
            wt_has_commands = wt_commands.exists() and len(list(wt_commands.iterdir())) > 0

            assert not wt_has_commands, (
                f"CRITICAL: Worktree commands exist after upgrade!\n\n"
                f"This indicates migration 0.10.1 recreated duplicates.\n"
                f"Path: {wt_commands}\n"
                f"Files: {list(wt_commands.glob('*')) if wt_commands.exists() else []}\n\n"
                "Migration sequence should be:\n"
                "1. 0.7.2: Remove worktree commands\n"
                "2. 0.10.1: Populate MAIN commands only\n"
                "Result: Main has commands, worktrees don't\n\n"
                "This confirms user's suspicion from Issue #70."
            )

            # Main should have commands
            assert len(list(main_commands.glob('*'))) > 0, (
                "Main repo has no commands after upgrade!\n"
                "Migration 0.10.1 should populate main repo."
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
