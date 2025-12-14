"""
Test Migration 0.4.8: Gitignore Agents

Tests the migration that adds all 12 agent directories + .github/copilot/
to the .gitignore file to prevent accidental commits of auth tokens.

Test Coverage:
1. Detection (1 test)
   - Detects incomplete .gitignore

2. Migration Execution (3 tests)
   - Adds all 12 agent directories
   - Preserves existing .gitignore content
   - Creates .gitignore if missing

3. Idempotency (1 test)
   - Already has agents → skips
"""

from pathlib import Path

import pytest


class TestGitignoreAgentsMigration:
    """Test adding agent directories to .gitignore."""

    def test_detect_missing_agent_dirs(self, v0_4_7_project):
        """Test: Detects incomplete .gitignore

        GIVEN: A project with .gitignore missing agent directories
        WHEN: Running detect()
        THEN: Should return True (migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        migration = GitignoreAgentsMigration()

        # Should detect missing agent dirs
        needs_migration = migration.detect(v0_4_7_project)

        assert needs_migration is True, \
            "Should detect that .gitignore needs agent directories"

        # Verify .gitignore exists but is incomplete
        gitignore = v0_4_7_project / '.gitignore'
        assert gitignore.exists(), \
            "Fixture should have .gitignore"

        content = gitignore.read_text()
        assert '.claude/' not in content, \
            "Fixture .gitignore should not have .claude/"

    def test_add_all_12_agent_directories(self, v0_4_7_project):
        """Test: Adds all agent dirs + .github/copilot/

        GIVEN: A project with incomplete .gitignore
        WHEN: Applying migration
        THEN: Should add all 12 agent dirs plus .github/copilot/
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        migration = GitignoreAgentsMigration()

        # Apply migration
        result = migration.apply(v0_4_7_project, dry_run=False)

        assert result.success, \
            f"Migration should succeed. Error: {result.error if hasattr(result, 'error') else 'N/A'}"

        # Verify all agent directories added
        gitignore = v0_4_7_project / '.gitignore'
        content = gitignore.read_text()

        required_entries = [
            '.claude/',
            '.codex/',
            '.gemini/',
            '.cursor/',
            '.qwen/',
            '.opencode/',
            '.windsurf/',
            '.kilocode/',
            '.augment/',
            '.roo/',
            '.amazonq/',
            '.github/copilot/'
        ]

        missing = []
        for entry in required_entries:
            if entry not in content:
                missing.append(entry)

        assert not missing, \
            f".gitignore missing required entries: {missing}"

    def test_preserve_existing_gitignore(self, v0_4_7_project):
        """Test: Appends, doesn't overwrite

        GIVEN: A project with existing .gitignore content
        WHEN: Applying migration
        THEN: Should append agent dirs, preserving existing content
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        migration = GitignoreAgentsMigration()

        # Note existing content
        gitignore = v0_4_7_project / '.gitignore'
        original_content = gitignore.read_text()

        # Verify has some content (from fixture)
        assert '__pycache__/' in original_content, \
            "Fixture should have existing .gitignore entries"

        # Apply migration
        result = migration.apply(v0_4_7_project, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify original content still present
        new_content = gitignore.read_text()

        assert '__pycache__/' in new_content, \
            "Original __pycache__/ entry should be preserved"

        assert 'venv/' in new_content, \
            "Original venv/ entry should be preserved"

        assert '.DS_Store' in new_content, \
            "Original .DS_Store entry should be preserved"

        # Verify new content added
        assert '.claude/' in new_content, \
            "Should have added .claude/"

        # Verify not duplicated if run twice would be tested in idempotency test

    def test_handles_no_gitignore(self, tmp_path):
        """Test: Creates .gitignore if missing

        GIVEN: A project with no .gitignore file
        WHEN: Applying migration
        THEN: Should create .gitignore with agent directories
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        migration = GitignoreAgentsMigration()

        # Create minimal project with no .gitignore
        (tmp_path / '.kittify').mkdir()

        # Verify no .gitignore
        gitignore = tmp_path / '.gitignore'
        assert not gitignore.exists(), \
            "Project should not have .gitignore initially"

        # Apply migration
        result = migration.apply(tmp_path, dry_run=False)

        assert result.success, "Migration should succeed"

        # Verify .gitignore created
        assert gitignore.exists(), \
            ".gitignore should be created"

        # Verify has agent directories
        content = gitignore.read_text()
        assert '.claude/' in content, \
            "Created .gitignore should have .claude/"

        assert '.github/copilot/' in content, \
            "Created .gitignore should have .github/copilot/"

    def test_already_has_agents_skips(self, v0_6_4_project):
        """Test: Idempotent if already present

        GIVEN: A project with complete .gitignore (has all agents)
        WHEN: Running detect()
        THEN: Should return False (no migration needed)
        """
        try:
            from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import GitignoreAgentsMigration
        except ImportError:
            pytest.skip("GitignoreAgentsMigration not yet implemented")

        migration = GitignoreAgentsMigration()

        # v0.6.4 fixture already has complete .gitignore
        gitignore = v0_6_4_project / '.gitignore'
        assert gitignore.exists(), \
            "Fixture should have .gitignore"

        content = gitignore.read_text()
        assert '.claude/' in content, \
            "Fixture should already have .claude/"

        # Should NOT detect migration need
        needs_migration = migration.detect(v0_6_4_project)

        assert not needs_migration, \
            "Should not need migration when .gitignore is complete"

        # If we apply anyway, should be safe (no duplicates)
        line_count_before = len(gitignore.read_text().split('\n'))

        result = migration.apply(v0_6_4_project, dry_run=False)

        # Should either skip or be safe
        line_count_after = len(gitignore.read_text().split('\n'))

        # Should not significantly increase (no duplication)
        assert abs(line_count_after - line_count_before) < 5, \
            "Should not duplicate entries if already present"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
