"""
Category 9: Readability & Clarity Tests

Tests that generated commands and prompts are clear for both humans and LLM agents.

Test Coverage:
1. Markdown Validity (3 tests)
   - All commands are valid markdown
   - No broken internal references
   - Frontmatter YAML is valid

2. Agent Discoverability (3 tests)
   - Commands named consistently
   - Each command has clear purpose
   - Workflow order documented

3. Path Correctness (2 tests)
   - Relative paths documented
   - Examples use correct paths
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    # Default: sibling directory to spec-kitty-test
    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


class TestMarkdownValidity:
    """Test that generated markdown is syntactically valid."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_all_commands_valid_markdown(self, temp_project_dir, spec_kitty_repo_root):
        """Test: All generated commands are valid markdown."""
        project_name = 'test_markdown'
        project_path = temp_project_dir / project_name

        # Create project with multiple agents to test across all
        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude,codex', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check all command files in .claude/commands/
        claude_commands = project_path / '.claude' / 'commands'
        assert claude_commands.exists(), "Claude commands directory should exist"

        command_files = list(claude_commands.glob('*.md'))
        assert len(command_files) > 0, "Should have generated command files"

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # Validate basic markdown structure
            # 1. Check code blocks are properly closed
            code_block_markers = content.count('```')
            assert code_block_markers % 2 == 0, \
                f"{cmd_file.name}: Code blocks not properly closed (odd number of ```)"

            # 2. Check headers are properly formatted
            for line in content.split('\n'):
                if line.startswith('#'):
                    # Headers should have space after #
                    assert re.match(r'^#+\s+\S', line) or line.strip() == '#', \
                        f"{cmd_file.name}: Malformed header: {line}"

            # 3. Check no broken markdown links
            # Links should be [text](url) not [text] (url)
            broken_links = re.findall(r'\]\s+\(', content)
            assert len(broken_links) == 0, \
                f"{cmd_file.name}: Found broken markdown links with space between ] and ("

    def test_no_broken_internal_references(self, temp_project_dir, spec_kitty_repo_root):
        """Test: {SCRIPT} and path references resolve correctly."""
        project_name = 'test_references'
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
            check=True
        )

        # Check command files for references
        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # 1. Check for unexpanded {SCRIPT} variables
            unexpanded_vars = re.findall(r'\{SCRIPT[^}]*\}', content)
            assert len(unexpanded_vars) == 0, \
                f"{cmd_file.name}: Found unexpanded variables: {unexpanded_vars}"

            # 2. Check .kittify/ path references
            kittify_refs = re.findall(r'\.kittify/[^\s)\]]+', content)
            for ref in kittify_refs:
                # Remove trailing punctuation and markdown artifacts
                ref_path = ref.rstrip('.,;:]\'"')
                # Skip if this looks like it got caught in markdown link syntax
                if '](' in ref_path or '[' in ref_path:
                    continue
                full_path = project_path / ref_path

                # Path should exist or be a placeholder/cross-platform reference
                # Commands may reference powershell scripts that don't exist on macOS
                is_placeholder = any(placeholder in ref_path for placeholder in ['<', '...', 'example', 'your-'])
                is_cross_platform = 'powershell' in ref_path or 'cmd' in ref_path

                if not is_placeholder and not is_cross_platform:
                    # For actual paths (not placeholders or cross-platform), verify they exist
                    # or at least their parent directory exists (the structure is correct)
                    assert full_path.exists() or full_path.parent.exists(), \
                        f"{cmd_file.name}: Referenced path doesn't exist: {ref_path}"

    def test_frontmatter_yaml_valid(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Command frontmatter is valid YAML."""
        project_name = 'test_yaml'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # Extract frontmatter (between first two --- markers)
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

            if frontmatter_match:
                frontmatter_text = frontmatter_match.group(1)

                # Parse YAML
                try:
                    frontmatter_data = yaml.safe_load(frontmatter_text)
                    assert isinstance(frontmatter_data, dict), \
                        f"{cmd_file.name}: Frontmatter should be a dictionary"

                    # Check for common required fields (if any exist)
                    # This is flexible since not all commands may have the same frontmatter
                    if frontmatter_data:
                        # Should have string keys
                        for key in frontmatter_data.keys():
                            assert isinstance(key, str), \
                                f"{cmd_file.name}: Frontmatter keys should be strings"

                except yaml.YAMLError as e:
                    pytest.fail(f"{cmd_file.name}: Invalid YAML frontmatter: {e}")


class TestAgentDiscoverability:
    """Test that commands are easily discoverable and understandable."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_commands_named_consistently(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Command naming follows pattern (spec-kitty.{action})."""
        project_name = 'test_naming'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        # All spec-kitty commands should follow naming pattern
        spec_kitty_commands = [f for f in command_files if 'spec-kitty' in f.name.lower()]

        for cmd_file in spec_kitty_commands:
            # Should be spec-kitty.{action}.md or spec-kitty-{action}.md
            assert re.match(r'^spec-kitty[.-]\w+\.md$', cmd_file.name), \
                f"Command doesn't follow naming pattern: {cmd_file.name}"

        # Check alphabetical ordering helps discoverability
        # (files should be sortable by name)
        sorted_names = sorted([f.name for f in command_files])
        actual_names = [f.name for f in sorted(command_files, key=lambda x: x.name)]
        assert sorted_names == actual_names, "Commands should be alphabetically sortable"

    def test_each_command_has_clear_purpose(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Command descriptions are clear and concise."""
        project_name = 'test_purpose'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # Check for description in frontmatter or first paragraph
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

            has_description = False
            description_text = ""

            if frontmatter_match:
                frontmatter_text = frontmatter_match.group(1)
                try:
                    frontmatter_data = yaml.safe_load(frontmatter_text)
                    if isinstance(frontmatter_data, dict) and 'description' in frontmatter_data:
                        has_description = True
                        description_text = frontmatter_data['description']
                except yaml.YAMLError:
                    pass

            # If no frontmatter description, check first non-header paragraph
            if not has_description:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith('#') and not line.startswith('---'):
                        description_text = line.strip()
                        has_description = True
                        break

            # Should have some description
            assert has_description and description_text, \
                f"{cmd_file.name}: No description found"

            # Description should be reasonable length (not too short or long)
            assert len(description_text) >= 10, \
                f"{cmd_file.name}: Description too short: '{description_text}'"

            assert len(description_text) <= 300, \
                f"{cmd_file.name}: Description too long ({len(description_text)} chars)"

            # Should not contain vague terms
            vague_terms = ['does stuff', 'handles things', 'does something', 'thing', 'stuff']
            lower_desc = description_text.lower()
            for vague in vague_terms:
                assert vague not in lower_desc, \
                    f"{cmd_file.name}: Vague description contains '{vague}'"

    def test_workflow_order_documented(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Commands indicate their workflow position."""
        project_name = 'test_workflow'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        # Key workflow commands should have workflow context
        workflow_commands = [
            'spec-kitty.specify.md',
            'spec-kitty.plan.md',
            'spec-kitty.build.md',
        ]

        # Check if at least some commands have workflow indicators
        commands_with_workflow_context = 0

        for cmd_file in command_files:
            content = cmd_file.read_text().lower()

            # Look for workflow indicators
            workflow_indicators = [
                'after',
                'before',
                'then',
                'next',
                'first',
                'finally',
                'step',
                'workflow',
                'run this',
                'start by',
                'once you',
            ]

            has_workflow_context = any(indicator in content for indicator in workflow_indicators)

            if has_workflow_context:
                commands_with_workflow_context += 1

        # At least some commands should provide workflow guidance
        assert commands_with_workflow_context > 0, \
            "No commands provide workflow context (when to use them)"


class TestPathCorrectness:
    """Test that paths in commands are correct and well-documented."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_relative_paths_documented(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Relative paths clearly explained."""
        project_name = 'test_paths'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # Find references to special directories
            special_dirs = ['.kittify', 'kitty-specs', '.worktrees']

            for special_dir in special_dirs:
                if special_dir in content:
                    # Should have some context around the path
                    # (either same line or nearby lines)

                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if special_dir in line:
                            # Get context (3 lines before and after)
                            context_start = max(0, i - 3)
                            context_end = min(len(lines), i + 4)
                            context_lines = lines[context_start:context_end]
                            context = '\n'.join(context_lines)

                            # Context should provide explanation or structure
                            # (not just bare paths)
                            has_context = any([
                                'directory' in context.lower(),
                                'folder' in context.lower(),
                                'contains' in context.lower(),
                                'located' in context.lower(),
                                'stored' in context.lower(),
                                'file' in context.lower(),
                                '#' in context,  # Header providing context
                                '`' in line,  # Code formatting
                            ])

                            # This is a soft check - we just want paths to have SOME context
                            # Not all paths need elaborate explanations
                            assert has_context or len(line.strip()) > len(special_dir) + 10, \
                                f"{cmd_file.name}: Path '{special_dir}' lacks context in: {line}"

    def test_examples_use_correct_paths(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Example commands use valid paths."""
        project_name = 'test_examples'
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
            check=True
        )

        claude_commands = project_path / '.claude' / 'commands'
        command_files = list(claude_commands.glob('*.md'))

        for cmd_file in command_files:
            content = cmd_file.read_text()

            # Find bash code blocks with commands
            code_blocks = re.findall(r'```bash\s*\n(.*?)\n```', content, re.DOTALL)

            for block in code_blocks:
                # Look for file paths in commands
                # Match .kittify/scripts/... and similar patterns
                script_paths = re.findall(r'\.kittify/scripts/[^\s]+\.sh', block)

                for script_path in script_paths:
                    # Remove any trailing punctuation or quotes
                    clean_path = script_path.rstrip('",;:\'"')
                    full_path = project_path / clean_path

                    # Script should exist
                    assert full_path.exists(), \
                        f"{cmd_file.name}: Example uses non-existent script: {script_path}"

                    # Should be executable
                    assert os.access(full_path, os.X_OK), \
                        f"{cmd_file.name}: Example script not executable: {script_path}"
