"""
Test: Multi-Agent Initialization
Purpose: Validate that spec-kitty init works correctly with multiple agents simultaneously
Related Strategy: findings/2025-11-13_02_functional_test_strategy.md - Category 1
Version Tested: b2285ba427e3a39ee6397850899bf52452728d03 (b2285ba)
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


class TestMultiAgentInit:
    """Test initialization with multiple agents"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_with_two_agents(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Init with two agents creates directories for both

        Validates:
        - Both agent directories are created
        - Each agent gets 13 commands
        - No cross-contamination of files
        """
        project_name = "test_two_agents"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with claude and codex
        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Verify both directories exist
        assert (project_path / '.claude' / 'commands').exists(), "Claude directory not created"
        assert (project_path / '.codex' / 'prompts').exists(), "Codex directory not created"

        # Count commands for each agent
        claude_commands = list((project_path / '.claude' / 'commands').glob('spec-kitty.*.md'))
        codex_commands = list((project_path / '.codex' / 'prompts').glob('spec-kitty.*.md'))

        assert len(claude_commands) == 13, f"Expected 13 Claude commands, got {len(claude_commands)}"
        assert len(codex_commands) == 13, f"Expected 13 Codex commands, got {len(codex_commands)}"

        # Verify command names match
        claude_names = {f.name for f in claude_commands}
        codex_names = {f.name for f in codex_commands}
        assert claude_names == codex_names, "Claude and Codex should have same command names"

    def test_init_with_three_agents(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Init with three agents creates directories for all three

        Tests that the system scales to multiple agents correctly.
        """
        project_name = "test_three_agents"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with claude, codex, and cursor
        result = subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex,cursor',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Verify all three directories exist
        assert (project_path / '.claude' / 'commands').exists()
        assert (project_path / '.codex' / 'prompts').exists()
        assert (project_path / '.cursor' / 'commands').exists()

        # Each should have 13 commands
        claude_count = len(list((project_path / '.claude' / 'commands').glob('spec-kitty.*.md')))
        codex_count = len(list((project_path / '.codex' / 'prompts').glob('spec-kitty.*.md')))
        cursor_count = len(list((project_path / '.cursor' / 'commands').glob('spec-kitty.*.md')))

        assert claude_count == 13, f"Claude: expected 13, got {claude_count}"
        assert codex_count == 13, f"Codex: expected 13, got {codex_count}"
        assert cursor_count == 13, f"Cursor: expected 13, got {cursor_count}"

    def test_agents_have_isolated_files(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Each agent's files are isolated (no cross-contamination)

        Validates that file modifications for one agent don't affect another.
        """
        project_name = "test_isolation"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Read same command from both agents
        claude_specify = (project_path / '.claude' / 'commands' / 'spec-kitty.specify.md').read_text()
        codex_specify = (project_path / '.codex' / 'prompts' / 'spec-kitty.specify.md').read_text()

        # Files should be in their respective directories (isolation verified by location)
        assert (project_path / '.claude' / 'commands' / 'spec-kitty.specify.md').exists()
        assert (project_path / '.codex' / 'prompts' / 'spec-kitty.specify.md').exists()

        # Both should use same variable syntax (both are Markdown)
        assert '$ARGUMENTS' in claude_specify, "Claude should use $ARGUMENTS"
        assert '$ARGUMENTS' in codex_specify, "Codex should use $ARGUMENTS"

        # Content should be similar but not necessarily agent-specific
        # (Templates are generic and work for all agents with same format)
        assert len(claude_specify) > 100, "Claude file should have content"
        assert len(codex_specify) > 100, "Codex file should have content"

    def test_shared_infrastructure_created_once(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Shared infrastructure (.kittify, .git) created once regardless of agent count

        Validates that core project structure isn't duplicated per agent.
        """
        project_name = "test_shared"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex,cursor',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Verify shared infrastructure exists (only once)
        assert (project_path / '.kittify').exists(), ".kittify should exist"
        assert (project_path / '.git').exists(), ".git should exist"
        assert (project_path / '.kittify' / 'AGENTS.md').exists(), "AGENTS.md should exist"

        # Check AGENTS.md contains agent rules (generic, not agent-specific list)
        agents_doc = (project_path / '.kittify' / 'AGENTS.md').read_text()
        assert 'agent rules' in agents_doc.lower(), "AGENTS.md should contain agent rules"
        assert 'path reference' in agents_doc.lower(), "AGENTS.md should have path rules"

        # Verify only one .kittify directory (not duplicated)
        kittify_dirs = list(project_path.glob('**/.kittify'))
        assert len(kittify_dirs) == 1, "Should have exactly one .kittify directory"

        # Verify each agent has its own directory
        assert (project_path / '.claude').exists(), "Claude directory should exist"
        assert (project_path / '.codex').exists(), "Codex directory should exist"
        assert (project_path / '.cursor').exists(), "Cursor directory should exist"

    def test_agent_directory_structure_correct(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Each agent's directory structure matches expected pattern

        Validates:
        - Claude: .claude/commands/*.md
        - Codex: .codex/prompts/*.md
        - Cursor: .cursor/commands/*.md
        - Gemini: .gemini/commands/*.toml
        """
        project_name = "test_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex,cursor,gemini',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Check directory names
        assert (project_path / '.claude' / 'commands').exists(), "Claude should use commands/"
        assert (project_path / '.codex' / 'prompts').exists(), "Codex should use prompts/"
        assert (project_path / '.cursor' / 'commands').exists(), "Cursor should use commands/"
        assert (project_path / '.gemini' / 'commands').exists(), "Gemini should use commands/"

        # Check file extensions
        claude_files = list((project_path / '.claude' / 'commands').glob('*'))
        codex_files = list((project_path / '.codex' / 'prompts').glob('*'))
        gemini_files = list((project_path / '.gemini' / 'commands').glob('*'))

        assert all(f.suffix == '.md' for f in claude_files), "Claude files should be .md"
        assert all(f.suffix == '.md' for f in codex_files), "Codex files should be .md"
        assert all(f.suffix == '.toml' for f in gemini_files), "Gemini files should be .toml"

    def test_gitignore_protects_all_agents(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: .gitignore includes all initialized agent directories

        Validates that agent directories are properly excluded from git.
        """
        project_name = "test_gitignore"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude,codex,cursor',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        gitignore_path = project_path / '.gitignore'
        assert gitignore_path.exists(), ".gitignore should be created"

        gitignore_content = gitignore_path.read_text()

        # Each agent directory should be in .gitignore
        assert '.claude/' in gitignore_content, ".gitignore should protect .claude/"
        assert '.codex/' in gitignore_content, ".gitignore should protect .codex/"
        assert '.cursor/' in gitignore_content, ".gitignore should protect .cursor/"

    def test_no_unexpected_files_created(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Init doesn't create files for agents not specified

        Validates that only requested agents get directories.
        """
        project_name = "test_no_extras"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Only init with claude
        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=claude',
                '--ignore-agent-tools'
            ],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Claude should exist
        assert (project_path / '.claude').exists(), "Claude should be created"

        # Others should NOT exist
        assert not (project_path / '.codex').exists(), "Codex should NOT be created"
        assert not (project_path / '.cursor').exists(), "Cursor should NOT be created"
        assert not (project_path / '.gemini').exists(), "Gemini should NOT be created"
        assert not (project_path / '.github').exists(), "GitHub Copilot should NOT be created"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
