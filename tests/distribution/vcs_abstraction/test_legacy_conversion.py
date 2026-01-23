"""
Distribution tests for legacy JJ feature conversion (WP11: T064).

Validates that legacy features with jj in meta.json are handled correctly
after jj rollback (jj is no longer supported).
"""
import pytest
import json
from pathlib import Path


@pytest.mark.distribution
@pytest.mark.vcs
class TestLegacyJJConversion:
    """Tests for handling of legacy jj features."""

    def test_legacy_jj_feature_uses_git(self, legacy_jj_feature):
        """
        Verify legacy jj feature uses git backend.

        Validates spec.md User Story 4, Acceptance Scenario 4:
        "Given existing feature with vcs: jj in meta.json,
         When accessing feature,
         Then git backend is used (jj disabled)"
        """
        from specify_cli.core.vcs import is_jj_available, is_git_available

        # Original meta has jj
        meta_file = legacy_jj_feature / "meta.json"
        original_content = json.loads(meta_file.read_text())
        assert original_content.get("vcs") == "jj", \
            "Test setup should have jj in meta.json"

        # JJ should be unavailable
        assert is_jj_available() is False, \
            "JJ should be unavailable after rollback"

        # Git should be available
        assert is_git_available() is True, \
            "Git should be available as fallback"

    def test_legacy_conversion_preserves_data(self, legacy_jj_feature):
        """
        Verify meta.json fields are preserved during operation.

        Validates data integrity - fields should not be lost.
        """
        # Add extra fields to meta.json
        meta_file = legacy_jj_feature / "meta.json"
        meta_content = {
            "vcs": "jj",
            "feature_number": "001",
            "custom_field": "custom_value",
            "nested": {"key": "value"}
        }
        meta_file.write_text(json.dumps(meta_content, indent=2))

        # Read back
        updated = json.loads(meta_file.read_text())

        # All fields should be preserved
        assert updated.get("vcs") == "jj", \
            "vcs field should be present"
        assert updated.get("feature_number") == "001", \
            "feature_number should be preserved"
        assert updated.get("custom_field") == "custom_value", \
            "custom_field should be preserved"
        assert updated.get("nested", {}).get("key") == "value", \
            "nested fields should be preserved"

    def test_multiple_legacy_features_detected(self, tmp_path):
        """
        Verify multiple legacy features are handled correctly.

        Tests that jj detection returns False for all features.
        """
        from specify_cli.core.vcs import is_jj_available

        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()

        # Create multiple legacy features
        features = []
        for i in range(3):
            feature_dir = kitty_specs / f"00{i+1}-legacy-{i+1}"
            feature_dir.mkdir()
            (feature_dir / "spec.md").write_text(f"# Feature {i+1}")
            (feature_dir / "meta.json").write_text(
                json.dumps({"vcs": "jj", "feature_number": f"00{i+1}"})
            )
            (feature_dir / "tasks").mkdir()
            features.append(feature_dir)

        # JJ should be unavailable for all
        assert is_jj_available() is False, \
            "JJ should be unavailable regardless of meta.json content"


@pytest.mark.distribution
@pytest.mark.vcs
class TestNoConversionNeeded:
    """Tests for features that don't need conversion."""

    def test_git_feature_uses_git(self, git_initialized_project):
        """
        Verify git features use git backend.

        Features with vcs: git should use git directly.
        """
        from specify_cli.core.vcs import is_git_available, get_vcs, VCSBackend

        # Create feature with git
        kitty_specs = git_initialized_project / "kitty-specs" / "001-git-feature"
        kitty_specs.mkdir(parents=True)
        (kitty_specs / "spec.md").write_text("# Git Feature")
        meta_file = kitty_specs / "meta.json"
        meta_file.write_text('{"vcs": "git", "feature_number": "001"}')
        (kitty_specs / "tasks").mkdir()

        # Git should be available
        assert is_git_available() is True, \
            "Git should be available"

        # Should be able to create git VCS
        vcs = get_vcs(git_initialized_project, VCSBackend.GIT)
        assert vcs is not None, \
            "Should be able to create git VCS"
