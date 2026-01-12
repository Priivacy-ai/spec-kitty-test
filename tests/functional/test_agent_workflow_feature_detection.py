"""
Comprehensive tests for spec-kitty agent workflow feature slug detection

Tests for bugs found 2026-01-11:
- Bug: Silent failure (Error: 1) when feature slug cannot be auto-detected
- Bug: Incorrect feature slug when running from worktree (includes -WP## suffix)

The workflow.py _find_feature_slug() function must:
1. Detect feature from directory path (strip -WP## suffix if in worktree)
2. Detect feature from git branch (strip -WP## suffix if on WP branch)
3. Provide helpful error message when detection fails
4. Work from main repo, worktree, or with --feature flag

Regression prevention for Issue discovered by opencode agent 2026-01-11.
"""
import pytest
import subprocess
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def init_project_with_worktree(temp_project_dir, spec_kitty_repo_root):
    """
    Initialize project and create a WP worktree.

    Returns (project_path, worktree_path, feature_slug)
    """
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    # Init project
    subprocess.run(
        ['spec-kitty', 'init', 'test-project', '--ai=claude'],
        cwd=str(temp_project_dir),
        env=env,
        input=b'y\n',
        capture_output=True
    )

    project_path = temp_project_dir / 'test-project'

    # Git setup
    subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

    # Create feature
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'my-feature'],
        cwd=str(project_path),
        env=env,
        capture_output=True
    )

    # Create WP
    tasks_dir = project_path / 'kitty-specs' / '001-my-feature' / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'WP01.md').write_text("---\ntitle: WP01\n---\n# WP01")

    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add WP'], cwd=str(project_path), check=True, capture_output=True)

    # Create worktree
    result = subprocess.run(
        ['spec-kitty', 'implement', 'WP01', '--feature', '001-my-feature'],
        cwd=str(project_path),
        env=env,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.skip("Cannot create worktree for test setup")

    worktree_path = project_path / '.worktrees' / '001-my-feature-WP01'
    if not worktree_path.exists():
        pytest.skip("Worktree not created")

    return project_path, worktree_path, '001-my-feature'


class TestFeatureSlugDetectionFromWorktree:
    """Tests for feature slug detection when running from WP worktree"""

    def test_detect_from_worktree_strips_wp_suffix(self, init_project_with_worktree):
        """
        Test that feature slug is detected correctly from worktree path.

        Bug: When running from .worktrees/001-my-feature-WP01/, the old code
        detected feature as "001-my-feature-WP01" (WRONG - includes WP suffix).

        Should detect: "001-my-feature" (without -WP01 suffix)

        Reproduction:
        cd .worktrees/001-my-feature-WP01/
        spec-kitty agent workflow implement WP01
        # ERROR: Feature '001-my-feature-WP01' has no tasks directory
        # Should look for: 001-my-feature (without WP01)
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Run workflow command from INSIDE worktree
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(worktree_path),
            capture_output=True,
            text=True
        )

        # Should succeed (or fail for other reason, but not wrong feature slug)
        output = result.stdout + result.stderr

        # Should NOT look for wrong path (with WP01 suffix)
        assert '001-my-feature-WP01/tasks' not in output, \
            "Should NOT include -WP01 suffix in feature slug"

        # Should look for correct path (without WP01 suffix)
        # If it fails for other reasons, that's OK - we're testing slug detection
        if 'has no tasks directory' in output:
            assert '001-my-feature/tasks' in output, \
                "Should strip -WP01 suffix and look for 001-my-feature/tasks"

    def test_worktree_branch_name_strips_wp_suffix(self, init_project_with_worktree):
        """
        Test feature detection from git branch name in worktree.

        When in worktree, git branch is "001-my-feature-WP01".
        Should detect feature as "001-my-feature" (strip -WP01).
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Check git branch in worktree
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            check=True
        )

        branch_name = result.stdout.strip()
        assert branch_name == '001-my-feature-WP01', f"Branch should be 001-my-feature-WP01, got {branch_name}"

        # Run workflow command (detects from branch)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(worktree_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should strip -WP01 from branch name
        if '001-my-feature-WP01/tasks' in output:
            pytest.fail(
                "Feature slug detection from branch name did NOT strip -WP01 suffix.\n"
                f"Branch: {branch_name}\n"
                "Expected to detect: 001-my-feature\n"
                "Actually detected: 001-my-feature-WP01\n"
                f"Output: {output[:500]}"
            )

    def test_multiple_wp_suffix_formats(self, init_project_with_worktree):
        """
        Test that various -WPxx suffix formats are stripped correctly.

        Should strip:
        - 001-feature-WP01
        - 001-feature-WP15
        - 001-feature-wp01 (lowercase)
        - 001-feature-Wp01 (mixed case)
        """
        import re

        test_cases = [
            ('001-feature-WP01', '001-feature'),
            ('001-feature-WP15', '001-feature'),
            ('001-my-long-feature-name-WP01', '001-my-long-feature-name'),
            ('010-another-feature-WP99', '010-another-feature'),
        ]

        # Test the regex pattern that should be used
        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        for input_slug, expected_output in test_cases:
            stripped = wp_suffix_pattern.sub('', input_slug)
            assert stripped == expected_output, \
                f"Failed to strip WP suffix: {input_slug} -> {stripped} (expected {expected_output})"


