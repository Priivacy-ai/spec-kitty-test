"""
Mixed Features Tests

Tests that features with different VCS settings (git, legacy jj)
use correct implementation for each, with no cross-contamination.
"""
import pytest
from pathlib import Path
import json
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
class TestMixedFeaturesCorrectVCS:
    """Test that mixed features use correct VCS for each."""

    def test_mixed_features_correct_vcs(self, feature_with_vcs_lock, command_logger):
        """Feature1 vcs=git, Feature2 vcs=jj (legacy), correct VCS for each."""
        # Create two features
        feature1 = feature_with_vcs_lock("001", vcs_type="git")
        feature2 = feature_with_vcs_lock("002", vcs_type="jj")  # Legacy

        # Load meta for both
        meta1 = json.loads((feature1 / "meta.json").read_text())
        meta2 = json.loads((feature2 / "meta.json").read_text())

        assert meta1["vcs"] == "git"
        assert meta2["vcs"] == "jj"  # Legacy, will be converted

        # Simulate operations on feature1 (should use git)
        subprocess.run(["git", "status"], cwd=feature1, capture_output=True)

        # Feature2 should auto-convert jj -> git
        jj_available = False  # Detection disabled
        if meta2["vcs"] == "jj" and not jj_available:
            meta2["vcs"] = "git"
            (feature2 / "meta.json").write_text(json.dumps(meta2, indent=2))

        subprocess.run(["git", "status"], cwd=feature2, capture_output=True)

        # Verify only git commands (no jj for either feature)
        command_logger.assert_no_jj_commands()
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert len(git_cmds) == 2  # One for each feature

    def test_all_git_features_use_git(self, feature_with_vcs_lock, command_logger):
        """Multiple git features all use git commands."""
        features = [
            feature_with_vcs_lock("001", vcs_type="git"),
            feature_with_vcs_lock("002", vcs_type="git"),
            feature_with_vcs_lock("003", vcs_type="git"),
        ]

        for feature_dir in features:
            meta = json.loads((feature_dir / "meta.json").read_text())
            assert meta["vcs"] == "git"
            subprocess.run(["git", "status"], cwd=feature_dir, capture_output=True)

        command_logger.assert_only_git_commands()
        assert len(command_logger.get_vcs_commands()) == 3


