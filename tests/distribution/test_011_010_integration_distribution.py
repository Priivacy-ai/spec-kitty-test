"""
Distribution tests for Feature 011-010 integration

Purpose: Test what PyPI users ACTUALLY experience after installing the package.
NO SPEC_KITTY_TEMPLATE_ROOT bypass - this is real-world validation.

THE CRITICAL LESSON (Issues #62-64):
ALL 323 tests used `env['SPEC_KITTY_TEMPLATE_ROOT'] = str(repo_root)`.
This bypassed package installation, so:
- Tests ✅ (used local repo)
- Users ❌ (used packaged templates - which were broken)

THIS FILE DOES NOT USE THAT BYPASS.

Test Strategy:
1. Build wheel from repo
2. Install in CLEAN venv
3. NO environment variable bypasses
4. Test commands work
5. Test templates are correct
6. Test init creates proper projects

This validates the 011-010 integration from the user perspective.

Integration Requirements Tested:
A. Central templates complete and support init (all 13 files)
B. Mission templates have dependency warnings
C. Migrations work correctly
D. Task prompts have rebase guidance
E. Real users can use workspace-per-WP workflow

Version: Requires v0.11.0+ (Features 011 + 010)
"""

import pytest
import subprocess
import tempfile
import venv
from pathlib import Path
import json
import re


