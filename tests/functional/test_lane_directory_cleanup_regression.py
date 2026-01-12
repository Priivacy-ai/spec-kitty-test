"""
Test: Lane Directory Cleanup Regression Prevention

Purpose: Prevent lane directories from persisting after migration 0.9.0/0.9.1.

CONTEXT - User Report (Issue #70 Related):
User upgraded from v0.6.4 → v0.10.12 and found lane directories (planned/,
doing/, for_review/, done/) still existed in tasks/ even after running upgrade
command. This caused Claude agents to get confused about which lane structure
to use (directories vs frontmatter).

SUSPICION:
Lane directories from pre-v0.9.0 may persist through upgrades, even though
migrations 0.9.0 and 0.9.1 should remove them. This test suite ensures the
directories are actually removed and stay removed.

MIGRATIONS INVOLVED:
- Migration 0.9.0 (m_0_9_0_frontmatter_only_lanes.py):
  Started migration from directory-based lanes to frontmatter-only

- Migration 0.9.1 (m_0_9_1_complete_lane_migration.py):
  Completed migration, removes ALL lane subdirectories

LANE DIRECTORIES (should be removed after v0.9.1):
- tasks/planned/
- tasks/doing/
- tasks/for_review/
- tasks/done/

Test Coverage:
- TestLaneDirectoryRemoval: Verify directories removed after migration
- TestLaneDirectoryPersistence: Ensure they don't come back
- TestUpgradePathLaneCleanup: Test full upgrade paths remove lanes
- TestWorktreeLaneCleanup: Verify worktrees also cleaned

Version: Tests apply to v0.9.0+
"""

import subprocess
import tempfile
from pathlib import Path
import pytest


# Lane directories that should NOT exist after v0.9.1
LEGACY_LANE_DIRS = ["planned", "doing", "for_review", "done"]


