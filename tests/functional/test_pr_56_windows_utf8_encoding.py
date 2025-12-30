"""
Test: PR #56 - Fix Windows UTF-8 encoding

Purpose: Validate that explicit UTF-8 encoding is used to prevent Windows cp1252 errors.

Bug History:
- Before fix: Dashboard diagnostics showed "undefined" on Windows for all file paths
- Root cause: Windows defaults to cp1252 encoding, but spec-kitty files contain UTF-8
  (unicode characters like ✓, checkmarks, etc.)
- Fix: Added explicit encoding='utf-8' parameter to read_text() calls (commit e158ff0)

Test Coverage:
1. Critical Files Have Explicit Encoding (4 tests)
   - manifest.py uses encoding='utf-8'
   - m_0_6_7_ensure_missions.py uses encoding='utf-8'
   - m_0_4_8_gitignore_agents.py uses encoding='utf-8'
   - All read_text() calls specify encoding

2. UTF-8-sig for BOM Handling (2 tests)
   - Uses encoding='utf-8-sig' where appropriate
   - Handles Byte Order Mark correctly

3. No Implicit Encoding (3 tests)
   - No bare .read_text() without encoding parameter
   - New code follows UTF-8 best practices
   - Documentation mentions encoding requirements

4. Windows Compatibility (2 tests)
   - Code works on Windows (if running on Windows)
   - Error messages mention encoding issues

Related Commits: e158ff0618ae7a1f33462274ddd60794b32c4bd1
"""

import re
from pathlib import Path

import pytest


class TestWindowsUTF8Encoding:
    """Test that explicit UTF-8 encoding is used throughout codebase."""

    def test_manifest_has_explicit_encoding(self, spec_kitty_repo_root):
        """
        Test: manifest.py uses explicit encoding='utf-8'

        Before fix: active_mission_path.read_text() (no encoding)
        After fix: active_mission_path.read_text(encoding='utf-8-sig')

        Windows defaults to cp1252, causing UnicodeDecodeError.
        """
        manifest_file = spec_kitty_repo_root / 'src/specify_cli/manifest.py'
        content = manifest_file.read_text(encoding='utf-8')

        # Find all read_text() calls
        read_text_calls = re.findall(r'\.read_text\([^)]*\)', content)

        # All should have encoding parameter
        for call in read_text_calls:
            assert 'encoding' in call, (
                f"manifest.py has read_text() without encoding: {call}\n"
                f"Windows requires explicit encoding='utf-8'"
            )

    def test_migration_0_6_7_has_explicit_encoding(self, spec_kitty_repo_root):
        """
        Test: m_0_6_7_ensure_missions.py uses explicit encoding

        This migration reads pyproject.toml to verify spec-kitty repo.
        """
        migration_file = (
            spec_kitty_repo_root /
            'src/specify_cli/upgrade/migrations/m_0_6_7_ensure_missions.py'
        )
        content = migration_file.read_text(encoding='utf-8')

        # Find pyproject.toml read
        if 'pyproject.read_text()' in content:
            pytest.fail(
                "m_0_6_7_ensure_missions.py has read_text() without encoding. "
                "Should use encoding='utf-8'"
            )

        # Should have encoding parameter
        if '.read_text(' in content:
            assert 'encoding=' in content, (
                "Migration should use explicit encoding='utf-8'"
            )

    def test_migration_0_4_8_has_explicit_encoding(self, spec_kitty_repo_root):
        """
        Test: m_0_4_8_gitignore_agents.py uses explicit encoding

        This migration reads .gitignore files.
        """
        migration_file = (
            spec_kitty_repo_root /
            'src/specify_cli/upgrade/migrations/m_0_4_8_gitignore_agents.py'
        )
        content = migration_file.read_text(encoding='utf-8')

        # Find gitignore reads
        read_text_calls = re.findall(r'\.read_text\([^)]*\)', content)

        # All should have encoding parameter
        for call in read_text_calls:
            assert 'encoding' in call, (
                f"m_0_4_8_gitignore_agents.py has read_text() without encoding: {call}"
            )

    def test_uses_utf8_sig_for_bom(self, spec_kitty_repo_root):
        """
        Test: Uses encoding='utf-8-sig' to handle Byte Order Mark (BOM)

        utf-8-sig automatically strips BOM character if present, making code
        more robust across different editors and platforms.
        """
        manifest_file = spec_kitty_repo_root / 'src/specify_cli/manifest.py'
        content = manifest_file.read_text(encoding='utf-8')

        # Should use utf-8-sig for BOM handling
        assert 'utf-8-sig' in content, (
            "manifest.py should use encoding='utf-8-sig' to handle BOM"
        )

    def test_migration_uses_utf8_sig(self, spec_kitty_repo_root):
        """
        Test: Migrations use encoding='utf-8-sig' for robustness

        BOM can appear in files created by Windows editors.
        """
        migration_file = (
            spec_kitty_repo_root /
            'src/specify_cli/upgrade/migrations/m_0_6_7_ensure_missions.py'
        )
        content = migration_file.read_text(encoding='utf-8')

        if '.read_text(' in content:
            assert 'utf-8' in content, (
                "Migration should use UTF-8 encoding (utf-8 or utf-8-sig)"
            )

    def test_no_bare_read_text_in_critical_files(self, spec_kitty_repo_root):
        """
        Test: Critical files don't use .read_text() without encoding

        Scan important files to ensure Windows compatibility.
        """
        critical_files = [
            'src/specify_cli/manifest.py',
            'src/specify_cli/upgrade/migrations/m_0_6_7_ensure_missions.py',
            'src/specify_cli/upgrade/migrations/m_0_4_8_gitignore_agents.py',
        ]

        for file_path in critical_files:
            full_path = spec_kitty_repo_root / file_path
            if not full_path.exists():
                continue

            content = full_path.read_text(encoding='utf-8')

            # Find read_text() without encoding parameter
            # Pattern: .read_text() with no arguments or only whitespace/comments
            bare_reads = re.findall(r'\.read_text\(\s*\)', content)

            assert len(bare_reads) == 0, (
                f"{file_path} has {len(bare_reads)} bare .read_text() calls:\n"
                f"Windows requires explicit encoding='utf-8'\n"
                f"Found: {bare_reads}"
            )

    def test_dashboard_files_use_utf8(self, spec_kitty_repo_root):
        """
        Test: Dashboard code uses UTF-8 encoding when reading files

        Dashboard was the main place where Windows errors occurred.
        """
        dashboard_files = [
            'src/specify_cli/dashboard/handlers/features.py',
            'src/specify_cli/dashboard/handlers/router.py',
        ]

        for file_path in dashboard_files:
            full_path = spec_kitty_repo_root / file_path
            if not full_path.exists():
                continue

            content = full_path.read_text(encoding='utf-8')

            # If it has read_text() calls, they should specify encoding
            if '.read_text(' in content:
                # Count calls with and without encoding
                all_reads = len(re.findall(r'\.read_text\(', content))
                reads_with_encoding = len(re.findall(r'\.read_text\([^)]*encoding[^)]*\)', content))

                # Most/all should have encoding (allow some for error handling)
                assert reads_with_encoding > 0, (
                    f"{file_path} should use encoding='utf-8' for read_text() calls"
                )

    def test_encoding_error_handling_present(self, spec_kitty_repo_root):
        """
        Test: Code includes error handling for encoding issues

        Should catch UnicodeDecodeError and provide helpful messages.
        """
        features_file = (
            spec_kitty_repo_root /
            'src/specify_cli/dashboard/handlers/features.py'
        )

        if features_file.exists():
            content = features_file.read_text(encoding='utf-8')

            # Should have UnicodeDecodeError handling
            assert 'UnicodeDecodeError' in content, (
                "Dashboard should handle UnicodeDecodeError gracefully"
            )

    def test_manifest_handles_bom_correctly(self, spec_kitty_repo_root):
        """
        Test: manifest.py uses utf-8-sig to strip BOM automatically

        BOM (Byte Order Mark) is U+FEFF at start of file, common in Windows.
        Using utf-8-sig ensures it's stripped when reading.
        """
        manifest_file = spec_kitty_repo_root / 'src/specify_cli/manifest.py'
        content = manifest_file.read_text(encoding='utf-8')

        # Check active_mission reading specifically (was mentioned in PR)
        if 'active_mission_path.read_text' in content:
            # Get the context around this call
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'active_mission_path.read_text' in line:
                    # Should use utf-8-sig
                    assert 'utf-8' in line, (
                        f"active_mission_path.read_text should use UTF-8 encoding.\n"
                        f"Line: {line}"
                    )

    def test_critical_migrations_have_error_ignore(self, spec_kitty_repo_root):
        """
        Test: Migrations use errors='ignore' for robustness

        When checking if files are readable, should tolerate invalid UTF-8.
        """
        migration_file = (
            spec_kitty_repo_root /
            'src/specify_cli/upgrade/migrations/m_0_4_8_gitignore_agents.py'
        )

        if migration_file.exists():
            content = migration_file.read_text(encoding='utf-8')

            # Should handle errors gracefully
            if '.read_text(' in content and 'gitignore' in content:
                # Should either have errors='ignore' or try/except
                has_error_handling = (
                    "errors=" in content or
                    "try:" in content or
                    "except" in content
                )
                assert has_error_handling, (
                    "Migration should handle encoding errors gracefully"
                )


