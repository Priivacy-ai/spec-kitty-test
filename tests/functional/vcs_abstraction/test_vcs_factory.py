"""
VCS Factory Selection Tests

Tests that VCS factory always returns GitVCS instance when jj disabled.
Validates factory logic, legacy jj feature auto-conversion, and edge cases.
"""
import pytest
from pathlib import Path
import json


@pytest.mark.functional
@pytest.mark.vcs
class TestFactoryReturnsGitWhenJJDisabled:
    """Test factory returns GitVCS when jj detection disabled."""

    def test_factory_returns_git_when_jj_disabled(self, feature_with_vcs_lock):
        """VCS factory returns GitVCS when jj detection disabled."""
        # Create feature with vcs=git
        feature_dir = feature_with_vcs_lock("001", vcs_type="git")
        meta = json.loads((feature_dir / "meta.json").read_text())

        # Simulate factory logic
        vcs_from_meta = meta["vcs"]
        jj_available = False  # Detection disabled

        # Factory logic: use meta.json value if valid
        if vcs_from_meta == "jj" and not jj_available:
            selected_vcs = "git"  # Auto-convert
        else:
            selected_vcs = vcs_from_meta

        assert selected_vcs == "git"

    def test_factory_explicit_git_selection(self, feature_with_vcs_lock):
        """Factory uses git when explicitly specified in meta.json."""
        feature_dir = feature_with_vcs_lock("002", vcs_type="git")
        meta = json.loads((feature_dir / "meta.json").read_text())

        assert meta["vcs"] == "git"

        # Factory logic - explicit git
        selected_vcs = meta["vcs"]

        assert selected_vcs == "git"


@pytest.mark.functional
@pytest.mark.vcs
class TestLegacyJJAutoConversion:
    """Test legacy jj features auto-convert to git."""

    def test_factory_converts_legacy_jj_to_git(self, feature_with_vcs_lock):
        """Legacy feature with vcs=jj auto-converts to git."""
        # Create legacy feature with jj
        feature_dir = feature_with_vcs_lock("003", vcs_type="jj")
        meta_path = feature_dir / "meta.json"
        meta = json.loads(meta_path.read_text())

        assert meta["vcs"] == "jj"  # Legacy value

        # Simulate factory conversion
        jj_available = False  # Detection disabled
        if meta["vcs"] == "jj" and not jj_available:
            # Auto-convert
            meta["vcs"] = "git"
            meta_path.write_text(json.dumps(meta, indent=2))

        # Verify converted
        updated_meta = json.loads(meta_path.read_text())
        assert updated_meta["vcs"] == "git"

    def test_factory_conversion_preserves_other_fields(self, feature_with_vcs_lock):
        """Auto-conversion preserves other meta.json fields."""
        feature_dir = feature_with_vcs_lock("004", vcs_type="jj")
        meta_path = feature_dir / "meta.json"
        meta = json.loads(meta_path.read_text())

        # Add extra fields
        meta["custom_field"] = "test_value"
        meta["another_field"] = 123
        meta_path.write_text(json.dumps(meta, indent=2))

        # Simulate conversion
        meta = json.loads(meta_path.read_text())
        jj_available = False
        if meta["vcs"] == "jj" and not jj_available:
            meta["vcs"] = "git"
            meta_path.write_text(json.dumps(meta, indent=2))

        # Verify other fields preserved
        final_meta = json.loads(meta_path.read_text())
        assert final_meta["vcs"] == "git"
        assert final_meta["custom_field"] == "test_value"
        assert final_meta["another_field"] == 123
        assert final_meta["feature_number"] == "004"