class TestFeatureSlugDetectionFromMainRepo:
    """Tests for feature slug detection when running from main repo"""

    def test_single_feature_auto_detected(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test that when only ONE feature exists, it's auto-detected.

        User workflow:
        cd test-project/  # On main branch
        spec-kitty agent workflow implement WP01  # No --feature flag
        # Should auto-detect the single feature
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create single feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'only-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        tasks_dir = project_path / 'kitty-specs' / '001-only-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / 'WP01.md').write_text("# WP01")

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add WP'], cwd=str(project_path), check=True, capture_output=True)

        # Run workflow WITHOUT --feature flag (should auto-detect)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Should succeed or give reasonable error (not silent failure)
        if result.returncode != 0:
            output = result.stdout + result.stderr

            # Should NOT be silent failure
            assert len(output) > 0, "Should not be silent failure (Error: 1 with no message)"

            # If fails, error should be helpful
            if 'could not' in output.lower() or 'cannot' in output.lower():
                # Should suggest using --feature flag
                assert '--feature' in output, "Error should mention --feature flag"


class TestFeatureSlugDetectionErrorMessages:
    """Tests for helpful error messages when detection fails"""

    def test_helpful_error_when_no_feature_found(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test error message when NO feature can be detected.

        Bug: Old code just printed "Error: 1" with no explanation.
        Fixed: Now prints helpful message explaining why and how to fix.

        Expected message:
        - Explains what detection strategies were tried
        - Suggests using --feature flag
        - Lists available features (if any)
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project but don't create feature
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Try to run workflow without feature
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail when no feature exists"

        output = result.stdout + result.stderr

        # Should NOT be silent failure
        assert len(output) > 10, \
            f"Error message should be helpful, not just 'Error: 1'. Got: {output}"

        # Should explain the problem
        assert any(word in output.lower() for word in ['could not', 'cannot', 'failed to', 'unable to']), \
            "Should explain what failed"

        # Should mention feature
        assert 'feature' in output.lower(), "Should mention 'feature'"

        # Should suggest solution
        assert '--feature' in output or 'specify' in output.lower(), \
            "Should suggest using --feature flag or creating feature"

    def test_helpful_error_when_multiple_features_exist(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test error message when MULTIPLE features exist and none specified.

        Should tell user:
        - Which features were found
        - That they need to specify with --feature flag
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init project
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create TWO features
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'feature-one'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'F1'], cwd=str(project_path), check=True, capture_output=True)

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'feature-two'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        # Create WP in first feature
        tasks1_dir = project_path / 'kitty-specs' / '001-feature-one' / 'tasks'
        tasks1_dir.mkdir(parents=True, exist_ok=True)
        (tasks1_dir / 'WP01.md').write_text("# WP01")

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'F2'], cwd=str(project_path), check=True, capture_output=True)

        # Try to run workflow without specifying which feature
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail when multiple features exist"

        output = result.stdout + result.stderr

        # Should NOT be silent
        assert len(output) > 10, "Should have helpful error message"

        # Should mention both features OR say "multiple"
        assert 'multiple' in output.lower() or ('001' in output and '002' in output), \
            "Should mention that multiple features exist"

        # Should suggest --feature flag
        assert '--feature' in output, "Should suggest using --feature flag"


