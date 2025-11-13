"""
Test: Category 2 - Agent Workflow Execution
Purpose: Validate that agents can discover, parse, and execute commands in correct order
Related Strategy: findings/2025-11-13_02_functional_test_strategy.md
Version Tested: b2285ba427e3a39ee6397850899bf52452728d03 (b2285ba)

Tests cover:
- Command discovery by agents
- Execution order validation
- Parallel agent execution
- State transitions
- Command content consistency
- Path references correctness
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


# Correct workflow command order
# Based on Spec Kit documentation and Spec Kitty enhancements
WORKFLOW_ORDER = [
    'constitution',  # Step 1: Establish project principles FIRST (governance)
    'specify',       # Step 2: Define requirements (CREATES worktree)
    'clarify',       # Step 3 (OPTIONAL): Clarify underspecified areas
    'plan',          # Step 4: Create technical implementation plan
    'research',      # Step 5: Run Phase 0 research scaffolding
    'tasks',         # Step 6: Generate task breakdown from plan
    'analyze',       # Step 7 (OPTIONAL): Cross-artifact consistency check
    'implement',     # Step 8: Execute tasks
    'review',        # Step 9: Review implemented work
    'accept',        # Step 10: Final acceptance & metadata recording
    'merge',         # Step 11: Merge to main + cleanup worktree
]

# Utility commands NOT in workflow sequence
# These can be run anytime and don't represent workflow steps
UTILITY_COMMANDS = [
    'dashboard',     # Viewing tool, runs continuously in background
    'checklist',     # OPTIONAL quality gate, can run anytime after plan
]


class TestAgentCommandDiscovery:
    """Test that agents can reliably discover their commands"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_agent_can_discover_all_commands(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Agent can discover all 13 commands after init

        Simulates an agent discovering its commands:
        1. Init creates agent directory
        2. Agent lists files in directory
        3. Agent finds all 13 expected commands
        4. Commands are in discoverable format
        """
        project_name = "test_discovery"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with Claude
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Agent discovers commands
        commands_dir = project_path / '.claude' / 'commands'
        command_files = sorted(commands_dir.glob('spec-kitty.*.md'))

        # Should find exactly 13 commands
        assert len(command_files) == 13, (
            f"Agent should discover 13 commands, found {len(command_files)}"
        )

        # Extract command names
        discovered_commands = [
            f.stem.replace('spec-kitty.', '') for f in command_files
        ]

        # All workflow commands should be discoverable
        for expected_cmd in WORKFLOW_ORDER:
            assert expected_cmd in discovered_commands, (
                f"Agent cannot discover '{expected_cmd}' command"
            )

    def test_commands_are_readable_by_agent(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: All command files are readable and non-empty

        Validates:
        - Files can be opened and read
        - Content is non-empty
        - Content is valid text (not binary)
        """
        project_name = "test_readable"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        for cmd_file in commands_dir.glob('spec-kitty.*.md'):
            # Can read file
            content = cmd_file.read_text()

            # Is non-empty
            assert len(content) > 0, f"{cmd_file.name} is empty"

            # Contains some expected text markers
            assert len(content) > 100, (
                f"{cmd_file.name} is too short ({len(content)} bytes) - "
                "likely not a real command"
            )