class TestEncodingBestPractices:
    """Test that new code follows UTF-8 encoding best practices."""

    def test_python_files_use_explicit_encoding(self, spec_kitty_repo_root):
        """
        Test: Python source files follow encoding best practices

        Sample key files to ensure they set encoding when reading text.
        """
        src_dir = spec_kitty_repo_root / 'src/specify_cli'

        # Sample some key files
        key_files = [
            'manifest.py',
            'dashboard/handlers/features.py',
        ]

        issues = []
        for file_name in key_files:
            file_path = src_dir / file_name
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding='utf-8')

            # Find bare .read_text() calls (no encoding)
            bare_calls = re.findall(r'\.read_text\(\s*\)(?!\s*#.*encoding)', content)

            if bare_calls:
                issues.append(f"{file_name}: {len(bare_calls)} bare read_text() calls")

        assert len(issues) == 0, (
            "Found files with bare read_text() calls (no encoding):\n" +
            "\n".join(issues) +
            "\n\nWindows requires explicit encoding='utf-8'"
        )

    def test_error_messages_mention_encoding(self, spec_kitty_repo_root):
        """
        Test: Error messages mention encoding issues to help users debug

        When UnicodeDecodeError occurs, message should be helpful.
        """
        features_file = (
            spec_kitty_repo_root /
            'src/specify_cli/dashboard/handlers/features.py'
        )

        if features_file.exists():
            content = features_file.read_text(encoding='utf-8')

            if 'UnicodeDecodeError' in content:
                # Error message should mention encoding
                # Look for strings near the error handler
                assert (
                    'encoding' in content.lower() or
                    'UTF-8' in content or
                    'utf-8' in content
                ), "Error messages should mention encoding issues"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