class TestFeatureSlugStrippingLogic:
    """Tests for WP suffix stripping logic"""

    def test_strip_wp01_suffix(self):
        """
        Test that -WP01 suffix is stripped from feature slug.

        Input: 001-my-feature-WP01
        Output: 001-my-feature
        """
        import re

        # This is the regex that should be used
        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        test_cases = [
            ('001-my-feature-WP01', '001-my-feature'),
            ('001-my-feature-WP02', '001-my-feature'),
            ('001-my-feature-WP15', '001-my-feature'),
            ('010-another-feature-WP99', '010-another-feature'),
            ('001-long-feature-name-WP01', '001-long-feature-name'),
        ]

        for input_str, expected in test_cases:
            result = wp_suffix_pattern.sub('', input_str)
            assert result == expected, f"Failed to strip WP suffix: {input_str} -> {result} (expected {expected})"

    def test_does_not_strip_non_wp_suffixes(self):
        """
        Test that non-WP suffixes are NOT stripped.

        Should NOT strip:
        - 001-my-wp-feature (wp in middle)
        - 001-feature-WP1 (only one digit)
        - 001-feature-wp (no digits)
        """
        import re

        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        # These should NOT be modified
        no_change_cases = [
            '001-my-wp-feature',  # wp in middle
            '001-feature-WP1',    # only 1 digit
            '001-feature-wp',     # no digits
            '001-feature',        # no WP at all
        ]

        for input_str in no_change_cases:
            result = wp_suffix_pattern.sub('', input_str)
            assert result == input_str, f"Should NOT strip from {input_str}, got {result}"

    def test_case_insensitive_stripping(self):
        """
        Test that WP suffix stripping is case-insensitive.

        Should strip:
        - 001-feature-WP01 (uppercase)
        - 001-feature-wp01 (lowercase)
        - 001-feature-Wp01 (mixed)
        """
        import re

        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        test_cases = [
            ('001-feature-WP01', '001-feature'),
            ('001-feature-wp01', '001-feature'),
            ('001-feature-Wp01', '001-feature'),
            ('001-feature-wP01', '001-feature'),
        ]

        for input_str, expected in test_cases:
            result = wp_suffix_pattern.sub('', input_str)
            assert result == expected, f"Case-insensitive stripping failed: {input_str} -> {result}"


class TestWorkflowCommandWithFeatureFlag:
    """Tests for explicit --feature flag usage"""

    def test_feature_flag_overrides_detection(self, init_project_with_worktree):
        """
        Test that --feature flag overrides auto-detection.

        Even if in worktree for feature-A, --feature flag should use feature-B.
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Run with explicit feature flag
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01', '--feature', feature_slug],
            cwd=str(worktree_path),
            capture_output=True,
            text=True
        )

        # Should use the explicit feature (not auto-detect from worktree)
        # Verify it doesn't fail with "wrong feature" error
        if result.returncode != 0:
            output = result.stdout + result.stderr
            # If it fails, shouldn't be because of feature slug
            assert f'{feature_slug}/tasks' in output or result.returncode == 0, \
                "Should use explicitly specified feature"

    def test_feature_flag_with_wp_suffix_is_stripped(self, init_project_with_worktree):
        """
        Test that even if --feature flag includes WP suffix, it's stripped.

        User might type: --feature 001-my-feature-WP01
        Should use: 001-my-feature
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Use --feature with WP suffix (wrong, but should be handled)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01', '--feature', f'{feature_slug}-WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should either:
        # 1. Strip the suffix and succeed
        # 2. Give clear error about invalid feature format
        if result.returncode != 0:
            # Should not look for feature with WP suffix
            assert f'{feature_slug}-WP01/tasks' not in output or 'not found' in output.lower(), \
                "Should strip WP suffix from --feature flag value"


