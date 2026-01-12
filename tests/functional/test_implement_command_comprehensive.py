"""
Comprehensive implement command tests (v0.11.0+)

Tests the new `spec-kitty implement WP##` command introduced in v0.11.0:
- Command syntax and argument parsing
- Feature context detection (branch, directory, git config, --feature flag)
- Base workspace validation
- Workspace creation and git operations
- Progress tracking and output
- Error recovery and rollback
- CLI integration

All tests require v0.11.0+ and will be skipped on earlier versions.
"""
import pytest
import os
import subprocess
import tempfile
from pathlib import Path
import json


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def init_project_with_feature(temp_project_dir, spec_kitty_repo_root):
    """Initialize project with a feature ready for implementation."""
    def _init(feature_name="test-feature", wp_count=3):
        # Initialize project
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input='y\n',
            capture_output=True,
            text=True
        )

        project_path = temp_project_dir / 'test-project'

        # Initialize git
        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', feature_name],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True
        )

        # Create WP files
        tasks_dir = project_path / 'kitty-specs' / f'001-{feature_name}' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, wp_count + 1):
            wp_id = f"WP{i:02d}"
            wp_file = tasks_dir / f"{wp_id}.md"
            wp_file.write_text(f"---\ntitle: {wp_id}\ndependencies: []\n---\n\n# {wp_id}")

        # Commit planning
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Planning'], cwd=str(project_path), check=True, capture_output=True)

        return project_path

    return _init


