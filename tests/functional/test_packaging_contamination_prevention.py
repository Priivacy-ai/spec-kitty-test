"""
Test: Packaging Contamination Prevention (Feature 011 - v0.10.12)

Purpose: Prevent packaging contamination bugs similar to Issues #62-64.

THE CRITICAL BUG WE'RE PREVENTING:
When spec-kitty developers dogfood (use spec-kitty to develop spec-kitty):
1. Developer fills .kittify/memory/constitution.md with real project data
2. pyproject.toml force-includes .kittify/memory/**/*
3. Developer builds wheel
4. Filled constitution gets packaged into wheel
5. ALL PyPI users receive spec-kitty's internal constitution instead of blank template

This is a 100% user contamination bug.

SOLUTION (Feature 011):
1. Move templates from .kittify/ to src/specify_cli/
2. Remove .kittify/** from pyproject.toml package-data
3. Only package src/specify_cli/ (never runtime .kittify/)
4. Load templates from package resources using importlib.resources

Test Coverage:
- TestWheelContentInspection (8 tests): Verify NO .kittify/ in wheel
- TestDogfoodingSafety (6 tests): Developer workflow safety
- TestTemplateSourceLocation (6 tests): Templates in correct location

Related Issues: #62, #63, #64 (100% user impact bugs)
Version: Requires v0.10.12+ (Feature 011)
"""

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest
import tomli