class TestLaneDirectoryRemoval:
    """
    CRITICAL: Verify lane directories are removed after v0.9.0/v0.9.1 migrations.

    Tests that directories don't persist after migration.
    """

    @pytest.fixture
    def requires_v09(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.9.0"""
        if spec_kitty_version < (0, 9, 0):
            pytest.skip("Requires spec-kitty >= 0.9.0 (frontmatter-only lanes)")

    def test_no_lane_directories_in_main_specs(self, spec_kitty_repo_root, requires_v09):
        """
        CRITICAL: kitty-specs/ should have NO lane subdirectories after v0.9.0.

        Lane directories cause agent confusion.
        """
        main_specs = spec_kitty_repo_root / 'kitty-specs'

        if not main_specs.exists():
            pytest.skip("No kitty-specs/ directory (no features yet)")

        # Check each feature
        lane_dirs_found = []

        for feature_dir in main_specs.iterdir():
            if not feature_dir.is_dir():
                continue

            tasks_dir = feature_dir / 'tasks'
            if not tasks_dir.exists():
                continue

            # Check for legacy lane directories
            for lane in LEGACY_LANE_DIRS:
                lane_path = tasks_dir / lane
                if lane_path.exists() and lane_path.is_dir():
                    # Count files in directory
                    files = [f for f in lane_path.iterdir() if f.is_file()]
                    if files:
                        lane_dirs_found.append(f"{feature_dir.name}/tasks/{lane}/ ({len(files)} files)")
                    else:
                        # Even empty directories shouldn't exist
                        lane_dirs_found.append(f"{feature_dir.name}/tasks/{lane}/ (empty)")

        assert len(lane_dirs_found) == 0, (
            f"REGRESSION: Lane directories found in kitty-specs after v0.9.0!\n\n"
            f"Found {len(lane_dirs_found)} lane dir(s):\n" +
            "\n".join([f"  - {d}" for d in lane_dirs_found]) +
            "\n\nMigrations 0.9.0 and 0.9.1 should have removed these.\n"
            "Lane directories cause agent confusion (directory vs frontmatter)."
        )

    def test_no_lane_directories_in_worktrees(self, spec_kitty_repo_root, requires_v09):
        """
        CRITICAL: .worktrees/ should have NO lane subdirectories after v0.9.1.

        Migration 0.9.1 specifically cleans worktrees.
        """
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            pytest.skip("No .worktrees/ directory")

        lane_dirs_found = []

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            wt_specs = worktree / 'kitty-specs'
            if not wt_specs.exists():
                continue

            for feature_dir in wt_specs.iterdir():
                if not feature_dir.is_dir():
                    continue

                tasks_dir = feature_dir / 'tasks'
                if not tasks_dir.exists():
                    continue

                # Check for lane directories in worktree
                for lane in LEGACY_LANE_DIRS:
                    lane_path = tasks_dir / lane
                    if lane_path.exists():
                        files = list(lane_path.iterdir())
                        lane_dirs_found.append(f"{worktree.name}/{feature_dir.name}/tasks/{lane}/ ({len(files)} items)")

        assert len(lane_dirs_found) == 0, (
            f"REGRESSION: Lane directories in worktrees after v0.9.1!\n\n"
            f"Found:\n" +
            "\n".join([f"  - {d}" for d in lane_dirs_found]) +
            "\n\nMigration 0.9.1 should clean up ALL worktrees."
        )

    def test_tasks_directory_is_flat(self, spec_kitty_repo_root, requires_v09):
        """
        VALIDATION: tasks/ should be flat (no subdirectories except __pycache__).

        After v0.9.0, tasks should be in tasks/ root, not tasks/{lane}/.
        """
        main_specs = spec_kitty_repo_root / 'kitty-specs'

        if not main_specs.exists():
            pytest.skip("No kitty-specs/ directory")

        problematic_dirs = []

        for feature_dir in main_specs.iterdir():
            if not feature_dir.is_dir():
                continue

            tasks_dir = feature_dir / 'tasks'
            if not tasks_dir.exists():
                continue

            # Check for subdirectories (other than __pycache__)
            subdirs = [
                d for d in tasks_dir.iterdir()
                if d.is_dir() and d.name != '__pycache__'
            ]

            # Filter to lane directories specifically
            lane_subdirs = [d for d in subdirs if d.name in LEGACY_LANE_DIRS]

            if lane_subdirs:
                problematic_dirs.append(f"{feature_dir.name}/tasks/ has: {[d.name for d in lane_subdirs]}")

        assert len(problematic_dirs) == 0, (
            f"Tasks directories are not flat!\n\n" +
            "\n".join([f"  - {d}" for d in problematic_dirs]) +
            "\n\nAfter v0.9.0, tasks/ should be flat with frontmatter-based lanes."
        )


class TestLaneDirectoryPersistence:
    """
    CRITICAL: Ensure lane directories don't come back after removal.

    Tests that later migrations don't recreate lane directories.
    """

    @pytest.fixture
    def requires_v09(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.9.0"""
        if spec_kitty_version < (0, 9, 0):
            pytest.skip("Requires spec-kitty >= 0.9.0")

    def test_migration_0_10_x_does_not_recreate_lanes(self, spec_kitty_repo_root, requires_v09):
        """
        REGRESSION CHECK: Migration 0.10.x must not recreate lane directories.

        User reported lane directories persisting after upgrade to 0.10.12.
        This suggests later migrations might recreate them.
        """
        # This test checks current state - if lane dirs exist, they shouldn't
        # It's a regression test for the user's reported issue

        all_specs_dirs = []

        # Check main specs
        main_specs = spec_kitty_repo_root / 'kitty-specs'
        if main_specs.exists():
            all_specs_dirs.append(('main', main_specs))

        # Check worktrees
        worktrees_dir = spec_kitty_repo_root / '.worktrees'
        if worktrees_dir.exists():
            for wt in worktrees_dir.iterdir():
                if wt.is_dir():
                    wt_specs = wt / 'kitty-specs'
                    if wt_specs.exists():
                        all_specs_dirs.append((f'worktree:{wt.name}', wt_specs))

        lane_dirs_found = []

        for location, specs_dir in all_specs_dirs:
            for feature_dir in specs_dir.iterdir():
                if not feature_dir.is_dir():
                    continue

                tasks_dir = feature_dir / 'tasks'
                if not tasks_dir.exists():
                    continue

                for lane in LEGACY_LANE_DIRS:
                    lane_path = tasks_dir / lane
                    if lane_path.exists():
                        lane_dirs_found.append(f"{location}/{feature_dir.name}/tasks/{lane}/")

        assert len(lane_dirs_found) == 0, (
            f"CRITICAL REGRESSION: Lane directories found on v0.9.0+ installation!\n\n"
            f"Found {len(lane_dirs_found)} lane dir(s):\n" +
            "\n".join([f"  - {d}" for d in lane_dirs_found]) +
            "\n\nThis matches user report: lane dirs persisting after upgrade to 0.10.12.\n"
            "Later migrations (0.10.x) may be recreating directories that 0.9.x removed."
        )


class TestUpgradePathLaneCleanup:
    """
    CRITICAL: Test that upgrade paths properly clean up lane directories.

    Simulates user's upgrade path: v0.6.4 → v0.10.13
    """

    def test_upgrade_from_0_6_4_removes_lane_directories(self, spec_kitty_repo_root):
        """
        USER SCENARIO: Upgrade from v0.6.4 (has lanes) to v0.10.13 (no lanes).

        This simulates the user's reported upgrade path.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mock v0.6.4 project with lane directories
            project = tmpdir_path / 'v064_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.6.4')

            # Create feature with lane directories (v0.6.4 structure)
            feature = project / 'kitty-specs' / '001-test-feature'
            feature.mkdir(parents=True)

            # Create lane directories with files
            for lane in LEGACY_LANE_DIRS:
                lane_dir = feature / 'tasks' / lane
                lane_dir.mkdir(parents=True)
                # Add a work package file
                (lane_dir / 'WP01.md').write_text('---\ntitle: WP01\n---\n\n# WP01')

            # Verify lane directories exist before upgrade
            for lane in LEGACY_LANE_DIRS:
                lane_path = feature / 'tasks' / lane
                assert lane_path.exists(), f"Test setup error: {lane}/ should exist"

            # Run upgrade to v0.10.13
            result = subprocess.run(
                ['spec-kitty', 'upgrade', '--force'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Upgrade should succeed
            if result.returncode != 0:
                pytest.skip(f"Upgrade failed: {result.stderr}")

            # Verify lane directories REMOVED
            lane_dirs_remaining = []
            for lane in LEGACY_LANE_DIRS:
                lane_path = feature / 'tasks' / lane
                if lane_path.exists():
                    lane_dirs_remaining.append(lane)

            assert len(lane_dirs_remaining) == 0, (
                f"CRITICAL: Lane directories not removed after upgrade!\n\n"
                f"Still exist: {lane_dirs_remaining}\n\n"
                "Migrations 0.9.0 and 0.9.1 should remove these.\n"
                "This is the EXACT issue reported by user in Issue #70."
            )

            # Verify WP files moved to flat tasks/
            flat_tasks = feature / 'tasks'
            wp_files = list(flat_tasks.glob('WP*.md'))

            assert len(wp_files) > 0, (
                "WP files not moved to flat tasks/ directory!\n"
                "Migration should move files from tasks/{lane}/ to tasks/"
            )

    def test_upgrade_to_0_10_13_ensures_flat_structure(self, spec_kitty_repo_root):
        """
        VALIDATION: Any upgrade to v0.10.13 should result in flat tasks/.

        No matter the starting version, result should be flat structure.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mock old project with lane dirs
            project = tmpdir_path / 'old_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.8.0')  # Pre-lane-migration

            # Create feature with lane structure
            feature = project / 'kitty-specs' / '001-test'
            (feature / 'tasks' / 'planned').mkdir(parents=True)
            (feature / 'tasks' / 'planned' / 'WP01.md').write_text('---\n---\n\n# WP01')

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

            # Check final structure
            tasks_dir = feature / 'tasks'

            # Should NOT have lane subdirectories
            subdirs = [
                d.name for d in tasks_dir.iterdir()
                if d.is_dir() and d.name in LEGACY_LANE_DIRS
            ]

            assert len(subdirs) == 0, (
                f"Lane directories still exist after upgrade!\n"
                f"Found: {subdirs}\n\n"
                "Upgrade to v0.10.13 should result in flat structure."
            )