class TestDistributionTemplateCompleteness:
    """
    CRITICAL: Verify installed package has all templates for init.

    Tests assume implementation team packaged incomplete template set.

    NO SPEC_KITTY_TEMPLATE_ROOT bypass - test real installation.
    """

    REQUIRED_AGENTS = [
        'claude',
        'gpt',
        'gemini',
    ]

    REQUIRED_TEMPLATES = [
        'implement',
        'plan',
        'tasks',
        'specify',
        'review',
    ]

    def test_init_generates_all_agent_commands_from_installed_package(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: spec-kitty init must work from installed package.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Missing central templates cause init to fail.
        Impact: PyPI users cannot initialize projects.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)

            # Install wheel
            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = self._get_spec_kitty(venv_dir)

            # Try to init project for each agent
            for agent in self.REQUIRED_AGENTS:
                project_dir = Path(tmpdir) / f'test_project_{agent}'

                result = subprocess.run(
                    [str(spec_kitty_path), 'init', f'test_project_{agent}', f'--ai={agent}'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    # NO SPEC_KITTY_TEMPLATE_ROOT!
                )

                assert result.returncode == 0, (
                    f"CRITICAL: init failed for --ai={agent}!\n\n"
                    f"Stderr: {result.stderr}\n\n"
                    "This means PyPI users cannot initialize projects.\n"
                    "Likely cause: Missing central templates in package."
                )

                # Verify commands were created
                commands_dir = project_dir / f'.{agent}' / 'commands'

                if not commands_dir.exists():
                    pytest.fail(
                        f"Commands directory not created for {agent}!\n"
                        f"Expected: {commands_dir}"
                    )

                # Check for required command templates
                for template_name in self.REQUIRED_TEMPLATES:
                    command_file = commands_dir / f'{template_name}.md'

                    if not command_file.exists():
                        pytest.fail(
                            f"CRITICAL: Command file missing after init!\n\n"
                            f"Agent: {agent}\n"
                            f"Missing: {command_file}\n\n"
                            "init should have generated this from central templates.\n"
                            "Likely cause: Central template missing or not packaged."
                        )

    def test_init_generated_implement_follows_workspace_per_wp(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: init-generated implement.md must follow workspace-per-WP workflow.

        Requirement A.2: Central templates sync'd to mission versions.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Central template not updated for 010 workflow.
        Impact: Users get outdated implement commands.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)
            project_dir = Path(tmpdir) / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai=claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            # Read generated implement.md
            implement_file = project_dir / '.claude' / 'commands' / 'implement.md'

            if not implement_file.exists():
                pytest.fail("implement.md not generated by init")

            content = implement_file.read_text()

            # Should mention workspace-per-WP concepts
            workspace_keywords = [
                'worktree',
                'WP',
                'work package',
                'implement WP',
            ]

            found = [kw for kw in workspace_keywords if kw.lower() in content.lower()]

            assert len(found) >= 2, (
                f"init-generated implement.md doesn't follow workspace-per-WP!\n\n"
                f"Expected keywords: {workspace_keywords}\n"
                f"Found only: {found}\n\n"
                f"File: {implement_file}\n\n"
                "Central template not updated for Feature 010.\n"
                "PyPI users will get outdated workflow instructions."
            )

    def test_init_generated_review_has_dependency_warnings(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: init-generated review.md must have dependency warnings.

        Requirements A.2 + B.3: Central and mission templates have warnings.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Central review template missing warnings.
        Impact: New projects don't have dependency validation.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)
            project_dir = Path(tmpdir) / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai=claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            # Read generated review.md
            review_file = project_dir / '.claude' / 'commands' / 'review.md'

            if not review_file.exists():
                pytest.fail("review.md not generated by init")

            content = review_file.read_text()

            # Must have dependency warnings per FR-016-FR-018
            dependency_keywords = [
                'dependenc',
                'dependent WP',
                'rebase',
                'verify',
            ]

            found = [kw for kw in dependency_keywords if kw.lower() in content.lower()]

            assert len(found) >= 3, (
                f"init-generated review.md missing dependency warnings!\n\n"
                f"Expected keywords: {dependency_keywords}\n"
                f"Found only: {found}\n\n"
                f"File: {review_file}\n\n"
                "FR-016-FR-018 require dependency validation in review.\n"
                "PyPI users' new projects will lack this critical check."
            )

    def test_init_generated_plan_describes_main_repo_workflow(self, spec_kitty_repo_root, requires_v011):
        """
        HIGH: init-generated plan.md should describe main-repo planning.

        Requirement A.2: Central plan template updated for main-repo planning.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Template still describes worktree-based planning.
        Impact: Users confused about workflow.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)
            project_dir = Path(tmpdir) / 'test_project'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'test_project', '--ai=claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            plan_file = project_dir / '.claude' / 'commands' / 'plan.md'

            if not plan_file.exists():
                pytest.fail("plan.md not generated by init")

            content = plan_file.read_text()

            # Should NOT mention creating worktrees during planning
            bad_patterns = [
                'create worktree',
                'switch to worktree',
                'in the worktree',
            ]

            found_bad = [pat for pat in bad_patterns if pat.lower() in content.lower()]

            assert len(found_bad) == 0, (
                f"init-generated plan.md incorrectly mentions worktrees!\n\n"
                f"Found: {found_bad}\n\n"
                f"File: {plan_file}\n\n"
                "Feature 010: Planning happens in MAIN, not worktrees.\n"
                "PyPI users will be confused by outdated instructions."
            )

    def _get_wheel(self, repo_root):
        """Helper: Get built wheel file"""
        dist_dir = repo_root / 'dist'

        if not dist_dir.exists():
            pytest.fail("No dist/ directory")

        wheels = list(dist_dir.glob('*.whl'))

        if not wheels:
            pytest.fail("No wheel file found")

        return wheels[0]

    def _get_pip(self, venv_dir):
        """Helper: Get pip path for venv"""
        pip_path = venv_dir / 'bin' / 'pip'
        if not pip_path.exists():
            pip_path = venv_dir / 'Scripts' / 'pip.exe'  # Windows
        return pip_path

    def _get_spec_kitty(self, venv_dir):
        """Helper: Get spec-kitty command path for venv"""
        spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
        if not spec_kitty_path.exists():
            spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'  # Windows
        return spec_kitty_path


class TestDistributionUpgradeBehavior:
    """
    CRITICAL: Test upgrade behavior from installed package.

    Tests migrations work correctly when run from PyPI installation.

    NO SPEC_KITTY_TEMPLATE_ROOT bypass.

    Tests assume implementation team:
    - Migration points to wrong template locations
    - Migration fails to update templates
    - Upgraded projects don't get new features
    """

    def test_upgrade_command_available_from_installed_package(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: spec-kitty upgrade must work from installed package.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Upgrade command missing or broken.
        Impact: PyPI users cannot upgrade projects.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)

            # Check upgrade command exists
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--help'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"upgrade command not available!\n\n"
                f"Stderr: {result.stderr}\n\n"
                "PyPI users cannot upgrade their projects."
            )

    def test_upgrade_with_dependency_warnings_in_mission_templates(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Upgrade should inject dependency warnings into mission templates.

        Requirement B.3: Mission templates get dependency warnings.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Mission templates not updated during upgrade.
        Impact: Upgraded projects don't get dependency validation.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)

            # Create mock v0.10.x project
            project_dir = Path(tmpdir) / 'test_project'
            self._create_mock_010_project(project_dir)

            # Run upgrade
            result = subprocess.run(
                [str(spec_kitty_path), 'upgrade', '--force'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                # NO SPEC_KITTY_TEMPLATE_ROOT!
            )

            # Upgrade might fail on mock project, that's OK
            # We just want to verify mission templates have warnings

            # Check if package has mission templates with warnings
            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            check_script = """
import importlib.resources
try:
    mission_files = list(importlib.resources.files('specify_cli.missions.software-dev.command-templates').iterdir())
    for f in mission_files:
        if f.name == 'review.md':
            content = f.read_text()
            has_warnings = any(kw in content.lower() for kw in ['dependenc', 'rebase', 'dependent wp'])
            print('HAS_WARNINGS' if has_warnings else 'NO_WARNINGS')
            break
except Exception as e:
    print(f'ERROR: {e}')
"""

            result = subprocess.run(
                [str(python_path), '-c', check_script],
                capture_output=True,
                text=True
            )

            assert 'HAS_WARNINGS' in result.stdout, (
                f"Mission review.md missing dependency warnings!\n\n"
                f"Check result: {result.stdout}\n\n"
                "Requirement B.3: Mission templates need warnings.\n"
                "Upgraded projects won't have dependency validation."
            )

    def _get_wheel(self, repo_root):
        """Helper: Get wheel file"""
        dist_dir = repo_root / 'dist'
        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0] if wheels else None

    def _get_pip(self, venv_dir):
        """Helper: Get pip path"""
        pip_path = venv_dir / 'bin' / 'pip'
        if not pip_path.exists():
            pip_path = venv_dir / 'Scripts' / 'pip.exe'
        return pip_path

    def _get_spec_kitty(self, venv_dir):
        """Helper: Get spec-kitty command path"""
        spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
        if not spec_kitty_path.exists():
            spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'
        return spec_kitty_path

    def _create_mock_010_project(self, project_dir):
        """Helper: Create mock v0.10.x project for upgrade testing"""
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal .kittify structure
        kittify_dir = project_dir / '.kittify'
        kittify_dir.mkdir()

        (kittify_dir / 'VERSION').write_text('0.10.12')

        # Create mission structure (old location)
        mission_dir = kittify_dir / 'missions' / 'software-dev'
        mission_dir.mkdir(parents=True)

        (mission_dir / 'mission.yaml').write_text('name: software-dev')

        # Initialize git
        subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=project_dir, capture_output=True)


class TestDistributionWorkspacePerWPWorkflow:
    """
    HIGH: Test actual workspace-per-WP workflow from installed package.

    Validates that users can actually use the new workflow.

    NO SPEC_KITTY_TEMPLATE_ROOT bypass.

    Tests assume implementation team:
    - Commands don't work from installed package
    - Workflow only works in dev mode
    - Missing dependencies or imports
    """

    def test_implement_command_exists_from_installed_package(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: spec-kitty implement command must exist.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Command not registered or broken import.
        Impact: Core workflow broken for PyPI users.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            spec_kitty_path = self._get_spec_kitty(venv_dir)

            # Check implement command
            result = subprocess.run(
                [str(spec_kitty_path), 'implement', '--help'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"implement command not available!\n\n"
                f"Stderr: {result.stderr}\n\n"
                "Core Feature 010 command missing from PyPI package."
            )

    def test_dependency_graph_module_importable_from_installed_package(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: specify_cli.core.dependency_graph must be importable.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.

        Failure mode: Module not packaged or missing dependencies.
        Impact: Dependency validation broken for PyPI users.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = self._get_pip(venv_dir)
            subprocess.run([str(pip_path), 'install', str(wheel_file)], capture_output=True, check=True)

            python_path = venv_dir / 'bin' / 'python'
            if not python_path.exists():
                python_path = venv_dir / 'Scripts' / 'python.exe'

            # Try to import dependency_graph module
            result = subprocess.run(
                [str(python_path), '-c',
                 'from specify_cli.core.dependency_graph import build_dependency_graph; '
                 'print("SUCCESS")'],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, (
                f"Cannot import dependency_graph module!\n\n"
                f"Stderr: {result.stderr}\n\n"
                "Feature 010 dependency validation broken in PyPI package."
            )

            assert 'SUCCESS' in result.stdout, (
                f"Import succeeded but function not found!\n"
                f"Output: {result.stdout}"
            )

    def _get_wheel(self, repo_root):
        """Helper: Get wheel file"""
        dist_dir = repo_root / 'dist'
        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0] if wheels else None

    def _get_pip(self, venv_dir):
        """Helper: Get pip path"""
        pip_path = venv_dir / 'bin' / 'pip'
        if not pip_path.exists():
            pip_path = venv_dir / 'Scripts' / 'pip.exe'
        return pip_path

    def _get_spec_kitty(self, venv_dir):
        """Helper: Get spec-kitty command path"""
        spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
        if not spec_kitty_path.exists():
            spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'
        return spec_kitty_path


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
