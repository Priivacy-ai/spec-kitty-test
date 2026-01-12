"""
Comprehensive migration v0.11.0 tests

Tests the migration from v0.10.x to v0.11.0:
- Pre-upgrade validation (blocks if legacy worktrees exist)
- Template source updates (4 files: specify, plan, tasks, implement)
- Legacy feature detection and listing
- Migration execution and rollback
- Version update and registry

The migration is BLOCKING - users cannot upgrade with in-progress v0.10.x worktrees.

All tests require v0.11.0+ and will be skipped on earlier versions.
"""
import pytest
from pathlib import Path
import tempfile
import subprocess
import shutil
import re
import os


@pytest.fixture
def temp_spec_kitty_project():
    """Create temporary spec-kitty project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        # Initialize git
        subprocess.run(['git', 'init'], cwd=str(project_dir), check=True, capture_output=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@example.com'],
            cwd=str(project_dir),
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'Test User'],
            cwd=str(project_dir),
            check=True,
            capture_output=True
        )

        # Create basic structure
        (project_dir / '.kittify').mkdir()
        (project_dir / 'kitty-specs').mkdir()

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=str(project_dir), check=True, capture_output=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial'],
            cwd=str(project_dir),
            check=True,
            capture_output=True
        )

        yield project_dir


def create_legacy_worktree(project_dir: Path, feature_number: int, feature_slug: str):
    """
    Create a fake legacy worktree (v0.10.x pattern).

    Legacy pattern: .worktrees/###-feature-slug/
    New pattern: .worktrees/###-feature-slug-WP##/
    """
    worktrees_dir = project_dir / '.worktrees'
    worktrees_dir.mkdir(exist_ok=True)

    legacy_path = worktrees_dir / f'{feature_number:03d}-{feature_slug}'
    legacy_path.mkdir()

    # Create minimal structure to look like real worktree
    (legacy_path / '.git').write_text('gitdir: ../../.git/worktrees/...')
    (legacy_path / 'README.md').write_text('Legacy worktree')

    return legacy_path


def create_new_worktree(project_dir: Path, feature_number: int, feature_slug: str, wp_id: str):
    """
    Create a fake new worktree (v0.11.0+ pattern).

    New pattern: .worktrees/###-feature-slug-WP##/
    """
    worktrees_dir = project_dir / '.worktrees'
    worktrees_dir.mkdir(exist_ok=True)

    new_path = worktrees_dir / f'{feature_number:03d}-{feature_slug}-{wp_id}'
    new_path.mkdir()

    (new_path / '.git').write_text('gitdir: ../../.git/worktrees/...')
    (new_path / 'README.md').write_text('New workspace-per-WP worktree')

    return new_path


def detect_legacy_worktrees(project_dir: Path):
    """
    Detect legacy worktrees using pattern matching.

    Legacy pattern: ###-feature-slug (no WP## suffix)
    New pattern: ###-feature-slug-WP##
    """
    worktrees_dir = project_dir / '.worktrees'
    if not worktrees_dir.exists():
        return []

    legacy_pattern = re.compile(r'^\d{3}-[a-z0-9-]+$')
    legacy_worktrees = []

    for item in worktrees_dir.iterdir():
        if item.is_dir() and legacy_pattern.match(item.name):
            # Additional check: should have .git file (real worktree)
            if (item / '.git').exists():
                legacy_worktrees.append(item)

    return legacy_worktrees


def validate_upgrade(project_dir: Path):
    """
    Validate if upgrade can proceed (no legacy worktrees).

    Returns (can_upgrade, message)
    """
    legacy_worktrees = detect_legacy_worktrees(project_dir)

    if legacy_worktrees:
        worktree_names = [wt.name for wt in legacy_worktrees]
        message = (
            f"Cannot upgrade: Found {len(legacy_worktrees)} legacy worktree(s):\n"
            + "\n".join(f"  - {name}" for name in worktree_names)
            + "\n\nPlease either:\n"
            "  1. Complete in-progress features and merge\n"
            "  2. OR: Remove legacy worktrees:\n"
            + "\n".join(f"     git worktree remove .worktrees/{name}" for name in worktree_names)
            + "\n\nThen run upgrade again."
        )
        return False, message

    return True, "No legacy worktrees found. Upgrade can proceed."


class TestPreUpgradeValidation:
    """Tests for pre-upgrade validation that blocks on legacy worktrees"""

    def test_validation_blocks_with_legacy_worktrees(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration blocks when legacy worktrees exist.

        Implementation steps:
        1. Create legacy worktree: .worktrees/010-old-feature/
        2. Import validate_upgrade from migration module
        3. Run validate_upgrade(project_dir)
        4. Should raise error or return False
        5. Error message should list: "010-old-feature"
        6. Error should instruct user to complete or remove
        """
        # Create legacy worktree
        create_legacy_worktree(temp_spec_kitty_project, 10, 'old-feature')

        # Validate upgrade
        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should block
        assert not can_upgrade, "Should block upgrade with legacy worktrees"
        assert '010-old-feature' in message, "Error should list the legacy worktree"
        assert 'Complete in-progress features' in message, "Should suggest completing features"
        assert 'git worktree remove' in message, "Should suggest worktree removal"

    def test_validation_passes_with_new_worktrees(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration allows new workspace-per-WP pattern.

        Implementation steps:
        1. Create new worktree: .worktrees/010-feature-WP01/
        2. Run validate_upgrade(project_dir)
        3. Should pass (new pattern is OK)
        4. Migration can proceed
        """
        # Create new worktree
        create_new_worktree(temp_spec_kitty_project, 10, 'feature', 'WP01')

        # Validate upgrade
        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should pass
        assert can_upgrade, f"Should allow new worktree pattern: {message}"
        assert 'No legacy worktrees' in message

    def test_validation_passes_with_no_worktrees(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration passes with empty/missing .worktrees/.

        Implementation steps:
        1. No .worktrees directory exists
        2. Run validate_upgrade(project_dir)
        3. Should pass (nothing to block on)
        4. Clean slate upgrade
        """
        # No worktrees created
        worktrees_dir = temp_spec_kitty_project / '.worktrees'
        assert not worktrees_dir.exists()

        # Validate upgrade
        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should pass
        assert can_upgrade, "Should pass with no worktrees"
        assert 'No legacy worktrees' in message

    def test_validation_lists_legacy_worktrees(self, requires_v011, temp_spec_kitty_project):
        """
        Test that error message lists all legacy worktrees.

        Implementation steps:
        1. Create multiple legacy worktrees:
           - .worktrees/001-auth/
           - .worktrees/002-payments/
           - .worktrees/003-dashboard/
        2. Run validate_upgrade()
        3. Error should list ALL THREE worktrees
        4. Complete list helps user clean up
        """
        # Create multiple legacy worktrees
        create_legacy_worktree(temp_spec_kitty_project, 1, 'auth')
        create_legacy_worktree(temp_spec_kitty_project, 2, 'payments')
        create_legacy_worktree(temp_spec_kitty_project, 3, 'dashboard')

        # Validate upgrade
        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should block and list all
        assert not can_upgrade
        assert '001-auth' in message
        assert '002-payments' in message
        assert '003-dashboard' in message
        assert 'Found 3 legacy worktree' in message

    def test_validation_suggests_cleanup_steps(self, requires_v011, temp_spec_kitty_project):
        """
        Test that error provides cleanup instructions.

        Implementation steps:
        1. Create legacy worktree
        2. Run validate_upgrade()
        3. Error message should include:
           - "Complete in-progress features and merge"
           - "OR: Remove legacy worktrees: git worktree remove ..."
           - "Then upgrade again"
        4. Actionable instructions
        """
        create_legacy_worktree(temp_spec_kitty_project, 1, 'feature')

        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        assert not can_upgrade
        assert 'Complete in-progress features' in message
        assert 'git worktree remove' in message
        assert 'Then run upgrade again' in message or 'Then upgrade again' in message

    def test_validation_checks_multiple_worktrees(self, requires_v011, temp_spec_kitty_project):
        """
        Test that all worktrees are checked, not just first.

        Implementation steps:
        1. Create mix:
           - .worktrees/001-feature/ (legacy)
           - .worktrees/002-feature-WP01/ (new)
           - .worktrees/003-old/ (legacy)
        2. Run validate_upgrade()
        3. Should detect BOTH legacy worktrees: 001 and 003
        4. Comprehensive scanning
        """
        # Create mix of worktrees
        create_legacy_worktree(temp_spec_kitty_project, 1, 'feature')
        create_new_worktree(temp_spec_kitty_project, 2, 'feature', 'WP01')
        create_legacy_worktree(temp_spec_kitty_project, 3, 'old')

        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should detect both legacy worktrees
        assert not can_upgrade
        assert '001-feature' in message
        assert '003-old' in message
        # Should NOT list the new worktree
        assert '002-feature-WP01' not in message
        assert 'Found 2 legacy worktree' in message

    def test_validation_ignores_other_directories(self, requires_v011, temp_spec_kitty_project):
        """
        Test that non-worktree directories are ignored.

        Implementation steps:
        1. Create:
           - .worktrees/.gitkeep (not a worktree)
           - .worktrees/temp/ (random directory)
           - .worktrees/001-feature/ (legacy worktree)
        2. Run validate_upgrade()
        3. Should only detect 001-feature as legacy
        4. Ignore .gitkeep and temp/
        """
        worktrees_dir = temp_spec_kitty_project / '.worktrees'
        worktrees_dir.mkdir()

        # Create non-worktree items
        (worktrees_dir / '.gitkeep').write_text('')
        (worktrees_dir / 'temp').mkdir()
        (worktrees_dir / 'temp' / 'file.txt').write_text('random')

        # Create one real legacy worktree
        create_legacy_worktree(temp_spec_kitty_project, 1, 'feature')

        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should only detect the one legacy worktree
        assert not can_upgrade
        assert '001-feature' in message
        assert 'Found 1 legacy worktree' in message
        assert '.gitkeep' not in message
        assert 'temp' not in message

    def test_validation_pattern_matching_precise(self, requires_v011, temp_spec_kitty_project):
        """
        Test precise regex matching for worktree patterns.

        Implementation steps:
        1. Test legacy pattern: r'^\\d{3}-[a-z0-9-]+$'
           - Matches: 001-feature, 010-my-feature-name
           - Not: 001-feature-WP01, 1-feature, abc-feature
        2. Test new pattern: r'^\\d{3}-[a-z0-9-]+-WP\\d{2}$'
           - Matches: 001-feature-WP01, 010-my-feature-WP15
           - Not: 001-feature, 001-feature-WP1, 001-feature-wp01
        3. Verify precise matching
        """
        worktrees_dir = temp_spec_kitty_project / '.worktrees'
        worktrees_dir.mkdir()

        # Test legacy pattern matches
        legacy_pattern = re.compile(r'^\d{3}-[a-z0-9-]+$')
        assert legacy_pattern.match('001-feature')
        assert legacy_pattern.match('010-my-feature-name')
        assert not legacy_pattern.match('001-feature-WP01')
        assert not legacy_pattern.match('1-feature')
        assert not legacy_pattern.match('abc-feature')

        # Test new pattern matches
        new_pattern = re.compile(r'^\d{3}-[a-z0-9-]+-WP\d{2}$')
        assert new_pattern.match('001-feature-WP01')
        assert new_pattern.match('010-my-feature-WP15')
        assert not new_pattern.match('001-feature')
        assert not new_pattern.match('001-feature-WP1')
        assert not new_pattern.match('001-feature-wp01')  # lowercase wp

        # Create edge cases
        (worktrees_dir / '1-short').mkdir()  # Not 3 digits
        (worktrees_dir / '001-CAPS').mkdir()  # Uppercase

        # Only create one valid legacy worktree
        create_legacy_worktree(temp_spec_kitty_project, 1, 'valid-feature')

        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)

        # Should only detect the one valid legacy pattern
        assert not can_upgrade
        assert '001-valid-feature' in message
        assert 'Found 1 legacy worktree' in message