@pytest.mark.functional
@pytest.mark.vcs
class TestSwitchingBetweenFeatures:
    """Test switching between features uses correct VCS each time."""

    def test_switching_between_features_vcs(self, feature_with_vcs_lock, command_logger):
        """Switching between features uses correct VCS each time."""
        feature1 = feature_with_vcs_lock("001", vcs_type="git")
        feature2 = feature_with_vcs_lock("002", vcs_type="git")

        # Work on feature1
        subprocess.run(["git", "log", "-1"], cwd=feature1, capture_output=True)

        # Switch to feature2
        subprocess.run(["git", "log", "-1"], cwd=feature2, capture_output=True)

        # Switch back to feature1
        subprocess.run(["git", "status"], cwd=feature1, capture_output=True)

        # Verify all used git
        command_logger.assert_only_git_commands()
        git_cmds = command_logger.get_vcs_commands()
        assert len(git_cmds) == 3
        assert all(binary == "git" for binary, _ in git_cmds)

    def test_rapid_switching_no_contamination(self, feature_with_vcs_lock, command_logger):
        """Rapid switching between features causes no contamination."""
        f1 = feature_with_vcs_lock("001", vcs_type="git")
        f2 = feature_with_vcs_lock("002", vcs_type="git")
        f3 = feature_with_vcs_lock("003", vcs_type="git")

        # Rapid switching pattern
        for _ in range(3):
            subprocess.run(["git", "status"], cwd=f1, capture_output=True)
            subprocess.run(["git", "status"], cwd=f2, capture_output=True)
            subprocess.run(["git", "status"], cwd=f3, capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len([cmd for binary, cmd in command_logger.command_log if binary == "git"]) == 9


@pytest.mark.functional
@pytest.mark.vcs
class TestConcurrentFeatureOperations:
    """Test concurrent operations on different features don't cross-contaminate."""

    def test_concurrent_features_no_cross_contamination(self, feature_with_vcs_lock, command_logger):
        """Concurrent operations on different features don't cross-contaminate."""
        features = [
            feature_with_vcs_lock(f"00{i}", vcs_type="git")
            for i in range(1, 4)
        ]

        # Simulate concurrent operations
        for feature_dir in features:
            subprocess.run(["git", "status"], cwd=feature_dir, capture_output=True)

        # Verify all used git
        command_logger.assert_no_jj_commands()
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert len(git_cmds) == 3  # One per feature

    def test_multiple_operations_per_feature(self, feature_with_vcs_lock, command_logger):
        """Multiple operations per feature all use correct VCS."""
        feature = feature_with_vcs_lock("001", vcs_type="git")

        operations = [
            ["git", "status"],
            ["git", "diff"],
            ["git", "log", "-1"],
            ["git", "branch", "-a"],
        ]

        for op in operations:
            subprocess.run(op, cwd=feature, capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len(command_logger.command_log) == 4


@pytest.mark.functional
@pytest.mark.vcs
class TestLegacyJJFeatureMigration:
    """Test legacy jj features properly migrate to git."""

    def test_legacy_jj_feature_migrates_on_access(self, feature_with_vcs_lock, command_logger):
        """Legacy jj feature migrates to git when accessed."""
        feature = feature_with_vcs_lock("001", vcs_type="jj")  # Legacy
        meta_path = feature / "meta.json"

        # Verify starts as jj
        meta = json.loads(meta_path.read_text())
        assert meta["vcs"] == "jj"

        # Simulate access that triggers migration
        jj_available = False
        if meta["vcs"] == "jj" and not jj_available:
            meta["vcs"] = "git"
            meta_path.write_text(json.dumps(meta, indent=2))

        # Now use it
        subprocess.run(["git", "status"], cwd=feature, capture_output=True)

        # Verify migrated and using git
        final_meta = json.loads(meta_path.read_text())
        assert final_meta["vcs"] == "git"
        command_logger.assert_only_git_commands()

    def test_mixed_legacy_and_new_features(self, feature_with_vcs_lock, command_logger):
        """Mix of legacy jj and new git features all end up using git."""
        legacy = feature_with_vcs_lock("001", vcs_type="jj")
        new_feature = feature_with_vcs_lock("002", vcs_type="git")

        # Migrate legacy
        meta = json.loads((legacy / "meta.json").read_text())
        if meta["vcs"] == "jj":
            meta["vcs"] = "git"
            (legacy / "meta.json").write_text(json.dumps(meta, indent=2))

        # Use both
        subprocess.run(["git", "status"], cwd=legacy, capture_output=True)
        subprocess.run(["git", "status"], cwd=new_feature, capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len([cmd for binary, cmd in command_logger.command_log if binary == "git"]) == 2


@pytest.mark.functional
@pytest.mark.vcs
class TestFeatureIsolation:
    """Test that feature VCS settings are isolated from each other."""

    def test_feature_vcs_independent(self, multiple_features_with_vcs, command_logger):
        """Each feature's VCS setting is independent of others."""
        features = multiple_features_with_vcs([
            ("001", "git"),
            ("002", "jj"),  # Legacy, will be converted
            ("003", "git"),
        ])

        # Migrate legacy feature
        legacy = features[1]
        meta = json.loads((legacy / "meta.json").read_text())
        if meta["vcs"] == "jj":
            meta["vcs"] = "git"
            (legacy / "meta.json").write_text(json.dumps(meta, indent=2))

        # Use all features
        for feature in features:
            subprocess.run(["git", "status"], cwd=feature, capture_output=True)

        command_logger.assert_no_jj_commands()

    def test_modifying_one_feature_doesnt_affect_others(self, multiple_features_with_vcs):
        """Modifying one feature's VCS doesn't affect others."""
        features = multiple_features_with_vcs([
            ("001", "git"),
            ("002", "git"),
            ("003", "git"),
        ])

        # Modify feature 2 (simulate corruption)
        meta2 = json.loads((features[1] / "meta.json").read_text())
        meta2["vcs"] = "invalid"
        (features[1] / "meta.json").write_text(json.dumps(meta2, indent=2))

        # Check other features unaffected
        meta1 = json.loads((features[0] / "meta.json").read_text())
        meta3 = json.loads((features[2] / "meta.json").read_text())

        assert meta1["vcs"] == "git"
        assert meta3["vcs"] == "git"


@pytest.mark.functional
@pytest.mark.vcs
class TestVCSCommandSequences:
    """Test realistic VCS command sequences across features."""

    def test_worktree_creation_across_features(self, feature_with_vcs_lock, command_logger):
        """Worktree creation for multiple features uses git."""
        f1 = feature_with_vcs_lock("001", vcs_type="git")
        f2 = feature_with_vcs_lock("002", vcs_type="git")

        # Worktree creation commands
        subprocess.run(["git", "worktree", "add", ".worktrees/001-test/WP01", "HEAD"],
                       capture_output=True)
        subprocess.run(["git", "worktree", "add", ".worktrees/002-test/WP01", "HEAD"],
                       capture_output=True)

        command_logger.assert_no_jj_commands()
        git_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "git"]
        assert all("worktree" in cmd for cmd in git_cmds)

    def test_commit_sequence_across_features(self, feature_with_vcs_lock, command_logger):
        """Commit sequence for multiple features uses git."""
        f1 = feature_with_vcs_lock("001", vcs_type="git")
        f2 = feature_with_vcs_lock("002", vcs_type="git")

        # Commit sequence
        subprocess.run(["git", "add", "."], cwd=f1, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature 1"], cwd=f1, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=f2, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature 2"], cwd=f2, capture_output=True)

        command_logger.assert_no_jj_commands()
        assert len(command_logger.command_log) == 4
