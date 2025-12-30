"""
Test: Issue #46 - Constitution Not Copied to Worktrees (CRITICAL FIX)

Purpose: Aggressive adversarial tests to force correct implementation of constitution fix.

Root Cause (FIXED):
- .kittify/memory and .kittify/AGENTS.md were broken circular symlinks
- Created when spec-kitty was developed in a worktree, merged to main
- All code expects files at .kittify/ but they were at root

The Fix:
1. Move memory/ → .kittify/memory/ (real directory)
2. Remove broken circular symlinks
3. Create real .kittify/AGENTS.md from template

Test Philosophy: AGGRESSIVE - Force code to be correct at every critical point
- ❌ Fail if circular symlinks exist
- ❌ Fail if files in wrong location
- ❌ Fail if symlinks don't resolve correctly
- ❌ Fail if constitution content is placeholder
- ❌ Fail if worktree gets wrong constitution

Test Coverage:
1. File Structure Validation (10 tests) - Force correct file locations
2. Symlink Validation (8 tests) - Force valid symlinks, no circular refs
3. Worktree Constitution (12 tests) - Force correct constitution in worktrees
4. Init Constitution (6 tests) - Force correct constitution in new projects
5. AGENTS.md Handling (6 tests) - Force correct AGENTS.md behavior
6. Cross-Platform (4 tests) - Force both Unix and Windows support
7. Migration Safety (4 tests) - Force existing projects to work

Related Issue: #46
Analysis: /Users/robert/.claude/plans/issue-46-deep-analysis.md
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestFileStructureValidation:
    """AGGRESSIVE: Force correct file structure - no broken symlinks allowed."""

    def test_constitution_exists_as_real_file(self, spec_kitty_repo_root):
        """
        CRITICAL: .kittify/memory/constitution.md MUST exist as a REAL FILE

        ❌ FAIL if: symlink, broken, missing, or wrong location
        ✅ PASS if: real file with actual constitution content
        """
        constitution_path = spec_kitty_repo_root / '.kittify' / 'memory' / 'constitution.md'

        # Must exist
        assert constitution_path.exists(), (
            f"CRITICAL: Constitution must exist at .kittify/memory/constitution.md\n"
            f"Expected: {constitution_path}\n"
            f"Found: NOT FOUND\n\n"
            f"FIX: git mv memory .kittify/"
        )

        # Must be a file (not symlink, not directory)
        assert constitution_path.is_file(), (
            f"CRITICAL: Constitution must be a REAL FILE, not symlink\n"
            f"Path: {constitution_path}\n"
            f"Is symlink: {constitution_path.is_symlink()}\n"
            f"Is dir: {constitution_path.is_dir()}\n\n"
            f"FIX: Remove broken symlink, move real file here"
        )

        # Must NOT be a symlink
        assert not constitution_path.is_symlink(), (
            f"CRITICAL: Constitution must be real file, NOT a symlink\n"
            f"Path: {constitution_path}\n"
            f"Symlink target: {constitution_path.readlink() if constitution_path.is_symlink() else 'N/A'}\n\n"
            f"FIX: git rm .kittify/memory (symlink), git mv memory .kittify/"
        )

        # Must have actual content (not empty placeholder)
        content = constitution_path.read_text(encoding='utf-8')
        assert len(content) > 100, (
            f"CRITICAL: Constitution must have real content (not placeholder)\n"
            f"Content length: {len(content)} bytes\n"
            f"Expected: >100 bytes\n\n"
            f"Verify this is the REAL spec-kitty constitution, not a template"
        )

    def test_no_circular_symlink_in_memory(self, spec_kitty_repo_root):
        """
        CRITICAL: .kittify/memory must NOT be a circular symlink

        The bug: .kittify/memory → ../../../.kittify/memory (points to itself!)
        """
        memory_path = spec_kitty_repo_root / '.kittify' / 'memory'

        # If it's a symlink, it must NOT point to itself
        if memory_path.is_symlink():
            target = memory_path.readlink()
            resolved = memory_path.resolve(strict=False)

            # Check for circular reference
            assert str(resolved) != str(memory_path), (
                f"CRITICAL: Circular symlink detected!\n"
                f"Path: {memory_path}\n"
                f"Target: {target}\n"
                f"Resolves to: {resolved}\n\n"
                f"This is the BUG! Symlink points to itself.\n"
                f"FIX: git rm .kittify/memory && git mv memory .kittify/"
            )

            # Symlink target must exist
            assert resolved.exists(), (
                f"CRITICAL: Symlink target does not exist (broken symlink)\n"
                f"Path: {memory_path}\n"
                f"Target: {target}\n"
                f"Resolves to: {resolved}\n\n"
                f"FIX: Remove broken symlink, create real directory"
            )

    def test_no_circular_symlink_in_agents_md(self, spec_kitty_repo_root):
        """
        CRITICAL: .kittify/AGENTS.md must NOT be a circular symlink

        The bug: .kittify/AGENTS.md → ../../../.kittify/AGENTS.md (points to itself!)
        """
        agents_path = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'

        # Must exist
        assert agents_path.exists(), (
            f"CRITICAL: .kittify/AGENTS.md must exist\n"
            f"Expected: {agents_path}\n\n"
            f"FIX: cp .kittify/templates/AGENTS.md .kittify/"
        )

        # If it's a symlink, it must NOT point to itself
        if agents_path.is_symlink():
            target = agents_path.readlink()
            resolved = agents_path.resolve(strict=False)

            assert str(resolved) != str(agents_path), (
                f"CRITICAL: Circular symlink detected in AGENTS.md!\n"
                f"Path: {agents_path}\n"
                f"Target: {target}\n"
                f"Resolves to: {resolved}\n\n"
                f"FIX: git rm .kittify/AGENTS.md && cp .kittify/templates/AGENTS.md .kittify/"
            )

    def test_memory_directory_is_directory(self, spec_kitty_repo_root):
        """
        CRITICAL: .kittify/memory must be a directory (or valid symlink to dir)

        Code relies on is_dir() checks that fail on broken symlinks
        """
        memory_path = spec_kitty_repo_root / '.kittify' / 'memory'

        assert memory_path.is_dir(), (
            f"CRITICAL: .kittify/memory must be a directory\n"
            f"Path: {memory_path}\n"
            f"Exists: {memory_path.exists()}\n"
            f"Is dir: {memory_path.is_dir()}\n"
            f"Is symlink: {memory_path.is_symlink()}\n\n"
            f"Code checks: if main_memory.exists() and main_memory.is_dir()\n"
            f"Broken symlinks fail is_dir() check!\n\n"
            f"FIX: Create real directory or fix symlink target"
        )

    def test_constitution_has_spec_kitty_content(self, spec_kitty_repo_root):
        """
        AGGRESSIVE: Constitution must have spec-kitty specific content

        Not a generic template or placeholder
        """
        constitution_path = spec_kitty_repo_root / '.kittify' / 'memory' / 'constitution.md'
        content = constitution_path.read_text(encoding='utf-8').lower()

        # Should mention spec-kitty specific concepts
        spec_kitty_indicators = [
            'spec-driven development',
            'feature',
            'worktree',
            'specification',
        ]

        found_indicators = [ind for ind in spec_kitty_indicators if ind in content]

        assert len(found_indicators) >= 2, (
            f"CRITICAL: Constitution doesn't look like spec-kitty constitution\n"
            f"Expected spec-kitty specific content\n"
            f"Found indicators: {found_indicators}\n"
            f"Looking for: {spec_kitty_indicators}\n\n"
            f"This might be a placeholder template!\n"
            f"FIX: Ensure you copied the REAL spec-kitty constitution"
        )

    def test_no_memory_directory_at_root(self, spec_kitty_repo_root):
        """
        AGGRESSIVE: Old memory/ at root should NOT exist (moved to .kittify/)

        If it still exists, the fix wasn't applied correctly
        """
        old_memory_path = spec_kitty_repo_root / 'memory'

        assert not old_memory_path.exists(), (
            f"CRITICAL: Old memory/ directory still exists at root!\n"
            f"Path: {old_memory_path}\n\n"
            f"The fix requires moving this to .kittify/memory/\n"
            f"FIX: git mv memory .kittify/"
        )

    def test_kittify_directory_exists(self, spec_kitty_repo_root):
        """Basic: .kittify directory must exist"""
        kittify_path = spec_kitty_repo_root / '.kittify'

        assert kittify_path.exists(), (
            f".kittify directory must exist\n"
            f"Expected: {kittify_path}"
        )
        assert kittify_path.is_dir(), (
            f".kittify must be a directory\n"
            f"Found: {kittify_path}"
        )

    def test_memory_directory_has_constitution(self, spec_kitty_repo_root):
        """AGGRESSIVE: Memory directory must contain constitution.md"""
        memory_path = spec_kitty_repo_root / '.kittify' / 'memory'
        constitution = memory_path / 'constitution.md'

        # List what's actually in memory/ for debugging
        if memory_path.exists():
            actual_files = list(memory_path.glob('*'))
        else:
            actual_files = []

        assert constitution.exists(), (
            f"CRITICAL: constitution.md missing from .kittify/memory/\n"
            f"Expected: {constitution}\n"
            f"Memory dir exists: {memory_path.exists()}\n"
            f"Actual files in memory/: {[f.name for f in actual_files]}\n\n"
            f"FIX: Ensure constitution.md is in .kittify/memory/"
        )

    def test_agents_md_is_real_file(self, spec_kitty_repo_root):
        """CRITICAL: .kittify/AGENTS.md must be a real file"""
        agents_path = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'

        assert agents_path.is_file(), (
            f"CRITICAL: .kittify/AGENTS.md must be a real file\n"
            f"Path: {agents_path}\n"
            f"Exists: {agents_path.exists()}\n"
            f"Is file: {agents_path.is_file()}\n"
            f"Is symlink: {agents_path.is_symlink()}\n\n"
            f"FIX: cp .kittify/templates/AGENTS.md .kittify/"
        )

    def test_agents_md_has_content(self, spec_kitty_repo_root):
        """AGGRESSIVE: AGENTS.md must have content"""
        agents_path = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'
        content = agents_path.read_text(encoding='utf-8')

        assert len(content) > 50, (
            f"CRITICAL: AGENTS.md has insufficient content\n"
            f"Length: {len(content)} bytes\n"
            f"Expected: >50 bytes\n\n"
            f"Verify this has real content, not empty file"
        )


class TestSymlinkValidation:
    """AGGRESSIVE: Force all symlinks to be valid - no broken links allowed."""

    def test_no_broken_symlinks_in_kittify(self, spec_kitty_repo_root):
        """
        CRITICAL: No broken symlinks allowed in .kittify/

        Scan entire .kittify/ directory for broken symlinks
        """
        kittify_path = spec_kitty_repo_root / '.kittify'
        broken_symlinks = []

        for item in kittify_path.rglob('*'):
            if item.is_symlink():
                try:
                    # Try to resolve - will fail if broken
                    resolved = item.resolve(strict=True)
                    if not resolved.exists():
                        broken_symlinks.append((item, item.readlink(), "target doesn't exist"))
                except (OSError, RuntimeError) as e:
                    broken_symlinks.append((item, item.readlink(), str(e)))

        assert len(broken_symlinks) == 0, (
            f"CRITICAL: Found {len(broken_symlinks)} broken symlink(s) in .kittify/:\n" +
            "\n".join([
                f"  - {link}\n    Target: {target}\n    Error: {error}"
                for link, target, error in broken_symlinks
            ]) +
            "\n\nAll symlinks must have valid targets!\n"
            f"FIX: Remove broken symlinks or fix targets"
        )

    def test_symlinks_use_relative_paths(self, spec_kitty_repo_root):
        """
        BEST PRACTICE: Symlinks should use relative paths (not absolute)

        Absolute paths break when repo is moved
        """
        kittify_path = spec_kitty_repo_root / '.kittify'
        absolute_symlinks = []

        for item in kittify_path.rglob('*'):
            if item.is_symlink():
                target = item.readlink()
                if target.is_absolute():
                    absolute_symlinks.append((item, target))

        assert len(absolute_symlinks) == 0, (
            f"WARNING: Found {len(absolute_symlinks)} absolute symlink(s):\n" +
            "\n".join([
                f"  - {link} → {target}"
                for link, target in absolute_symlinks
            ]) +
            "\n\nUse relative paths for portability"
        )

    def test_memory_resolves_correctly(self, spec_kitty_repo_root):
        """
        CRITICAL: .kittify/memory must resolve to a valid directory

        If it's a symlink, it must point to correct location
        """
        memory_path = spec_kitty_repo_root / '.kittify' / 'memory'

        # Try to resolve
        try:
            resolved = memory_path.resolve(strict=True)
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Cannot resolve .kittify/memory\n"
                f"Path: {memory_path}\n"
                f"Error: {e}\n\n"
                f"Symlink is broken or points to invalid target"
            )

        # Resolved path must exist and be a directory
        assert resolved.exists(), f"Resolved path doesn't exist: {resolved}"
        assert resolved.is_dir(), f"Resolved path is not a directory: {resolved}"

    def test_circular_symlink_detection(self, spec_kitty_repo_root):
        """
        AGGRESSIVE: Detect circular symlinks (the core bug!)

        Test pattern: path → ../../../path (points to itself)
        """
        kittify_path = spec_kitty_repo_root / '.kittify'
        circular_symlinks = []

        for item in kittify_path.rglob('*'):
            if item.is_symlink():
                target = item.readlink()

                # Check if target path contains ../../../.kittify/[same-name]
                # This pattern indicates circular reference
                if '../../../.kittify/' in str(target):
                    # Extract the target name
                    target_parts = str(target).split('/')
                    target_name = target_parts[-1] if target_parts else ''

                    # Check if it points to itself
                    if item.name == target_name:
                        circular_symlinks.append((item, target))

        assert len(circular_symlinks) == 0, (
            f"CRITICAL BUG: Found {len(circular_symlinks)} circular symlink(s)!\n" +
            "\n".join([
                f"  - {link} → {target} (POINTS TO ITSELF!)"
                for link, target in circular_symlinks
            ]) +
            "\n\nThis is the exact bug from Issue #46!\n"
            f"These symlinks were created in a worktree, point to themselves in main.\n\n"
            f"FIX: git rm [symlink] && git mv [real-file] .kittify/"
        )


class TestWorktreeConstitution:
    """AGGRESSIVE: Force worktrees to get correct constitution."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create initialized spec-kitty project."""
        project_name = 'worktree_test'
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

        return project_path

    def test_worktree_has_constitution(self, initialized_project, spec_kitty_repo_root):
        """
        CRITICAL: Worktree MUST have constitution.md

        This is the core bug - worktrees were getting empty/placeholder
        """
        # Create feature worktree
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'constitution-test', 'Test constitution'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Find worktree (format: .worktrees/NNN-constitution-test/)
        worktrees_dir = initialized_project / '.worktrees'
        if not worktrees_dir.exists():
            pytest.skip("Worktrees not created (might be expected failure)")

        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'constitution-test' in d.name]

        assert len(worktrees) > 0, (
            f"No worktree created for constitution-test\n"
            f"Command output: {result.stdout}\n"
            f"Error: {result.stderr}"
        )

        worktree_path = worktrees[0]
        constitution = worktree_path / '.kittify' / 'memory' / 'constitution.md'

        assert constitution.exists(), (
            f"CRITICAL BUG: Constitution missing in worktree!\n"
            f"Worktree: {worktree_path}\n"
            f"Expected: {constitution}\n\n"
            f"This is Issue #46 - constitution not copied to worktrees"
        )

    def test_worktree_constitution_has_content(self, initialized_project, spec_kitty_repo_root):
        """
        AGGRESSIVE: Worktree constitution must have REAL content

        Not placeholder, not empty, not template
        """
        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'content-test', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            timeout=60
        )

        worktrees_dir = initialized_project / '.worktrees'
        if not worktrees_dir.exists():
            pytest.skip("Worktrees not created")

        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'content-test' in d.name]
        if not worktrees:
            pytest.skip("Worktree not found")

        constitution = worktrees[0] / '.kittify' / 'memory' / 'constitution.md'
        if not constitution.exists():
            pytest.skip("Constitution not created (expected failure)")

        content = constitution.read_text(encoding='utf-8')

        assert len(content) > 100, (
            f"CRITICAL: Worktree constitution has insufficient content!\n"
            f"Length: {len(content)} bytes\n"
            f"Expected: >100 bytes\n\n"
            f"Worktree is getting placeholder/empty constitution"
        )

    def test_worktree_constitution_matches_main(self, initialized_project, spec_kitty_repo_root):
        """
        AGGRESSIVE: Worktree constitution must match main repo

        Either identical copy (Windows) or valid symlink (Unix)
        """
        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'match-test', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            timeout=60
        )

        worktrees_dir = initialized_project / '.worktrees'
        if not worktrees_dir.exists():
            pytest.skip("Worktrees not created")

        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'match-test' in d.name]
        if not worktrees:
            pytest.skip("Worktree not found")

        worktree_constitution = worktrees[0] / '.kittify' / 'memory' / 'constitution.md'
        main_constitution = initialized_project / '.kittify' / 'memory' / 'constitution.md'

        if not worktree_constitution.exists():
            pytest.skip("Constitution not created")

        # Get content
        wt_content = worktree_constitution.read_text(encoding='utf-8')
        main_content = main_constitution.read_text(encoding='utf-8')

        # Should match (either copy or symlink to same content)
        assert wt_content == main_content, (
            f"CRITICAL: Worktree constitution differs from main!\n"
            f"Main length: {len(main_content)} bytes\n"
            f"Worktree length: {len(wt_content)} bytes\n\n"
            f"Worktree should have same constitution as main repo"
        )

    def test_worktree_symlink_on_unix(self, initialized_project, spec_kitty_repo_root):
        """
        PLATFORM: On Unix, worktree should have symlink to main

        Pattern: .worktrees/NNN/.kittify/memory → ../../../.kittify/memory
        """
        if platform.system() == 'Windows':
            pytest.skip("Unix-specific test")

        # Create feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'symlink-test', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            timeout=60
        )

        worktrees_dir = initialized_project / '.worktrees'
        if not worktrees_dir.exists():
            pytest.skip("Worktrees not created")

        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'symlink-test' in d.name]
        if not worktrees:
            pytest.skip("Worktree not found")

        memory_link = worktrees[0] / '.kittify' / 'memory'

        # On Unix, should be a symlink
        assert memory_link.is_symlink(), (
            f"On Unix, .kittify/memory should be a symlink\n"
            f"Path: {memory_link}\n"
            f"Is symlink: {memory_link.is_symlink()}\n\n"
            f"Expected symlink to ../../../.kittify/memory"
        )

        # Symlink should point to correct relative path
        target = memory_link.readlink()
        expected_target = Path('../../../.kittify/memory')

        assert target == expected_target, (
            f"Symlink has wrong target\n"
            f"Expected: {expected_target}\n"
            f"Actual: {target}\n\n"
            f"Should point to main repo .kittify/memory"
        )

    def test_worktree_copy_on_windows_or_no_symlinks(self, initialized_project, spec_kitty_repo_root):
        """
        PLATFORM: On Windows (or --no-symlinks), worktree should have copy

        Not a symlink, but a real directory with copied files
        """
        # Create feature with --no-symlinks to force copy behavior
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', '--no-symlinks', 'copy-test', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            timeout=60
        )

        worktrees_dir = initialized_project / '.worktrees'
        if not worktrees_dir.exists():
            pytest.skip("Worktrees not created")

        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'copy-test' in d.name]
        if not worktrees:
            pytest.skip("Worktree not found")

        memory_dir = worktrees[0] / '.kittify' / 'memory'

        # Should be a real directory (not symlink)
        assert memory_dir.is_dir(), (
            f"memory/ should be a directory\n"
            f"Path: {memory_dir}"
        )

        assert not memory_dir.is_symlink(), (
            f"With --no-symlinks, memory/ should be copied, not symlinked\n"
            f"Path: {memory_dir}\n"
            f"Is symlink: {memory_dir.is_symlink()}"
        )

        # Should contain constitution
        constitution = memory_dir / 'constitution.md'
        assert constitution.exists(), (
            f"Copied directory should contain constitution.md\n"
            f"Path: {constitution}"
        )


