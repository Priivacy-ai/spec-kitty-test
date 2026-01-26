"""
Test: spec-kitty init Non-Interactive Mode
Purpose: Validate that spec-kitty init can run completely non-interactively for CI/automation
Related: Gap analysis for non-interactive init mode
Status: These tests document the DESIRED behavior for non-interactive mode
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def spec_kitty_env(spec_kitty_repo_root):
    """Create environment with SPEC_KITTY_TEMPLATE_ROOT set."""
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
    return env


class TestNonInteractiveFlagsComplete:
    """Test that init works non-interactively when all required flags are provided."""

    def test_init_with_all_flags_no_interaction(self, temp_project_dir, spec_kitty_env):
        """
        Test: Init with all flags completes without requiring user input.

        This test should PASS when non-interactive mode is implemented.
        Currently EXPECTED TO FAIL because:
        - No --non-interactive flag exists
        - Agent selection strategy always prompts
        - Preferred implementer/reviewer always prompt when strategy=preferred

        Required flags for full non-interactive:
        - --ai (agent selection)
        - --agent-strategy (NEW: not yet implemented)
        - --preferred-implementer (NEW: not yet implemented)
        - --preferred-reviewer (NEW: not yet implemented)
        - --non-interactive or env SPEC_KITTY_NON_INTERACTIVE=1 (NEW: not yet implemented)
        """
        project_name = "test_noninteractive"
        project_path = temp_project_dir / project_name

        # This command should complete without stdin input once flags are added
        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=preferred',  # NEW FLAG (not yet implemented)
                '--preferred-implementer=claude',  # NEW FLAG (not yet implemented)
                '--preferred-reviewer=codex',  # NEW FLAG (not yet implemented)
                '--non-interactive',  # NEW FLAG (not yet implemented)
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,  # No stdin - should fail if interaction required
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed without interaction
        assert result.returncode == 0, f"Init failed: {result.stderr}"
        assert project_path.exists(), "Project directory not created"
        assert (project_path / '.kittify').exists(), ".kittify not created"
        assert (project_path / '.claude').exists(), "Claude directory not created"
        assert (project_path / '.codex').exists(), "Codex directory not created"

    def test_init_with_random_strategy_no_preferred_flags(self, temp_project_dir, spec_kitty_env):
        """
        Test: Init with random strategy doesn't require preferred implementer/reviewer.

        When --agent-strategy=random, the --preferred-implementer and
        --preferred-reviewer flags should be optional (or error if provided).
        """
        project_name = "test_random_strategy"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=random',  # NEW FLAG
                '--non-interactive',  # NEW FLAG
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Init failed: {result.stderr}"

    def test_init_single_agent_auto_selects_for_both_roles(self, temp_project_dir, spec_kitty_env):
        """
        Test: Init with single agent in non-interactive mode auto-selects for both roles.

        When only one agent is selected and strategy=preferred, that agent should
        automatically be used for both implementation and review without prompting.
        """
        project_name = "test_single_agent"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--agent-strategy=preferred',  # NEW FLAG
                # No preferred-implementer/reviewer - should auto-select claude for both
                '--non-interactive',  # NEW FLAG
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Init failed: {result.stderr}"


class TestNonInteractiveMissingFlags:
    """Test that init fails clearly when non-interactive but required flags missing."""

    def test_init_noninteractive_without_agent_strategy_fails(self, temp_project_dir, spec_kitty_env):
        """
        Test: Non-interactive mode without --agent-strategy fails with clear error.

        Should fail with message like:
        "Error: --agent-strategy required in non-interactive mode.
         Choose from: preferred, random"
        """
        project_name = "test_missing_strategy"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--non-interactive',  # NEW FLAG
                # Missing --agent-strategy
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail when strategy not specified"
        assert '--agent-strategy' in result.stderr, "Error should mention missing --agent-strategy flag"

    def test_init_noninteractive_preferred_without_implementer_fails(self, temp_project_dir, spec_kitty_env):
        """
        Test: Non-interactive mode with strategy=preferred but missing implementer fails.

        Should fail with message like:
        "Error: --preferred-implementer required when --agent-strategy=preferred
         in non-interactive mode"
        """
        project_name = "test_missing_implementer"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=preferred',  # NEW FLAG
                # Missing --preferred-implementer
                '--preferred-reviewer=codex',
                '--non-interactive',  # NEW FLAG
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail when implementer not specified"
        assert '--preferred-implementer' in result.stderr, "Error should mention missing --preferred-implementer flag"

    def test_init_noninteractive_preferred_without_reviewer_fails(self, temp_project_dir, spec_kitty_env):
        """
        Test: Non-interactive mode with strategy=preferred but missing reviewer fails.

        Should fail with message like:
        "Error: --preferred-reviewer required when --agent-strategy=preferred
         in non-interactive mode"
        """
        project_name = "test_missing_reviewer"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=preferred',  # NEW FLAG
                '--preferred-implementer=claude',
                # Missing --preferred-reviewer
                '--non-interactive',  # NEW FLAG
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail when reviewer not specified"
        assert '--preferred-reviewer' in result.stderr, "Error should mention missing --preferred-reviewer flag"


class TestNonInteractiveHereFlag:
    """Test --here flag behavior in non-interactive mode."""

    def test_here_with_empty_dir_no_force_needed(self, spec_kitty_env):
        """
        Test: --here in empty directory works without --force in non-interactive mode.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    'spec-kitty', 'init', '--here',
                    '--ai=claude',
                    '--agent-strategy=preferred',  # NEW FLAG
                    '--preferred-implementer=claude',  # NEW FLAG
                    '--preferred-reviewer=claude',  # NEW FLAG
                    '--non-interactive',  # NEW FLAG
                    '--ignore-agent-tools',
                ],
                cwd=tmpdir,
                env=spec_kitty_env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Init failed: {result.stderr}"

    def test_here_with_nonempty_dir_requires_force_in_noninteractive(self, spec_kitty_env):
        """
        Test: --here in non-empty directory requires --force in non-interactive mode.

        Should fail with message like:
        "Error: Directory not empty. Use --force to proceed in non-interactive mode"
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create a file to make directory non-empty
            (tmppath / "existing.txt").write_text("exists")

            result = subprocess.run(
                [
                    'spec-kitty', 'init', '--here',
                    '--ai=claude',
                    '--agent-strategy=preferred',  # NEW FLAG
                    '--preferred-implementer=claude',  # NEW FLAG
                    '--preferred-reviewer=claude',  # NEW FLAG
                    '--non-interactive',  # NEW FLAG
                    # Missing --force
                    '--ignore-agent-tools',
                ],
                cwd=tmpdir,
                env=spec_kitty_env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail when directory not empty without --force"
            assert 'force' in result.stderr.lower(), "Error should mention --force flag"

    def test_here_with_nonempty_dir_succeeds_with_force(self, spec_kitty_env):
        """
        Test: --here in non-empty directory succeeds with --force in non-interactive mode.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create a file to make directory non-empty
            (tmppath / "existing.txt").write_text("exists")

            result = subprocess.run(
                [
                    'spec-kitty', 'init', '--here',
                    '--ai=claude',
                    '--agent-strategy=preferred',  # NEW FLAG
                    '--preferred-implementer=claude',  # NEW FLAG
                    '--preferred-reviewer=claude',  # NEW FLAG
                    '--non-interactive',  # NEW FLAG
                    '--force',
                    '--ignore-agent-tools',
                ],
                cwd=tmpdir,
                env=spec_kitty_env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Init should succeed with --force: {result.stderr}"
            assert (tmppath / '.kittify').exists(), ".kittify should be created"
            assert (tmppath / 'existing.txt').exists(), "Existing file should be preserved"


class TestEnvironmentVariableOverride:
    """Test environment variable for non-interactive mode."""

    def test_env_var_enables_noninteractive_mode(self, temp_project_dir, spec_kitty_env):
        """
        Test: SPEC_KITTY_NON_INTERACTIVE=1 enables non-interactive mode.

        Alternative to --non-interactive flag for CI environments.
        """
        project_name = "test_env_noninteractive"

        env = spec_kitty_env.copy()
        env['SPEC_KITTY_NON_INTERACTIVE'] = '1'  # NEW ENV VAR

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--agent-strategy=preferred',  # NEW FLAG
                '--preferred-implementer=claude',  # NEW FLAG
                '--preferred-reviewer=claude',  # NEW FLAG
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Init failed: {result.stderr}"

    def test_env_var_with_missing_flags_fails_appropriately(self, temp_project_dir, spec_kitty_env):
        """
        Test: SPEC_KITTY_NON_INTERACTIVE=1 with missing flags fails clearly.

        Even with env var, missing required flags should cause clear failure.
        """
        project_name = "test_env_missing_flags"

        env = spec_kitty_env.copy()
        env['SPEC_KITTY_NON_INTERACTIVE'] = '1'  # NEW ENV VAR

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                # Missing agent-strategy and preferred flags
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail with missing flags even with env var"
        assert '--agent-strategy' in result.stderr, "Error should mention missing flags"


class TestInvalidAgentPreferences:
    """Test validation of agent preferences in non-interactive mode."""

    def test_preferred_implementer_not_in_selected_agents_fails(self, temp_project_dir, spec_kitty_env):
        """
        Test: Preferred implementer must be one of the selected agents.

        Should fail with message like:
        "Error: --preferred-implementer 'cursor' is not in selected agents [claude, codex]"
        """
        project_name = "test_invalid_implementer"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=preferred',
                '--preferred-implementer=cursor',  # Not in selected agents
                '--preferred-reviewer=claude',
                '--non-interactive',
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail when implementer not in selected agents"
        assert 'not in selected agents' in result.stderr.lower() or 'invalid' in result.stderr.lower()

    def test_preferred_reviewer_not_in_selected_agents_fails(self, temp_project_dir, spec_kitty_env):
        """
        Test: Preferred reviewer must be one of the selected agents.

        Should fail with message like:
        "Error: --preferred-reviewer 'cursor' is not in selected agents [claude, codex]"
        """
        project_name = "test_invalid_reviewer"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--agent-strategy=preferred',
                '--preferred-implementer=claude',
                '--preferred-reviewer=cursor',  # Not in selected agents
                '--non-interactive',
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "Should fail when reviewer not in selected agents"
        assert 'not in selected agents' in result.stderr.lower() or 'invalid' in result.stderr.lower()


class TestBackwardsCompatibility:
    """Test that interactive mode still works as before."""

    def test_init_without_noninteractive_flag_still_prompts(self, temp_project_dir, spec_kitty_env):
        """
        Test: Init without --non-interactive flag still prompts interactively.

        Ensures backwards compatibility - existing interactive behavior preserved.
        This test provides stdin input to simulate user interaction.
        """
        project_name = "test_interactive_compat"

        # Simulate user selections via stdin:
        # 1. Agent selection (if --ai not provided)
        # 2. Strategy selection
        # 3. Preferred implementer selection
        # 4. Preferred reviewer selection
        stdin_input = "\n".join([
            " ",  # Select default agents (space to toggle)
            "",   # Confirm selection (enter)
            "",   # Select default strategy (enter)
            "",   # Select default implementer (enter)
            "",   # Select default reviewer (enter)
        ])

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',  # Provide AI to skip that prompt
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed with interactive input
        assert result.returncode == 0, f"Interactive init should still work: {result.stderr}"


@pytest.mark.skip(reason="Current implementation DOES NOT support non-interactive mode - these tests document desired behavior")
class TestCurrentLimitations:
    """
    Document current limitations that prevent non-interactive operation.

    These tests are SKIPPED because the features don't exist yet.
    Remove the skip decorator as features are implemented.
    """

    def test_current_implementation_requires_stdin_for_strategy(self, temp_project_dir, spec_kitty_env):
        """
        CURRENT LIMITATION: Even with --ai, init still prompts for strategy.

        Lines 347-351 in init.py always call select_with_arrows for strategy,
        which requires stdin interaction via readchar.

        This test documents the gap - remove skip when fixed.
        """
        project_name = "test_current_limitation"

        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--ignore-agent-tools',
            ],
            cwd=temp_project_dir,
            env=spec_kitty_env,
            stdin=subprocess.DEVNULL,  # No stdin
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Currently fails because it tries to read from stdin
        assert result.returncode != 0, "Current implementation requires stdin"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