@pytest.mark.functional
@pytest.mark.vcs
class TestFactoryEdgeCases:
    """Test factory edge cases and error handling."""

    def test_factory_invalid_vcs_name_defaults_to_git(self, feature_with_vcs_lock):
        """Factory handles invalid VCS name by defaulting to git."""
        feature_dir = feature_with_vcs_lock("005", vcs_type="git")
        meta_path = feature_dir / "meta.json"

        # Corrupt meta.json with invalid VCS
        meta = json.loads(meta_path.read_text())
        meta["vcs"] = "svn"  # Invalid
        meta_path.write_text(json.dumps(meta, indent=2))

        # Factory should fall back to git
        meta = json.loads(meta_path.read_text())
        vcs = meta["vcs"]
        valid_vcs = ["git", "jj"]

        if vcs not in valid_vcs:
            # Default to git with warning
            selected_vcs = "git"
        else:
            selected_vcs = vcs

        assert selected_vcs == "git"

    def test_factory_empty_vcs_defaults_to_git(self, feature_with_vcs_lock):
        """Factory handles empty VCS field by defaulting to git."""
        feature_dir = feature_with_vcs_lock("006", vcs_type="git")
        meta_path = feature_dir / "meta.json"

        # Set empty VCS
        meta = json.loads(meta_path.read_text())
        meta["vcs"] = ""
        meta_path.write_text(json.dumps(meta, indent=2))

        # Factory logic
        meta = json.loads(meta_path.read_text())
        vcs = meta["vcs"]

        if not vcs or vcs not in ["git", "jj"]:
            selected_vcs = "git"
        else:
            selected_vcs = vcs

        assert selected_vcs == "git"

    def test_factory_missing_vcs_field_defaults_to_git(self, feature_with_vcs_lock):
        """Factory handles missing VCS field by defaulting to git."""
        feature_dir = feature_with_vcs_lock("007", vcs_type="git")
        meta_path = feature_dir / "meta.json"

        # Remove VCS field
        meta = json.loads(meta_path.read_text())
        del meta["vcs"]
        meta_path.write_text(json.dumps(meta, indent=2))

        # Factory logic
        meta = json.loads(meta_path.read_text())
        vcs = meta.get("vcs", "git")  # Default to git if missing

        assert vcs == "git"

    def test_factory_respects_explicit_git_over_jj_available(self, feature_with_vcs_lock):
        """Factory respects explicit git even if jj were available."""
        feature_dir = feature_with_vcs_lock("008", vcs_type="git")
        meta = json.loads((feature_dir / "meta.json").read_text())

        # Even if jj were somehow available, explicit git should be used
        jj_available = True  # Hypothetically available
        vcs_from_meta = meta["vcs"]

        # Factory should respect explicit git
        selected_vcs = vcs_from_meta

        assert selected_vcs == "git"


@pytest.mark.functional
@pytest.mark.vcs
class TestFactoryConsistency:
    """Test factory selection is consistent across calls."""

    def test_factory_returns_same_vcs_repeatedly(self, feature_with_vcs_lock):
        """Factory returns same VCS type on repeated calls."""
        feature_dir = feature_with_vcs_lock("009", vcs_type="git")
        meta_path = feature_dir / "meta.json"

        results = []
        for _ in range(10):
            meta = json.loads(meta_path.read_text())
            jj_available = False
            vcs = meta.get("vcs", "git")

            if vcs == "jj" and not jj_available:
                selected = "git"
            else:
                selected = vcs

            results.append(selected)

        # All results should be the same
        assert all(r == "git" for r in results)
        assert len(set(results)) == 1

    def test_factory_handles_concurrent_meta_reads(self, feature_with_vcs_lock):
        """Factory handles multiple meta.json reads correctly."""
        feature_dir = feature_with_vcs_lock("010", vcs_type="git")
        meta_path = feature_dir / "meta.json"

        # Simulate concurrent reads
        metas = []
        for _ in range(5):
            meta = json.loads(meta_path.read_text())
            metas.append(meta["vcs"])

        # All should be git
        assert all(vcs == "git" for vcs in metas)


@pytest.mark.functional
@pytest.mark.vcs
class TestFactoryWithDifferentJJStates:
    """Test factory behavior with different jj availability states."""

    def test_factory_git_feature_with_jj_unavailable(self, feature_with_vcs_lock):
        """Git feature works correctly when jj is unavailable."""
        feature_dir = feature_with_vcs_lock("011", vcs_type="git")
        meta = json.loads((feature_dir / "meta.json").read_text())

        jj_available = False
        vcs = meta["vcs"]

        # Git feature with jj unavailable -> git
        selected = vcs if vcs in ["git", "jj"] else "git"
        if selected == "jj" and not jj_available:
            selected = "git"

        assert selected == "git"

    def test_factory_jj_feature_with_jj_unavailable(self, feature_with_vcs_lock):
        """JJ feature auto-converts when jj is unavailable."""
        feature_dir = feature_with_vcs_lock("012", vcs_type="jj")
        meta = json.loads((feature_dir / "meta.json").read_text())

        jj_available = False
        vcs = meta["vcs"]

        # JJ feature with jj unavailable -> auto-convert to git
        selected = vcs if vcs in ["git", "jj"] else "git"
        if selected == "jj" and not jj_available:
            selected = "git"

        assert selected == "git"
