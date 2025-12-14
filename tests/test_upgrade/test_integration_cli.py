"""
Test Upgrade CLI Integration

Tests the full `spec-kitty upgrade` command as users would invoke it.

These are end-to-end integration tests that:
- Run the actual CLI command via subprocess
- Verify exit codes, stdout/stderr output
- Test all command-line options
- Validate error messages and user guidance
- Ensure proper handling of edge cases

Test Coverage:
1. Basic Upgrade (5 tests)
   - No changes needed (current version)
   - Single migration upgrade
   - Full upgrade path (multiple migrations)
   - Output format and migration plan
   - Creates metadata if missing

2. Command Options (5 tests)
   - --dry-run shows plan without changes
   - --force skips confirmation
   - --target VERSION stops at specific version
   - --json produces machine-readable output
   - -v/--verbose shows detailed progress

3. Edge Cases (5 tests)
   - Uncommitted changes warning
   - Not a git repository error
   - Not a kittify project error
   - Corrupted metadata fallback
   - Error when run from worktree
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestUpgradeCommandBasic:
    """Test basic upgrade command functionality."""

    def test_upgrade_no_changes_needed(self, v0_6_6_project):
        """Test: Current version → no-op

        GIVEN: A project already at current version (v0.6.6+)
        WHEN: Running spec-kitty upgrade
        THEN: Should indicate no upgrades needed
        """
        # v0.6.6 project has current structure, just missing metadata
        # After adding metadata, should be current

        # Run upgrade command
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=v0_6_6_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Upgrade should succeed. stderr: {result.stderr}"

        # Output should indicate already current or minimal work
        output = result.stdout.lower()

        # Might say "no upgrades needed" or "already current" or just add metadata
        assert 'no migrations needed' in output or 'already up to date' in output or 'metadata' in output, \
            f"Should indicate current or just metadata update. Output: {result.stdout}"

    def test_upgrade_single_migration(self, v0_6_4_project):
        """Test: v0.6.4 → v0.6.5 (commands rename)

        GIVEN: A v0.6.4 project (needs only commands rename)
        WHEN: Running spec-kitty upgrade
        THEN: Should run commands rename migration
        """
        # Run upgrade with auto-confirm
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30,
            input='y\n'  # Confirm if --force not available
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Upgrade should succeed. stderr: {result.stderr}"

        # Verify migration ran
        commands_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        templates_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        assert not commands_dir.exists(), \
            "commands/ should be renamed"

        assert templates_dir.exists(), \
            "command-templates/ should exist"

        # Output should mention the migration
        output = result.stdout

        assert 'commands' in output.lower() or '0.6.5' in output, \
            f"Output should mention commands migration. Got: {output}"

    def test_upgrade_full_path(self, v0_1_x_project):
        """Test: v0.1.x → current (4 migrations)

        GIVEN: A v0.1.x project (oldest version)
        WHEN: Running spec-kitty upgrade
        THEN: Should execute all migrations in order
        """
        # Run upgrade with auto-confirm
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_1_x_project,
            capture_output=True,
            text=True,
            timeout=60  # Longer timeout for multiple migrations
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Full upgrade should succeed. stderr: {result.stderr}"

        # Verify .specify/ → .kittify/
        assert not (v0_1_x_project / '.specify').exists(), \
            ".specify/ should be renamed"

        assert (v0_1_x_project / '.kittify').exists(), \
            ".kittify/ should exist"

        # Verify specs/ → kitty-specs/
        assert not (v0_1_x_project / 'specs').exists(), \
            "specs/ should be renamed"

        assert (v0_1_x_project / 'kitty-specs').exists(), \
            "kitty-specs/ should exist"

        # Verify gitignore has agent directories
        gitignore = v0_1_x_project / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            assert '.claude/' in content, \
                ".gitignore should have agent directories"

        # Verify pre-commit hook installed
        hook = v0_1_x_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        assert hook.exists(), \
            "Pre-commit hook should be installed"

        # Verify commands renamed (if applicable after .specify → .kittify)
        # The v0.1.x structure might be different, but final result should have command-templates

        # Output should show multiple migrations
        output = result.stdout

        # Should mention multiple migrations or show progress
        migration_count = output.count('✓') + output.count('✔') + output.count('SUCCESS')

        assert migration_count >= 3, \
            f"Should show multiple successful migrations. Output: {output}"

    def test_upgrade_output_format(self, v0_4_7_project):
        """Test: Shows migration plan table

        GIVEN: A project needing multiple migrations
        WHEN: Running spec-kitty upgrade
        THEN: Should display clear migration plan before executing
        """
        # Run with dry-run to see plan without executing
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=v0_4_7_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Dry run should succeed. stderr: {result.stderr}"

        output = result.stdout

        # Should show migration plan
        assert 'migration' in output.lower() or 'plan' in output.lower(), \
            "Should show migration plan"

        # Should list specific migrations
        assert '0.4.8' in output or 'gitignore' in output.lower(), \
            "Should mention gitignore migration"

        assert '0.5.0' in output or 'hook' in output.lower(), \
            "Should mention hooks migration"

        assert '0.6.5' in output or 'command' in output.lower(), \
            "Should mention commands migration"

        # Should indicate dry-run (no actual changes)
        assert 'dry' in output.lower() or 'preview' in output.lower() or 'would' in output.lower(), \
            "Should indicate this is a preview"

    def test_upgrade_creates_metadata(self, v0_6_6_project):
        """Test: Adds metadata.yaml if missing

        GIVEN: A project with current structure but no metadata
        WHEN: Running spec-kitty upgrade
        THEN: Should create metadata.yaml with current version
        """
        # v0.6.6 fixture has NO metadata.yaml
        metadata_file = v0_6_6_project / '.kittify' / 'metadata.yaml'

        assert not metadata_file.exists(), \
            "Fixture should not have metadata.yaml initially"

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_6_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Upgrade should succeed. stderr: {result.stderr}"

        # Verify metadata created
        assert metadata_file.exists(), \
            "metadata.yaml should be created"

        # Verify metadata has version
        import yaml
        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)

        assert 'version' in metadata, \
            "Metadata should have version field"

        assert metadata['version'].startswith('0.6'), \
            f"Version should be 0.6.x, got {metadata['version']}"


class TestUpgradeCommandOptions:
    """Test command-line options and flags."""

    def test_dry_run_no_changes(self, v0_6_4_project):
        """Test: --dry-run shows plan, makes no changes

        GIVEN: A project needing migration
        WHEN: Running with --dry-run
        THEN: Should show what would happen without modifying files
        """
        # Verify starting state
        commands_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        templates_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        assert commands_dir.exists(), "Should have commands/ initially"
        assert not templates_dir.exists(), "Should not have templates/ initially"

        # Run with --dry-run
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Dry run should succeed. stderr: {result.stderr}"

        # Verify NO changes made
        assert commands_dir.exists(), \
            "commands/ should still exist (no changes)"

        assert not templates_dir.exists(), \
            "command-templates/ should not be created (no changes)"

        # Output should indicate dry-run
        output = result.stdout.lower()

        assert 'dry' in output or 'preview' in output or 'would' in output, \
            "Should indicate dry-run mode"

    def test_force_skips_confirmation(self, v0_6_4_project):
        """Test: --force auto-confirms

        GIVEN: A project needing migration
        WHEN: Running with --force
        THEN: Should not prompt for confirmation
        """
        # Run with --force (no input needed)
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed without hanging on confirmation prompt
        assert result.returncode == 0, \
            f"Upgrade with --force should succeed. stderr: {result.stderr}"

        # Verify migration actually ran
        templates_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        assert templates_dir.exists(), \
            "Migration should have run (not just shown plan)"

    def test_target_version(self, v0_4_7_project):
        """Test: --target 0.6.5 stops at specific version

        GIVEN: A project needing multiple migrations
        WHEN: Running with --target 0.5.0
        THEN: Should only run migrations up to 0.5.0
        """
        # Run upgrade targeting 0.5.0 (stop before 0.6.5 commands rename)
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--target', '0.5.0', '--force'],
            cwd=v0_4_7_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Targeted upgrade should succeed. stderr: {result.stderr}"

        # Should have run gitignore (0.4.8) and hooks (0.5.0)
        gitignore = v0_4_7_project / '.gitignore'
        gitignore_content = gitignore.read_text()

        assert '.claude/' in gitignore_content, \
            "Gitignore migration should have run"

        hook = v0_4_7_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        assert hook.exists(), \
            "Hooks migration should have run"

        # Should NOT have run commands rename (0.6.5)
        commands_dir = v0_4_7_project / '.kittify' / 'missions' / 'software-dev' / 'commands'
        templates_dir = v0_4_7_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        assert commands_dir.exists(), \
            "Commands should still exist (migration not run)"

        assert not templates_dir.exists(), \
            "Templates should not exist (migration not run)"

    def test_json_output(self, v0_6_4_project, extract_json_from_output):
        """Test: --json produces machine-readable output

        GIVEN: A project needing migration
        WHEN: Running with --json
        THEN: Should output valid JSON with migration details
        """
        # Run with --json flag
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--json', '--dry-run'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"JSON upgrade should succeed. stderr: {result.stderr}"

        # Extract and parse JSON
        json_output = extract_json_from_output(result.stdout)

        assert json_output is not None, \
            f"Output should contain valid JSON. Got: {result.stdout}"

        # Verify JSON structure
        assert 'current_version' in json_output or 'migrations' in json_output, \
            "JSON should have version or migrations info"

        # If migrations listed, should have details
        if 'migrations' in json_output:
            migrations = json_output['migrations']

            assert isinstance(migrations, list), \
                "Migrations should be a list"

            if len(migrations) > 0:
                first_migration = migrations[0]

                assert 'migration_id' in first_migration or 'id' in first_migration, \
                    "Each migration should have an ID"

    def test_verbose_logging(self, v0_6_4_project):
        """Test: -v shows detailed progress

        GIVEN: A project needing migration
        WHEN: Running with -v or --verbose
        THEN: Should show detailed migration steps
        """
        # Run with -v flag
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '-v', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Verbose upgrade should succeed. stderr: {result.stderr}"

        output = result.stdout

        # Verbose output should be longer and more detailed
        assert len(output) > 100, \
            "Verbose output should have substantial content"

        # Should show migration details
        # (Exact format depends on implementation, but should mention steps)

        # May show in stdout or stderr depending on implementation
        combined_output = result.stdout + result.stderr

        # Should mention what's happening
        assert 'commands' in combined_output.lower() or 'rename' in combined_output.lower(), \
            "Verbose output should describe what's happening"


class TestUpgradeCommandEdgeCases:
    """Test error handling and edge cases."""

    def test_upgrade_with_uncommitted_changes(self, v0_6_4_project):
        """Test: Warns but proceeds (or fails?)

        GIVEN: A project with uncommitted changes
        WHEN: Running spec-kitty upgrade
        THEN: Should warn about uncommitted changes (behavior TBD)
        """
        # Create uncommitted changes
        test_file = v0_6_4_project / 'uncommitted.txt'
        test_file.write_text("Uncommitted test content")

        # Add to git but don't commit
        subprocess.run(
            ['git', 'add', 'uncommitted.txt'],
            cwd=v0_6_4_project,
            capture_output=True
        )

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Might warn or might just proceed
        # (Implementation decision: strict vs lenient)

        combined_output = (result.stdout + result.stderr).lower()

        # If warns, should mention uncommitted or changes
        if 'uncommitted' in combined_output or 'changes' in combined_output:
            # Warning is shown (good practice)
            pass

        # Should either succeed (with warning) or fail (with clear message)
        if result.returncode != 0:
            assert 'commit' in combined_output or 'changes' in combined_output, \
                "If failing, should explain about uncommitted changes"

    def test_upgrade_not_git_repo(self, tmp_path):
        """Test: Clear error message

        GIVEN: A directory that's not a git repository
        WHEN: Running spec-kitty upgrade
        THEN: Should show clear error message
        """
        # Create non-git project
        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should fail
        assert result.returncode != 0, \
            "Should fail when not a git repository"

        # Error message should mention git
        error_output = (result.stdout + result.stderr).lower()

        assert 'git' in error_output, \
            f"Error should mention git repository. Got: {result.stderr}"

    def test_upgrade_not_kittify_project(self, tmp_path):
        """Test: Detects missing .kittify/

        GIVEN: A git repo that's not a spec-kitty project
        WHEN: Running spec-kitty upgrade
        THEN: Should detect missing .kittify/ and error clearly
        """
        # Create git repo without .kittify/
        subprocess.run(['git', 'init'], cwd=tmp_path, capture_output=True)

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should fail
        assert result.returncode != 0, \
            "Should fail when not a spec-kitty project"

        # Error should mention .kittify or spec-kitty project
        error_output = (result.stdout + result.stderr).lower()

        assert 'kittify' in error_output or 'spec-kitty' in error_output, \
            f"Error should mention kittify project. Got: {result.stderr}"

    def test_upgrade_corrupted_metadata(self, v0_6_4_project, corrupt_metadata):
        """Test: Falls back to heuristic detection

        GIVEN: A project with corrupted metadata.yaml
        WHEN: Running spec-kitty upgrade
        THEN: Should detect version via heuristics and proceed
        """
        # Corrupt metadata
        corrupt_metadata(v0_6_4_project, 'syntax_error')

        # Run upgrade
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=v0_6_4_project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed (falls back to heuristic detection)
        assert result.returncode == 0, \
            f"Should succeed with heuristic fallback. stderr: {result.stderr}"

        # Verify migration ran
        templates_dir = v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        assert templates_dir.exists(), \
            "Migration should run despite corrupted metadata"

    def test_upgrade_from_worktree(self, create_project_with_worktrees):
        """Test: Error: must run from main repo

        GIVEN: Running upgrade from a worktree directory
        WHEN: Executing spec-kitty upgrade
        THEN: Should error, directing user to run from main repo
        """
        # Create project with worktrees
        main_project = create_project_with_worktrees(
            version="0.6.4",
            num_worktrees=1
        )

        # Get first worktree
        worktrees_dir = main_project / '.worktrees'
        worktrees = list(worktrees_dir.iterdir())

        assert len(worktrees) >= 1, "Should have at least one worktree"

        worktree = worktrees[0]

        # Try to run upgrade from worktree (should fail)
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should fail with clear message
        assert result.returncode != 0, \
            "Should fail when run from worktree"

        error_output = (result.stdout + result.stderr).lower()

        assert 'worktree' in error_output or 'main' in error_output, \
            f"Error should mention worktree limitation. Got: {result.stderr}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