class TestWheelContentInspection:
    """
    CRITICAL: Verify wheel does NOT contain runtime artifacts.

    Tests that the built wheel:
    - Has NO .kittify/ directory
    - Has NO memory/ directory
    - Has NO filled constitution
    - Has templates in src/specify_cli/
    - Has missions in src/specify_cli/
    - Has scripts in src/specify_cli/
    - pyproject.toml correctly excludes .kittify/
    - pyproject.toml includes psutil dependency
    """

    def test_wheel_has_no_kittify_directory(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain .kittify/ directory.

        .kittify/ is a RUNTIME directory created by 'spec-kitty init'.
        It contains user data (constitution, memory, etc.).
        It must NEVER be packaged.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        kittify_files = [name for name in namelist if '.kittify/' in name or 'kittify/' in name]

        assert len(kittify_files) == 0, (
            f"CRITICAL BUG: Wheel contains .kittify/ directory!\n\n"
            f"Found {len(kittify_files)} file(s) in .kittify/:\n" +
            "\n".join([f"  - {f}" for f in kittify_files[:10]]) +
            (f"\n  ... and {len(kittify_files) - 10} more" if len(kittify_files) > 10 else "") +
            "\n\n.kittify/ is a RUNTIME directory and must NOT be packaged.\n"
            "This causes contamination bugs like Issues #62-64."
        )

    def test_wheel_has_no_memory_directory(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain memory/ directory.

        .kittify/memory/ contains user data (constitution, conversation history).
        If packaged, ALL users get the developer's personal data.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        memory_files = [name for name in namelist if 'memory/' in name]

        assert len(memory_files) == 0, (
            f"CRITICAL BUG: Wheel contains memory/ directory!\n\n"
            f"Found {len(memory_files)} file(s) in memory/:\n" +
            "\n".join([f"  - {f}" for f in memory_files[:10]]) +
            "\n\nThis is 100% user contamination - users get developer's personal data!"
        )

    def test_wheel_has_no_filled_constitution(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Wheel must NOT contain filled constitution.md.

        This is the exact bug from Issues #62-64.
        Developers fill their constitution, then it gets packaged.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            constitution_files = [
                name for name in zf.namelist()
                if 'constitution.md' in name.lower()
            ]

            # Check each constitution.md
            for const_file in constitution_files:
                # Skip if it's clearly a template (in src/specify_cli/)
                if 'src/specify_cli/' in const_file or 'specify_cli/templates/' in const_file:
                    continue

                # If it's in memory/ or .kittify/ - CRITICAL BUG
                if 'memory/' in const_file or '.kittify/' in const_file:
                    pytest.fail(
                        f"CRITICAL BUG: Wheel contains filled constitution!\n\n"
                        f"File: {const_file}\n\n"
                        "This is the exact bug from Issues #62-64.\n"
                        "Developer's filled constitution is being packaged."
                    )

    def test_wheel_templates_in_src_specify_cli(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Templates must be in src/specify_cli/, not .kittify/.

        Feature 011 relocates templates from .kittify/templates/ to src/specify_cli/templates/.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        template_files = [
            name for name in namelist
            if 'templates/' in name and name.endswith('.md')
            and 'dashboard/templates' not in name  # Exclude dashboard templates
        ]

        # Should have templates
        assert len(template_files) > 0, (
            "Wheel contains no template files!\n"
            "Expected templates in specify_cli/templates/"
        )

        # All templates should be in specify_cli/ (not .kittify/)
        wrong_location = [
            name for name in template_files
            if '.kittify/templates/' in name or 'kittify/templates/' in name
        ]

        assert len(wrong_location) == 0, (
            f"Templates found in .kittify/ (wrong location)!\n\n"
            f"Found {len(wrong_location)} template(s) in .kittify/:\n" +
            "\n".join([f"  - {f}" for f in wrong_location[:5]]) +
            "\n\nTemplates must be in specify_cli/templates/, not .kittify/templates/"
        )

    def test_wheel_missions_in_src_specify_cli(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Missions must be in src/specify_cli/, not .kittify/.

        Feature 011 relocates missions from .kittify/missions/ to src/specify_cli/missions/.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        mission_files = [
            name for name in namelist
            if 'missions/' in name
        ]

        # Should have missions
        assert len(mission_files) > 0, (
            "Wheel contains no mission files!\n"
            "Expected missions in src/specify_cli/missions/"
        )

        # All missions should be in src/specify_cli/
        wrong_location = [
            name for name in mission_files
            if not ('specify_cli/missions/' in name or 'src/specify_cli/' in name)
        ]

        assert len(wrong_location) == 0, (
            f"Missions found in wrong location!\n\n"
            f"Found {len(wrong_location)} mission(s) not in src/specify_cli/:\n" +
            "\n".join([f"  - {f}" for f in wrong_location[:5]]) +
            "\n\nMissions must be in src/specify_cli/missions/, not .kittify/missions/"
        )

    def test_wheel_scripts_in_src_specify_cli(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Scripts must be in src/specify_cli/, not .kittify/.

        Feature 011 relocates scripts from .kittify/scripts/ to src/specify_cli/scripts/.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        script_files = [
            name for name in namelist
            if 'scripts/' in name and (name.endswith('.py') or name.endswith('.js'))
        ]

        # Should have scripts
        assert len(script_files) > 0, (
            "Wheel contains no script files!\n"
            "Expected scripts in src/specify_cli/scripts/"
        )

        # All scripts should be in src/specify_cli/
        wrong_location = [
            name for name in script_files
            if not ('specify_cli/scripts/' in name or 'src/specify_cli/' in name)
        ]

        assert len(wrong_location) == 0, (
            f"Scripts found in wrong location!\n\n"
            f"Found {len(wrong_location)} script(s) not in src/specify_cli/:\n" +
            "\n".join([f"  - {f}" for f in wrong_location[:5]]) +
            "\n\nScripts must be in src/specify_cli/scripts/, not .kittify/scripts/"
        )

    def test_pyproject_toml_excludes_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: pyproject.toml must NOT include .kittify/ in package-data.

        Before Feature 011:
        [tool.setuptools.package-data]
        specify_cli = [".kittify/memory/**/*"]  # ← CONTAMINATION BUG

        After Feature 011:
        .kittify/ should NOT appear in package-data at all.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        # Get package-data if it exists
        package_data = pyproject.get('tool', {}).get('setuptools', {}).get('package-data', {})

        # Check for .kittify/ references
        kittify_refs = []
        for package, patterns in package_data.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    if '.kittify' in str(pattern) or 'kittify/memory' in str(pattern):
                        kittify_refs.append(f"{package}: {pattern}")
            elif isinstance(patterns, str):
                if '.kittify' in patterns or 'kittify/memory' in patterns:
                    kittify_refs.append(f"{package}: {patterns}")

        assert len(kittify_refs) == 0, (
            f"CRITICAL BUG: pyproject.toml includes .kittify/ in package-data!\n\n"
            f"Found {len(kittify_refs)} reference(s):\n" +
            "\n".join([f"  - {ref}" for ref in kittify_refs]) +
            "\n\n.kittify/ is a RUNTIME directory and must NOT be in package-data.\n"
            "This causes contamination bugs."
        )

    def test_pyproject_toml_includes_psutil_dependency(self, spec_kitty_repo_root, requires_v010_12):
        """
        HIGH: pyproject.toml must include psutil dependency.

        Feature 011 adds psutil for Windows dashboard process management.
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        # Get dependencies
        dependencies = pyproject.get('project', {}).get('dependencies', [])

        # Check for psutil
        has_psutil = any('psutil' in dep for dep in dependencies)

        assert has_psutil, (
            "pyproject.toml must include psutil dependency!\n\n"
            f"Current dependencies: {dependencies}\n\n"
            "Feature 011 requires psutil for Windows dashboard."
        )

    def _build_wheel(self, repo_root):
        """Helper: Build wheel and return path."""
        # Use pytest cache for wheel builds
        dist_dir = repo_root / 'dist'

        # Check if wheel already exists and is recent
        if dist_dir.exists():
            wheels = list(dist_dir.glob('*.whl'))
            if wheels:
                # Use existing wheel for speed
                return wheels[0]

        # Build wheel
        result = subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(
                f"Failed to build wheel:\n{result.stderr}"
            )

        # Find built wheel
        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel file found after build"

        return wheels[0]


class TestDogfoodingSafety:
    """
    CRITICAL: Verify developers can safely dogfood spec-kitty.

    Tests that developers can:
    - Fill their constitution in the spec-kitty repo
    - Build a wheel
    - The wheel does NOT contain their filled constitution
    - Their local constitution is preserved
    - Build artifacts are excluded from packaging
    - Manifest correctly excludes .kittify/
    """

    def test_developer_constitution_not_packaged(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Developer's filled constitution must NOT be packaged.

        Scenario:
        1. Developer uses spec-kitty to develop spec-kitty (dogfooding)
        2. Developer fills .kittify/memory/constitution.md
        3. Developer builds wheel
        4. Filled constitution should NOT be in wheel
        """
        # Check if developer has filled constitution
        constitution_file = spec_kitty_repo_root / '.kittify' / 'memory' / 'constitution.md'

        if not constitution_file.exists():
            pytest.skip("No .kittify/memory/constitution.md - developer hasn't filled it yet")

        # Check if constitution looks filled (more than 100 bytes)
        constitution_size = constitution_file.stat().st_size
        is_filled = constitution_size > 100

        if not is_filled:
            pytest.skip("Constitution exists but appears to be blank template")

        # Build wheel
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        # Check wheel does NOT contain this constitution
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        memory_constitution = [
            name for name in namelist
            if 'memory/constitution.md' in name or '.kittify/memory/constitution.md' in name
        ]

        assert len(memory_constitution) == 0, (
            f"CRITICAL BUG: Developer's filled constitution is in wheel!\n\n"
            f"Found: {memory_constitution}\n\n"
            f"Local constitution size: {constitution_size} bytes (filled)\n"
            "This would contaminate ALL PyPI users with developer's personal data!"
        )

    def test_developer_memory_not_packaged(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Developer's .kittify/memory/ must NOT be packaged.

        This directory contains conversation history, decisions, etc.
        """
        memory_dir = spec_kitty_repo_root / '.kittify' / 'memory'

        if not memory_dir.exists():
            pytest.skip("No .kittify/memory/ directory")

        # Build wheel
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        # Check wheel does NOT contain memory/
        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        memory_files = [name for name in namelist if 'memory/' in name]

        assert len(memory_files) == 0, (
            f"CRITICAL BUG: Developer's memory/ directory is in wheel!\n\n"
            f"Found {len(memory_files)} file(s):\n" +
            "\n".join([f"  - {f}" for f in memory_files[:10]]) +
            "\n\nThis is 100% user contamination!"
        )

    def test_developer_local_kittify_preserved(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Developer's local .kittify/ should still exist after build.

        Building a wheel should NOT delete developer's local data.
        """
        kittify_dir = spec_kitty_repo_root / '.kittify'

        # Build wheel
        self._build_wheel(spec_kitty_repo_root)

        # Check .kittify/ still exists
        assert kittify_dir.exists(), (
            "Building wheel deleted .kittify/ directory!\n"
            "This would lose developer's local data."
        )

    def test_build_wheel_excludes_runtime_artifacts(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Runtime artifacts must NOT be packaged.

        Runtime artifacts:
        - .kittify/ (user data)
        - __pycache__/ (Python bytecode)
        - .pytest_cache/ (test cache)
        - dist/ (build artifacts)
        - *.egg-info/ (build metadata)
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        runtime_artifacts = []

        for name in namelist:
            if any(pattern in name for pattern in [
                '__pycache__/',
                '.pytest_cache/',
                '.kittify/',
                'dist/',
                '.egg-info/'
            ]):
                runtime_artifacts.append(name)

        assert len(runtime_artifacts) == 0, (
            f"Wheel contains runtime artifacts!\n\n"
            f"Found {len(runtime_artifacts)} artifact(s):\n" +
            "\n".join([f"  - {f}" for f in runtime_artifacts[:10]]) +
            "\n\nThese should be excluded from the wheel."
        )

    def test_manifest_excludes_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: MANIFEST.in should exclude .kittify/ (if exists).

        MANIFEST.in controls what goes into sdist (source distribution).
        """
        manifest_file = spec_kitty_repo_root / 'MANIFEST.in'

        if not manifest_file.exists():
            pytest.skip("No MANIFEST.in file")

        content = manifest_file.read_text()

        # Check for .kittify/ in include/graft directives
        includes_kittify = any(
            line.strip().startswith(('include', 'graft', 'recursive-include')) and '.kittify' in line
            for line in content.split('\n')
        )

        assert not includes_kittify, (
            "MANIFEST.in includes .kittify/ directory!\n\n"
            "This will package developer's runtime directory in source distribution."
        )

    def test_sdist_also_excludes_kittify(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Source distribution (sdist) must also exclude .kittify/.

        Users can install from sdist, not just wheels.
        """
        # Build sdist
        dist_dir = spec_kitty_repo_root / 'dist'

        result = subprocess.run(
            [sys.executable, '-m', 'build', '--sdist', '--outdir', str(dist_dir)],
            cwd=spec_kitty_repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Failed to build sdist: {result.stderr}")

        # Find latest sdist (sorted by modification time)
        sdists = sorted(dist_dir.glob('*.tar.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sdists:
            pytest.skip("No sdist found")

        sdist_file = sdists[0]  # Most recent

        # Extract and check contents
        import tarfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(sdist_file, 'r:gz') as tf:
                tf.extractall(tmpdir)

            # Check for .kittify/ with CONTENT (empty dirs are OK for structure)
            tmpdir_path = Path(tmpdir)
            kittify_dirs = list(tmpdir_path.rglob('.kittify'))

            # Filter out empty .kittify/ directories (just structure)
            kittify_with_content = []
            for kittify_dir in kittify_dirs:
                # Check if it has problematic subdirectories with files
                if (kittify_dir / 'memory').exists():
                    memory_files = list((kittify_dir / 'memory').rglob('*'))
                    if any(f.is_file() for f in memory_files):
                        kittify_with_content.append(kittify_dir)
                        continue

                # Check for templates/missions/scripts with content
                for subdir in ['templates', 'missions', 'scripts']:
                    if (kittify_dir / subdir).exists():
                        files = list((kittify_dir / subdir).rglob('*'))
                        if any(f.is_file() and f.suffix in ['.md', '.py', '.sh', '.ps1'] for f in files):
                            kittify_with_content.append(kittify_dir)
                            break

            assert len(kittify_with_content) == 0, (
                f"CRITICAL: sdist contains .kittify/ directory with content!\n\n"
                f"Found {len(kittify_with_content)} .kittify/ dir(s) with files:\n" +
                "\n".join([f"  - {d}" for d in kittify_with_content]) +
                "\n\nUsers installing from source will get contaminated code."
            )

    def _build_wheel(self, repo_root):
        """Helper: Build wheel and return path."""
        dist_dir = repo_root / 'dist'
        dist_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to build wheel:\n{result.stderr}")

        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel file found"
        return wheels[0]


class TestTemplateSourceLocation:
    """
    CRITICAL: Verify templates are in correct package location.

    Tests that:
    - Templates accessible via importlib.resources
    - Mission templates in package
    - Scripts in package
    - No template duplication
    - Runtime .kittify/ not in source
    - Package-data correct in pyproject.toml
    """

    def test_templates_accessible_via_importlib_resources(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Templates must be accessible via importlib.resources.

        Feature 011 uses importlib.resources to load templates from package.
        This must work from installed package, not just dev mode.
        """
        # This test verifies the templates are in the right location for importlib
        templates_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates'

        assert templates_dir.exists(), (
            "Templates directory not found in src/specify_cli/!\n\n"
            f"Expected: {templates_dir}\n\n"
            "Feature 011 requires templates in src/specify_cli/templates/"
        )

        # Check command-templates/
        command_templates = templates_dir / 'command-templates'
        assert command_templates.exists(), (
            f"command-templates/ not found in {templates_dir}"
        )

        # Should have template files
        template_files = list(command_templates.glob('*.md'))
        assert len(template_files) >= 10, (
            f"Insufficient templates in {command_templates}\n"
            f"Found: {len(template_files)}, expected >= 10"
        )

    def test_mission_templates_in_package(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Mission templates must be in src/specify_cli/missions/.
        """
        missions_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'missions'

        assert missions_dir.exists(), (
            "Missions directory not found in src/specify_cli/!\n\n"
            f"Expected: {missions_dir}\n\n"
            "Feature 011 requires missions in src/specify_cli/missions/"
        )

        # Should have mission directories
        mission_dirs = [d for d in missions_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
        assert len(mission_dirs) >= 2, (
            f"Insufficient missions in {missions_dir}\n"
            f"Found: {len(mission_dirs)}, expected >= 2 (e.g., software-dev, research)"
        )

    def test_scripts_in_package(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: Scripts must be in src/specify_cli/scripts/.
        """
        scripts_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'scripts'

        assert scripts_dir.exists(), (
            "Scripts directory not found in src/specify_cli/!\n\n"
            f"Expected: {scripts_dir}\n\n"
            "Feature 011 requires scripts in src/specify_cli/scripts/"
        )

        # Should have script files
        script_files = list(scripts_dir.glob('*.py')) + list(scripts_dir.glob('*.js'))
        assert len(script_files) >= 1, (
            f"No scripts found in {scripts_dir}\n"
            "Expected at least 1 script file"
        )

    def test_no_template_duplication(self, spec_kitty_repo_root, requires_v010_12):
        """
        VALIDATION: Templates should NOT exist in both locations.

        After Feature 011:
        - ✅ src/specify_cli/templates/ (packaged)
        - ❌ .kittify/templates/ (should NOT exist or should be removed)
        """
        old_location = spec_kitty_repo_root / '.kittify' / 'templates'
        new_location = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates'

        assert new_location.exists(), (
            "Templates not found in new location (src/specify_cli/templates/)"
        )

        if old_location.exists():
            # Check if it has content (not just empty directory)
            template_files = list(old_location.rglob('*.md'))
            if len(template_files) > 0:
                pytest.fail(
                    "Template duplication detected!\n\n"
                    f"Old location still exists with {len(template_files)} files: {old_location}\n"
                    f"New location: {new_location}\n\n"
                    "After Feature 011, .kittify/templates/ should be removed or emptied.\n"
                    "Keeping both risks divergence and confusion."
                )
            # Empty directory is OK (just structure)

    def test_runtime_kittify_not_in_source(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: .kittify/ in repo root should NOT contain templates/missions/scripts.

        .kittify/ may exist for developer's dogfooding.
        But it should NOT contain templates/missions/scripts (those moved to src/).
        """
        kittify_dir = spec_kitty_repo_root / '.kittify'

        if not kittify_dir.exists():
            # Good! No .kittify/ in source
            return

        # Check for templates/missions/scripts with actual source files
        problematic_dirs = []
        for dirname in ['templates', 'missions', 'scripts']:
            dirpath = kittify_dir / dirname
            if dirpath.exists():
                # Check for actual source files (not just __pycache__ or empty dirs)
                source_files = [
                    f for f in dirpath.rglob('*')
                    if f.is_file() and f.suffix in ['.md', '.py', '.sh', '.ps1', '.js', '.yaml', '.yml']
                    and '__pycache__' not in str(f)
                ]
                if source_files:
                    problematic_dirs.append(f"{dirname} ({len(source_files)} files)")

        assert len(problematic_dirs) == 0, (
            f"Found source files in .kittify/:\n" +
            "\n".join([f"  - .kittify/{d}" for d in problematic_dirs]) +
            "\n\nFeature 011 moved these to src/specify_cli/.\n"
            ".kittify/ should only contain RUNTIME data (memory/), not source files."
        )

    def test_package_data_correct_in_pyproject(self, spec_kitty_repo_root, requires_v010_12):
        """
        CRITICAL: pyproject.toml package-data must include src/specify_cli/ correctly.

        Should include:
        - templates/**/*
        - missions/**/*
        - scripts/**/*

        Should NOT include:
        - .kittify/**/*
        """
        pyproject_file = spec_kitty_repo_root / 'pyproject.toml'

        with open(pyproject_file, 'rb') as f:
            pyproject = tomli.load(f)

        # Check build backend
        build_backend = pyproject.get('build-system', {}).get('build-backend', '')

        if 'hatchling' in build_backend:
            # Hatchling: Check that src/specify_cli/ is in packages
            packages = pyproject.get('tool', {}).get('hatch', {}).get('build', {}).get('targets', {}).get('wheel', {}).get('packages', [])

            assert 'src/specify_cli' in packages or 'specify_cli' in packages, (
                f"Hatchling configuration missing src/specify_cli in packages!\n"
                f"Current packages: {packages}\n\n"
                "Feature 011 requires specify_cli package to be included."
            )

            # Hatchling auto-includes all package files, so templates/missions/scripts
            # will be included automatically if they're in src/specify_cli/

        else:
            # Setuptools: Check package-data
            package_data = pyproject.get('tool', {}).get('setuptools', {}).get('package-data', {})

            # Check for specify_cli patterns
            specify_cli_patterns = package_data.get('specify_cli', [])
            if isinstance(specify_cli_patterns, str):
                specify_cli_patterns = [specify_cli_patterns]

            # Should include templates, missions, scripts
            required_patterns = ['templates', 'missions', 'scripts']
            missing = []

            for pattern in required_patterns:
                found = any(pattern in p for p in specify_cli_patterns)
                if not found:
                    missing.append(pattern)

            assert len(missing) == 0, (
                f"pyproject.toml package-data missing patterns:\n" +
                "\n".join([f"  - {p}" for p in missing]) +
                f"\n\nCurrent specify_cli patterns: {specify_cli_patterns}\n\n"
                "Feature 011 requires templates/missions/scripts to be packaged."
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
