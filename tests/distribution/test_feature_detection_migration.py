"""
Migration Validation Tests for Feature Detection Refactor

These tests ensure all 10 old implementations are properly replaced
with the centralized feature_detection module.

**What This Tests:**
1. No orphaned implementations remain
2. No "highest numbered" heuristic logic exists
3. All imports use centralized module
4. Backward compatibility maintained
5. Error messages updated consistently

**Critical Validation:**
This test suite answers: "Did we actually replace ALL the old code,
or did we miss some that will cause bugs later?"

Run: pytest tests/distribution/test_feature_detection_migration.py -xvs
"""

import subprocess
from pathlib import Path
import pytest
import re

pytestmark = [
    pytest.mark.distribution,
    pytest.mark.adversarial,
    pytest.mark.regression,
]


class TestNoOrphanedImplementations:
    """
    Verify all 10 old implementations are removed or replaced.

    CRITICAL: If any old implementation remains, it could still use
    the "highest numbered" heuristic and cause bugs.
    """

    def test_no_find_feature_slug_implementations(self, spec_kitty_repo_root):
        """
        find_feature_slug() should only exist in centralized module.

        Old implementations that should be DELETED:
        - core/paths.py::find_feature_slug()
        - agent/workflow.py::_find_feature_slug()
        - agent/tasks.py::_find_feature_slug() (duplicate)
        """
        # Search for function definitions (not imports)
        result = subprocess.run(
            ["grep", "-r", "-n", "^def.*find_feature_slug\\|^def _find_feature_slug",
             str(spec_kitty_repo_root / "src" / "specify_cli")],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')
            # Should only find it in centralized feature_detection.py
            allowed_locations = ["core/feature_detection.py"]

            orphaned = []
            for line in findings:
                if not any(loc in line for loc in allowed_locations):
                    orphaned.append(line)

            if orphaned:
                pytest.fail(
                    f"Found orphaned find_feature_slug implementations:\n" +
                    "\n".join(orphaned) +
                    "\n\nThese should be deleted and replaced with imports from core.feature_detection"
                )

    def test_no_detect_feature_slug_duplicates(self, spec_kitty_repo_root):
        """
        detect_feature_slug() should only exist in centralized module.

        Old implementations that should be DELETED:
        - acceptance.py::detect_feature_slug() (keep but refactor)
        - scripts/tasks/acceptance_support.py::detect_feature_slug() (DELETE duplicate)
        """
        result = subprocess.run(
            ["grep", "-r", "-n", "^def detect_feature_slug",
             str(spec_kitty_repo_root / "src" / "specify_cli")],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')
            # Should only be in feature_detection.py and acceptance.py (which imports it)
            allowed_files = [
                "core/feature_detection.py",
                "acceptance.py"  # Allowed to keep as wrapper
            ]

            orphaned = []
            for line in findings:
                if not any(allowed in line for allowed in allowed_files):
                    orphaned.append(line)

            if orphaned:
                pytest.fail(
                    f"Found duplicate detect_feature_slug implementations:\n" +
                    "\n".join(orphaned) +
                    "\n\nThese should be deleted (scripts/tasks/acceptance_support.py)"
                )

    def test_no_detect_current_feature_orphans(self, spec_kitty_repo_root):
        """
        detect_current_feature() should be replaced.

        Old implementations:
        - mission.py::_detect_current_feature()
        - orchestrate.py::detect_current_feature()
        """
        result = subprocess.run(
            ["grep", "-r", "-n", "^def.*detect_current_feature\\|^def _detect_current_feature",
             str(spec_kitty_repo_root / "src" / "specify_cli")],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')
            # Should only be in feature_detection.py (or maybe as wrapper)
            allowed = ["core/feature_detection.py"]

            orphaned = []
            for line in findings:
                if not any(loc in line for loc in allowed):
                    orphaned.append(line)

            if orphaned:
                pytest.fail(
                    f"Found orphaned detect_current_feature implementations:\n" +
                    "\n".join(orphaned) +
                    "\n\nThese should be replaced with detect_feature() from centralized module"
                )

    def test_no_find_feature_directory_duplicates(self, spec_kitty_repo_root):
        """
        _find_feature_directory() should only exist in centralized module.

        Old implementations (same name, different code!):
        - agent/context.py::_find_feature_directory()
        - agent/feature.py::_find_feature_directory()
        """
        result = subprocess.run(
            ["grep", "-r", "-n", "^def _find_feature_directory",
             str(spec_kitty_repo_root / "src" / "specify_cli")],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')
            # Should only be in feature_detection.py
            allowed = ["core/feature_detection.py"]

            duplicates = []
            for line in findings:
                if not any(loc in line for loc in allowed):
                    duplicates.append(line)

            if duplicates:
                pytest.fail(
                    f"Found duplicate _find_feature_directory implementations:\n" +
                    "\n".join(duplicates) +
                    "\n\nThese should be replaced with detect_feature_directory()"
                )


class TestNoHighestNumberedHeuristic:
    """
    Verify NO code still uses "highest numbered" fallback logic.

    This is the root cause of the bug - must be completely removed.
    """

    def test_no_max_feature_number_logic(self, spec_kitty_repo_root):
        """
        No code should select feature by maximum number.

        Search for patterns like:
        - max(feature_numbers)
        - sorted(features)[-1]
        - highest_feature
        - latest_feature
        """
        # Search for suspicious patterns
        patterns = [
            r"max.*feature",
            r"sorted.*feature.*\[-1\]",
            r"highest.*feature",
            r"latest.*feature",
        ]

        findings = []
        for pattern in patterns:
            result = subprocess.run(
                ["grep", "-r", "-i", "-n", pattern,
                 str(spec_kitty_repo_root / "src" / "specify_cli"),
                 "--include=*.py"],
                capture_output=True,
                text=True
            )

            if result.stdout:
                # Filter out comments and docstrings
                for line in result.stdout.strip().split('\n'):
                    # Skip if it's in a comment or docstring
                    if not ('#' in line or '"""' in line or "'''" in line):
                        findings.append(f"{pattern}: {line}")

        if findings:
            # Some findings might be legitimate (e.g., test code, docs)
            # But we should review them
            pytest.fail(
                f"Found potential 'highest numbered' heuristic logic:\n" +
                "\n".join(findings[:10]) +  # Limit output
                "\n\nVerify these are NOT using non-deterministic selection"
            )

    def test_no_numeric_sort_selection(self, spec_kitty_repo_root):
        """
        No code should sort features numerically and pick one.

        This was the pattern in core/paths.py that caused the bug.
        """
        # Look for feature number extraction + sorting
        result = subprocess.run(
            ["grep", "-r", "-n", "int.*feature.*split\\|feature.*int.*split",
             str(spec_kitty_repo_root / "src" / "specify_cli"),
             "--include=*.py"],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')

            # Filter out test files and feature_detection.py itself
            suspicious = []
            for line in findings:
                if "test_" not in line and "feature_detection.py" not in line:
                    suspicious.append(line)

            if suspicious:
                pytest.fail(
                    f"Found numeric feature sorting (potential bug):\n" +
                    "\n".join(suspicious) +
                    "\n\nVerify this is not selecting 'highest numbered' feature"
                )


class TestCentralizedImports:
    """
    Verify all code imports from centralized module.

    No module should implement its own detection logic.
    """

    def test_all_imports_from_feature_detection(self, spec_kitty_repo_root):
        """
        All modules should import from core.feature_detection.

        Expected imports:
        - from specify_cli.core.feature_detection import detect_feature
        - from specify_cli.core.feature_detection import detect_feature_slug
        - from specify_cli.core.feature_detection import detect_feature_directory
        """
        # Check that imports exist
        result = subprocess.run(
            ["grep", "-r", "-n", "from.*feature_detection import",
             str(spec_kitty_repo_root / "src" / "specify_cli"),
             "--include=*.py"],
            capture_output=True,
            text=True
        )

        if not result.stdout:
            pytest.fail(
                "No imports from feature_detection found!\n"
                "Migration may not be complete - modules should import from centralized module"
            )

        # Verify imports are correct
        imports = result.stdout.strip().split('\n')
        expected_functions = ["detect_feature", "detect_feature_slug", "detect_feature_directory"]

        found_functions = set()
        for line in imports:
            for func in expected_functions:
                if func in line:
                    found_functions.add(func)

        if not found_functions:
            pytest.fail(
                f"Imports from feature_detection found, but none of the expected functions:\n" +
                "\n".join(imports) +
                f"\n\nExpected: {', '.join(expected_functions)}"
            )

    def test_no_local_feature_detection(self, spec_kitty_repo_root):
        """
        No module should have local helper functions for detection.

        Pattern to avoid: def _local_detect_feature()
        """
        result = subprocess.run(
            ["grep", "-r", "-n", "^def _.*detect.*feature\\|^def _.*find.*feature",
             str(spec_kitty_repo_root / "src" / "specify_cli"),
             "--include=*.py"],
            capture_output=True,
            text=True
        )

        if result.stdout:
            findings = result.stdout.strip().split('\n')

            # Filter allowed locations
            allowed = ["core/feature_detection.py"]
            local_helpers = []

            for line in findings:
                if not any(loc in line for loc in allowed):
                    local_helpers.append(line)

            if local_helpers:
                pytest.fail(
                    f"Found local feature detection helper functions:\n" +
                    "\n".join(local_helpers) +
                    "\n\nThese should be deleted - use centralized module instead"
                )


class TestBackwardCompatibility:
    """
    Ensure existing workflows still work after migration.
    """

    def test_implement_command_still_works(self, tmp_path, spec_kitty_repo_root):
        """
        spec-kitty implement command should still work.

        This is a critical command that users rely on.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True)

        # Create single feature
        feature_dir = repo / "kitty-specs" / "020-test-feature"
        feature_dir.mkdir(parents=True)

        import json
        meta = {"feature_id": "020-test-feature", "title": "Test", "mission": "software-dev"}
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        wp_content = """---
work_package_id: WP01
title: Test WP
lane: planned
dependencies: []
---

# WP01
"""
        (tasks_dir / "WP01-test.md").write_text(wp_content)

        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo, capture_output=True)

        # Test: implement command should still work
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01", "--feature", "020-test-feature"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # Should work (or fail gracefully with clear error)
        if result.returncode != 0:
            assert "020-test-feature" in result.stderr or "WP01" in result.stderr, \
                f"Error should reference correct feature: {result.stderr}"

    def test_agent_commands_have_feature_flag(self, tmp_path, spec_kitty_repo_root):
        """
        Agent commands should accept --feature flag.

        Critical for the fix - agents need to specify feature explicitly.
        """
        # Test that --feature flag is recognized (not "unrecognized option")
        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "setup-plan", "--help"],
            capture_output=True,
            text=True
        )

        help_output = result.stdout.lower()

        # Should mention --feature in help
        assert "--feature" in help_output, \
            "agent feature setup-plan should have --feature flag in help"

        # Test workflow commands
        result = subprocess.run(
            ["spec-kitty", "agent", "workflow", "--help"],
            capture_output=True,
            text=True
        )

        # Workflow commands should support feature detection
        assert result.returncode == 0, "Workflow commands should have help"


class TestErrorMessageQuality:
    """
    Verify error messages are improved and consistent.
    """

    def test_ambiguous_errors_mention_feature_flag(self, spec_kitty_repo_root):
        """
        Errors about ambiguous feature should suggest --feature flag.

        This is critical UX - guide users to the solution.
        """
        # Check error message templates in centralized module
        feature_detection_file = spec_kitty_repo_root / "src" / "specify_cli" / "core" / "feature_detection.py"

        if not feature_detection_file.exists():
            pytest.skip("feature_detection.py not yet created")

        content = feature_detection_file.read_text()

        # Should have error messages that mention --feature
        assert "--feature" in content.lower(), \
            "feature_detection.py should mention --feature flag in error messages"

        # Should have helpful error classes
        assert "FeatureDetectionError" in content or "MultipleFeaturesError" in content, \
            "Should define custom error classes for clear error handling"

    def test_error_messages_list_available_features(self, spec_kitty_repo_root):
        """
        When multiple features exist, error should list them.

        Example: "Found features: 020-feature-a, 021-feature-b"
        """
        feature_detection_file = spec_kitty_repo_root / "src" / "specify_cli" / "core" / "feature_detection.py"

        if not feature_detection_file.exists():
            pytest.skip("feature_detection.py not yet created")

        content = feature_detection_file.read_text()

        # Should enumerate available features in error
        has_listing = any(pattern in content for pattern in [
            "available.*feature",
            "found.*feature",
            "list.*feature",
            "features.*:",
        ])

        assert has_listing, \
            "Error messages should list available features to help users"
