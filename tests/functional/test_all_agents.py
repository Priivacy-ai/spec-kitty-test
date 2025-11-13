"""
Test: All 12 Agents Comprehensive Validation
Purpose: Evidence-based testing of all supported agents based on empirical research
Related Finding: findings/2025-11-13_05_agent_research.md
Version Tested: b2285ba427e3a39ee6397850899bf52452728d03 (b2285ba)
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


# Agent test matrix based on empirical research
AGENT_TEST_MATRIX = {
    "claude": {
        "dir": ".claude/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "copilot": {
        "dir": ".github/prompts",
        "ext": "prompt.md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "has_vscode_settings": True,
    },
    "gemini": {
        "dir": ".gemini/commands",
        "ext": "toml",
        "var_format": "{{args}}",
        "file_count": 13,
    },
    "cursor": {
        "dir": ".cursor/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "qwen": {
        "dir": ".qwen/commands",
        "ext": "toml",
        "var_format": "{{args}}",
        "file_count": 13,
    },
    "opencode": {
        "dir": ".opencode/command",  # NOTE: Singular!
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "codex": {
        "dir": ".codex/prompts",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "windsurf": {
        "dir": ".windsurf/workflows",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "kilocode": {
        "dir": ".kilocode/workflows",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "auggie": {
        "dir": ".augment/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "roo": {
        "dir": ".roo/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
    "q": {
        "dir": ".amazonq/prompts",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
    },
}


class TestAllAgents:
    """Comprehensive validation of all 12 supported agents"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.parametrize("agent_name,agent_config", AGENT_TEST_MATRIX.items())
    def test_agent_directory_structure(self, temp_project_dir, spec_kitty_repo_root, agent_name, agent_config):
        """
        Test: Each agent creates correct directory structure

        Validates for all 12 agents:
        - Directory created at expected path
        - Correct subdirectory name (commands/prompts/workflows/command)
        - Directory exists and is accessible
        """
        project_name = f"test_{agent_name}"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Init with this agent
        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                f'--ai={agent_name}',
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

        # Verify directory exists
        agent_dir = project_path / agent_config["dir"]
        assert agent_dir.exists(), f"{agent_name}: Directory {agent_config['dir']} not created"
        assert agent_dir.is_dir(), f"{agent_name}: {agent_config['dir']} is not a directory"

    @pytest.mark.parametrize("agent_name,agent_config", AGENT_TEST_MATRIX.items())
    def test_agent_file_count_and_extension(self, temp_project_dir, spec_kitty_repo_root, agent_name, agent_config):
        """
        Test: Each agent gets exactly 13 files with correct extension

        Validates:
        - Exactly 13 command files created
        - All files have correct extension
        - All files are non-empty
        """
        project_name = f"test_{agent_name}"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                f'--ai={agent_name}',
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

        agent_dir = project_path / agent_config["dir"]

        # Find all files with expected extension
        files = list(agent_dir.glob(f'spec-kitty.*.{agent_config["ext"]}'))

        assert len(files) == agent_config["file_count"], (
            f"{agent_name}: Expected {agent_config['file_count']} files, "
            f"got {len(files)}"
        )

        # Verify all files are non-empty
        for file in files:
            assert file.stat().st_size > 0, f"{agent_name}: {file.name} is empty"

    @pytest.mark.parametrize("agent_name,agent_config", AGENT_TEST_MATRIX.items())
    def test_agent_variable_syntax(self, temp_project_dir, spec_kitty_repo_root, agent_name, agent_config):
        """
        Test: Each agent uses correct variable syntax

        Validates:
        - Markdown agents use $ARGUMENTS
        - TOML agents use {{args}}
        - No cross-contamination between formats
        """
        project_name = f"test_{agent_name}"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                f'--ai={agent_name}',
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

        agent_dir = project_path / agent_config["dir"]

        # Check a sample file (specify command exists for all agents)
        sample_file = agent_dir / f'spec-kitty.specify.{agent_config["ext"]}'
        assert sample_file.exists(), f"{agent_name}: sample file not found"

        content = sample_file.read_text()

        # Verify correct variable format is present
        expected_var = agent_config["var_format"]
        assert expected_var in content, (
            f"{agent_name}: Expected variable '{expected_var}' not found in {sample_file.name}"
        )

        # Verify wrong variable format is NOT present
        if expected_var == "$ARGUMENTS":
            wrong_var = "{{args}}"
        else:
            wrong_var = "$ARGUMENTS"

        assert wrong_var not in content, (
            f"{agent_name}: Wrong variable format '{wrong_var}' found in {sample_file.name}. "
            f"Should only use '{expected_var}'"
        )

    def test_copilot_creates_vscode_settings(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: GitHub Copilot creates .vscode/settings.json

        Special case: Copilot is the only agent that creates VS Code settings
        """
        project_name = "test_copilot_vscode"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=copilot',
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

        vscode_settings = project_path / '.vscode' / 'settings.json'
        assert vscode_settings.exists(), "Copilot should create .vscode/settings.json"

        # Verify it's valid JSON
        import json
        with open(vscode_settings) as f:
            settings = json.load(f)
            assert isinstance(settings, dict), "settings.json should be valid JSON object"

    def test_opencode_singular_directory(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: opencode uses 'command' (singular) not 'commands' (plural)

        Special case: opencode is the only agent using singular directory name
        """
        project_name = "test_opencode_singular"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            [
                'spec-kitty', 'init', project_name,
                '--ai=opencode',
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

        # Verify singular form
        singular_dir = project_path / '.opencode' / 'command'
        assert singular_dir.exists(), "opencode should use 'command' (singular)"

        # Verify plural does NOT exist
        plural_dir = project_path / '.opencode' / 'commands'
        assert not plural_dir.exists(), "opencode should NOT have 'commands' (plural)"

    def test_toml_agents_valid_format(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: TOML agents (gemini, qwen) produce valid TOML files

        Validates:
        - Files can be parsed as TOML
        - Required fields present (description, prompt)
        - Correct variable syntax {{args}}
        """
        import tomllib  # Python 3.11+ or pip install tomli for earlier versions

        for agent_name in ["gemini", "qwen"]:
            project_name = f"test_{agent_name}_toml"
            project_path = temp_project_dir / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                [
                    'spec-kitty', 'init', project_name,
                    f'--ai={agent_name}',
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

            agent_config = AGENT_TEST_MATRIX[agent_name]
            agent_dir = project_path / agent_config["dir"]
            sample_file = agent_dir / 'spec-kitty.specify.toml'

            # Parse as TOML
            with open(sample_file, 'rb') as f:
                toml_data = tomllib.load(f)

            # Verify structure
            assert 'description' in toml_data, f"{agent_name}: TOML missing 'description' field"
            assert 'prompt' in toml_data, f"{agent_name}: TOML missing 'prompt' field"

            # Verify variable syntax in prompt
            assert '{{args}}' in toml_data['prompt'], (
                f"{agent_name}: TOML prompt should contain {{{{args}}}}"
            )

    def test_all_agents_create_shared_infrastructure(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: All agents create same shared infrastructure

        Validates that regardless of agent choice:
        - .kittify/ directory created
        - .git/ repository initialized
        - AGENTS.md present
        """
        # Test with a few representative agents
        test_agents = ["claude", "gemini", "cursor"]

        for agent_name in test_agents:
            project_name = f"test_{agent_name}_infra"
            project_path = temp_project_dir / project_name

            env = os.environ.copy()
            env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

            subprocess.run(
                [
                    'spec-kitty', 'init', project_name,
                    f'--ai={agent_name}',
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

            # Verify shared infrastructure
            assert (project_path / '.kittify').exists(), f"{agent_name}: .kittify not created"
            assert (project_path / '.git').exists(), f"{agent_name}: .git not created"
            assert (project_path / '.kittify' / 'AGENTS.md').exists(), (
                f"{agent_name}: AGENTS.md not created"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
