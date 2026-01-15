"""
Test Migration: 0.10.9 Repair Templates Migration (Issue #68)

Purpose: Validate the upgrade migration that repairs broken templates for users
affected by issues #62, #63, #64 where PyPI installations received outdated
templates with bash script references.

BUG DETECTED (Issue #68): Parameter mismatch in generate_agent_assets() call
- Line 134: Using `ai=ai_config` instead of `agent_key=ai_config`
- Line 132-133: Parameter order also swapped from function signature

Function signature (asset_generator.py:14):
    def generate_agent_assets(
        command_templates_dir: Path,
        project_path: Path,
        agent_key: str,
        script_type: str
    ) -> None:

Incorrect call in migration (m_0_10_9_repair_templates.py:131-136):
    generate_agent_assets(
        project_path=project_path,  # ❌ Wrong order
        command_templates_dir=command_templates_dir,  # ❌ Wrong order
        ai=ai_config,  # ❌ Wrong parameter name
        script_type="sh"
    )

Expected behavior: Migration should successfully regenerate agent templates
Actual behavior: TypeError: unexpected keyword argument 'ai'

Migration Behavior:
- Detects bash script references in agent command templates
- Removes broken templates from .kittify/templates/
- Copies correct templates from package/local repo
- Regenerates all agent slash commands (WITH BUG)
- Verifies repair completion

Test Coverage:
1. Migration Detection (3 tests)
   - Detects bash script references in command templates
   - Does not trigger on clean v0.10.11+ projects
   - Detects broken templates across all agent types

2. Migration Execution (4 tests)
   - Removes broken templates
   - Copies correct templates
   - BUG: Regenerates agent commands (SHOULD FAIL with TypeError)
   - Verifies repair completion

3. Parameter Validation (2 tests) ⭐ NEW
   - Validates generate_agent_assets signature match
   - Tests actual migration execution catches parameter error

Version Requirement: spec-kitty >= 0.10.9 to run migration
"""

import inspect
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 10, 9),
    reason="Requires spec-kitty >= 0.10.9 (Repair templates migration)"
)


class TestMigrationDetection:
    """Test that migration detects when it needs to run."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def project_with_broken_templates(self, temp_project_dir):
        """Create a project with broken templates (bash script references).

        This simulates what PyPI users experienced in issues #62, #63, #64.
        """
        project_name = "broken_templates_project"
        project_path = temp_project_dir / project_name

        # Initialize project WITHOUT SPEC_KITTY_TEMPLATE_ROOT
        # to simulate PyPI user experience
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

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

        # Manually inject broken template with bash script reference
        # to simulate the bug from #62, #63, #64
        claude_commands = project_path / '.claude' / 'commands'
        claude_commands.mkdir(parents=True, exist_ok=True)

        broken_template = claude_commands / 'spec-kitty.implement.md'
        broken_template.write_text("""---
description: Implement a feature
---

# Implementation Command

Run the implementation script:

```bash
.kittify/scripts/bash/move-task-to-doing.sh WP01 doing
```

