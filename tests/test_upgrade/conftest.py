"""
Shared Fixtures and Helpers for Upgrade Tests

Provides fixtures for historical project states and helper functions
for creating test scenarios programmatically.

Fixtures Available:
- spec_kitty_repo_root: Path to spec-kitty repository
- v0_1_x_project: Old .specify/ directory structure
- v0_4_7_project: Missing git protection
- v0_6_4_project: Doubled commands bug (agentfunc scenario)
- v0_6_6_project: Current structure, missing metadata
- broken_mission_project: Corrupted mission.yaml

Helper Functions:
- create_project_with_worktrees: Add git worktrees to test project
- inject_custom_content: Add user content that should be preserved
- corrupt_metadata: Create malformed metadata for error tests
- create_conflicting_state: Create projects with specific conflicts
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest


# ============================================================================
# Session-Level Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def spec_kitty_repo_root():
    """Get spec-kitty repository root.

    Priority order:
    1. SPEC_KITTY_REPO environment variable
    2. Default: ~/Code/spec-kitty

    Raises:
        ValueError: If spec-kitty repo not found
    """
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path.home() / 'Code' / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "spec-kitty repository not found. "
        "Set SPEC_KITTY_REPO environment variable or place repo at ~/Code/spec-kitty"
    )


# ============================================================================
# Static Fixture Loaders
# ============================================================================

@pytest.fixture
def v0_1_x_project(tmp_path):
    """Load v0.1.x fixture (uses .specify/ directory).

    Represents oldest version with .specify/ directory that needs
    to be renamed to .kittify/.

    Returns:
        Path: Temporary copy of v0.1.x project
    """
    fixture_path = Path(__file__).parent / 'fixtures' / 'v0_1_x_project'
    project_path = tmp_path / 'v0_1_x_project'

    # Copy entire fixture
    shutil.copytree(fixture_path, project_path, symlinks=True)

    # Initialize git repo (fixtures can't store .git/ directories)
    subprocess.run(
        ['git', 'init'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'add', '.'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit for v0.1.x fixture'],
        cwd=project_path,
        capture_output=True,
        check=True
    )

    return project_path


@pytest.fixture
def v0_4_7_project(tmp_path):
    """Load v0.4.7 fixture (missing git protection).

    Represents project that needs:
    - .gitignore updated with agent directories
    - Pre-commit hooks installed
    - Commands renamed to command-templates

    Returns:
        Path: Temporary copy of v0.4.7 project
    """
    fixture_path = Path(__file__).parent / 'fixtures' / 'v0_4_7_project'
    project_path = tmp_path / 'v0_4_7_project'

    shutil.copytree(fixture_path, project_path, symlinks=True)

    # Initialize git repo (fixtures can't store .git/ directories)
    subprocess.run(
        ['git', 'init'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'add', '.'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit for v0.4.7 fixture'],
        cwd=project_path,
        capture_output=True,
        check=True
    )

    return project_path


@pytest.fixture
def v0_6_4_project(tmp_path):
    """Load v0.6.4 fixture (doubled commands bug - CRITICAL).

    This is the agentfunc scenario - most important fixture.

    Represents project with:
    - Template pollution (.kittify/templates/ shouldn't exist)
    - Old commands/ directories
    - Doubled slash commands in .claude/commands/

    Returns:
        Path: Temporary copy of v0.6.4 project
    """
    fixture_path = Path(__file__).parent / 'fixtures' / 'v0_6_4_project'
    project_path = tmp_path / 'v0_6_4_project'

    shutil.copytree(fixture_path, project_path, symlinks=True)

    # Initialize git repo (fixtures can't store .git/ directories)
    subprocess.run(
        ['git', 'init'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'add', '.'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit for v0.6.4 fixture'],
        cwd=project_path,
        capture_output=True,
        check=True
    )

    # Add old pre-commit-agent-check hook (v0.6.4 had hooks installed)
    hooks_dir = project_path / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / 'pre-commit-agent-check'
    hook_file.write_text("""#!/bin/bash
# Installed by spec-kitty v0.5.0
# Prevents committing agent configuration files

# Check for agent files in staged changes
if git diff --cached --name-only | grep -qE '^\\.claude/|^\\.codex/|^\\.gemini/'; then
    echo "ERROR: Agent configuration files detected in commit."
    exit 1
fi

exit 0
""")
    hook_file.chmod(0o755)

    return project_path


@pytest.fixture
def v0_6_6_project(tmp_path):
    """Load v0.6.6 fixture (current structure, missing metadata).

    Represents already-upgraded project that just needs metadata added.

    Returns:
        Path: Temporary copy of v0.6.6 project
    """
    fixture_path = Path(__file__).parent / 'fixtures' / 'v0_6_6_project'
    project_path = tmp_path / 'v0_6_6_project'

    shutil.copytree(fixture_path, project_path, symlinks=True)

    # Initialize git repo (fixtures can't store .git/ directories)
    subprocess.run(
        ['git', 'init'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'add', '.'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit for v0.6.6 fixture'],
        cwd=project_path,
        capture_output=True,
        check=True
    )

    return project_path


@pytest.fixture
def broken_mission_project(tmp_path):
    """Load broken_mission fixture (corrupted mission.yaml).

    Represents project where dashboard shows "Mission: Unknown mission"
    due to corrupted mission metadata. Affects "most people" according
    to user feedback.

    Returns:
        Path: Temporary copy of broken_mission project
    """
    fixture_path = Path(__file__).parent / 'fixtures' / 'broken_mission_project'
    project_path = tmp_path / 'broken_mission_project'

    shutil.copytree(fixture_path, project_path, symlinks=True)

    # Initialize git repo (fixtures can't store .git/ directories)
    subprocess.run(
        ['git', 'init'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'add', '.'],
        cwd=project_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ['git', 'commit', '-m', 'Initial commit for broken_mission fixture'],
        cwd=project_path,
        capture_output=True,
        check=True
    )

    return project_path


# ============================================================================
# Programmatic Project Creation Helpers
# ============================================================================

@pytest.fixture
def create_project_with_worktrees():
    """Factory fixture to create project with multiple worktrees.

    Returns:
        Callable: Function to create project with worktrees

    Example:
        >>> project = create_project_with_worktrees(
        ...     base_fixture=v0_6_4_project,
        ...     num_worktrees=2
        ... )
        >>> assert (project / '.worktrees' / 'feature-001').exists()
    """
    def _create(base_fixture: Path, num_worktrees: int = 2) -> Path:
        """Create worktrees for a project.

        Args:
            base_fixture: Path to base project fixture
            num_worktrees: Number of worktrees to create

        Returns:
            Path: Project path with worktrees created
        """
        # Worktrees directory
        worktrees_dir = base_fixture / '.worktrees'
        worktrees_dir.mkdir(exist_ok=True)

        # Create worktrees using git
        for i in range(num_worktrees):
            branch_name = f'feature-{i+1:03d}'
            worktree_path = worktrees_dir / branch_name

            # Create branch
            subprocess.run(
                ['git', 'branch', branch_name],
                cwd=base_fixture,
                capture_output=True,
                check=True
            )

            # Create worktree
            subprocess.run(
                ['git', 'worktree', 'add', str(worktree_path), branch_name],
                cwd=base_fixture,
                capture_output=True,
                check=True
            )

            # Copy .kittify from main (simulating spec-kitty's worktree setup)
            kittify_src = base_fixture / '.kittify'
            kittify_dst = worktree_path / '.kittify'
            if kittify_src.exists() and not kittify_dst.exists():
                shutil.copytree(kittify_src, kittify_dst, symlinks=True)

        return base_fixture

    return _create


@pytest.fixture
def inject_custom_content():
    """Factory to inject custom user content into projects.

    Used to test that user-created files are preserved during migration.

    Returns:
        Callable: Function to inject content

    Example:
        >>> inject_custom_content(
        ...     project_path,
        ...     '.kittify/memory/custom-notes.md',
        ...     '# My Custom Notes\\nImportant stuff'
        ... )
    """
    def _inject(project_path: Path, relative_path: str, content: str) -> None:
        """Inject custom content into project.

        Args:
            project_path: Project root directory
            relative_path: Path relative to project root
            content: File content to write
        """
        file_path = project_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    return _inject


@pytest.fixture
def corrupt_metadata():
    """Factory to create malformed metadata for error handling tests.

    Returns:
        Callable: Function to corrupt metadata

    Example:
        >>> corrupt_metadata(project_path, 'invalid_yaml')
        >>> corrupt_metadata(project_path, 'missing_version')
    """
    def _corrupt(project_path: Path, corruption_type: str) -> None:
        """Create corrupted metadata.yaml file.

        Args:
            project_path: Project root directory
            corruption_type: Type of corruption to introduce
                - 'invalid_yaml': Malformed YAML syntax
                - 'missing_version': Missing required version field
                - 'bad_date': Invalid date format
                - 'empty': Empty file
                - 'partial': Incomplete data structure
        """
        metadata_path = project_path / '.kittify' / 'metadata.yaml'
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        if corruption_type == 'invalid_yaml':
            metadata_path.write_text("""
spec_kitty:
  version: "0.6.7
  # ERROR: Unclosed quote above
  initialized_at: 2025-01-01T10:00:00Z

environment
  # ERROR: Missing colon above
  python_version: "3.11"
{invalid syntax}
""")

        elif corruption_type == 'missing_version':
            metadata_path.write_text("""
spec_kitty:
  # version field is MISSING
  initialized_at: 2025-01-01T10:00:00Z

environment:
  python_version: "3.11"
  platform: "darwin"
""")

        elif corruption_type == 'bad_date':
            metadata_path.write_text("""
spec_kitty:
  version: "0.6.7"
  initialized_at: "not a valid date"

environment:
  python_version: "3.11"
""")

        elif corruption_type == 'empty':
            metadata_path.write_text("")

        elif corruption_type == 'partial':
            metadata_path.write_text("""
spec_kitty:
  version: "0.6.7"
  # Missing everything else
""")

        else:
            raise ValueError(f"Unknown corruption type: {corruption_type}")

    return _corrupt


@pytest.fixture
def create_conflicting_state():
    """Factory to create projects with specific conflict scenarios.

    Returns:
        Callable: Function to create conflicts

    Example:
        >>> create_conflicting_state(
        ...     project_path,
        ...     ['both_specify_and_kittify', 'both_commands_and_templates']
        ... )
    """
    def _create(project_path: Path, conflicts: List[str]) -> None:
        """Create project with specific conflicts.

        Args:
            project_path: Project root directory
            conflicts: List of conflict types to create:
                - 'both_specify_and_kittify': Both .specify/ and .kittify/ exist
                - 'both_commands_and_templates': Both old and new command dirs
                - 'template_pollution': .kittify/templates/ exists (shouldn't)
                - 'missing_gitignore': .gitignore doesn't exist
                - 'no_git': No .git directory
        """
        for conflict in conflicts:
            if conflict == 'both_specify_and_kittify':
                # Create both old and new directories
                specify_dir = project_path / '.specify' / 'memory'
                specify_dir.mkdir(parents=True, exist_ok=True)
                (specify_dir / 'constitution.md').write_text("# Old structure")

                kittify_dir = project_path / '.kittify' / 'memory'
                kittify_dir.mkdir(parents=True, exist_ok=True)
                (kittify_dir / 'constitution.md').write_text("# New structure")

            elif conflict == 'both_commands_and_templates':
                # Create both old and new command directories
                old_dir = project_path / '.kittify' / 'missions' / 'software-dev' / 'commands'
                old_dir.mkdir(parents=True, exist_ok=True)
                (old_dir / 'specify.md').write_text("# Old commands/")

                new_dir = project_path / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
                new_dir.mkdir(parents=True, exist_ok=True)
                (new_dir / 'specify.md').write_text("# New command-templates/")

            elif conflict == 'template_pollution':
                # Create template pollution
                template_dir = project_path / '.kittify' / 'templates' / 'commands'
                template_dir.mkdir(parents=True, exist_ok=True)
                (template_dir / 'specify.md').write_text("# Template pollution")

            elif conflict == 'missing_gitignore':
                # Remove .gitignore if it exists
                gitignore = project_path / '.gitignore'
                if gitignore.exists():
                    gitignore.unlink()

            elif conflict == 'no_git':
                # Remove .git directory
                git_dir = project_path / '.git'
                if git_dir.exists():
                    shutil.rmtree(git_dir)

            else:
                raise ValueError(f"Unknown conflict type: {conflict}")

    return _create


# ============================================================================
# Helper Functions (not fixtures, but imported by tests)
# ============================================================================

def extract_json_from_output(output: str) -> Optional[dict]:
    """Extract JSON from script output that may contain log messages.

    Searches for the first line that looks like valid JSON.

    Args:
        output: Script output containing JSON (possibly mixed with logs)

    Returns:
        dict: Parsed JSON data, or None if no valid JSON found

    Example:
        >>> output = "Starting...\\n{\"status\": \"ok\"}\\nDone"
        >>> data = extract_json_from_output(output)
        >>> assert data['status'] == 'ok'
    """
    import json

    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return None


def count_files_in_directory(directory: Path, pattern: str = '*') -> int:
    """Count files matching pattern in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern (default: all files)

    Returns:
        int: Number of matching files

    Example:
        >>> count = count_files_in_directory(
        ...     project_path / '.claude' / 'commands',
        ...     'spec-kitty.*.md'
        ... )
    """
    if not directory.exists():
        return 0

    return len(list(directory.glob(pattern)))


def assert_file_contains(file_path: Path, expected_content: str, message: str = ""):
    """Assert that file contains expected content.

    Args:
        file_path: Path to file
        expected_content: Content that should be present
        message: Optional custom assertion message

    Raises:
        AssertionError: If content not found or file doesn't exist
    """
    assert file_path.exists(), f"File not found: {file_path}"

    content = file_path.read_text()
    assert expected_content in content, (
        message or
        f"Expected '{expected_content}' not found in {file_path}"
    )


def assert_file_not_contains(file_path: Path, unexpected_content: str, message: str = ""):
    """Assert that file does NOT contain unexpected content.

    Args:
        file_path: Path to file
        unexpected_content: Content that should NOT be present
        message: Optional custom assertion message

    Raises:
        AssertionError: If content found
    """
    if not file_path.exists():
        return  # File doesn't exist, so it definitely doesn't contain the content

    content = file_path.read_text()
    assert unexpected_content not in content, (
        message or
        f"Unexpected '{unexpected_content}' found in {file_path}"
    )


def get_git_current_branch(project_path: Path) -> str:
    """Get current git branch name.

    Args:
        project_path: Project root directory

    Returns:
        str: Branch name

    Raises:
        subprocess.CalledProcessError: If not a git repository
    """
    result = subprocess.run(
        ['git', 'branch', '--show-current'],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def is_symlink_relative(symlink_path: Path) -> bool:
    """Check if symlink uses relative path (not absolute).

    Args:
        symlink_path: Path to symlink

    Returns:
        bool: True if symlink target is relative

    Raises:
        ValueError: If path is not a symlink
    """
    if not symlink_path.is_symlink():
        raise ValueError(f"{symlink_path} is not a symlink")

    target = os.readlink(symlink_path)
    return not os.path.isabs(target)
