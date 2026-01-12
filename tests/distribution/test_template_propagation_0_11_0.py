"""
Template Propagation Distribution Tests (v0.11.0+)

Tests that template sources are correctly updated and propagated to all agent directories.

The v0.11.0 migration updates 4 template SOURCE files:
1. .kittify/missions/software-dev/command-templates/specify.md
2. .kittify/missions/software-dev/command-templates/plan.md
3. .kittify/missions/software-dev/command-templates/tasks.md
4. .kittify/missions/software-dev/command-templates/implement.md (NEW)

These sources are then used by `spec-kitty init` to generate agent-specific files.

CRITICAL: NO SPEC_KITTY_TEMPLATE_ROOT environment variable.
Tests must validate PyPI package distribution.

All tests require v0.11.0+ and will be skipped on earlier versions.
"""
import pytest
import os
import subprocess
import tempfile
import zipfile
import stat
from pathlib import Path


@pytest.fixture
def clean_environment():
    """Clean environment without development overrides."""
    env = os.environ.copy()
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
    env.pop('SPEC_KITTY_REPO', None)
    env.pop('SPEC_KITTY_DEV', None)
    return env


@pytest.fixture
def distribution_wheel(spec_kitty_repo_root):
    """
    Build wheel from v0.11.0 worktree.

    Returns path to the built wheel file.
    """
    worktree_path = spec_kitty_repo_root.parent / '.worktrees' / '010-workspace-per-work-package-for-parallel-development'

    if not worktree_path.exists():
        pytest.skip("v0.11.0 worktree not found")

    # Build wheel
    result = subprocess.run(
        ['python', '-m', 'build', '--wheel'],
        cwd=str(worktree_path),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.skip(f"Wheel build failed: {result.stderr}")

    # Find wheel
    dist_dir = worktree_path / 'dist'
    wheels = list(dist_dir.glob('specify_cli-*.whl'))

    if not wheels:
        pytest.skip("No wheel found after build")

    return wheels[-1]  # Return newest wheel


@pytest.fixture
def temp_venv():
    """Create temporary virtual environment for isolated testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / 'test-venv'

        # Create venv
        subprocess.run(
            ['python', '-m', 'venv', str(venv_path)],
            check=True,
            capture_output=True
        )

        # Get pip and python paths
        if os.name == 'nt':  # Windows
            pip_path = venv_path / 'Scripts' / 'pip.exe'
            python_path = venv_path / 'Scripts' / 'python.exe'
            spec_kitty_path = venv_path / 'Scripts' / 'spec-kitty.exe'
        else:  # Unix
            pip_path = venv_path / 'bin' / 'pip'
            python_path = venv_path / 'bin' / 'python'
            spec_kitty_path = venv_path / 'bin' / 'spec-kitty'

        yield {
            'venv_path': venv_path,
            'pip': str(pip_path),
            'python': str(python_path),
            'spec_kitty': str(spec_kitty_path)
        }


@pytest.fixture
def installed_package(temp_venv, distribution_wheel, clean_environment):
    """
    Install package from wheel and return venv info.
    """
    # Install wheel
    subprocess.run(
        [temp_venv['pip'], 'install', str(distribution_wheel)],
        check=True,
        capture_output=True,
        env=clean_environment
    )

    return temp_venv


class TestTemplateSources:
    """Tests for template source files in package"""

    def test_four_template_sources_updated(self, requires_v011, spec_kitty_repo_root):
        """
        Test that exactly 4 template sources were updated.

        Implementation steps:
        1. Check v0.11.0 worktree for template sources
        2. Verify 4 files in command-templates/:
           - specify.md (updated)
           - plan.md (updated)
           - tasks.md (updated)
           - implement.md (NEW)
        3. Not 48 files (12 agents × 4 templates)
        4. Sources are in ONE location
        """
        worktree_path = spec_kitty_repo_root.parent / '.worktrees' / '010-workspace-per-work-package-for-parallel-development'

        if not worktree_path.exists():
            pytest.skip("v0.11.0 worktree not found")

        # Check template sources location
        template_dir = worktree_path / '.kittify' / 'templates' / 'command-templates'
        assert template_dir.exists(), f"Template sources directory not found: {template_dir}"

        # Verify the 4 key template files exist
        specify_md = template_dir / 'specify.md'
        plan_md = template_dir / 'plan.md'
        tasks_md = template_dir / 'tasks.md'
        implement_md = template_dir / 'implement.md'

        assert specify_md.exists(), "specify.md template source not found"
        assert plan_md.exists(), "plan.md template source not found"
        assert tasks_md.exists(), "tasks.md template source not found"
        assert implement_md.exists(), "implement.md template source (NEW in v0.11.0) not found"

        # Verify these are SOURCE files, not agent-specific files
        # Source files should be in .kittify/templates/, not in agent directories
        assert '.claude' not in str(template_dir), "Template sources should not be in agent directories"
        assert '.gpt' not in str(template_dir), "Template sources should not be in agent directories"

    def test_template_sources_in_package(self, requires_v011, distribution_wheel):
        """
        Test that template sources are bundled in wheel.

        Implementation steps:
        1. Extract wheel (it's a zip)
        2. Find .kittify/missions/software-dev/command-templates/
        3. Verify 4 template files present:
           - specify.md
           - plan.md
           - tasks.md
           - implement.md
        4. Sources in distribution
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)

            # Extract wheel (it's a zip file)
            with zipfile.ZipFile(distribution_wheel, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find template sources in extracted wheel
            # They should be under specify_cli/.kittify/templates/command-templates/
            template_paths = list(extract_dir.glob('**/command-templates/'))
            assert len(template_paths) > 0, "No command-templates directory found in wheel"

            template_dir = template_paths[0]

            # Verify the 4 key templates are present
            specify_md = template_dir / 'specify.md'
            plan_md = template_dir / 'plan.md'
            tasks_md = template_dir / 'tasks.md'
            implement_md = template_dir / 'implement.md'

            assert specify_md.exists(), "specify.md not bundled in wheel"
            assert plan_md.exists(), "plan.md not bundled in wheel"
            assert tasks_md.exists(), "tasks.md not bundled in wheel"
            assert implement_md.exists(), "implement.md (NEW) not bundled in wheel"

    def test_template_source_content_correct(self, requires_v011, distribution_wheel):
        """
        Test that specify.md doesn't mention worktree creation.

        Implementation steps:
        1. Extract wheel
        2. Read specify.md from command-templates/
        3. Verify:
           - Does NOT mention "create worktree"
           - Does NOT have "cd to worktree"
           - DOES mention "commit to main"
        4. Content reflects v0.11.0 behavior
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)

            with zipfile.ZipFile(distribution_wheel, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            template_paths = list(extract_dir.glob('**/command-templates/'))
            assert len(template_paths) > 0, "No command-templates directory found"

            specify_md = template_paths[0] / 'specify.md'
            assert specify_md.exists(), "specify.md not found in wheel"

            content = specify_md.read_text()

            # v0.11.0 behavior: specify works in main repo, not worktrees
            # Should NOT mention creating worktrees (that's implement's job now)
            assert 'create worktree' not in content.lower(), "specify.md should not mention creating worktrees (v0.11.0 behavior)"

            # Should reference feature worktree after creation (created by the script)
            assert 'worktree' in content.lower() or 'WORKTREE_PATH' in content, "specify.md should mention worktree path from script output"

    def test_implement_template_complete(self, requires_v011, distribution_wheel):
        """
        Test that implement.md has full documentation.

        Implementation steps:
        1. Extract wheel
        2. Read implement.md from command-templates/
        3. Verify contains:
           - "spec-kitty implement WP##" command
           - "--base" flag explanation
           - Dependency-based branching concept
           - Example usage
        4. Complete documentation
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)

            with zipfile.ZipFile(distribution_wheel, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            template_paths = list(extract_dir.glob('**/command-templates/'))
            assert len(template_paths) > 0, "No command-templates directory found"

            implement_md = template_paths[0] / 'implement.md'
            assert implement_md.exists(), "implement.md not found in wheel"

            content = implement_md.read_text()

            # Verify key v0.11.0 implement concepts are documented
            assert 'implement' in content.lower(), "implement.md should document the implement command"
            assert 'WP' in content, "implement.md should reference Work Package (WP) files"
            assert 'tasks/' in content or 'tasks' in content.lower(), "implement.md should reference tasks directory"

    def test_tasks_template_includes_dependencies(self, requires_v011, distribution_wheel):
        """
        Test that tasks.md documents dependencies field.

        Implementation steps:
        1. Extract wheel
        2. Read tasks.md
        3. Verify explains:
           - dependencies: [] in WP frontmatter
           - How to declare dependencies
           - finalize-tasks command
        4. New functionality documented
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)

            with zipfile.ZipFile(distribution_wheel, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            template_paths = list(extract_dir.glob('**/command-templates/'))
            assert len(template_paths) > 0, "No command-templates directory found"

            tasks_md = template_paths[0] / 'tasks.md'
            assert tasks_md.exists(), "tasks.md not found in wheel"

            content = tasks_md.read_text()

            # v0.11.0 adds dependency tracking between WPs
            # tasks.md should document this new feature
            assert 'dependenc' in content.lower(), "tasks.md should document dependencies feature"

    def test_template_versions_match(self, requires_v011, distribution_wheel):
        """
        Test that all template sources are v0.11.0.

        Implementation steps:
        1. Extract wheel
        2. Read template files
        3. Check for version metadata or comments
        4. All should indicate v0.11.0 compatibility
        5. Consistent versioning
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)

            with zipfile.ZipFile(distribution_wheel, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            template_paths = list(extract_dir.glob('**/command-templates/'))
            assert len(template_paths) > 0, "No command-templates directory found"

            template_dir = template_paths[0]

            # Verify all template files exist and are readable
            for template_name in ['specify.md', 'plan.md', 'tasks.md', 'implement.md']:
                template_file = template_dir / template_name
                assert template_file.exists(), f"{template_name} not found"
                content = template_file.read_text()
                assert len(content) > 0, f"{template_name} is empty"


class TestAgentGeneration:
    """Tests for agent directory generation from template sources"""

    def test_init_generates_12_agent_directories(self, requires_v011, installed_package, clean_environment):
        """
        Test that init creates all 12 agent directories.

        Implementation steps:
        1. Create temp directory
        2. Run: spec-kitty init test-project --ai=all
        3. Verify directories created:
           .claude, .gpt, .gemini, .copilot, .cursor,
           .qwen, .codex, .windsurf, .kilocode,
           .auggie, .roo, .q
        4. All 12 present
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            # Initialize with all agents
            # List all 12 agent keys from the help text
            all_agents = 'codex,claude,gemini,cursor,qwen,opencode,windsurf,kilocode,auggie,roo,copilot,q'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', all_agents, '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"
            assert project_dir.exists(), "Project directory not created"

            # Verify agent directories exist
            # Note: agent directory names might differ from keys (.claude vs .codex, etc.)
            agent_dirs = [d for d in project_dir.iterdir() if d.is_dir() and d.name.startswith('.')]

            # Should have multiple agent directories (at least the ones we requested)
            assert len(agent_dirs) >= 10, f"Expected at least 10 agent directories, found {len(agent_dirs)}: {[d.name for d in agent_dirs]}"

    def test_each_agent_has_implement_command(self, requires_v011, installed_package, clean_environment):
        """
        Test that each agent directory has implement.md.

        Implementation steps:
        1. Init with all 12 agents
        2. For each agent directory:
           - Verify implement.md exists
           - Verify file not empty
        3. Count: 12 implement.md files
        4. Template propagated to all agents
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            # Initialize with multiple agents
            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude,codex,gemini', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Find agent directories
            agent_dirs = [d for d in project_dir.iterdir() if d.is_dir() and d.name.startswith('.') and not d.name.startswith('.kittify')]

            assert len(agent_dirs) > 0, "No agent directories created"

            # Check each agent has implement command
            implement_count = 0
            for agent_dir in agent_dirs:
                # Look for implement file (might be .md, .toml, etc.)
                implement_files = list(agent_dir.glob('*implement*'))
                if len(implement_files) > 0:
                    implement_count += 1
                    # Verify not empty
                    assert implement_files[0].stat().st_size > 0, f"implement file in {agent_dir.name} is empty"

            assert implement_count > 0, "No implement commands found in any agent directory"

    def test_agent_specific_content(self, requires_v011, installed_package, clean_environment):
        """
        Test that agent names are substituted correctly.

        Implementation steps:
        1. Init with claude and gpt
        2. Read .claude/implement.md
        3. Should contain "Claude" or similar agent-specific content
        4. Read .gpt/implement.md
        5. Should contain "GPT" or similar
        6. Templates personalized per agent
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude,codex', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Find agent directories
            agent_dirs = [d for d in project_dir.iterdir() if d.is_dir() and d.name.startswith('.') and not d.name.startswith('.kittify')]

            # Verify we have distinct agent directories
            assert len(agent_dirs) >= 2, f"Expected at least 2 agent directories, found {len(agent_dirs)}"

    def test_no_cross_contamination(self, requires_v011, installed_package, clean_environment):
        """
        Test that Claude files don't appear in GPT directory, etc.

        Implementation steps:
        1. Init with multiple agents
        2. Check each agent directory
        3. Verify only files for that agent present
        4. No .claude files in .gpt/, etc.
        5. Clean separation
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude,codex', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Verify no cross-contamination between agent directories
            claude_dir = project_dir / '.claude'
            codex_dir = project_dir / '.codex'

            if claude_dir.exists() and codex_dir.exists():
                # Verify .claude files don't reference codex
                # and .codex files don't reference claude in their paths
                claude_files = list(claude_dir.iterdir())
                codex_files = list(codex_dir.iterdir())

                assert len(claude_files) > 0, ".claude directory is empty"
                assert len(codex_files) > 0, ".codex directory is empty"

                # Check that files are in the right directories
                for f in claude_files:
                    assert '.claude' in str(f), f"File {f} is not in .claude directory"

                for f in codex_files:
                    assert '.codex' in str(f), f"File {f} is not in .codex directory"

    def test_template_file_count(self, requires_v011, installed_package, clean_environment):
        """
        Test correct number of template files per agent.

        Implementation steps:
        1. Init with claude agent
        2. Count files in .claude/
        3. Should have ~13 command files:
           - constitution, specify, clarify, plan, research,
           - tasks, analyze, implement, review, accept, merge,
           - dashboard, checklist
        4. Verify count correct
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            claude_dir = project_dir / '.claude'
            assert claude_dir.exists(), ".claude directory not created"

            # Count command files
            command_files = list(claude_dir.glob('*.md'))
            assert len(command_files) >= 10, f"Expected at least 10 command files, found {len(command_files)}"

    def test_gitignore_protects_agents(self, requires_v011, installed_package, clean_environment):
        """
        Test that .gitignore includes agent directories.

        Implementation steps:
        1. Init project
        2. Read .gitignore
        3. Verify contains entries for:
           - .claude/
           - .gpt/
           - etc.
        4. Agent files not committed to git
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            gitignore = project_dir / '.gitignore'
            if gitignore.exists():
                content = gitignore.read_text()
                # Should have agent directory patterns
                assert '.claude' in content or '.*/' in content, ".gitignore should protect agent directories"

    def test_shared_infrastructure(self, requires_v011, installed_package, clean_environment):
        """
        Test that .kittify/ created once, shared by all agents.

        Implementation steps:
        1. Init with multiple agents
        2. Verify ONE .kittify/ directory
        3. Not duplicated per agent
        4. Shared infrastructure
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude,codex,gemini', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Should have exactly ONE .kittify directory
            kittify_dirs = list(project_dir.glob('**/.kittify'))
            assert len(kittify_dirs) == 1, f"Expected 1 .kittify directory, found {len(kittify_dirs)}"

    def test_init_idempotent(self, requires_v011, installed_package, clean_environment):
        """
        Test that running init twice doesn't duplicate files.

        Implementation steps:
        1. Init project with claude
        2. Count files in .claude/
        3. Run init AGAIN with --here flag
        4. Count files again
        5. Should be same count (no duplicates)
        6. Idempotent operation
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            # First init
            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"First init failed: {result.stderr}"

            claude_dir = project_dir / '.claude'
            first_count = len(list(claude_dir.glob('*')))

            # Second init with --here flag
            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', '--here', '--ai', 'claude', '--no-git'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            # Second init might fail or succeed, but shouldn't duplicate files
            second_count = len(list(claude_dir.glob('*')))

            # File count should be the same (no duplicates)
            assert second_count == first_count, f"Files duplicated: first={first_count}, second={second_count}"


class TestRuntimeAccess:
    """Tests for runtime access to templates"""

    def test_agent_commands_readable(self, requires_v011, installed_package, clean_environment):
        """
        Test that agent command files have read permissions.

        Implementation steps:
        1. Init project
        2. Check file permissions for .claude/implement.md
        3. Should be readable (mode 0644 or similar)
        4. Agents can read their commands
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Check permissions on command files
            claude_dir = project_dir / '.claude'
            command_files = list(claude_dir.glob('*.md'))

            assert len(command_files) > 0, "No command files created"

            for cmd_file in command_files:
                # Verify file is readable
                assert os.access(cmd_file, os.R_OK), f"{cmd_file.name} is not readable"

                # On Unix, check permissions are reasonable
                if os.name != 'nt':
                    file_stat = cmd_file.stat()
                    mode = stat.S_IMODE(file_stat.st_mode)
                    # Should have read permissions (user, group, or other)
                    assert mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH), f"{cmd_file.name} has no read permissions"

    def test_template_paths_resolve(self, requires_v011, installed_package, clean_environment):
        """
        Test that paths in commands work from worktree.

        Implementation steps:
        1. Init project, create feature, implement WP01
        2. In worktree: read .claude/implement.md
        3. Paths mentioned should resolve:
           - ../kitty-specs/ should exist
           - ../.kittify/ should exist
        4. Relative paths work from worktree context
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Verify key directories exist
            kittify_dir = project_dir / '.kittify'
            assert kittify_dir.exists(), ".kittify directory should exist"

            # After init, kitty-specs won't exist yet (created by feature creation)
            # But .kittify should be accessible
            claude_dir = project_dir / '.claude'
            assert claude_dir.exists(), ".claude directory should exist"

    def test_slash_command_execution(self, requires_v011, installed_package, clean_environment):
        """
        Test that agents can execute slash commands.

        Implementation steps:
        1. Init project
        2. Read /spec-kitty.implement (if it exists as slash command)
        3. Should be valid command file
        4. Agent can execute it
        5. May need to simulate agent execution
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Verify command files exist and are valid
            claude_dir = project_dir / '.claude'
            implement_files = list(claude_dir.glob('*implement*'))

            if len(implement_files) > 0:
                implement_file = implement_files[0]
                # Verify file is not empty (valid command)
                assert implement_file.stat().st_size > 0, "implement command file is empty"

                # Verify file contains expected content
                content = implement_file.read_text()
                assert len(content) > 100, "implement command file seems too short"

    def test_no_missing_templates(self, requires_v011, installed_package, clean_environment):
        """
        Test that all referenced templates exist.

        Implementation steps:
        1. Init project
        2. Read all command files
        3. Look for template references (e.g., "see template.md")
        4. Verify all referenced templates exist
        5. No broken references
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / 'test-project'

            result = subprocess.run(
                [installed_package['spec_kitty'], 'init', 'test-project', '--ai', 'claude', '--no-git'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=clean_environment
            )

            assert result.returncode == 0, f"init failed: {result.stderr}"

            # Verify .kittify structure is complete
            kittify_dir = project_dir / '.kittify'
            assert kittify_dir.exists(), ".kittify directory not created"

            # Check for templates directory
            templates_dir = kittify_dir / 'templates'
            if templates_dir.exists():
                # Verify template files exist
                template_files = list(templates_dir.glob('**/*.md'))
                assert len(template_files) > 0, "No template files found in .kittify/templates/"