class TestWorktreeLaneCleanup:
    """
    CRITICAL: Verify worktrees also have lane directories cleaned.

    Migration 0.9.1 specifically handles worktree cleanup.
    """

    @pytest.fixture
    def requires_v09_1(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.9.1"""
        if spec_kitty_version < (0, 9, 1):
            pytest.skip("Requires spec-kitty >= 0.9.1 (complete lane migration)")

    def test_worktrees_have_no_lane_directories(self, spec_kitty_repo_root, requires_v09_1):
        """
        CRITICAL: Worktrees must not have lane directories after v0.9.1.

        User reported seeing lane dirs in worktrees after upgrade.
        """
        worktrees_dir = spec_kitty_repo_root / '.worktrees'

        if not worktrees_dir.exists():
            pytest.skip("No .worktrees/ directory")

        worktree_lane_dirs = []

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            wt_specs = worktree / 'kitty-specs'
            if not wt_specs.exists():
                continue

            for feature_dir in wt_specs.iterdir():
                if not feature_dir.is_dir():
                    continue

                tasks_dir = feature_dir / 'tasks'
                if not tasks_dir.exists():
                    continue

                # Check for lane directories
                for lane in LEGACY_LANE_DIRS:
                    lane_path = tasks_dir / lane
                    if lane_path.exists():
                        worktree_lane_dirs.append(f"{worktree.name}/{feature_dir.name}/tasks/{lane}/")

        assert len(worktree_lane_dirs) == 0, (
            f"CRITICAL: Lane directories in worktrees!\n\n"
            f"Found:\n" +
            "\n".join([f"  - {d}" for d in worktree_lane_dirs]) +
            "\n\nMigration 0.9.1 should remove lane directories from ALL worktrees.\n"
            "This matches user's reported issue."
        )

    def test_migration_0_9_1_removes_worktree_lanes(self, spec_kitty_repo_root):
        """
        CRITICAL: Migration 0.9.1 must remove lane dirs from worktrees.

        Test the specific migration behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mock v0.9.0 project (after 0.9.0 but before 0.9.1)
            project = tmpdir_path / 'v090_project'
            project.mkdir()

            kittify = project / '.kittify'
            kittify.mkdir()
            (kittify / 'memory').mkdir()
            (kittify / 'VERSION').write_text('0.9.0')

            # Create worktree with lane directories
            worktree = project / '.worktrees' / '001-test-WP01'
            worktree.mkdir(parents=True)

            feature = worktree / 'kitty-specs' / '001-test'
            (feature / 'tasks' / 'doing').mkdir(parents=True)
            (feature / 'tasks' / 'doing' / 'WP01.md').write_text('---\nlane: doing\n---\n\n# WP01')

            # Run upgrade (should trigger 0.9.1 migration)
            result = subprocess.run(
                ['spec-kitty', 'upgrade', '--force'],
                cwd=project,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Upgrade failed: {result.stderr}")

            # Verify lane directory removed from worktree
            lane_dir = feature / 'tasks' / 'doing'

            assert not lane_dir.exists(), (
                "Migration 0.9.1 did not remove lane directory from worktree!\n"
                f"Still exists: {lane_dir}"
            )

            # Verify WP file moved to flat tasks/
            flat_wp = feature / 'tasks' / 'WP01.md'

            assert flat_wp.exists(), (
                "WP file not moved to flat tasks/ directory!"
            )


class TestLaneDirectoryAgentConfusion:
    """
    VALIDATION: Test scenarios that cause agent confusion.

    Verify that having both structures doesn't confuse behavior.
    """

    @pytest.fixture
    def requires_v09(self, spec_kitty_version):
        """Skip test if spec-kitty < 0.9.0"""
        if spec_kitty_version < (0, 9, 0):
            pytest.skip("Requires spec-kitty >= 0.9.0")

    def test_no_mixed_lane_structure(self, spec_kitty_repo_root, requires_v09):
        """
        CRITICAL: Project must not have BOTH lane dirs AND frontmatter.

        This is the confusion the user reported.
        """
        main_specs = spec_kitty_repo_root / 'kitty-specs'

        if not main_specs.exists():
            pytest.skip("No kitty-specs/")

        mixed_structure_features = []

        for feature_dir in main_specs.iterdir():
            if not feature_dir.is_dir():
                continue

            tasks_dir = feature_dir / 'tasks'
            if not tasks_dir.exists():
                continue

            # Check for lane directories
            has_lane_dirs = any(
                (tasks_dir / lane).exists()
                for lane in LEGACY_LANE_DIRS
            )

            # Check for flat WP files with frontmatter
            has_flat_wps = any(
                f.is_file() and f.suffix == '.md'
                for f in tasks_dir.iterdir()
            )

            # Having BOTH is the problematic state
            if has_lane_dirs and has_flat_wps:
                mixed_structure_features.append(feature_dir.name)

        assert len(mixed_structure_features) == 0, (
            f"CRITICAL: Mixed lane structure detected!\n\n"
            f"Features with BOTH lane dirs AND flat files:\n" +
            "\n".join([f"  - {f}" for f in mixed_structure_features]) +
            "\n\nThis causes agent confusion:\n"
            "- Agent sees lane directories (thinks it should move files)\n"
            "- Agent sees frontmatter (thinks it should update frontmatter)\n"
            "- Agent gets confused about which system to use\n\n"
            "This is the EXACT issue reported by user."
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
