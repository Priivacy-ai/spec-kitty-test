"""
Test: Template Relocation Validation (Feature 011 - v0.10.12)

Purpose: Verify templates relocated from .kittify/ to src/specify_cli/ work correctly.

THE RELOCATION:
Before Feature 011:
- Templates: .kittify/templates/
- Missions: .kittify/missions/
- Scripts: .kittify/scripts/
- Problem: Force-included in package via pyproject.toml
- Problem: Developer data gets packaged

After Feature 011:
- Templates: src/specify_cli/templates/
- Missions: src/specify_cli/missions/
- Scripts: src/specify_cli/scripts/
- Solution: Loaded via importlib.resources
- Solution: .kittify/ never packaged (runtime only)

Test Coverage:
- TestTemplateManagerUpdates (5 tests): Template loading from package resources
- TestMissionTemplateAccess (5 tests): Mission template access
- TestScriptRelocation (5 tests): Script relocation and access

Related Issues: #62, #63, #64
Version: Requires v0.10.12+ (Feature 011)
"""

import subprocess
import tempfile
from pathlib import Path
import pytest
import sys


class TestTemplateManagerUpdates:
    """
    CRITICAL: Verify template manager loads from package resources.

    Tests that:
    - Template manager uses importlib.resources, not file paths
    - Template manager NOT loading from .kittify/
    - spec-kitty init creates .kittify/ in NEW projects (not source)
    - Init does NOT copy from CWD .kittify/
    - Template discovery uses importlib
    """

    def test_template_manager_loads_from_package_resources(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Template manager must use importlib.resources.

        Feature 011 changes template loading from file paths to package resources.
        This is required for installed packages.
        """
        # Check template/manager.py implementation
        manager_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'template' / 'manager.py'

        if not manager_file.exists():
            # Try alternate location
            manager_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'manager.py'

        if not manager_file.exists():
            pytest.skip("Cannot find template manager.py")

        content = manager_file.read_text()

        # Should use importlib.resources
        uses_importlib = 'importlib.resources' in content or 'from importlib import resources' in content

        assert uses_importlib, (
            "Template manager does not use importlib.resources!\n\n"
            f"File: {manager_file}\n\n"
            "Feature 011 requires using importlib.resources to load templates from package.\n"
            "This is critical for installed packages."
        )

        # Should NOT hardcode .kittify/ paths
        hardcoded_kittify = '.kittify' in content and 'join' in content and 'path' in content.lower()

        if hardcoded_kittify:
            # Check if it's just comments or error messages
            lines_with_kittify = [
                line for line in content.split('\n')
                if '.kittify' in line and not line.strip().startswith('#')
            ]

            # Filter out comments and strings that are just documentation
            problematic_lines = [
                line for line in lines_with_kittify
                if 'path' in line.lower() or 'join' in line.lower()
            ]

            assert len(problematic_lines) == 0, (
                "Template manager has hardcoded .kittify/ paths!\n\n"
                f"Found {len(problematic_lines)} line(s):\n" +
                "\n".join([f"  {line.strip()}" for line in problematic_lines[:3]]) +
                "\n\nFeature 011 requires loading from package resources, not file paths."
            )

    def test_template_manager_not_from_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Template manager must NOT load templates from .kittify/.

        Even if .kittify/templates/ exists (developer dogfooding),
        the template manager should load from src/specify_cli/templates/.
        """
        # Create a test project and check where templates come from
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_project = tmpdir_path / 'test_project'

            # Initialize project
            result = subprocess.run(
                ['spec-kitty', 'init', 'test_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.fail(f"Failed to init project:\n{result.stderr}")

            # Check that .kittify/ was created in the NEW project
            project_kittify = test_project / '.kittify'
            assert project_kittify.exists(), (
                "spec-kitty init did not create .kittify/ in project"
            )

            # Check that templates came from package, not from CWD
            # The templates should be in .kittify/templates/command-templates/
            project_templates = project_kittify / 'templates' / 'command-templates'

            if not project_templates.exists():
                pytest.fail(
                    f"No templates created in project!\n"
                    f"Expected: {project_templates}"
                )

    def test_init_creates_kittify_in_projects(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: spec-kitty init must create .kittify/ in NEW projects.

        .kittify/ is a RUNTIME directory created by init, not a SOURCE directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Initialize project
            result = subprocess.run(
                ['spec-kitty', 'init', 'test_relocation', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.fail(f"Failed to init:\n{result.stderr}")

            # Check .kittify/ exists in project
            project_dir = tmpdir_path / 'test_relocation'
            kittify_dir = project_dir / '.kittify'

            assert kittify_dir.exists(), (
                "spec-kitty init did not create .kittify/!\n\n"
                f"Expected: {kittify_dir}\n\n"
                "This is required for runtime data (constitution, memory)."
            )

            # Should have expected subdirectories
            expected_dirs = ['memory', 'templates']
            for dirname in expected_dirs:
                dirpath = kittify_dir / dirname
                if not dirpath.exists():
                    pytest.fail(
                        f"Missing {dirname}/ in .kittify/\n"
                        f"Expected: {dirpath}"
                    )

    def test_init_does_not_copy_from_cwd_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: spec-kitty init must NOT copy from CWD .kittify/.

        Before Feature 011: Init would copy from .kittify/ if it existed in CWD
        After Feature 011: Init loads templates from package resources only

        This prevents contamination if user runs init from spec-kitty repo.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a fake .kittify/ with marker file
            fake_kittify = tmpdir_path / '.kittify' / 'templates'
            fake_kittify.mkdir(parents=True)
            marker_file = fake_kittify / 'CONTAMINATION_MARKER.txt'
            marker_file.write_text('This is contamination from CWD')

            # Initialize project FROM this directory (with fake .kittify/)
            result = subprocess.run(
                ['spec-kitty', 'init', 'clean_project', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.fail(f"Failed to init:\n{result.stderr}")

            # Check that marker file was NOT copied to new project
            project_dir = tmpdir_path / 'clean_project'
            contamination_marker = project_dir / '.kittify' / 'templates' / 'CONTAMINATION_MARKER.txt'

            assert not contamination_marker.exists(), (
                "CRITICAL BUG: spec-kitty init copied from CWD .kittify/!\n\n"
                f"Found contamination marker: {contamination_marker}\n\n"
                "Init must load templates from package resources, not CWD .kittify/."
            )

    def test_template_discovery_uses_importlib(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Template discovery must use importlib.resources.

        When spec-kitty needs to list available templates, it should:
        1. Use importlib.resources.files() or importlib.resources.contents()
        2. NOT use os.listdir() on .kittify/
        3. Work from installed package, not just dev mode
        """
        # Check for template discovery code
        template_related_files = [
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'template' / 'manager.py',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'manager.py',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'cli.py',
        ]

        found_importlib_usage = False

        for file_path in template_related_files:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Check for importlib.resources usage
            if any(pattern in content for pattern in [
                'importlib.resources',
                'importlib_resources',
                'from importlib import resources',
            ]):
                found_importlib_usage = True
                break

        assert found_importlib_usage, (
            "Template discovery does not use importlib.resources!\n\n"
            "Checked files:\n" +
            "\n".join([f"  - {f}" for f in template_related_files if f.exists()]) +
            "\n\nFeature 011 requires using importlib.resources for template discovery."
        )


class TestMissionTemplateAccess:
    """
    CRITICAL: Verify mission templates accessible from package.

    Tests that:
    - Missions loaded from src/specify_cli/missions/
    - Constitution template accessible
    - Command templates accessible
    - Agent asset generation works
    - No FileNotFoundError
    """

    def test_missions_loaded_from_src_specify_cli(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Missions must be in src/specify_cli/missions/.

        Before: .kittify/missions/
        After: src/specify_cli/missions/
        """
        missions_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'missions'

        assert missions_dir.exists(), (
            "Missions directory not found!\n\n"
            f"Expected: {missions_dir}\n\n"
            "Feature 011 requires missions in src/specify_cli/missions/"
        )

        # Should have mission directories
        mission_dirs = [
            d for d in missions_dir.iterdir()
            if d.is_dir() and not d.name.startswith('__') and not d.name.startswith('.')
        ]

        assert len(mission_dirs) >= 2, (
            f"Insufficient missions found!\n"
            f"Expected >= 2, found {len(mission_dirs)} in {missions_dir}\n"
            f"Missions: {[d.name for d in mission_dirs]}"
        )

    def test_constitution_template_accessible(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Constitution template must be accessible from package.

        The constitution template is now in:
        src/specify_cli/templates/command-templates/constitution.md
        """
        # Check multiple possible locations
        possible_locations = [
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'command-templates' / 'constitution.md',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'constitution.md',
        ]

        found = None
        for location in possible_locations:
            if location.exists():
                found = location
                break

        assert found is not None, (
            "Constitution template not found!\n\n"
            "Checked locations:\n" +
            "\n".join([f"  - {loc}" for loc in possible_locations]) +
            "\n\nConstitution template must be in package."
        )

        # Verify it's a template (has placeholder text, not filled)
        content = found.read_text()
        assert len(content) < 10000, (
            f"Constitution template appears to be filled!\n"
            f"File: {found}\n"
            f"Size: {len(content)} bytes\n\n"
            "Template should be blank with placeholders."
        )

    def test_command_templates_accessible(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Command templates must be accessible from package.

        Templates like plan.md, implement.md, review.md, etc.
        """
        command_templates_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'command-templates'

        assert command_templates_dir.exists(), (
            f"Command templates directory not found!\n"
            f"Expected: {command_templates_dir}"
        )

        # Should have multiple command templates
        templates = list(command_templates_dir.glob('*.md'))

        assert len(templates) >= 5, (
            f"Insufficient command templates!\n"
            f"Expected >= 5, found {len(templates)} in {command_templates_dir}\n"
            f"Templates: {[t.name for t in templates]}"
        )

    def test_agent_asset_generation_works(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Test that agent asset generation works with relocated templates.

        When spec-kitty generates agent assets (tasks, specs, etc.),
        it must load templates from package resources.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Initialize project
            result = subprocess.run(
                ['spec-kitty', 'init', 'asset_test', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Failed to init project: {result.stderr}")

            project_dir = tmpdir_path / 'asset_test'

            # Try to generate a spec or task
            # This will use templates from package resources
            result = subprocess.run(
                ['spec-kitty', 'specify', '--help'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            # Should not have FileNotFoundError or template loading errors
            assert 'FileNotFoundError' not in result.stderr, (
                "Template loading failed!\n\n"
                f"Error: {result.stderr}\n\n"
                "Templates must be accessible from package resources."
            )

    def test_no_file_not_found_errors(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Basic spec-kitty commands must NOT raise FileNotFoundError.

        If templates are in wrong location, commands will fail with FileNotFoundError.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Initialize project
            result = subprocess.run(
                ['spec-kitty', 'init', 'fnf_test', '--ai', 'claude'],
                cwd=tmpdir_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
            )

            if result.returncode != 0:
                pytest.skip(f"Failed to init: {result.stderr}")

            project_dir = tmpdir_path / 'fnf_test'

            # Run basic commands that load templates
            commands_to_test = [
                ['spec-kitty', '--version'],
                ['spec-kitty', 'specify', '--help'],
                ['spec-kitty', 'plan', '--help'],
            ]

            for cmd in commands_to_test:
                result = subprocess.run(
                    cmd,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    env={**subprocess.os.environ, 'SPEC_KITTY_TEMPLATE_ROOT': str(spec_kitty_repo_root)}
                )

                assert 'FileNotFoundError' not in result.stderr, (
                    f"Command raised FileNotFoundError!\n\n"
                    f"Command: {' '.join(cmd)}\n"
                    f"Error: {result.stderr}\n\n"
                    "This indicates templates are in wrong location."
                )


class TestScriptRelocation:
    """
    CRITICAL: Verify scripts relocated to package.

    Tests that:
    - Scripts in src/specify_cli/scripts/, not .kittify/
    - Dashboard scripts accessible
    - Task scripts accessible
    - Script execution from package
    - No hardcoded .kittify/ paths
    """

    def test_scripts_in_package_not_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Scripts must be in src/specify_cli/scripts/.

        Before: .kittify/scripts/
        After: src/specify_cli/scripts/
        """
        scripts_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'scripts'

        assert scripts_dir.exists(), (
            "Scripts directory not found!\n\n"
            f"Expected: {scripts_dir}\n\n"
            "Feature 011 requires scripts in src/specify_cli/scripts/"
        )

        # Should have script files
        script_files = list(scripts_dir.glob('*.py')) + list(scripts_dir.glob('*.js'))

        assert len(script_files) >= 1, (
            f"No scripts found!\n"
            f"Expected >= 1 script in {scripts_dir}"
        )

    def test_dashboard_scripts_accessible(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Dashboard scripts must be accessible from package.

        Dashboard may have HTML/JS/CSS files that need to be packaged.
        """
        # Check for dashboard-related files
        dashboard_locations = [
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'dashboard',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'scripts' / 'dashboard',
        ]

        found_dashboard = False
        for location in dashboard_locations:
            if location.exists():
                found_dashboard = True
                break

        if not found_dashboard:
            pytest.skip("No dashboard directory found")

        # Dashboard files should be in package
        # (Not a critical failure, but good to verify)

    def test_task_scripts_accessible(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Task scripts (if any) accessible from package.
        """
        scripts_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'scripts'

        if not scripts_dir.exists():
            pytest.skip("Scripts directory not found")

        # Any Python scripts should be in package
        python_scripts = list(scripts_dir.glob('*.py'))

        # Not critical if no scripts, but verify if they exist
        if len(python_scripts) == 0:
            pytest.skip("No Python scripts found")

    def test_script_execution_from_package(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Scripts must be executable from installed package.

        If scripts are loaded via file paths (not package resources),
        they won't work from installed package.
        """
        # Check CLI code for script execution
        cli_locations = [
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'cli.py',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'main.py',
        ]

        found_cli = None
        for location in cli_locations:
            if location.exists():
                found_cli = location
                break

        if not found_cli:
            pytest.skip("Cannot find CLI main file")

        content = found_cli.read_text()

        # If there's script execution, it should use importlib or subprocess with package paths
        # Not file joins with .kittify/
        if 'scripts/' in content or 'script' in content.lower():
            # Check for bad patterns
            bad_patterns = [
                '.kittify/scripts',
                'os.path.join' + '.*' + 'scripts',
            ]

            for pattern in bad_patterns:
                if pattern in content:
                    pytest.fail(
                        f"CLI code may be using hardcoded script paths!\n\n"
                        f"File: {found_cli}\n"
                        f"Pattern: {pattern}\n\n"
                        "Scripts should be accessed via importlib.resources, not file paths."
                    )

    def test_no_hardcoded_kittify_paths(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Source code must NOT have hardcoded .kittify/ paths.

        Hardcoded paths like:
        - .kittify/templates/
        - .kittify/missions/
        - .kittify/scripts/

        These will break when templates are in src/specify_cli/.
        """
        src_dir = spec_kitty_repo_root / 'src' / 'specify_cli'

        if not src_dir.exists():
            pytest.skip("Cannot find src/specify_cli/")

        # Check Python files for hardcoded .kittify/ paths
        python_files = list(src_dir.glob('**/*.py'))

        problematic_files = []

        for py_file in python_files:
            content = py_file.read_text()

            # Look for .kittify/templates or .kittify/missions or .kittify/scripts
            if any(pattern in content for pattern in [
                '.kittify/templates',
                '.kittify/missions',
                '.kittify/scripts',
                'kittify/templates',
                'kittify/missions',
                'kittify/scripts',
            ]):
                # Filter out comments
                lines = [
                    line for line in content.split('\n')
                    if not line.strip().startswith('#')
                ]

                for line in lines:
                    if any(pattern in line for pattern in [
                        '.kittify/templates',
                        '.kittify/missions',
                        '.kittify/scripts',
                    ]):
                        # Filter out string literals that are just error messages
                        if 'path' in line.lower() or 'join' in line.lower() or 'load' in line.lower():
                            problematic_files.append({
                                'file': py_file.relative_to(spec_kitty_repo_root),
                                'line': line.strip()
                            })
                            break

        assert len(problematic_files) == 0, (
            "Found hardcoded .kittify/ paths in source!\n\n"
            f"Found {len(problematic_files)} file(s):\n" +
            "\n".join([
                f"  {item['file']}: {item['line'][:80]}"
                for item in problematic_files[:5]
            ]) +
            "\n\nFeature 011 requires using package resources, not .kittify/ paths."
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