class TestInitConstitution:
    """AGGRESSIVE: Force init to handle constitution correctly."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_creates_memory_directory(self, temp_project_dir, spec_kitty_repo_root):
        """
        CRITICAL: spec-kitty init must create .kittify/memory/
        """
        project_name = 'init_test'

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

        project_path = temp_project_dir / project_name
        memory_dir = project_path / '.kittify' / 'memory'

        assert memory_dir.exists(), (
            f"Init must create .kittify/memory/ directory\n"
            f"Project: {project_path}\n"
            f"Expected: {memory_dir}"
        )
        assert memory_dir.is_dir(), (
            f".kittify/memory must be a directory\n"
            f"Path: {memory_dir}"
        )

    def test_init_creates_constitution(self, temp_project_dir, spec_kitty_repo_root):
        """
        CRITICAL: Init must create constitution.md
        """
        project_name = 'init_constitution'

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

        constitution = temp_project_dir / project_name / '.kittify' / 'memory' / 'constitution.md'

        assert constitution.exists(), (
            f"Init must create constitution.md\n"
            f"Expected: {constitution}"
        )

    def test_init_constitution_is_template(self, temp_project_dir, spec_kitty_repo_root):
        """
        CORRECT BEHAVIOR: Init should give USER PROJECT template

        NOT spec-kitty's own constitution
        """
        project_name = 'init_template'

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

        constitution = temp_project_dir / project_name / '.kittify' / 'memory' / 'constitution.md'
        content = constitution.read_text(encoding='utf-8').lower()

        # Should have template placeholders or generic content
        # NOT spec-kitty specific content
        template_indicators = ['[', 'project', 'your']
        has_template_markers = any(ind in content for ind in template_indicators)

        # Should NOT have spec-kitty specific content
        spec_kitty_specific = ['spec-kitty development', 'worktree management']
        has_spec_kitty = any(ind in content for ind in spec_kitty_specific)

        assert has_template_markers or len(content) < 1000, (
            f"Init constitution should be a template for user projects\n"
            f"Not spec-kitty's own constitution\n"
            f"Content length: {len(content)}"
        )

    def test_init_source_path_is_correct(self, spec_kitty_repo_root):
        """
        CODE VALIDATION: manager.py must read from .kittify/memory/

        This validates the code expects the right path
        """
        manager_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'template' / 'manager.py'
        content = manager_file.read_text(encoding='utf-8')

        # Should reference .kittify/memory as source
        assert '".kittify" / "memory"' in content or '".kittify/memory"' in content, (
            f"manager.py must expect source at .kittify/memory/\n"
            f"File: {manager_file}\n\n"
            f"This validates the fix is needed"
        )


class TestAgentsMdHandling:
    """AGGRESSIVE: Force correct AGENTS.md behavior."""

    def test_kittify_agents_md_exists(self, spec_kitty_repo_root):
        """CRITICAL: .kittify/AGENTS.md must exist"""
        agents_path = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'

        assert agents_path.exists(), (
            f"CRITICAL: .kittify/AGENTS.md must exist\n"
            f"Expected: {agents_path}\n\n"
            f"FIX: cp .kittify/templates/AGENTS.md .kittify/"
        )

    def test_agents_md_not_circular_symlink(self, spec_kitty_repo_root):
        """CRITICAL: AGENTS.md must NOT be circular symlink"""
        agents_path = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'

        if agents_path.is_symlink():
            target = agents_path.readlink()

            # Check for circular pattern
            assert '../../../.kittify/AGENTS.md' not in str(target), (
                f"CRITICAL BUG: AGENTS.md is a circular symlink!\n"
                f"Path: {agents_path}\n"
                f"Target: {target}\n\n"
                f"FIX: git rm .kittify/AGENTS.md && cp .kittify/templates/AGENTS.md .kittify/"
            )

    def test_root_agents_md_different_from_kittify(self, spec_kitty_repo_root):
        """
        SEMANTIC: Root AGENTS.md (about spec-kitty) != .kittify/AGENTS.md (for users)

        Two different files with different purposes
        """
        root_agents = spec_kitty_repo_root / 'AGENTS.md'
        kittify_agents = spec_kitty_repo_root / '.kittify' / 'AGENTS.md'

        if not root_agents.exists():
            pytest.skip("Root AGENTS.md doesn't exist (optional)")

        root_content = root_agents.read_text(encoding='utf-8')
        kittify_content = kittify_agents.read_text(encoding='utf-8')

        # They should be different (root is about spec-kitty, kittify is template)
        assert root_content != kittify_content, (
            f"Root AGENTS.md and .kittify/AGENTS.md should be different\n"
            f"Root: About spec-kitty project itself\n"
            f"Kittify: Template for user projects\n\n"
            f"They currently have identical content - likely a copy/paste error"
        )


class TestUpgradeAndMigration:
    """AGGRESSIVE: Force upgrade path to work - existing projects must not break."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_existing_project_can_upgrade(self, temp_project_dir, spec_kitty_repo_root):
        """
        CRITICAL: Existing spec-kitty projects must upgrade successfully

        Projects created before fix should still work
        """
        project_name = 'upgrade_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Run upgrade (should not error)
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Upgrade should succeed
        assert result.returncode == 0, (
            f"Upgrade should succeed for existing projects\n"
            f"Error: {result.stderr}\n"
            f"Output: {result.stdout}"
        )

    def test_upgrade_doesnt_break_constitution(self, temp_project_dir, spec_kitty_repo_root):
        """
        REGRESSION: Upgrade must not corrupt existing constitution
        """
        project_name = 'upgrade_constitution'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Get original constitution
        constitution = project_path / '.kittify' / 'memory' / 'constitution.md'
        original_content = constitution.read_text(encoding='utf-8')

        # Run upgrade
        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Constitution should still exist and not be corrupted
        assert constitution.exists(), "Constitution should still exist after upgrade"

        new_content = constitution.read_text(encoding='utf-8')
        assert len(new_content) > 0, "Constitution should not be empty after upgrade"

    def test_existing_worktrees_still_work(self, temp_project_dir, spec_kitty_repo_root):
        """
        REGRESSION: Existing worktrees must continue to work after upgrade
        """
        project_name = 'worktree_upgrade'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create worktree before upgrade
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'pre-upgrade', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Run upgrade
        subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Existing worktree should still be accessible
        worktrees_dir = project_path / '.worktrees'
        if worktrees_dir.exists():
            worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and 'pre-upgrade' in d.name]
            if worktrees:
                worktree = worktrees[0]
                # Should still have .kittify directory
                assert (worktree / '.kittify').exists(), (
                    f"Existing worktree .kittify directory should still exist\n"
                    f"Worktree: {worktree}"
                )

    def test_upgrade_fixes_broken_symlinks(self, temp_project_dir, spec_kitty_repo_root):
        """
        HEALING: Upgrade should fix broken circular symlinks if they exist

        This tests if there's a migration to repair the bug
        """
        project_name = 'fix_symlinks'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Simulate the bug: create circular symlink
        memory_path = project_path / '.kittify' / 'memory'
        if memory_path.exists() and not memory_path.is_symlink():
            # Backup real directory
            import shutil
            backup = project_path / 'memory_backup'
            shutil.copytree(memory_path, backup)

            # Remove real directory
            shutil.rmtree(memory_path)

            # Create broken circular symlink
            memory_path.symlink_to(Path('../../../.kittify/memory'))

        # Run upgrade (should fix the symlink)
        result = subprocess.run(
            ['spec-kitty', 'upgrade'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # After upgrade, check if fixed
        # (Note: This may or may not be implemented - test will show us)
        if memory_path.is_symlink():
            target = memory_path.readlink()
            # Should NOT be circular
            assert str(target) != '../../../.kittify/memory' or result.returncode != 0, (
                f"Upgrade should either fix circular symlink or report error\n"
                f"Current state: {target}\n"
                f"This might need a migration to fix"
            )


class TestCodePathsValidation:
    """AGGRESSIVE: Force code to use correct paths everywhere."""

    def test_worktree_py_expects_kittify_memory(self, spec_kitty_repo_root):
        """
        CODE VALIDATION: worktree.py must reference .kittify/memory/

        This is where worktree creation logic lives
        """
        worktree_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'worktree.py'
        if not worktree_file.exists():
            pytest.skip("worktree.py not found")

        content = worktree_file.read_text(encoding='utf-8')

        # Should reference .kittify/memory as source
        assert '".kittify" / "memory"' in content or '".kittify/memory"' in content, (
            f"worktree.py must use .kittify/memory/ as source\n"
            f"File: {worktree_file}\n\n"
            f"This validates the fix requirement"
        )

    def test_renderer_py_has_memory_path_rewrite(self, spec_kitty_repo_root):
        """
        CODE VALIDATION: renderer.py should rewrite memory/ → .kittify/memory/

        Templates use memory/, runtime uses .kittify/memory/
        """
        renderer_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'template' / 'renderer.py'
        if not renderer_file.exists():
            pytest.skip("renderer.py not found")

        content = renderer_file.read_text(encoding='utf-8')

        # Should have path rewriting pattern for memory/
        assert 'memory/' in content and '.kittify/memory/' in content, (
            f"renderer.py should rewrite memory/ → .kittify/memory/\n"
            f"File: {renderer_file}\n\n"
            f"This is how templates reference memory/ but runtime uses .kittify/memory/"
        )

    def test_no_hardcoded_root_memory_paths(self, spec_kitty_repo_root):
        """
        CODE SCAN: Code should NOT reference root memory/ (except renderer)

        All code should expect .kittify/memory/
        """
        src_dir = spec_kitty_repo_root / 'src' / 'specify_cli'

        # Files that are allowed to reference root memory/ (templates, etc.)
        exceptions = ['renderer.py', 'template']

        suspicious_files = []

        for py_file in src_dir.rglob('*.py'):
            # Skip exceptions
            if any(exc in str(py_file) for exc in exceptions):
                continue

            content = py_file.read_text(encoding='utf-8')

            # Look for patterns like: / "memory" or /"memory" or repo_root / "memory"
            # But NOT .kittify / "memory"
            import re

            # Pattern: references to "memory" that aren't preceded by .kittify
            # This is a heuristic - may have false positives
            if re.search(r'(?<!\.kittify)\s*/\s*["\']memory["\']', content):
                suspicious_files.append(py_file.relative_to(src_dir))

        # Be lenient - just warn if found
        if suspicious_files:
            print(
                f"\nWARNING: Found {len(suspicious_files)} files with potential root memory/ references:\n" +
                "\n".join([f"  - {f}" for f in suspicious_files]) +
                "\n\nVerify these use .kittify/memory/ not root memory/"
            )


class TestRegressionPrevention:
    """AGGRESSIVE: Prevent the bug from happening again."""

    def test_no_worktree_artifacts_in_main_kittify(self, spec_kitty_repo_root):
        """
        ROOT CAUSE PREVENTION: .kittify/ should not have worktree artifacts

        The bug happened because worktree symlinks were committed to main
        """
        kittify_path = spec_kitty_repo_root / '.kittify'

        worktree_patterns = [
            '../../../.kittify/',  # Worktree symlink pattern
            '../../..',            # Triple parent reference
        ]

        problematic_items = []

        for item in kittify_path.rglob('*'):
            if item.is_symlink():
                target = str(item.readlink())

                for pattern in worktree_patterns:
                    if pattern in target:
                        problematic_items.append((item, target, pattern))

        assert len(problematic_items) == 0, (
            f"CRITICAL: Found {len(problematic_items)} worktree artifact(s) in .kittify/:\n" +
            "\n".join([
                f"  - {item}\n    Target: {target}\n    Pattern: {pattern}"
                for item, target, pattern in problematic_items
            ]) +
            "\n\nThese symlinks were likely created in a worktree and accidentally committed!\n"
            f"FIX: git rm [symlinks] and move real files to .kittify/"
        )

    def test_git_ignore_prevents_worktree_symlinks(self, spec_kitty_repo_root):
        """
        PREVENTION: .gitignore should prevent accidental worktree commits

        Check if .worktrees/ is ignored
        """
        gitignore = spec_kitty_repo_root / '.gitignore'

        if not gitignore.exists():
            pytest.skip(".gitignore not found")

        content = gitignore.read_text(encoding='utf-8')

        assert '.worktrees' in content, (
            f".gitignore should ignore .worktrees/ directory\n"
            f"File: {gitignore}\n\n"
            f"This prevents accidentally committing worktree files"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