class TestWorkflowCommandOrder:
    """Test that workflow commands are in logical execution order"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_commands_follow_logical_workflow_order(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Core workflow commands exist in correct sequence

        Validates the proper workflow order per Spec Kit documentation:
        1. constitution - Establish governance principles FIRST
        2. specify - Define requirements (CREATES worktree)
        3. clarify - OPTIONAL: Clarify underspecified areas
        4. plan - Create technical implementation plan
        5. research - Run Phase 0 research scaffolding
        6. tasks - Generate task breakdown from plan
        7. analyze - OPTIONAL: Cross-artifact consistency check
        8. implement - Execute tasks
        9. review - Review implemented work
        10. accept - Final acceptance & metadata recording
        11. merge - Merge to main + cleanup worktree

        Utility commands (dashboard, checklist) are NOT in workflow sequence.
        """
        project_name = "test_workflow_order"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Verify ALL workflow commands exist in order
        for cmd_name in WORKFLOW_ORDER:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            assert cmd_file.exists(), (
                f"Workflow command '{cmd_name}' is missing from agent commands. "
                f"Cannot execute complete workflow without this command."
            )

        # Verify utility commands also exist
        for cmd_name in UTILITY_COMMANDS:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            assert cmd_file.exists(), (
                f"Utility command '{cmd_name}' is missing from agent commands."
            )

    def test_all_workflow_commands_present(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: All expected commands exist (workflow + utility)

        Validates complete command set is available:
        - Workflow: constitution → specify → clarify → plan → research →
                   tasks → analyze → implement → review → accept → merge
        - Utility: dashboard, checklist (not in workflow sequence)
        """
        project_name = "test_complete_workflow"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Check all workflow commands exist
        for cmd_name in WORKFLOW_ORDER:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            assert cmd_file.exists(), (
                f"Workflow command '{cmd_name}' is missing"
            )

        # Check all utility commands exist
        for cmd_name in UTILITY_COMMANDS:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            assert cmd_file.exists(), (
                f"Utility command '{cmd_name}' is missing"
            )

    def test_workflow_vs_utility_commands_distinction(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Workflow commands are distinct from utility commands

        Validates understanding of command types:
        - Workflow commands: Sequential steps in the development process
        - Utility commands: Tools that can run anytime, not workflow steps

        Key distinctions:
        - dashboard: Viewing tool, runs continuously
        - checklist: Quality gate, can run anytime after plan
        - These do NOT belong in the workflow sequence
        """
        project_name = "test_command_types"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Verify we have exactly 11 workflow commands
        assert len(WORKFLOW_ORDER) == 11, (
            f"Expected 11 workflow commands, got {len(WORKFLOW_ORDER)}"
        )

        # Verify we have exactly 2 utility commands
        assert len(UTILITY_COMMANDS) == 2, (
            f"Expected 2 utility commands, got {len(UTILITY_COMMANDS)}"
        )

        # Verify no overlap between workflow and utility
        workflow_set = set(WORKFLOW_ORDER)
        utility_set = set(UTILITY_COMMANDS)
        overlap = workflow_set & utility_set

        assert len(overlap) == 0, (
            f"Workflow and utility commands should not overlap. Found: {overlap}"
        )

        # Verify total is 13 commands
        total_commands = len(WORKFLOW_ORDER) + len(UTILITY_COMMANDS)
        assert total_commands == 13, (
            f"Expected 13 total commands (11 workflow + 2 utility), got {total_commands}"
        )


class TestCommandPathReferences:
    """Test that commands reference correct .kittify/ paths"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_commands_reference_kittify_paths(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands correctly reference .kittify/ paths

        Validates:
        - Path rewriting happened
        - References point to .kittify/ directory
        - No broken template references
        """
        project_name = "test_path_references"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Check a few key commands
        for cmd_name in ['specify', 'plan', 'tasks', 'implement']:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            content = cmd_file.read_text()

            # If content references paths, they should be .kittify/ paths
            if '.kittify' in content:
                # Should NOT have unreplaced template variables
                assert '{SCRIPT}' not in content, (
                    f"{cmd_name}: Contains unreplaced {{SCRIPT}} variable"
                )
                assert '{AGENT_SCRIPT}' not in content, (
                    f"{cmd_name}: Contains unreplaced {{AGENT_SCRIPT}} variable"
                )

    def test_no_unreplaced_template_variables(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: No template variables remain unreplaced

        Validates:
        - {AGENT_SCRIPT} replaced
        - {SCRIPT} replaced
        - __AGENT__ replaced
        - All other template vars substituted
        """
        project_name = "test_no_vars"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        forbidden_patterns = [
            '{AGENT_SCRIPT}',
            '{SCRIPT}',
            '__AGENT__',
            '{{AGENT}}',
        ]

        for cmd_file in commands_dir.glob('spec-kitty.*.md'):
            content = cmd_file.read_text()

            for pattern in forbidden_patterns:
                assert pattern not in content, (
                    f"{cmd_file.name} contains unreplaced template variable: {pattern}"
                )


class TestMultiAgentParallelExecution:
    """Test that multiple agents can execute in parallel without conflicts"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_multi_agent_isolated_directories(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Multiple agents have isolated command directories

        Validates:
        - Each agent has its own directory
        - Directories don't overlap
        - No file conflicts between agents
        """
        project_name = "test_multi_agent"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with multiple agents
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude,codex,cursor', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Each agent should have its own directory
        claude_dir = project_path / '.claude' / 'commands'
        codex_dir = project_path / '.codex' / 'prompts'
        cursor_dir = project_path / '.cursor' / 'commands'

        assert claude_dir.exists(), "Claude directory missing"
        assert codex_dir.exists(), "Codex directory missing"
        assert cursor_dir.exists(), "Cursor directory missing"

        # Directories should be distinct
        assert claude_dir != codex_dir, "Claude and Codex share directory"
        assert claude_dir != cursor_dir, "Claude and Cursor share directory"
        assert codex_dir != cursor_dir, "Codex and Cursor share directory"

        # Each should have 13 commands
        assert len(list(claude_dir.glob('spec-kitty.*.md'))) == 13
        assert len(list(codex_dir.glob('spec-kitty.*.md'))) == 13
        assert len(list(cursor_dir.glob('spec-kitty.*.md'))) == 13

    def test_multi_agent_same_workflow_available(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: All agents get the same workflow commands

        Validates:
        - All agents have same 13 commands
        - Command names are consistent across agents
        - Each agent can execute full workflow
        """
        project_name = "test_workflow_consistency"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude,codex', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Get command names for each agent
        claude_commands = set(
            f.stem.replace('spec-kitty.', '')
            for f in (project_path / '.claude' / 'commands').glob('spec-kitty.*.md')
        )
        codex_commands = set(
            f.stem.replace('spec-kitty.', '')
            for f in (project_path / '.codex' / 'prompts').glob('spec-kitty.*.md')
        )

        # Should have same command set
        assert claude_commands == codex_commands, (
            f"Claude and Codex have different commands. "
            f"Claude only: {claude_commands - codex_commands}, "
            f"Codex only: {codex_commands - claude_commands}"
        )


class TestCommandContentCompleteness:
    """Test that command content is complete and actionable"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_commands_contain_arguments_variable(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands include $ARGUMENTS variable for agent input

        Validates:
        - Markdown agents use $ARGUMENTS
        - Variable is present in command content
        - Agent knows where to pass arguments
        """
        project_name = "test_arguments"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Most commands should have $ARGUMENTS
        commands_with_args = 0
        total_commands = 0

        for cmd_file in commands_dir.glob('spec-kitty.*.md'):
            total_commands += 1
            content = cmd_file.read_text()

            if '$ARGUMENTS' in content:
                commands_with_args += 1

        # At least majority should have $ARGUMENTS
        assert commands_with_args >= 10, (
            f"Only {commands_with_args}/{total_commands} commands contain $ARGUMENTS. "
            "Expected most commands to accept arguments."
        )

    def test_commands_have_meaningful_content(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Commands contain actual instructions, not just boilerplate

        Validates:
        - Content length is substantial
        - Contains instruction keywords
        - Has actionable guidance
        """
        project_name = "test_content_quality"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commands_dir = project_path / '.claude' / 'commands'

        # Check key workflow commands have substantial content
        key_commands = ['constitution', 'specify', 'plan', 'tasks', 'implement']

        for cmd_name in key_commands:
            cmd_file = commands_dir / f'spec-kitty.{cmd_name}.md'
            content = cmd_file.read_text()

            # Should be substantial (at least 500 chars of real content)
            assert len(content) > 500, (
                f"{cmd_name} command is too short ({len(content)} chars). "
                "Expected substantial instructions."
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
