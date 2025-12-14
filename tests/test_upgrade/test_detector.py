"""
Test Version Detector

Tests the heuristic-based version detection system that identifies
project version when metadata.yaml is missing.

Test Coverage:
1. Detection With Metadata (2 tests)
   - Read version from metadata.yaml
   - Metadata takes precedence over heuristics

2. Detection Heuristics (7 tests)
   - Detect v0.1.x from .specify/ directory
   - Detect v0.4.7 from missing gitignore
   - Detect v0.6.4 from commands/ directories
   - Detect v0.6.5+ from command-templates/
   - Detect broken mission system
   - Unknown version for ambiguous state
   - Multiple heuristics agree

3. Edge Cases (2 tests)
   - Mixed old/new structure
   - Fresh install detection

Dependencies: Used by upgrade command to know what migrations to apply
"""

from pathlib import Path

import pytest


class TestDetectionWithMetadata:
    """Test version detection when metadata.yaml exists."""

    def test_detect_from_metadata_file(self, tmp_path):
        """Test: Read version from metadata.yaml

        GIVEN: A project with valid metadata.yaml
        WHEN: Detecting version
        THEN: Should read version from metadata file
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create project with metadata
        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=None,
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )
        metadata.save(kittify_dir)

        # Detect version
        detected = VersionDetector.detect_version(tmp_path)

        assert detected == "0.6.7", \
            f"Should detect version from metadata, got {detected}"

    def test_metadata_takes_precedence(self, tmp_path):
        """Test: Metadata overrides heuristics

        GIVEN: A project with metadata AND old structure indicators
        WHEN: Detecting version
        THEN: Should use metadata version (not heuristics)
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
            from specify_cli.upgrade.metadata import ProjectMetadata
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create project with OLD structure (.specify/)
        specify_dir = tmp_path / '.specify' / 'memory'
        specify_dir.mkdir(parents=True)
        (specify_dir / 'constitution.md').write_text("# Old structure")

        # But ALSO add metadata saying it's v0.6.7
        kittify_dir = tmp_path / '.kittify'
        kittify_dir.mkdir()

        metadata = ProjectMetadata(
            version="0.6.7",
            initialized_at=None,
            python_version="3.11",
            platform="darwin",
            platform_version="Darwin 24.5.0"
        )
        metadata.save(kittify_dir)

        # Detect version
        detected = VersionDetector.detect_version(tmp_path)

        # Should use metadata, NOT heuristic
        assert detected == "0.6.7", \
            "Metadata should take precedence over heuristics"