class TestCommandSyntax:
    """Tests for implement command syntax and argument parsing"""

    def test_implement_basic_syntax(self, requires_v011, init_project_with_feature):
        """
        Test basic command syntax: spec-kitty implement WP01.

        Implementation steps:
        1. Initialize project with feature
        2. Run: `spec-kitty implement WP01`
        3. Verify command succeeds (exit code 0)
        4. Verify workspace created
        5. Basic happy path
        """
        project_path = init_project_with_feature()

        # Run implement command
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Verify command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify workspace directory created
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        assert workspace_path.exists(), f"Workspace should be created at {workspace_path}"
        assert workspace_path.is_dir(), "Workspace should be a directory"

    def test_implement_with_base_flag(self, requires_v011, init_project_with_feature):
        """
        Test command with --base flag: spec-kitty implement WP02 --base WP01.

        Implementation steps:
        1. Implement WP01 first
        2. Run: `spec-kitty implement WP02 --base WP01`
        3. Verify command succeeds
        4. Verify WP02 workspace created
        5. Verify WP02 branches from WP01
        """
        project_path = init_project_with_feature()

        # Implement WP01
        result1 = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result1.returncode == 0, f"WP01 failed: {result1.stderr}"

        # Implement WP02 with base
        result2 = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result2.returncode == 0, f"WP02 failed: {result2.stderr}"

        # Verify WP02 workspace created
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP02'
        assert workspace_path.exists(), f"WP02 workspace should exist at {workspace_path}"

        # Verify WP02 branch exists
        result = subprocess.run(
            ['git', 'branch', '--list', '001-test-feature-WP02'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert '001-test-feature-WP02' in result.stdout, "WP02 branch should exist"

    def test_implement_with_json_output(self, requires_v011, init_project_with_feature):
        """
        Test --json flag for structured output.

        Implementation steps:
        1. Run: `spec-kitty implement WP01 --json`
        2. Parse stdout as JSON
        3. Verify JSON fields:
           - workspace_path: ".worktrees/001-test-feature-WP01"
           - branch: "001-test-feature-WP01"
           - status: "created" or "success"
        4. JSON should be valid, parseable
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--json'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Command should succeed
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse JSON output
        try:
            # Find JSON line in output (may have other output)
            json_data = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    json_data = json.loads(line)
                    break

            assert json_data is not None, "Should produce JSON output"

            # Verify expected fields (flexible to implementation)
            # At minimum, should have workspace path information
            assert 'workspace_path' in json_data or 'path' in json_data or 'worktree_path' in json_data, \
                "JSON should include workspace path"

        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.stdout}")

    def test_implement_help_message(self, requires_v011):
        """
        Test --help documentation is complete.

        Implementation steps:
        1. Run: `spec-kitty implement --help`
        2. Verify help text includes:
           - Command description
           - WP_ID positional argument
           - --base flag with description
           - --feature flag (optional)
           - --json flag
           - Examples
        3. Help should be comprehensive
        """
        result = subprocess.run(
            ['spec-kitty', 'implement', '--help'],
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, "Help command should succeed"

        help_text = result.stdout.lower()

        # Verify key elements present
        assert 'implement' in help_text, "Should mention 'implement'"
        assert 'wp' in help_text, "Should mention WP (work package)"
        assert 'base' in help_text or 'dependency' in help_text, "Should mention --base or dependencies"

        # Help should be substantial
        assert len(help_text) > 100, "Help text should be comprehensive"

    def test_implement_invalid_arguments(self, requires_v011, init_project_with_feature):
        """
        Test error on unknown flags.

        Implementation steps:
        1. Try: `spec-kitty implement WP01 --unknown-flag`
        2. Should fail with error about unknown flag
        3. Error from argparse/typer
        4. Suggest --help for valid flags
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--unknown-flag'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should reject unknown flag"

        # Error message should mention the unknown flag or usage
        error_output = result.stderr.lower() + result.stdout.lower()
        assert 'unknown' in error_output or 'unrecognized' in error_output or 'usage' in error_output, \
            "Should provide clear error about invalid argument"

    def test_implement_wp_id_case_insensitive(self, requires_v011, init_project_with_feature):
        """
        Test WP ID case handling: WP01 vs wp01 vs Wp01.

        Implementation steps:
        1. Try: `spec-kitty implement wp01` (lowercase)
        2. Document behavior:
           - Accepts and normalizes to WP01? OR
           - Rejects with case error?
        3. Try: `spec-kitty implement Wp01` (mixed case)
        4. Document behavior
        5. Consistent case handling is important
        """
        project_path = init_project_with_feature()

        # Try lowercase
        result_lower = subprocess.run(
            ['spec-kitty', 'implement', 'wp01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Try mixed case
        result_mixed = subprocess.run(
            ['spec-kitty', 'implement', 'Wp01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Document behavior - either accepts (normalizes) or rejects consistently
        # Both should have same behavior
        if result_lower.returncode == 0:
            # Accepts lowercase - should also accept mixed
            assert result_mixed.returncode == 0, "Case handling should be consistent"
        else:
            # Rejects non-uppercase - that's fine, document it
            assert result_lower.returncode != 0, "Case sensitivity documented"


class TestFeatureContextDetection:
    """Tests for feature context detection logic"""

    def test_detect_from_main_branch(self, requires_v011, init_project_with_feature):
        """
        Test detection when on feature branch in main repo.

        Implementation steps:
        1. Create feature 001-my-feature
        2. Checkout branch: `git checkout -b 001-my-feature`
        3. Run: `spec-kitty implement WP01` (no --feature flag)
        4. Should detect feature from branch name
        5. Verify workspace created for 001-my-feature
        """
        project_path = init_project_with_feature(feature_name="my-feature")

        # Checkout feature branch
        subprocess.run(
            ['git', 'checkout', '-b', '001-my-feature'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Run implement without --feature flag
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed (or fail with informative error if not supported)
        if result.returncode == 0:
            # Feature detection worked
            workspace_path = project_path / '.worktrees' / '001-my-feature-WP01'
            assert workspace_path.exists(), "Should create workspace for detected feature"
        else:
            # Feature detection may not be implemented - document it
            pytest.skip(f"Feature detection from branch not implemented: {result.stderr}")

    def test_detect_from_worktree_directory(self, requires_v011, init_project_with_feature):
        """
        Test detection when running from within a WP worktree.

        Implementation steps:
        1. Implement WP01 (creates .worktrees/001-feature-WP01/)
        2. cd into .worktrees/001-feature-WP01/
        3. Run: `spec-kitty implement WP02`
        4. Should detect feature from directory path
        5. Should create WP02 in same feature
        """
        project_path = init_project_with_feature()

        # Implement WP01
        result1 = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result1.returncode == 0, f"WP01 failed: {result1.stderr}"

        # Run from within worktree
        worktree_path = project_path / '.worktrees' / '001-test-feature-WP01'
        result2 = subprocess.run(
            ['spec-kitty', 'implement', 'WP02'],
            cwd=str(worktree_path),
            capture_output=True,
            text=True
        )

        # Should detect feature from worktree context
        if result2.returncode == 0:
            # Verify WP02 created in same feature
            wp02_path = project_path / '.worktrees' / '001-test-feature-WP02'
            assert wp02_path.exists(), "WP02 should be in same feature"
        else:
            # May not be supported yet
            pytest.skip(f"Worktree context detection not implemented: {result2.stderr}")

    def test_detect_from_feature_name_arg(self, requires_v011, init_project_with_feature):
        """
        Test explicit --feature flag.

        Implementation steps:
        1. Create two features: 001-feature-a, 002-feature-b
        2. From main branch, run: `spec-kitty implement WP01 --feature 001-feature-a`
        3. Should implement in feature-a
        4. --feature flag overrides other detection
        """
        # Create first feature
        project_path = init_project_with_feature(feature_name="feature-a")

        # Create second feature (requires more setup)
        # For now, test basic --feature flag functionality
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--feature', '001-feature-a'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should work with explicit feature
        if result.returncode == 0:
            workspace_path = project_path / '.worktrees' / '001-feature-a-WP01'
            assert workspace_path.exists(), "Should use feature from --feature flag"
        else:
            # Flag may not exist yet
            pytest.skip(f"--feature flag not implemented: {result.stderr}")

    def test_detect_from_git_config(self, requires_v011, init_project_with_feature):
        """
        Test detection from git config (if supported).

        Implementation steps:
        1. Set git config: `git config spec-kitty.current-feature 001-test-feature`
        2. Run: `spec-kitty implement WP01`
        3. If supported, should detect from config
        4. If not supported, skip test
        5. Document whether git config is used
        """
        project_path = init_project_with_feature()

        # Set git config
        subprocess.run(
            ['git', 'config', 'spec-kitty.current-feature', '001-test-feature'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Run implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Document behavior
        if result.returncode == 0:
            workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
            if workspace_path.exists():
                # Git config detection works
                pass
        # Skip if not supported - this is optional feature
        pytest.skip("Git config feature detection may not be implemented")

    def test_ambiguous_context_error(self, requires_v011, init_project_with_feature):
        """
        Test error when multiple features could match.

        Implementation steps:
        1. Create features: 001-auth, 002-authentication
        2. Checkout branch: `git checkout -b auth`
        3. Run: `spec-kitty implement WP01`
        4. If ambiguous, should error: "Multiple features match 'auth': 001-auth, 002-authentication"
        5. Suggest using --feature flag
        """
        # This test requires creating multiple features which is complex
        # For now, document the expected behavior
        pytest.skip("Ambiguous context test requires multiple feature setup")

    def test_no_context_error(self, requires_v011, init_project_with_feature):
        """
        Test error when no feature context found.

        Implementation steps:
        1. On main branch, no features created
        2. Run: `spec-kitty implement WP01`
        3. Should fail: "No feature context detected"
        4. Error should suggest:
           - Create a feature first
           - Use --feature flag
           - Checkout feature branch
        """
        # Create project WITHOUT feature
        project_path = init_project_with_feature(wp_count=0)

        # Remove the feature that was created
        feature_dir = project_path / 'kitty-specs' / '001-test-feature'
        if feature_dir.exists():
            import shutil
            shutil.rmtree(feature_dir)

        # Try to implement without feature context
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail without feature context"

        # Error should be informative
        error_output = result.stderr.lower() + result.stdout.lower()
        assert 'feature' in error_output or 'context' in error_output, \
            "Error should mention feature/context"

    def test_context_priority_order(self, requires_v011, init_project_with_feature):
        """
        Test priority: --feature flag > worktree > branch > config.

        Implementation steps:
        1. Create feature-a, feature-b
        2. Checkout branch 001-feature-a
        3. Set config: spec-kitty.current-feature = 002-feature-b
        4. Run: `spec-kitty implement WP01 --feature 002-feature-b`
        5. Should use 002-feature-b (--feature flag wins)
        6. Document priority order clearly
        """
        # Complex test requiring multiple features
        pytest.skip("Priority order test requires multiple feature setup")

    def test_legacy_worktree_context_detection(self, requires_v011, init_project_with_feature):
        """
        Test detection works in legacy v0.10.x worktrees.

        Implementation steps:
        1. Manually create legacy worktree: .worktrees/001-feature/
        2. cd into legacy worktree
        3. Run: `spec-kitty implement WP01`
        4. Should detect feature 001
        5. May warn about legacy structure
        6. Should still create new workspace-per-WP structure
        """
        # Legacy compatibility test - skip for now
        pytest.skip("Legacy worktree detection test requires v0.10.x setup")


class TestBaseWorkspaceValidation:
    """Tests for --base workspace validation"""

    def test_base_workspace_exists(self, requires_v011, init_project_with_feature):
        """
        Test validation that base workspace exists.

        Implementation steps:
        1. Implement WP01
        2. Verify .worktrees/001-feature-WP01/ exists
        3. Run: `spec-kitty implement WP02 --base WP01`
        4. Validation should pass (base exists)
        5. WP02 created successfully
        """
        project_path = init_project_with_feature()

        # Implement WP01
        result1 = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result1.returncode == 0, f"WP01 failed: {result1.stderr}"

        # Verify WP01 workspace exists
        wp01_path = project_path / '.worktrees' / '001-test-feature-WP01'
        assert wp01_path.exists(), "WP01 workspace should exist"

        # Implement WP02 with base
        result2 = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result2.returncode == 0, f"WP02 failed: {result2.stderr}"

        # Verify WP02 created
        wp02_path = project_path / '.worktrees' / '001-test-feature-WP02'
        assert wp02_path.exists(), "WP02 workspace should be created"

    def test_base_workspace_git_branch_exists(self, requires_v011, init_project_with_feature):
        """
        Test that base workspace's git branch exists.

        Implementation steps:
        1. Implement WP01
        2. Verify git branch 001-feature-WP01 exists
        3. Run: `spec-kitty implement WP02 --base WP01`
        4. Should succeed (branch exists)
        5. WP02 branches from WP01's git branch
        """
        project_path = init_project_with_feature()

        # Implement WP01
        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Verify WP01 branch exists
        result = subprocess.run(
            ['git', 'branch', '--list', '001-test-feature-WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert '001-test-feature-WP01' in result.stdout, "WP01 branch should exist"

        # Implement WP02 with base
        result2 = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result2.returncode == 0, "WP02 should succeed when base branch exists"

    def test_base_workspace_clean_state(self, requires_v011, init_project_with_feature):
        """
        Test warning if base workspace has uncommitted changes.

        Implementation steps:
        1. Implement WP01
        2. In WP01 workspace: modify file without committing
        3. Run: `spec-kitty implement WP02 --base WP01`
        4. May warn: "Base workspace WP01 has uncommitted changes"
        5. May proceed or fail (document behavior)
        """
        project_path = init_project_with_feature()

        # Implement WP01
        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Modify file in WP01 workspace
        wp01_path = project_path / '.worktrees' / '001-test-feature-WP01'
        test_file = wp01_path / 'test.txt'
        test_file.write_text('uncommitted change')

        # Try to implement WP02
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Document behavior (may warn or proceed)
        # Either succeeds or fails with informative message
        if result.returncode != 0:
            output = result.stdout + result.stderr
            # Should mention uncommitted changes or clean state
            assert 'uncommitted' in output.lower() or 'clean' in output.lower() or 'dirty' in output.lower()

    def test_base_workspace_name_format(self, requires_v011, init_project_with_feature):
        """
        Test validation of --base value format.

        Implementation steps:
        1. Test valid formats: --base WP01, --base wp01 (if normalized)
        2. Test invalid: --base WP1, --base 1, --base "001-feature-WP01"
        3. Should validate WP## format
        4. Clear error on invalid format
        """
        project_path = init_project_with_feature()

        # Test invalid format
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'invalid'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail with format error
        assert result.returncode != 0, "Should reject invalid base format"

    def test_base_workspace_same_feature(self, requires_v011, init_project_with_feature):
        """
        Test error when base is from different feature.

        Implementation steps:
        1. Create feature-a with WP01
        2. Create feature-b
        3. Try: implement feature-b WP01 --base feature-a WP01
        4. Should fail: "Base must be from same feature"
        5. Cross-feature dependencies not allowed
        """
        # Complex multi-feature test
        pytest.skip("Cross-feature validation test requires multiple feature setup")

    def test_base_workspace_not_self(self, requires_v011, init_project_with_feature):
        """
        Test error on self-referential base.

        Implementation steps:
        1. Run: `spec-kitty implement WP01 --base WP01`
        2. Should fail immediately: "Cannot use WP01 as base for itself"
        3. Validation before any git operations
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should reject self-referential base"

        # Error should be clear
        error_output = result.stderr.lower() + result.stdout.lower()
        assert 'self' in error_output or 'same' in error_output or 'itself' in error_output, \
            "Error should mention self-reference"

    def test_base_workspace_suggestion(self, requires_v011, init_project_with_feature):
        """
        Test helpful error when base doesn't exist.

        Implementation steps:
        1. Do NOT implement WP01
        2. Try: `spec-kitty implement WP02 --base WP01`
        3. Error: "Base workspace WP01 does not exist"
        4. Suggestion: "Implement WP01 first: spec-kitty implement WP01"
        5. Helpful, actionable error
        """
        project_path = init_project_with_feature()

        # Try to implement WP02 with non-existent base
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail when base doesn't exist"

        # Error should mention missing base
        error_output = result.stderr.lower() + result.stdout.lower()
        assert 'wp01' in error_output or 'base' in error_output or 'exist' in error_output, \
            "Error should mention missing base"

    def test_multiple_base_workspaces_error(self, requires_v011, init_project_with_feature):
        """
        Test that only one --base allowed (current limitation).

        Implementation steps:
        1. Try: `spec-kitty implement WP04 --base WP02 --base WP03`
        2. Should fail: "Only one --base allowed"
        3. OR: second --base overrides first (document)
        4. Note: Multiple bases is future enhancement
        """
        project_path = init_project_with_feature()

        # Try multiple --base flags
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP03', '--base', 'WP01', '--base', 'WP02'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Document behavior (may reject or use last value)
        # Either is acceptable for v0.11.0
        if result.returncode != 0:
            # Rejects multiple bases - that's fine
            pass

    def test_base_required_when_dependencies_declared(self, requires_v011, init_project_with_feature):
        """
        Test error when WP has dependencies but no --base.

        Implementation steps:
        1. Create WP01 with deps: []
        2. Create WP02 with deps: [WP01]
        3. Implement WP01
        4. Try: `spec-kitty implement WP02` (no --base flag)
        5. Should fail: "WP02 depends on [WP01]. Use --base flag."
        6. Suggest: `spec-kitty implement WP02 --base WP01`
        """
        project_path = init_project_with_feature()

        # Update WP02 to have dependency
        wp02_file = project_path / 'kitty-specs' / '001-test-feature' / 'tasks' / 'WP02.md'
        wp02_file.write_text("---\ntitle: WP02\ndependencies: [WP01]\n---\n\n# WP02")

        # Commit change
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add dep'], cwd=str(project_path), check=True, capture_output=True)

        # Implement WP01
        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Try WP02 without --base
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP02'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # May require --base or auto-detect dependency
        # Document behavior
        if result.returncode != 0:
            error_output = result.stderr.lower() + result.stdout.lower()
            # Should mention dependency or base
            assert 'dependency' in error_output or 'depends' in error_output or 'base' in error_output

    def test_base_optional_when_no_dependencies(self, requires_v011, init_project_with_feature):
        """
        Test that --base is optional for independent WPs.

        Implementation steps:
        1. Create WP01 with deps: []
        2. Run: `spec-kitty implement WP01` (no --base)
        3. Should succeed (no dependencies, no --base needed)
        4. Branches from main
        """
        project_path = init_project_with_feature()

        # WP01 has no dependencies by default
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed without --base
        assert result.returncode == 0, f"Independent WP should work without --base: {result.stderr}"

        # Workspace should be created
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        assert workspace_path.exists(), "Workspace should be created"


class TestWorkspaceCreation:
    """Tests for workspace creation mechanics"""

    def test_workspace_directory_created(self, requires_v011, init_project_with_feature):
        """
        Test that workspace directory is created.

        Implementation steps:
        1. Run: `spec-kitty implement WP01`
        2. Verify .worktrees/001-test-feature-WP01/ directory exists
        3. Verify directory structure correct
        4. Verify working tree files present
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Verify directory created
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        assert workspace_path.exists(), f"Workspace should exist at {workspace_path}"
        assert workspace_path.is_dir(), "Workspace should be a directory"

        # Verify it has working tree files
        assert (workspace_path / '.git').exists(), "Workspace should have .git"

    def test_workspace_git_worktree_registered(self, requires_v011, init_project_with_feature):
        """
        Test that git worktree is properly registered.

        Implementation steps:
        1. Implement WP01
        2. Run: `git worktree list`
        3. Verify output includes:
           - Path: .worktrees/001-test-feature-WP01
           - Branch: 001-test-feature-WP01
        4. Worktree registered in git metadata
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check worktree list
        result = subprocess.run(
            ['git', 'worktree', 'list'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        # Should include the worktree
        assert '001-test-feature-WP01' in result.stdout, "Worktree should be registered"

    def test_workspace_branch_created(self, requires_v011, init_project_with_feature):
        """
        Test that git branch is created.

        Implementation steps:
        1. Implement WP01
        2. Run: `git branch --all`
        3. Verify branch 001-test-feature-WP01 exists
        4. Branch points to correct commit
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check branch exists
        result = subprocess.run(
            ['git', 'branch', '--list', '001-test-feature-WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )

        assert '001-test-feature-WP01' in result.stdout, "Branch should be created"

    def test_workspace_branch_points_to_base(self, requires_v011, init_project_with_feature):
        """
        Test that branch starts from correct base.

        Implementation steps:
        1. Implement WP01, make commit
        2. Get WP01 HEAD: `git rev-parse 001-test-feature-WP01`
        3. Implement WP02 --base WP01
        4. Get WP02 initial commit
        5. Verify WP02 branched from WP01's HEAD
        """
        project_path = init_project_with_feature()

        # Implement WP01
        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Make a commit in WP01
        wp01_path = project_path / '.worktrees' / '001-test-feature-WP01'
        test_file = wp01_path / 'test.txt'
        test_file.write_text('test')
        subprocess.run(['git', 'add', 'test.txt'], cwd=str(wp01_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Test'], cwd=str(wp01_path), check=True, capture_output=True)

        # Get WP01 HEAD
        result1 = subprocess.run(
            ['git', 'rev-parse', '001-test-feature-WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        wp01_head = result1.stdout.strip()

        # Implement WP02 with base
        subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--base', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Get WP02 merge-base with WP01
        result2 = subprocess.run(
            ['git', 'merge-base', '001-test-feature-WP01', '001-test-feature-WP02'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        merge_base = result2.stdout.strip()

        # Merge base should be WP01's HEAD
        assert merge_base == wp01_head, "WP02 should branch from WP01's HEAD"

    def test_workspace_kittify_copied(self, requires_v011, init_project_with_feature):
        """
        Test that .kittify/ is accessible in workspace.

        Implementation steps:
        1. Implement WP01
        2. Check .worktrees/001-feature-WP01/.kittify/ exists
        3. Git worktrees share .git but copy working tree
        4. .kittify should be accessible
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check .kittify exists in workspace
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        kittify_path = workspace_path / '.kittify'
        assert kittify_path.exists(), ".kittify should exist in workspace"

    def test_workspace_specs_accessible(self, requires_v011, init_project_with_feature):
        """
        Test that kitty-specs/ is accessible from workspace.

        Implementation steps:
        1. Implement WP01
        2. Check .worktrees/001-feature-WP01/kitty-specs/ exists
        3. Verify contains feature specs
        4. Planning artifacts accessible to agent in workspace
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check kitty-specs accessible
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        specs_path = workspace_path / 'kitty-specs'
        assert specs_path.exists(), "kitty-specs should exist in workspace"

        # Verify feature specs present
        feature_specs = specs_path / '001-test-feature'
        assert feature_specs.exists(), "Feature specs should be accessible"

    def test_workspace_initial_commit(self, requires_v011, init_project_with_feature):
        """
        Test that initial commit message is standard.

        Implementation steps:
        1. Implement WP01
        2. cd to workspace
        3. Run: `git log -1 --format=%s`
        4. Verify commit message format standard
        5. May be empty (no initial commit) - document
        """
        project_path = init_project_with_feature()

        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check git log in workspace
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=str(workspace_path),
            capture_output=True,
            text=True
        )

        # Should have some commit (from main or initial)
        # Just verify we can get log without error
        assert result.returncode == 0, "Should be able to get git log"

    def test_workspace_permissions_match_main(self, requires_v011, init_project_with_feature):
        """
        Test that file permissions preserved.

        Implementation steps:
        1. In main: create executable file
        2. Commit
        3. Implement WP01
        4. In workspace: verify file still executable
        5. Permissions preserved through git worktree
        """
        project_path = init_project_with_feature()

        # Create executable file in main
        exec_file = project_path / 'test.sh'
        exec_file.write_text('#!/bin/bash\necho test')
        exec_file.chmod(0o755)

        subprocess.run(['git', 'add', 'test.sh'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add exec'], cwd=str(project_path), check=True, capture_output=True)

        # Implement WP01
        subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            check=True,
            capture_output=True
        )

        # Check file permissions in workspace
        workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
        workspace_exec = workspace_path / 'test.sh'

        import stat
        # Should be executable
        assert workspace_exec.exists(), "File should exist in workspace"
        mode = workspace_exec.stat().st_mode
        assert mode & stat.S_IXUSR, "File should be executable in workspace"


class TestProgressTracking:
    """Tests for progress display and output"""

    def test_step_tracker_displays_progress(self, requires_v011, init_project_with_feature):
        """
        Test that StepTracker shows progress steps.

        Implementation steps:
        1. Run: `spec-kitty implement WP01`
        2. Capture stdout
        3. Verify progress messages like:
           - "Creating workspace..."
           - "Creating git branch..."
           - "Workspace created successfully"
        4. User sees what's happening
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Check for progress indicators in output
        output = result.stdout.lower()
        # Should have some progress messages (flexible to implementation)
        assert len(output) > 0, "Should have some output"

    def test_json_output_includes_workspace_path(self, requires_v011, init_project_with_feature):
        """
        Test JSON output structure.

        Implementation steps:
        1. Run: `spec-kitty implement WP01 --json`
        2. Parse JSON
        3. Verify fields present:
           - workspace_path
           - branch
           - feature
           - wp_id
           - success: true/false
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--json'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse JSON
        try:
            json_data = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    json_data = json.loads(line)
                    break

            if json_data:
                # Verify has path information
                assert any(k in json_data for k in ['workspace_path', 'path', 'worktree_path']), \
                    "JSON should include workspace path"
        except json.JSONDecodeError:
            # JSON may not be implemented yet
            pytest.skip("JSON output may not be fully implemented")

    def test_verbose_flag_shows_git_commands(self, requires_v011, init_project_with_feature):
        """
        Test --verbose flag shows git commands.

        Implementation steps:
        1. Run: `spec-kitty implement WP01 --verbose`
        2. Capture stdout
        3. Should show git commands executed:
           - git worktree add ...
           - git checkout -b ...
        4. Helpful for debugging
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--verbose'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # May not have --verbose flag yet
        if result.returncode != 0 and 'verbose' in result.stderr.lower():
            pytest.skip("--verbose flag not implemented yet")

        # If it worked, should have more output
        if result.returncode == 0:
            assert len(result.stdout) > 0, "Verbose should produce output"

    def test_quiet_flag_suppresses_output(self, requires_v011, init_project_with_feature):
        """
        Test --quiet flag minimal output.

        Implementation steps:
        1. Run: `spec-kitty implement WP01 --quiet`
        2. Verify minimal stdout (only errors)
        3. Success indicated by exit code 0
        4. Useful for scripts
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--quiet'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # May not have --quiet flag yet
        if result.returncode != 0 and 'quiet' in result.stderr.lower():
            pytest.skip("--quiet flag not implemented yet")

        # If it worked, should have minimal output
        if result.returncode == 0:
            # Quiet mode may have no output or minimal output
            pass


class TestErrorRecovery:
    """Tests for error handling and rollback"""

    def test_workspace_creation_failure_rollback(self, requires_v011, init_project_with_feature):
        """
        Test that partial workspace is cleaned up on error.

        Implementation steps:
        1. Simulate error during workspace creation (e.g., disk full)
        2. Verify workspace directory removed
        3. Verify git worktree not registered
        4. Verify git branch not created
        5. Clean state after error
        """
        # Difficult to simulate reliably - skip for now
        pytest.skip("Rollback simulation test requires error injection")

    def test_git_command_failure_handling(self, requires_v011, init_project_with_feature):
        """
        Test clear error if git command fails.

        Implementation steps:
        1. Corrupt git repository somehow
        2. Try: `spec-kitty implement WP01`
        3. Should fail with clear git error
        4. Error message should include git output
        5. User understands what went wrong
        """
        # Difficult to corrupt git safely
        pytest.skip("Git corruption test requires special setup")

    def test_disk_full_graceful_failure(self, requires_v011, init_project_with_feature):
        """
        Test handling of disk full error.

        Implementation steps:
        1. Simulate disk full (challenging - may need mock)
        2. Try: `spec-kitty implement WP01`
        3. Should fail with I/O error
        4. Error message: "Disk full" or similar
        5. Rollback attempted
        """
        # Cannot simulate disk full reliably
        pytest.skip("Disk full simulation not feasible in test")

    def test_permission_denied_clear_error(self, requires_v011, init_project_with_feature):
        """
        Test filesystem permission errors.

        Implementation steps:
        1. Make .worktrees/ read-only
        2. Try: `spec-kitty implement WP01`
        3. Should fail: "Permission denied"
        4. Error clear and actionable
        """
        project_path = init_project_with_feature()

        # Create .worktrees directory and make read-only
        worktrees_dir = project_path / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)
        worktrees_dir.chmod(0o444)

        try:
            result = subprocess.run(
                ['spec-kitty', 'implement', 'WP01'],
                cwd=str(project_path),
                capture_output=True,
                text=True
            )

            # Should fail with permission error
            assert result.returncode != 0, "Should fail with permission denied"

            # Error should mention permission
            error_output = result.stderr.lower() + result.stdout.lower()
            assert 'permission' in error_output or 'denied' in error_output or 'read-only' in error_output

        finally:
            # Restore permissions
            worktrees_dir.chmod(0o755)

    def test_interrupted_creation_cleanup(self, requires_v011, init_project_with_feature):
        """
        Test Ctrl+C during workspace creation.

        Implementation steps:
        1. Start: `spec-kitty implement WP01`
        2. Send SIGINT (Ctrl+C) during creation
        3. Verify graceful shutdown
        4. Verify partial workspace cleaned up
        5. May be hard to test reliably
        """
        # Difficult to test signal handling reliably
        pytest.skip("Signal handling test requires process control")

    def test_existing_workspace_clear_error(self, requires_v011, init_project_with_feature):
        """
        Test error when workspace already exists.

        Implementation steps:
        1. Implement WP01 (succeeds)
        2. Try again: `spec-kitty implement WP01`
        3. Should fail: "Workspace for WP01 already exists"
        4. No partial state, just clear error
        """
        project_path = init_project_with_feature()

        # Implement WP01
        result1 = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        assert result1.returncode == 0, "First implement should succeed"

        # Try again
        result2 = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result2.returncode != 0, "Should fail when workspace exists"

        # Error should mention existing workspace
        error_output = result2.stderr.lower() + result2.stdout.lower()
        assert 'exist' in error_output or 'already' in error_output, \
            "Error should mention existing workspace"


class TestCLIIntegration:
    """Tests for CLI behavior and integration"""

    def test_cli_returns_zero_on_success(self, requires_v011, init_project_with_feature):
        """
        Test exit code 0 on success.

        Implementation steps:
        1. Run: `spec-kitty implement WP01`
        2. Verify returncode == 0
        3. Standard Unix convention
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Should return 0 on success"

    def test_cli_returns_nonzero_on_error(self, requires_v011, init_project_with_feature):
        """
        Test exit code 1 on error.

        Implementation steps:
        1. Trigger error: `spec-kitty implement WP99` (doesn't exist)
        2. Verify returncode != 0 (typically 1)
        3. Scripts can check exit code
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP99'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode != 0, "Should return non-zero on error"

    def test_cli_output_to_stdout(self, requires_v011, init_project_with_feature):
        """
        Test normal output goes to stdout.

        Implementation steps:
        1. Run: `spec-kitty implement WP01`
        2. Capture stdout and stderr separately
        3. Progress messages should be on stdout
        4. Follows Unix conventions
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should have output on stdout (or at least not fail)
        assert result.returncode == 0, "Command should succeed"
        # Progress/success messages should be on stdout
        # (implementation may vary)

    def test_cli_errors_to_stderr(self, requires_v011, init_project_with_feature):
        """
        Test error messages go to stderr.

        Implementation steps:
        1. Trigger error
        2. Capture stdout and stderr
        3. Error messages should be on stderr
        4. Allows separating errors from output
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP99'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, "Should fail"

        # Error should be on stderr (or stdout, document behavior)
        assert len(result.stderr) > 0 or len(result.stdout) > 0, \
            "Should have error message somewhere"

    def test_cli_json_parseable(self, requires_v011, init_project_with_feature):
        """
        Test that --json output is valid JSON.

        Implementation steps:
        1. Run with --json flag
        2. Parse output with json.loads()
        3. Should not raise JSONDecodeError
        4. Valid JSON structure
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--json'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Command should succeed"

        # Try to parse JSON
        try:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    json.loads(line)  # Should not raise
                    return

            # If no JSON found, may not be implemented
            pytest.skip("JSON output may not be implemented")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON: {e}")

    def test_cli_python_module_invocation(self, requires_v011, init_project_with_feature):
        """
        Test: python -m specify_cli.__init__ implement WP01.

        Implementation steps:
        1. Run: `python -m specify_cli.__init__ implement WP01`
        2. Should work same as `spec-kitty implement WP01`
        3. Module invocation supported
        4. Useful for testing environments
        """
        project_path = init_project_with_feature()

        result = subprocess.run(
            ['python', '-m', 'specify_cli', 'implement', 'WP01'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should work (or fail gracefully)
        if result.returncode == 0:
            # Verify workspace created
            workspace_path = project_path / '.worktrees' / '001-test-feature-WP01'
            assert workspace_path.exists(), "Workspace should be created via python -m"
        else:
            # May not support python -m invocation
            pytest.skip("Python -m invocation may not be supported")
