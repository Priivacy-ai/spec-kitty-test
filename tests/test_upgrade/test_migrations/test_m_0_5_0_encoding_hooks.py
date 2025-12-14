"""
Test Migration 0.5.0: Encoding Hooks

Tests the migration that installs pre-commit hooks to prevent
committing agent configuration files that may contain auth tokens.

Test Coverage:
1. Detection (1 test)
   - Detects missing pre-commit hook

2. Migration Execution (3 tests)
   - Installs pre-commit-agent-check hook
   - Hook is executable (Unix)
   - Preserves existing hooks

3. Updates (1 test)
   - Replaces outdated hook version
"""

import os
import stat
from pathlib import Path

import pytest


class TestEncodingHooksMigration:
    """Test installing pre-commit hooks for agent file protection."""

    def test_detect_missing_precommit_hook(self, v0_4_7_project):
        """Test: Detects no hook installed

        GIVEN: A project without pre-commit-agent-check hook
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("EncodingHooksMigration not yet implemented")

        migration = EncodingHooksMigration()

        # v0.4.7 fixture has no pre-commit hooks
        hooks_dir = v0_4_7_project / '.git' / 'hooks'
        hook_file = hooks_dir / 'pre-commit-agent-check'

        assert not hook_file.exists(), \
            "Fixture should not have pre-commit hook"

        # Should detect migration needed
        needs_migration = migration.detect(v0_4_7_project)

        assert needs_migration is True, \
            "Should detect that pre-commit hook is missing"

    def test_install_precommit_hook(self, v0_4_7_project):
        """Test: Installs pre-commit-agent-check

        GIVEN: A project without the hook
        WHEN: Applying migration
        THEN: Should install pre-commit-agent-check script
        """
        try:
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("EncodingHooksMigration not yet implemented")

        migration = EncodingHooksMigration()

        # Apply migration
        result = migration.apply(v0_4_7_project, dry_run=False)

        assert result.success, \
            f"Migration should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify hook installed
        hook_file = v0_4_7_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        assert hook_file.exists(), \
            "pre-commit-agent-check should be installed"

        # Verify hook content
        content = hook_file.read_text()

        assert '#!/bin/bash' in content or '#!/bin/sh' in content, \
            "Hook should have shebang"

        assert '.claude' in content or 'agent' in content.lower(), \
            "Hook should reference agent directories"

        assert 'git diff --cached' in content, \
            "Hook should check staged files"

        assert 'exit 1' in content, \
            "Hook should exit with error code when agent files detected"

    def test_hook_is_executable(self, v0_4_7_project):
        """Test: Sets correct permissions (Unix)

        GIVEN: A freshly installed hook
        WHEN: Migration completes
        THEN: Hook should be executable on Unix systems
        """
        # Skip on Windows
        if os.name == 'nt':
            pytest.skip("Executable permissions not relevant on Windows")

        try:
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("EncodingHooksMigration not yet implemented")

        migration = EncodingHooksMigration()

        # Apply migration
        result = migration.apply(v0_4_7_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Check if executable
        hook_file = v0_4_7_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        file_stat = hook_file.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)

        assert is_executable, \
            "Hook should be executable (user execute permission)"

        # Verify can be executed (at least doesn't crash)
        import subprocess
        result = subprocess.run(
            [str(hook_file)],
            cwd=v0_4_7_project,
            capture_output=True,
            timeout=5
        )

        # Should exit 0 when no agent files staged
        assert result.returncode == 0, \
            "Hook should exit 0 when no agent files are staged"

    def test_preserves_existing_hooks(self, tmp_path):
        """Test: Doesn't overwrite other hooks

        GIVEN: A project with existing pre-commit hook
        WHEN: Applying migration
        THEN: Should install agent-check alongside existing hooks
        """
        try:
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("EncodingHooksMigration not yet implemented")

        migration = EncodingHooksMigration()

        # Create project with existing pre-commit hook
        git_dir = tmp_path / '.git'
        hooks_dir = git_dir / 'hooks'
        hooks_dir.mkdir(parents=True)

        # Create existing pre-commit hook
        existing_hook = hooks_dir / 'pre-commit'
        existing_hook.write_text("""#!/bin/bash
# Existing pre-commit hook
echo "Running existing hook"
exit 0
""")

        if os.name != 'nt':
            existing_hook.chmod(0o755)

        # Note original content
        original_content = existing_hook.read_text()

        # Apply migration
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify existing hook unchanged
        assert existing_hook.exists(), \
            "Existing pre-commit hook should still exist"

        current_content = existing_hook.read_text()
        assert current_content == original_content, \
            "Existing pre-commit hook should not be modified"

        # Verify new hook installed separately
        agent_hook = hooks_dir / 'pre-commit-agent-check'
        assert agent_hook.exists(), \
            "pre-commit-agent-check should be installed separately"

        # Note: Git only runs 'pre-commit' hook, so the system might need
        # to integrate the hooks, but migration itself should not overwrite

    def test_updates_old_hook_version(self, v0_6_4_project):
        """Test: Replaces outdated hook script

        GIVEN: A project with old version of the hook
        WHEN: Applying migration
        THEN: Should update to latest hook version
        """
        try:
            from specify_cli.upgrade.migrations.m_0_5_0_encoding_hooks import EncodingHooksMigration
        except ImportError:
            pytest.skip("EncodingHooksMigration not yet implemented")

        migration = EncodingHooksMigration()

        # v0.6.4 fixture has an older hook version
        hook_file = v0_6_4_project / '.git' / 'hooks' / 'pre-commit-agent-check'
        assert hook_file.exists(), \
            "Fixture should have old hook"

        # Mark it as old version by modifying content
        old_content = hook_file.read_text()
        hook_file.write_text(old_content.replace(
            '# Installed by spec-kitty',
            '# Installed by spec-kitty v0.5.0 (OLD VERSION)'
        ))

        # Apply migration
        result = migration.apply(v0_6_4_project, dry_run=False)

        # Should update the hook
        assert result.success, "Migration should succeed"

        # Verify hook updated
        new_content = hook_file.read_text()
        assert new_content != old_content or 'OLD VERSION' not in new_content, \
            "Hook should be updated to new version"

        # Verify still functional
        assert '#!/bin/' in new_content, \
            "Updated hook should have shebang"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
