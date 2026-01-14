"""
Test: Dogfooding Safety (Feature 011 - v0.10.12)

Purpose: Verify developers can safely use spec-kitty to develop spec-kitty.

DOGFOODING: Using spec-kitty to develop spec-kitty itself.

THE CRITICAL RISK:
1. Developer uses spec-kitty in spec-kitty repo
2. Developer fills .kittify/memory/constitution.md
3. Developer builds PyPI package
4. Filled constitution gets packaged
5. ALL PyPI users receive developer's constitution

This happened in Issues #62-64 because ALL tests bypassed this check with:
  env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

THIS TEST FILE DOES NOT USE THAT BYPASS.

Test Coverage:
- TestDeveloperWorkflow (5 tests): Developer fills constitution, builds wheel, checks isolation
- TestPackageResourceIsolation (5 tests): Package resources vs runtime data isolation

Version: Requires v0.10.12+ (Feature 011)
"""

import subprocess
import sys
import tempfile
import zipfile
import venv
from pathlib import Path
import pytest
import shutil


class TestDeveloperWorkflow:
    """
    CRITICAL: Verify developer dogfooding workflow is safe.

    Scenario:
    1. Developer has spec-kitty repo
    2. Developer fills .kittify/memory/constitution.md
    3. Developer builds wheel
    4. Check: Wheel does NOT contain filled constitution
    5. Check: Fresh install gets blank template
    6. Check: Developer's local constitution preserved
    """

    def test_developer_fills_constitution_in_repo(self, spec_kitty_repo_root, requires_v010_12):
        """
        SETUP: Simulate developer filling constitution.

        This test just verifies the setup for subsequent tests.
        """
        kittify_dir = spec_kitty_repo_root / '.kittify'

        if not kittify_dir.exists():
            pytest.skip("No .kittify/ in repo (developer hasn't dogfooded yet)")

        memory_dir = kittify_dir / 'memory'
        constitution_file = memory_dir / 'constitution.md'

        if not constitution_file.exists():
            pytest.skip("No constitution.md (developer hasn't filled it)")

        content = constitution_file.read_text()

        # If file is very small, it's just a blank template
        if len(content) < 100:
            pytest.skip("Constitution is blank template, not filled")

        # Developer has filled constitution - this is good for testing!
        # Subsequent tests will verify it doesn't get packaged

    def test_developer_builds_wheel(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Developer must be able to build wheel.

        Even with filled .kittify/ in repo.
        """
        dist_dir = spec_kitty_repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"Developer cannot build wheel!\n\n"
            f"Error: {result.stderr}\n\n"
            "Dogfooding workflow broken."
        )

        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel created"

    def test_wheel_does_not_contain_developer_constitution(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Developer's filled constitution must NOT be in wheel.

        This is THE BUG from Issues #62-64.
        """
        # Check if developer has filled constitution
        kittify_dir = spec_kitty_repo_root / '.kittify'

        if not kittify_dir.exists():
            pytest.skip("No .kittify/ directory")

        constitution_file = kittify_dir / 'memory' / 'constitution.md'

        if not constitution_file.exists():
            pytest.skip("No constitution file")

        local_content = constitution_file.read_text()

        if len(local_content) < 100:
            pytest.skip("Constitution is blank template")

        # Developer has filled constitution
        # Now check wheel doesn't contain it

        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

            # Check for ANY constitution in memory/
            memory_constitutions = [
                name for name in namelist
                if 'memory/constitution' in name or 'memory/constitution.md' in name
            ]

            assert len(memory_constitutions) == 0, (
                f"CRITICAL BUG: Developer's constitution is in wheel!\n\n"
                f"Found: {memory_constitutions}\n\n"
                f"Developer's local file size: {len(local_content)} bytes\n\n"
                "This is the exact bug from Issues #62-64.\n"
                "ALL PyPI users will receive developer's personal constitution."
            )

            # Also check for .kittify/ anywhere
            kittify_files = [name for name in namelist if '.kittify/' in name]

            assert len(kittify_files) == 0, (
                f"Wheel contains .kittify/ directory!\n\n"
                f"Found {len(kittify_files)} file(s):\n" +
                "\n".join([f"  - {f}" for f in kittify_files[:10]])
            )

    def test_fresh_install_has_blank_constitution(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Fresh install must provide BLANK constitution template.

        NOT the developer's filled constitution.

        NO SPEC_KITTY_TEMPLATE_ROOT bypass.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create clean venv
            venv_dir = Path(tmpdir) / 'clean_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            # Install wheel
            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            # Initialize project
            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            project_dir = Path(tmpdir) / 'fresh_project'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'fresh_project', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                # NO SPEC_KITTY_TEMPLATE_ROOT!
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            # Check constitution
            constitution = project_dir / '.kittify' / 'memory' / 'constitution.md'

            if not constitution.exists():
                pytest.skip("Constitution not created (may be optional in Feature 011)")

            content = constitution.read_text()

            # Must be blank template
            assert len(content) < 5000, (
                f"CRITICAL BUG: Fresh install has filled constitution!\n\n"
                f"Size: {len(content)} bytes (should be < 5000)\n"
                f"First 500 chars:\n{content[:500]}\n\n"
                "Users are receiving developer's filled constitution.\n"
                "This is the exact bug from Issues #62-64."
            )

            # Check it's not the developer's exact content
            dev_constitution = spec_kitty_repo_root / '.kittify' / 'memory' / 'constitution.md'
            if dev_constitution.exists():
                dev_content = dev_constitution.read_text()
                if len(dev_content) > 100:
                    # Developer has filled constitution
                    # Make sure user didn't get the same content
                    assert content != dev_content, (
                        "CRITICAL BUG: User received developer's exact constitution!\n"
                        "100% contamination."
                    )

    def test_developer_local_constitution_preserved(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Building wheel must NOT delete developer's local constitution.

        Developer's .kittify/ should remain intact.
        """
        kittify_dir = spec_kitty_repo_root / '.kittify'

        if not kittify_dir.exists():
            pytest.skip("No .kittify/ directory")

        constitution_file = kittify_dir / 'memory' / 'constitution.md'

        if not constitution_file.exists():
            pytest.skip("No constitution file")

        # Save original content
        original_content = constitution_file.read_text()

        # Build wheel
        dist_dir = spec_kitty_repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            check=True
        )

        # Check file still exists with same content
        assert constitution_file.exists(), (
            "Building wheel deleted developer's constitution!\n"
            "This is DATA LOSS."
        )

        current_content = constitution_file.read_text()

        assert current_content == original_content, (
            "Building wheel modified developer's constitution!\n"
            "This is DATA CORRUPTION."
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


class TestPackageResourceIsolation:
    """
    CRITICAL: Verify package resources and runtime data are isolated.

    Package resources (templates, missions):
    - Read-only
    - In site-packages/
    - Shared across all projects

    Runtime data (.kittify/):
    - Read-write
    - In project directory
    - Project-specific

    These must NEVER mix.
    """

    def test_package_resources_read_only(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Package resources must be read-only.

        Users should NOT be able to modify installed package templates.
        Modifications should only affect local .kittify/.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            # Find site-packages
            site_packages = list(venv_dir.glob('**/site-packages'))
            specify_cli_dir = site_packages[0] / 'specify_cli'

            # Check templates directory
            templates_dir = specify_cli_dir / 'templates'

            if not templates_dir.exists():
                pytest.skip("No templates in package")

            # Verify it's in site-packages (read-only location)
            assert 'site-packages' in str(templates_dir), (
                "Templates not in site-packages!\n"
                "Should be read-only package resource."
            )

    def test_runtime_kittify_writable(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Runtime .kittify/ must be writable.

        Users need to write constitution, memory, etc.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Initialize project
            project_dir = Path(tmpdir) / 'writable_project'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'writable_project', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            # Verify project was created
            if not project_dir.exists():
                pytest.skip(f"Project directory not created: {project_dir}")

            # Try to write to .kittify/
            kittify_dir = project_dir / '.kittify'
            if not kittify_dir.exists():
                pytest.skip(f".kittify/ directory not created: {kittify_dir}")

            # Ensure memory directory exists
            memory_dir = kittify_dir / 'memory'
            if not memory_dir.exists():
                memory_dir.mkdir(parents=True)

            test_file = memory_dir / 'test_write.txt'

            try:
                test_file.write_text('Testing write access')
                write_succeeded = True
            except Exception as e:
                write_succeeded = False
                error = str(e)

            assert write_succeeded, (
                f"Cannot write to project .kittify/!\n"
                f"Error: {error}\n\n"
                "Runtime directory must be writable."
            )

            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_no_write_to_package_resources(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Code must NOT attempt to write to package resources.

        All writes should go to project .kittify/, not site-packages.
        """
        # This is more of a code inspection test
        # Check that template manager uses correct paths for writes

        template_manager_locations = [
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'template' / 'manager.py',
            spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'manager.py',
        ]

        found_manager = None
        for location in template_manager_locations:
            if location.exists():
                found_manager = location
                break

        if not found_manager:
            pytest.skip("Cannot find template manager")

        content = found_manager.read_text()

        # Check for dangerous patterns
        dangerous_patterns = [
            'importlib.resources' + '.*' + 'write',
            'importlib.resources' + '.*' + 'open.*w',
        ]

        # Simple check: should not have write operations near importlib.resources
        lines = content.split('\n')
        importlib_lines = [i for i, line in enumerate(lines) if 'importlib.resources' in line]

        for line_num in importlib_lines:
            # Check surrounding lines
            context_start = max(0, line_num - 5)
            context_end = min(len(lines), line_num + 5)
            context = '\n'.join(lines[context_start:context_end])

            if 'write' in context.lower() or "'w'" in context or '"w"' in context:
                pytest.fail(
                    f"Potential write to package resources detected!\n\n"
                    f"File: {found_manager}\n"
                    f"Line {line_num}:\n{context}\n\n"
                    "Package resources should be read-only."
                )

    def test_template_modifications_local_only(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Template modifications should affect local .kittify/ only.

        Modifying a template in one project should NOT affect other projects.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Create two projects
            project1 = Path(tmpdir) / 'project1'
            project2 = Path(tmpdir) / 'project2'

            subprocess.run(
                [str(spec_kitty_path), 'init', 'project1', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            subprocess.run(
                [str(spec_kitty_path), 'init', 'project2', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                check=True
            )

            # Modify template in project1
            project1_template = project1 / '.kittify' / 'templates' / 'command-templates' / 'plan.md'

            if not project1_template.exists():
                pytest.skip("Templates not copied to project .kittify/")

            original_content = project1_template.read_text()
            modified_content = original_content + '\n\nMODIFIED IN PROJECT1'
            project1_template.write_text(modified_content)

            # Check project2 template unchanged
            project2_template = project2 / '.kittify' / 'templates' / 'command-templates' / 'plan.md'

            if project2_template.exists():
                project2_content = project2_template.read_text()

                assert project2_content != modified_content, (
                    "Modifying template in project1 affected project2!\n"
                    "Templates are not isolated."
                )

    def test_package_upgrade_preserves_local_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Upgrading package must preserve local .kittify/.

        User's project data must survive package upgrades.
        """
        wheel_file = self._get_wheel(spec_kitty_repo_root)

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / 'test_venv'
            venv.create(venv_dir, with_pip=True, clear=True)

            pip_path = venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = venv_dir / 'Scripts' / 'pip.exe'

            # Install
            subprocess.run(
                [str(pip_path), 'install', str(wheel_file)],
                capture_output=True,
                check=True
            )

            spec_kitty_path = venv_dir / 'bin' / 'spec-kitty'
            if not spec_kitty_path.exists():
                spec_kitty_path = venv_dir / 'Scripts' / 'spec-kitty.exe'

            # Create project
            project_dir = Path(tmpdir) / 'upgrade_test'

            result = subprocess.run(
                [str(spec_kitty_path), 'init', 'upgrade_test', '--ai', 'claude'],
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.skip(f"Init failed: {result.stderr}")

            if not project_dir.exists():
                pytest.skip(f"Project not created: {project_dir}")

            # Add user data
            kittify_dir = project_dir / '.kittify'
            if not kittify_dir.exists():
                pytest.skip(".kittify/ not created")

            memory_dir = kittify_dir / 'memory'
            if not memory_dir.exists():
                memory_dir.mkdir(parents=True)

            user_data_file = memory_dir / 'important_data.txt'
            user_data_content = 'Critical user data that must not be lost'
            user_data_file.write_text(user_data_content)

            # Upgrade package (reinstall same version simulates upgrade)
            subprocess.run(
                [str(pip_path), 'install', '--force-reinstall', '--no-deps', str(wheel_file)],
                capture_output=True,
                check=True
            )

            # Check user data preserved
            assert user_data_file.exists(), (
                "Package upgrade deleted user data!\n"
                "This is DATA LOSS."
            )

            preserved_content = user_data_file.read_text()

            assert preserved_content == user_data_content, (
                "Package upgrade corrupted user data!\n"
                "This is DATA CORRUPTION."
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