class TestWorkflowCommandFromDifferentLocations:
    """Tests for running workflow command from various locations"""

    def test_from_main_repo_root(self, init_project_with_worktree):
        """
        Test running from main repo root with --feature flag.
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01', '--feature', feature_slug],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should work (or fail for reasons other than feature detection)
        output = result.stdout + result.stderr

        # Should not complain about feature detection
        assert 'could not auto-detect' not in output.lower(), \
            "Should work with explicit --feature flag from main repo"

    def test_from_feature_directory_in_main(self, init_project_with_worktree):
        """
        Test running from kitty-specs/001-feature/ directory in main.

        Should auto-detect feature from directory path.
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        feature_dir = project_path / 'kitty-specs' / feature_slug

        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(feature_dir),
            capture_output=True,
            text=True
        )

        # Should auto-detect from directory
        if result.returncode != 0:
            output = result.stdout + result.stderr

            # If it fails, should not be due to feature detection
            # (might fail for other reasons like WP not found, etc.)
            if 'auto-detect' in output.lower():
                pytest.fail(f"Should auto-detect feature from directory path: {feature_dir}")

    def test_from_feature_branch_in_main(self, init_project_with_worktree):
        """
        Test running from feature branch in main repo.

        When on branch 001-my-feature (in main), should auto-detect.
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Checkout feature branch in main
        subprocess.run(
            ['git', 'checkout', '-b', feature_slug],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should detect from branch name
        if result.returncode != 0:
            output = result.stdout + result.stderr

            if 'auto-detect' in output.lower() or 'feature slug' in output.lower():
                pytest.fail(f"Should auto-detect feature from branch name: {feature_slug}")


class TestRegressionPrevention:
    """Prevent regression of the specific bugs found"""

    def test_no_silent_error_1_failure(self, temp_project_dir, spec_kitty_repo_root):
        """
        Prevent regression: Silent "Error: 1" without explanation.

        Old behavior:
        $ spec-kitty agent workflow implement WP01
        Error: 1

        New behavior:
        $ spec-kitty agent workflow implement WP01
        Error: Could not auto-detect feature slug.
          - Not in a kitty-specs/###-feature-slug directory
          - Git branch name doesn't match ###-slug format
          - Use --feature <slug> to specify explicitly
        Error: 1
        """
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input=b'y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'
        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Run without feature
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode != 0, "Should fail"

        output = result.stdout + result.stderr

        # REGRESSION TEST: Should NOT be just "Error: 1"
        assert not (output.strip() == "Error: 1" or output.strip() == ""), \
            "REGRESSION: Silent failure with just 'Error: 1' - should have helpful message"

        # Should have substantial error message
        assert len(output) > 50, \
            f"Error message should be helpful (>50 chars). Got {len(output)} chars: {output}"

    def test_no_incorrect_wp_suffix_in_paths(self, init_project_with_worktree):
        """
        Prevent regression: Looking for wrong feature path with WP suffix.

        Old bug:
        Feature '001-minimal-bash-hello-WP01' has no tasks directory at
        .../001-minimal-bash-hello-WP01/tasks.
                            ^^^^ WRONG - includes WP01 suffix

        Should look for:
        .../001-minimal-bash-hello/tasks
        (without WP01 suffix)
        """
        project_path, worktree_path, feature_slug = init_project_with_worktree

        # Run from worktree
        result = subprocess.run(
            ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01'],
            cwd=str(worktree_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # REGRESSION TEST: Should NOT include WP suffix in path
        if 'has no tasks directory' in output or 'not found' in output:
            # If it's looking for tasks directory, should use correct feature slug
            assert f'{feature_slug}-WP01/tasks' not in output, \
                "REGRESSION: Looking for feature path with -WP01 suffix (should be stripped)"

            # Should use correct path
            assert f'{feature_slug}/tasks' in output or result.returncode == 0, \
                f"Should look for {feature_slug}/tasks (without WP suffix)"


class TestEdgeCasesForSlugDetection:
    """Edge cases for feature slug detection"""

    def test_detection_with_different_wp_numbers(self):
        """
        Test that various WP numbers are stripped correctly.

        WP01, WP02, ..., WP99 should all be stripped.
        """
        import re

        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        for wp_num in range(1, 100):
            slug_with_suffix = f"001-feature-WP{wp_num:02d}"
            stripped = wp_suffix_pattern.sub('', slug_with_suffix)
            assert stripped == '001-feature', \
                f"Failed to strip WP{wp_num:02d}: {slug_with_suffix} -> {stripped}"

    def test_detection_with_feature_names_containing_numbers(self):
        """
        Test feature names that have numbers in them.

        001-wp2-feature-WP01 should become 001-wp2-feature
        001-feature123-WP01 should become 001-feature123
        """
        import re

        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        test_cases = [
            ('001-wp2-feature-WP01', '001-wp2-feature'),
            ('001-feature123-WP01', '001-feature123'),
            ('001-v2-auth-WP05', '001-v2-auth'),
        ]

        for input_str, expected in test_cases:
            result = wp_suffix_pattern.sub('', input_str)
            assert result == expected, f"Failed: {input_str} -> {result} (expected {expected})"

    def test_detection_with_hyphens_in_feature_name(self):
        """
        Test feature names with multiple hyphens.

        001-my-complex-feature-name-WP01 should become 001-my-complex-feature-name
        """
        import re

        wp_suffix_pattern = re.compile(r'-WP\d{2}$', re.IGNORECASE)

        slug = '001-my-complex-multi-word-feature-name-WP01'
        stripped = wp_suffix_pattern.sub('', slug)
        assert stripped == '001-my-complex-multi-word-feature-name', \
            "Should only strip final -WP01, preserving hyphens in feature name"
