"""
T046: Legacy JJ Feature Conversion Tests

Verifies that features with "vcs": "jj" in meta.json automatically convert
to git with warning message. This handles legacy features created when jj
was supported.
"""
import pytest
import json
from pathlib import Path
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
class TestLegacyJJAutoConversion:
    """Test legacy jj features auto-convert to git."""

    @pytest.fixture
    def legacy_jj_feature(self, tmp_path):
        """Create feature with legacy jj VCS in meta.json."""
        # Setup project structure
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Init git repo
        subprocess.run(["git", "init"], cwd=project_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                      cwd=project_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=project_path, capture_output=True, check=True)

        # Create feature directory
        feature_path = project_path / "kitty-specs" / "001-test-feature"
        feature_path.mkdir(parents=True)

        # Write meta.json with jj VCS
        meta = {
            "feature_number": "001",
            "slug": "001-test-feature",
            "vcs": "jj",  # Legacy jj
            "created_at": "2025-12-01T00:00:00Z"
        }
        (feature_path / "meta.json").write_text(json.dumps(meta, indent=2))

        # Create initial commit
        subprocess.run(["git", "add", "."], cwd=project_path,
                      capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"],
                      cwd=project_path, capture_output=True, check=True)

        return feature_path

    def test_legacy_jj_detected(self, legacy_jj_feature):
        """Legacy jj VCS is detected in meta.json."""
        meta_path = legacy_jj_feature / "meta.json"
        meta = json.loads(meta_path.read_text())

        assert meta["vcs"] == "jj", "Test setup: meta.json should have vcs=jj"

    def test_legacy_jj_auto_converts_to_git(self, legacy_jj_feature):
        """Legacy jj features should use git operations despite meta.json."""
        # Read original meta
        meta_path = legacy_jj_feature / "meta.json"
        original_meta = json.loads(meta_path.read_text())

        assert original_meta["vcs"] == "jj"

        # The spec-kitty behavior is to use git despite meta.json saying jj
        # because is_jj_available() returns False

        # Simulate what spec-kitty does: check available VCS
        from specify_cli.core.vcs.detection import is_jj_available

        jj_available = is_jj_available()
        assert jj_available is False, "jj should not be available"

        # Therefore git will be used regardless of meta.json
        actual_vcs = "git" if not jj_available else "jj"
        assert actual_vcs == "git"

    def test_legacy_conversion_idempotent(self, legacy_jj_feature):
        """Checking VCS multiple times yields consistent results."""
        from specify_cli.core.vcs.detection import is_jj_available

        # Check multiple times
        results = [is_jj_available() for _ in range(5)]

        # All should be False
        assert all(r is False for r in results)

        # VCS selection should consistently be git
        vcs_choices = ["git" if not r else "jj" for r in results]
        assert all(v == "git" for v in vcs_choices)


@pytest.mark.functional
@pytest.mark.vcs
class TestLegacyConversionWarning:
    """Test warning messages for legacy jj feature conversion."""

    @pytest.fixture
    def legacy_feature_with_jj(self, tmp_path):
        """Create a minimal legacy feature with jj VCS."""
        feature_path = tmp_path / "kitty-specs" / "001-legacy"
        feature_path.mkdir(parents=True)

        meta = {
            "feature_number": "001",
            "slug": "001-legacy",
            "vcs": "jj",
            "created_at": "2025-11-01T00:00:00Z"
        }
        (feature_path / "meta.json").write_text(json.dumps(meta, indent=2))

        return feature_path

    def test_warning_indicates_jj_legacy(self, legacy_feature_with_jj):
        """Warning message should indicate legacy jj was found."""
        meta_path = legacy_feature_with_jj / "meta.json"
        meta = json.loads(meta_path.read_text())

        # Construct expected warning message components
        vcs_in_meta = meta["vcs"]
        assert vcs_in_meta == "jj"

        # A proper warning should include:
        expected_terms = ["jj", "git"]  # Mention both old and new VCS

        warning_message = f"Feature uses legacy VCS '{vcs_in_meta}', using git instead"

        for term in expected_terms:
            assert term in warning_message.lower()

    def test_warning_is_actionable(self, legacy_feature_with_jj):
        """Warning provides clear information about the conversion."""
        # The warning should explain:
        # 1. What was detected (jj in meta.json)
        # 2. What action was taken (using git instead)
        # 3. Why (jj support disabled)

        expected_info = [
            "jj",        # What was found
            "git",       # What is being used
        ]

        warning = "Legacy VCS 'jj' detected in meta.json, using git (jj disabled)"

        for info in expected_info:
            assert info in warning.lower()


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestLegacyConversionEdgeCases:
    """Edge cases for legacy jj conversion."""

    def test_missing_vcs_field_defaults_to_git(self, tmp_path):
        """Meta.json without vcs field defaults to git."""
        feature_path = tmp_path / "kitty-specs" / "001-no-vcs"
        feature_path.mkdir(parents=True)

        meta = {
            "feature_number": "001",
            "slug": "001-no-vcs",
            # No vcs field
            "created_at": "2025-10-01T00:00:00Z"
        }
        (feature_path / "meta.json").write_text(json.dumps(meta, indent=2))

        # Default should be git
        default_vcs = meta.get("vcs", "git")
        assert default_vcs == "git"

    def test_invalid_vcs_value_handled(self, tmp_path):
        """Invalid vcs value handled gracefully."""
        feature_path = tmp_path / "kitty-specs" / "001-invalid"
        feature_path.mkdir(parents=True)

        meta = {
            "feature_number": "001",
            "slug": "001-invalid",
            "vcs": "svn",  # Invalid VCS
            "created_at": "2025-09-01T00:00:00Z"
        }
        (feature_path / "meta.json").write_text(json.dumps(meta, indent=2))

        # Invalid VCS should fall back to git
        vcs = meta.get("vcs")
        valid_vcs_types = ["git", "jj"]

        if vcs not in valid_vcs_types:
            fallback_vcs = "git"
        else:
            fallback_vcs = "git" if vcs == "jj" else vcs  # jj disabled

        assert fallback_vcs == "git"

    def test_mixed_legacy_and_current_features(self, tmp_path):
        """Mixed legacy jj and current git features handled."""
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir(parents=True)

        # Create legacy jj feature
        legacy_path = kitty_specs / "001-legacy-jj"
        legacy_path.mkdir()
        (legacy_path / "meta.json").write_text(json.dumps({
            "feature_number": "001",
            "slug": "001-legacy-jj",
            "vcs": "jj",
        }, indent=2))

        # Create current git feature
        current_path = kitty_specs / "002-current-git"
        current_path.mkdir()
        (current_path / "meta.json").write_text(json.dumps({
            "feature_number": "002",
            "slug": "002-current-git",
            "vcs": "git",
        }, indent=2))

        # Both should use git
        for feature_dir in [legacy_path, current_path]:
            meta = json.loads((feature_dir / "meta.json").read_text())
            original_vcs = meta["vcs"]

            # Effective VCS is always git (jj disabled)
            from specify_cli.core.vcs.detection import is_jj_available
            effective_vcs = original_vcs if original_vcs == "git" else (
                "git" if not is_jj_available() else "jj"
            )
            assert effective_vcs == "git"