class TestDetectionHeuristics:
    """Test version detection using structural heuristics."""

    def test_detect_v0_1_x_from_specify_dir(self, v0_1_x_project):
        """Test: .specify/ directory → v0.1.x

        GIVEN: A project with .specify/ directory (no .kittify/)
        WHEN: Detecting version
        THEN: Should identify as v0.1.x
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Verify fixture has .specify/ and not .kittify/
        assert (v0_1_x_project / '.specify').exists(), \
            "Fixture should have .specify/ directory"

        assert not (v0_1_x_project / '.kittify').exists(), \
            "Fixture should not have .kittify/ directory"

        # Detect version
        detected = VersionDetector.detect_version(v0_1_x_project)

        assert detected.startswith("0.1"), \
            f"Should detect v0.1.x, got {detected}"

    def test_detect_v0_4_7_missing_gitignore(self, v0_4_7_project):
        """Test: No agent dirs in .gitignore → v0.4.7

        GIVEN: Project with .kittify/ but incomplete .gitignore
        WHEN: Detecting version
        THEN: Should identify as v0.4.7 (needs git protection)
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Verify fixture has .kittify/ and .gitignore exists
        assert (v0_4_7_project / '.kittify').exists(), \
            "Fixture should have .kittify/ directory"

        assert (v0_4_7_project / '.gitignore').exists(), \
            "Fixture should have .gitignore"

        # Verify gitignore is incomplete (no .claude/)
        gitignore_content = (v0_4_7_project / '.gitignore').read_text()
        assert '.claude/' not in gitignore_content, \
            "Fixture .gitignore should not have agent directories"

        # Detect version
        detected = VersionDetector.detect_version(v0_4_7_project)

        # Should detect as v0.4.7 or similar (before git protection was added)
        assert detected.startswith("0.4"), \
            f"Should detect v0.4.x, got {detected}"

    def test_detect_v0_6_4_from_commands_dir(self, v0_6_4_project):
        """Test: .kittify/templates/commands/ → v0.6.4

        GIVEN: Project with template pollution (templates/commands/)
        WHEN: Detecting version
        THEN: Should identify as v0.6.4 (needs commands rename)
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Verify fixture has template pollution
        assert (v0_6_4_project / '.kittify' / 'templates' / 'commands').exists(), \
            "Fixture should have template pollution"

        # Verify has old commands/ in missions
        assert (v0_6_4_project / '.kittify' / 'missions' / 'software-dev' / 'commands').exists(), \
            "Fixture should have old commands/ directory"

        # Detect version
        detected = VersionDetector.detect_version(v0_6_4_project)

        assert detected == "0.6.4" or detected.startswith("0.6.4"), \
            f"Should detect v0.6.4, got {detected}"

    def test_detect_v0_6_5_from_command_templates(self, v0_6_6_project):
        """Test: command-templates/ → v0.6.5+

        GIVEN: Project with command-templates/ (no commands/)
        WHEN: Detecting version
        THEN: Should identify as v0.6.5+
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Verify fixture has NEW structure
        assert (v0_6_6_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates').exists(), \
            "Fixture should have command-templates/ directory"

        # Verify NO old commands/
        assert not (v0_6_6_project / '.kittify' / 'missions' / 'software-dev' / 'commands').exists(), \
            "Fixture should NOT have old commands/ directory"

        # Verify NO template pollution
        assert not (v0_6_6_project / '.kittify' / 'templates').exists(), \
            "Fixture should NOT have template pollution"

        # Detect version
        detected = VersionDetector.detect_version(v0_6_6_project)

        # Should detect as v0.6.5+
        # (v0.6.6 is missing metadata, but structurally is v0.6.5+)
        assert detected.startswith("0.6"), \
            f"Should detect v0.6.x, got {detected}"

        # More specifically, should be >= 0.6.5
        version_parts = detected.split('.')
        if len(version_parts) >= 3:
            minor = int(version_parts[1])
            patch = int(version_parts[2])
            assert minor > 6 or (minor == 6 and patch >= 5), \
                f"Should detect v0.6.5 or later, got {detected}"

    def test_detect_broken_mission_system(self, broken_mission_project):
        """Test: Dashboard shows "Unknown mission" → needs mission repair

        GIVEN: Project with corrupted mission.yaml
        WHEN: Detecting version and checking mission status
        THEN: Should detect broken mission system
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Verify fixture has corrupted mission.yaml
        mission_yaml = broken_mission_project / '.kittify' / 'missions' / 'software-dev' / 'mission.yaml'
        assert mission_yaml.exists(), \
            "Fixture should have mission.yaml"

        # Try to parse it (should fail or be invalid)
        import yaml
        try:
            with open(mission_yaml) as f:
                data = yaml.safe_load(f)
                # If parsing succeeds, data should be incomplete/invalid
                # (our fixture has syntax errors that might partially parse)
        except yaml.YAMLError:
            # Expected - file is corrupted
            pass

        # Detect if mission system is broken
        # This might involve trying to query dashboard or parsing mission files
        is_broken = VersionDetector.detect_broken_mission_system(broken_mission_project)

        assert is_broken, \
            "Should detect broken mission system from corrupted YAML"

    def test_detect_unknown_version(self, tmp_path):
        """Test: Ambiguous state returns "unknown"

        GIVEN: A project with no clear version indicators
        WHEN: Detecting version
        THEN: Should return "unknown"
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create minimal project with no clear indicators
        # Just a git repo, nothing else
        (tmp_path / '.git').mkdir()

        # Detect version
        detected = VersionDetector.detect_version(tmp_path)

        assert detected == "unknown" or detected is None, \
            f"Should return 'unknown' for ambiguous project, got {detected}"

    def test_multiple_heuristics_agree(self, v0_6_4_project):
        """Test: Consistent signals give confident version

        GIVEN: Project with multiple consistent version indicators
        WHEN: Detecting version
        THEN: All heuristics should agree on same version
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # v0.6.4 project has:
        # - .kittify/ directory (v0.2.0+)
        # - templates/commands/ (v0.6.4 bug)
        # - missions/*/commands/ (pre-v0.6.5)
        # - Complete .gitignore (v0.4.8+)
        # - Pre-commit hook (v0.5.0+)

        # All these together should clearly indicate v0.6.4
        detected = VersionDetector.detect_version(v0_6_4_project)

        assert detected == "0.6.4" or detected.startswith("0.6.4"), \
            f"Multiple heuristics should converge on v0.6.4, got {detected}"

        # If detector provides confidence score, it should be high
        if hasattr(VersionDetector, 'detect_version_with_confidence'):
            version, confidence = VersionDetector.detect_version_with_confidence(v0_6_4_project)
            assert confidence > 0.8, \
                f"Confidence should be high with multiple agreeing signals, got {confidence}"


class TestDetectionEdgeCases:
    """Test edge cases in version detection."""

    def test_detect_mixed_old_new_structure(self, tmp_path, create_conflicting_state):
        """Test: Both commands/ and command-templates/ exist

        GIVEN: Project with BOTH old and new command directories
        WHEN: Detecting version
        THEN: Should detect conflict and suggest manual cleanup
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create project with conflicting state
        create_conflicting_state(tmp_path, ['both_commands_and_templates'])

        # Detect version
        detected = VersionDetector.detect_version(tmp_path)

        # Should detect as needing migration (or as conflict)
        # Exact behavior depends on implementation choice
        # At minimum, should not crash
        assert detected is not None, \
            "Should handle mixed structure without crashing"

        # If detector can report conflicts
        if hasattr(VersionDetector, 'detect_conflicts'):
            conflicts = VersionDetector.detect_conflicts(tmp_path)
            assert 'commands_and_templates' in conflicts or 'mixed_structure' in conflicts, \
                "Should detect structural conflict"

    def test_detect_fresh_install(self, tmp_path, spec_kitty_repo_root):
        """Test: Current version with all features

        GIVEN: A freshly initialized project (current version)
        WHEN: Detecting version
        THEN: Should detect as current version (no upgrades needed)
        """
        try:
            from specify_cli.upgrade.detector import VersionDetector
        except ImportError:
            pytest.skip("VersionDetector not yet implemented")

        # Create fresh project structure (simulate spec-kitty init)
        kittify_dir = tmp_path / '.kittify'
        missions_dir = kittify_dir / 'missions' / 'software-dev' / 'command-templates'
        missions_dir.mkdir(parents=True)

        memory_dir = kittify_dir / 'memory'
        memory_dir.mkdir()

        # Add complete .gitignore
        gitignore = tmp_path / '.gitignore'
        gitignore.write_text("""
.claude/
.codex/
.gemini/
.cursor/
.qwen/
.opencode/
.windsurf/
.kilocode/
.augment/
.roo/
.amazonq/
.github/copilot/
""")

        # Add .claudeignore
        claudeignore = tmp_path / '.claudeignore'
        claudeignore.write_text(".kittify/templates/\n")

        # Detect version
        detected = VersionDetector.detect_version(tmp_path)

        # Should detect as current version (likely v0.6.6+ or v0.6.7)
        assert detected.startswith("0.6"), \
            f"Fresh install should be detected as current version, got {detected}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