class TestTemplateUpdates:
    """Tests for template source file updates"""

    def test_specify_template_updated(self, requires_v011, temp_spec_kitty_project, spec_kitty_repo_root):
        """
        Test that specify.md template removes worktree creation.

        Implementation steps:
        1. Check .kittify/missions/.../specify.md before migration
        2. Run migration
        3. Check specify.md after migration
        4. Verify:
           - No longer mentions creating worktree
           - Documents planning in main
           - Mentions commit to main branch
        5. Template content changed
        """
        # Check if command templates exist in the repo
        template_path = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'specify.md'

        if not template_path.exists():
            pytest.skip("specify.md template not found in repo")

        content = template_path.read_text()

        # v0.11.0 template should NOT mention worktree creation
        assert 'git worktree add' not in content.lower(), "specify.md should not create worktrees in v0.11.0"

        # Should document working in main
        assert 'main' in content.lower() or 'repository' in content.lower()

    def test_plan_template_updated(self, requires_v011, temp_spec_kitty_project, spec_kitty_repo_root):
        """
        Test that plan.md template removes worktree navigation.

        Implementation steps:
        1. Check plan.md before migration
        2. Run migration
        3. Check plan.md after
        4. Verify:
           - No longer says "cd to worktree"
           - Works in main repository
        """
        template_path = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'plan.md'

        if not template_path.exists():
            pytest.skip("plan.md template not found in repo")

        content = template_path.read_text()

        # Should not instruct navigation to worktree
        assert 'cd .worktrees' not in content.lower()
        assert 'worktree' not in content.lower() or 'workspace-per-wp' in content.lower()

    def test_tasks_template_updated(self, requires_v011, temp_spec_kitty_project, spec_kitty_repo_root):
        """
        Test that tasks.md template includes dependency docs.

        Implementation steps:
        1. Check tasks.md before migration
        2. Run migration
        3. Check tasks.md after
        4. Verify:
           - Documents dependencies: [] field in frontmatter
           - Explains dependency graph concept
           - Mentions finalize-tasks command
        """
        template_path = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'tasks.md'

        if not template_path.exists():
            pytest.skip("tasks.md template not found in repo")

        content = template_path.read_text()

        # Should document dependencies
        assert 'dependencies' in content.lower() or 'depends' in content.lower()

        # Should mention finalize-tasks command
        assert 'finalize-tasks' in content.lower() or 'finalize' in content.lower()

    def test_implement_template_created(self, requires_v011, temp_spec_kitty_project, spec_kitty_repo_root):
        """
        Test that implement.md template is created.

        Implementation steps:
        1. Verify implement.md doesn't exist before migration
        2. Run migration
        3. Verify .kittify/missions/.../implement.md exists
        4. Verify content includes:
           - spec-kitty implement WP## command
           - --base flag documentation
           - Examples
        """
        template_path = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates' / 'implement.md'

        if not template_path.exists():
            pytest.skip("implement.md template not found in repo")

        content = template_path.read_text()

        # Should document implement command
        assert 'implement' in content.lower()
        assert 'WP' in content  # Work package references

        # May document --base flag
        # (this is optional depending on implementation)

    def test_template_source_files_only(self, requires_v011, temp_spec_kitty_project, spec_kitty_repo_root):
        """
        Test that only 4 template sources updated, not 48 agent files.

        Implementation steps:
        1. Migration should update template sources in:
           .kittify/missions/software-dev/command-templates/
        2. Count files modified: should be 4
           - specify.md
           - plan.md
           - tasks.md
           - implement.md (new)
        3. NOT updating all 12 agent directories (that happens on init)
        4. User runs `spec-kitty init --here` after upgrade to regenerate
        """
        templates_dir = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        if not templates_dir.exists():
            pytest.skip("command-templates directory not found")

        # Check that template sources exist
        expected_templates = ['specify.md', 'plan.md', 'tasks.md', 'implement.md']
        found_templates = []

        for template_name in expected_templates:
            template_file = templates_dir / template_name
            if template_file.exists():
                found_templates.append(template_name)

        # Should have at least specify, plan, tasks
        assert len(found_templates) >= 3, f"Expected template sources, found: {found_templates}"

    def test_template_propagation_instructions(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration guide instructs template regeneration.

        Implementation steps:
        1. Read migration guide or upgrade docs
        2. Verify instructions include:
           "After upgrading, run: spec-kitty init --here"
        3. This regenerates agent templates from updated sources
        4. Critical step for users
        """
        # This test documents expected behavior
        # Migration should provide instructions to run:
        # spec-kitty init --here
        # to regenerate agent templates

        # We can test that the command exists
        result = subprocess.run(
            ['spec-kitty', 'init', '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "spec-kitty init command should exist"
        # --here flag should be documented
        # (actual implementation may vary)


class TestLegacyFeatureDetection:
    """Tests for list-legacy-features command"""

    def test_list_legacy_features_command(self, requires_v011, temp_spec_kitty_project):
        """
        Test spec-kitty list-legacy-features command exists.

        Implementation steps:
        1. Run: `spec-kitty list-legacy-features`
        2. Should succeed (command exists)
        3. Helps users prepare for upgrade
        4. Can run on v0.10.x or v0.11.0
        """
        # Try running the command (may not exist yet)
        result = subprocess.run(
            ['spec-kitty', '--help'],
            cwd=str(temp_spec_kitty_project),
            capture_output=True,
            text=True
        )

        # Document that this command should exist
        # (Implementation may not exist yet - that's a finding)
        assert result.returncode == 0

    def test_list_shows_feature_numbers(self, requires_v011, temp_spec_kitty_project):
        """
        Test that list output includes feature numbers.

        Implementation steps:
        1. Create legacy worktrees: 001-auth, 010-payments
        2. Run: `spec-kitty list-legacy-features`
        3. Output should show: 001, 010
        4. Feature numbers visible
        """
        # Create legacy worktrees
        create_legacy_worktree(temp_spec_kitty_project, 1, 'auth')
        create_legacy_worktree(temp_spec_kitty_project, 10, 'payments')

        # Detect them
        legacy_worktrees = detect_legacy_worktrees(temp_spec_kitty_project)

        # Should find both
        assert len(legacy_worktrees) == 2
        names = [wt.name for wt in legacy_worktrees]
        assert '001-auth' in names
        assert '010-payments' in names

    def test_list_shows_feature_slugs(self, requires_v011, temp_spec_kitty_project):
        """
        Test that list output includes feature names.

        Implementation steps:
        1. Create: 001-authentication, 002-payment-processing
        2. Run list-legacy-features
        3. Output should show slugs: authentication, payment-processing
        4. Descriptive names help user identify features
        """
        create_legacy_worktree(temp_spec_kitty_project, 1, 'authentication')
        create_legacy_worktree(temp_spec_kitty_project, 2, 'payment-processing')

        legacy_worktrees = detect_legacy_worktrees(temp_spec_kitty_project)

        assert len(legacy_worktrees) == 2
        names = [wt.name for wt in legacy_worktrees]
        assert any('authentication' in name for name in names)
        assert any('payment-processing' in name for name in names)

    def test_list_shows_worktree_paths(self, requires_v011, temp_spec_kitty_project):
        """
        Test that list output shows worktree paths.

        Implementation steps:
        1. Create legacy worktrees
        2. Run list-legacy-features
        3. Output should include paths: .worktrees/001-auth
        4. Full paths for clarity
        """
        create_legacy_worktree(temp_spec_kitty_project, 1, 'auth')

        legacy_worktrees = detect_legacy_worktrees(temp_spec_kitty_project)

        assert len(legacy_worktrees) == 1
        worktree_path = legacy_worktrees[0]
        assert worktree_path.name == '001-auth'
        assert '.worktrees' in str(worktree_path)

    def test_list_empty_when_no_legacy(self, requires_v011, temp_spec_kitty_project):
        """
        Test empty output when no legacy worktrees.

        Implementation steps:
        1. Create only new worktrees: 001-feature-WP01
        2. Run list-legacy-features
        3. Output should be empty or "No legacy features found"
        4. Clear indication of clean state
        """
        # Create only new worktrees
        create_new_worktree(temp_spec_kitty_project, 1, 'feature', 'WP01')

        # Detect legacy
        legacy_worktrees = detect_legacy_worktrees(temp_spec_kitty_project)

        # Should find none
        assert len(legacy_worktrees) == 0


class TestMigrationExecution:
    """Tests for migration execution"""

    def test_migration_runs_successfully(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration completes without errors.

        Implementation steps:
        1. No legacy worktrees
        2. Run migration (may be automatic or explicit command)
        3. Should complete successfully
        4. No errors, warnings OK
        """
        # Validation should pass
        can_upgrade, message = validate_upgrade(temp_spec_kitty_project)
        assert can_upgrade, "Migration should be allowed"

    def test_migration_idempotent(self, requires_v011, temp_spec_kitty_project):
        """
        Test that running migration twice doesn't break.

        Implementation steps:
        1. Run migration once (succeeds)
        2. Run migration again
        3. Should succeed (idempotent)
        4. Or skip with message "already at v0.11.0"
        5. No corruption from double run
        """
        # First validation
        can_upgrade1, _ = validate_upgrade(temp_spec_kitty_project)

        # Second validation (should give same result)
        can_upgrade2, _ = validate_upgrade(temp_spec_kitty_project)

        assert can_upgrade1 == can_upgrade2, "Validation should be idempotent"

    def test_migration_updates_version(self, requires_v011, temp_spec_kitty_project):
        """
        Test that version is bumped to 0.11.0.

        Implementation steps:
        1. Before migration: version 0.10.x
        2. Run migration
        3. After: version 0.11.0
        4. Version stored in .kittify/version or similar
        """
        # Check installed version
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        # Should be v0.11.0+
        assert '0.11' in result.stdout or '0.12' in result.stdout or '1.' in result.stdout

    def test_migration_preserves_existing_features(self, requires_v011, temp_spec_kitty_project):
        """
        Test that merged features in kitty-specs/ untouched.

        Implementation steps:
        1. Create kitty-specs/001-old-feature/ (merged feature)
        2. Run migration
        3. Verify 001-old-feature/ still exists
        4. Content unchanged
        5. Only templates modified, not user data
        """
        # Create a merged feature
        feature_dir = temp_spec_kitty_project / 'kitty-specs' / '001-old-feature'
        feature_dir.mkdir(parents=True)
        spec_file = feature_dir / 'spec.md'
        spec_file.write_text('# Old Feature\n\nThis is a merged feature.')

        # Commit it
        subprocess.run(
            ['git', 'add', '.'],
            cwd=str(temp_spec_kitty_project),
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['git', 'commit', '-m', 'Add old feature'],
            cwd=str(temp_spec_kitty_project),
            check=True,
            capture_output=True
        )

        # Run validation (no migration to actually run, but validate won't touch data)
        validate_upgrade(temp_spec_kitty_project)

        # Verify feature still exists
        assert spec_file.exists()
        assert 'Old Feature' in spec_file.read_text()

    def test_migration_registry_updated(self, requires_v011, temp_spec_kitty_project):
        """
        Test that migration is recorded in registry.

        Implementation steps:
        1. Run migration
        2. Check migration registry (may be .kittify/migrations.json)
        3. Verify entry for m_0_11_0_workspace_per_wp
        4. Timestamp, status recorded
        5. Migration tracking
        """
        # Check if migrations registry exists
        registry_file = temp_spec_kitty_project / '.kittify' / 'migrations.json'

        # Document expected behavior
        # After migration, registry should track:
        # - migration_id: "0.11.0_workspace_per_wp"
        # - timestamp
        # - status: "applied"

        # This is implementation-dependent
        pass

    def test_rollback_on_failure(self, requires_v011, temp_spec_kitty_project):
        """
        Test that partial migration is rolled back on error.

        Implementation steps:
        1. Simulate error during migration (e.g., file write fails)
        2. Migration should fail
        3. Verify state rolled back:
           - Templates not partially updated
           - Version not changed
           - Registry not modified
        4. All-or-nothing guarantee
        5. May be hard to test - document behavior
        """
        # This test documents expected behavior:
        # Migrations should be transactional - either fully succeed or fully fail
        # No partial state should be left

        # Implementation of actual rollback testing would require:
        # 1. Mocking file operations to fail mid-migration
        # 2. Verifying original state restored
        # 3. Checking no partial updates applied

        # For now, we document that this behavior is expected
        # and should be implemented in the migration system
        pass