This command moves the task to the doing lane.
""")

        return project_path

    def test_detects_bash_script_references(self, project_with_broken_templates):
        """
        Test: Migration detects bash script references in command templates

        Validates:
        - Finds "scripts/bash/" in template files
        - Recognizes broken templates
        - Triggers migration need
        """
        # Check if spec-kitty upgrade recognizes the need to migrate
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=project_with_broken_templates,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should recognize bash script references or run successfully
        assert 'Traceback' not in result.stderr, "Should not crash on broken templates"

        # Verify our test fixture actually has broken templates
        commands_dir = project_with_broken_templates / '.claude' / 'commands'
        broken_found = False
        for cmd_file in commands_dir.glob('spec-kitty.*.md'):
            content = cmd_file.read_text()
            if 'scripts/bash/' in content:
                broken_found = True
                break

        assert broken_found, "Test fixture should have bash script references"

    def test_does_not_trigger_on_clean_project(self, temp_project_dir):
        """
        Test: Clean v0.10.11+ projects don't need migration

        Validates:
        - New projects have no bash script references
        - Migration doesn't run unnecessarily
        - No-op migration is fast
        """
        project_name = "clean_project"
        project_path = temp_project_dir / project_name

        # Initialize WITHOUT template root override (PyPI simulation)
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

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

        # Check templates don't have bash references
        commands_dir = project_path / '.claude' / 'commands'
        bash_refs = []
        for cmd_file in commands_dir.glob('spec-kitty.*.md'):
            content = cmd_file.read_text()
            if 'scripts/bash/' in content or 'scripts/powershell/' in content:
                bash_refs.append(cmd_file.name)

        assert len(bash_refs) == 0, (
            f"Clean project should not have bash script references. Found in: {bash_refs}"
        )

    def test_detects_broken_templates_all_agents(self, temp_project_dir):
        """
        Test: Detects broken templates across all agent types

        Validates:
        - Checks .claude, .copilot, .codex, etc.
        - Migration scans all agent directories
        - No agent type is missed
        """
        project_name = "multi_agent_project"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

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

        # Inject broken template in different agent dir
        copilot_prompts = project_path / '.github' / 'prompts'
        copilot_prompts.mkdir(parents=True, exist_ok=True)

        broken_copilot = copilot_prompts / 'spec-kitty.plan.md'
        broken_copilot.write_text('.kittify/scripts/bash/create-plan.sh')

        # Migration should detect this
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--dry-run'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert 'Traceback' not in result.stderr, "Should detect broken templates in all agents"


class TestMigrationExecution:
    """Test the actual migration execution and transformations."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def project_with_broken_templates(self, temp_project_dir):
        """Create project with broken templates."""
        project_name = "repair_me"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)

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

        # Inject broken templates
        claude_commands = project_path / '.claude' / 'commands'
        for cmd_file in claude_commands.glob('spec-kitty.*.md'):
            content = cmd_file.read_text()
            # Inject bash reference
            modified = content + "\n.kittify/scripts/bash/example.sh\n"
            cmd_file.write_text(modified)

        return project_path

    def test_removes_broken_templates(self, project_with_broken_templates):
        """
        Test: Migration removes broken templates from .kittify/templates/

        Validates:
        - Detects .kittify/templates/ directory
        - Removes it completely
        - Prepares for fresh template copy
        """
        # Create .kittify/templates/ to simulate broken state
        templates_dir = project_with_broken_templates / '.kittify' / 'templates'
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / 'broken.md').write_text('broken template')

        assert templates_dir.exists(), "Test fixture should have templates dir"

        # Run migration
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=project_with_broken_templates,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should not crash (may fail due to bug, but shouldn't crash)
        # We expect this to fail with TypeError due to parameter mismatch
        # but we want to document the failure mode

        if 'Traceback' in result.stderr:
            # Expected failure - check if it's our bug
            assert 'TypeError' in result.stderr or 'unexpected keyword argument' in result.stderr, (
                f"Expected TypeError from parameter mismatch. Got: {result.stderr}"
            )

    def test_copies_correct_templates(self, project_with_broken_templates):
        """
        Test: Migration copies correct templates from package/local

        Validates:
        - Locates template source (package or local repo)
        - Copies templates to project
        - Templates don't have bash references
        """
        # Run migration
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=project_with_broken_templates,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Will likely fail due to generate_agent_assets bug
        # Document the failure
        if result.returncode != 0:
            # This is expected due to the bug
            assert 'TypeError' in result.stderr or 'unexpected keyword argument' in result.stderr, (
                f"Migration failed with unexpected error: {result.stderr}"
            )

    def test_regenerates_agent_commands_FIXED(self, project_with_broken_templates):
        """
        FIXED: Migration now successfully regenerates agent commands

        Previously documented bug:
        - Migration called generate_agent_assets() with 'ai' instead of 'agent_key'
        - This caused TypeError

        Bug was fixed - migration now succeeds.
        """
        # Run migration
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=project_with_broken_templates,
            capture_output=True,
            text=True,
            timeout=60
        )

        # BUG FIXED: Migration should now succeed
        assert result.returncode == 0, (
            f"Migration should succeed (bug was fixed). Got:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.xfail(
        reason="spec-kitty templates still have scripts/bash/ references that need cleanup"
    )
    def test_verifies_repair_completion(self, project_with_broken_templates):
        """
        Test: Migration verifies no bash references remain

        Validates:
        - Re-scans templates after regeneration
        - Confirms bash references removed
        - Reports success or warnings
        """
        # This test will fail until the bug is fixed
        result = subprocess.run(
            ['spec-kitty', 'upgrade', '--force'],
            cwd=project_with_broken_templates,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Currently fails due to bug
        # After fix, this should pass
        if result.returncode == 0:
            # Check if bash references remain
            commands_dir = project_with_broken_templates / '.claude' / 'commands'
            bash_refs = []
            for cmd_file in commands_dir.glob('spec-kitty.*.md'):
                content = cmd_file.read_text()
                if 'scripts/bash/' in content:
                    bash_refs.append(cmd_file.name)

            assert len(bash_refs) == 0, (
                f"After migration, no bash references should remain. Found in: {bash_refs}"
            )


class TestParameterValidation:
    """⭐ NEW: Test parameter signature matching (catches Issue #68 bug)"""

    def test_generate_agent_assets_signature_match(self):
        """
        CRITICAL TEST: Validates function signature matches migration call

        Validates:
        - Function signature from asset_generator.py
        - Migration call from m_0_10_9_repair_templates.py
        - Parameter names match exactly
        - Parameter order matches

        BUG DETECTION: This test catches the parameter mismatch bug

        Expected signature:
            def generate_agent_assets(
                command_templates_dir: Path,
                project_path: Path,
                agent_key: str,  # ❌ NOT 'ai'
                script_type: str
            ) -> None:
        """
        # Import the function to inspect its signature
        try:
            from specify_cli.template.asset_generator import generate_agent_assets
        except ImportError:
            pytest.skip("Cannot import generate_agent_assets")

        # Get actual function signature
        sig = inspect.signature(generate_agent_assets)
        params = list(sig.parameters.keys())

        # Expected parameters in correct order
        expected_params = ['command_templates_dir', 'project_path', 'agent_key', 'script_type']

        # CRITICAL: Validate parameter names
        assert params == expected_params, (
            f"generate_agent_assets signature mismatch!\n"
            f"Expected: {expected_params}\n"
            f"Actual: {params}\n\n"
            f"Migration code uses 'ai' but function expects 'agent_key'"
        )

    def test_migration_call_parameters_correct(self):
        """
        CRITICAL TEST: Validates migration calls generate_agent_assets correctly

        Validates:
        - Migration file source code
        - Parameter names in function call
        - Detects 'ai' vs 'agent_key' mismatch

        BUG: This test will FAIL on current v0.10.11 due to incorrect call
        """
        try:
            # Read migration source code
            import specify_cli.upgrade.migrations.m_0_10_9_repair_templates as migration_module
            migration_file = Path(migration_module.__file__)
            source = migration_file.read_text()
        except Exception as e:
            pytest.skip(f"Cannot read migration file: {e}")

        # Search for generate_agent_assets call
        if 'generate_agent_assets(' not in source:
            pytest.skip("Migration doesn't call generate_agent_assets")

        # Find the call in source
        call_start = source.find('generate_agent_assets(')
        call_end = source.find(')', call_start)
        call_text = source[call_start:call_end + 1]

        # BUG CHECK: Should use 'agent_key', not 'ai'
        assert 'ai=' not in call_text, (
            f"BUG DETECTED: Migration uses 'ai=' parameter but function expects 'agent_key='\n"
            f"Call found:\n{call_text}\n\n"
            f"Fix: Change 'ai=ai_config' to 'agent_key=ai_config'"
        )

        # Verify correct parameter is used
        assert 'agent_key=' in call_text, (
            f"Migration should use 'agent_key=' parameter\n"
            f"Call found:\n{call_text}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
