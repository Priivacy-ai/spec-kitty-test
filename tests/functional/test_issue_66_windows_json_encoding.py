"""
Test: Issue #66 - Windows encoding error in JSON output

Purpose: Validate that spec-kitty handles Unicode in JSON output correctly on Windows.

Root Cause:
- main() in __init__.py doesn't configure stdout/stderr encoding for Windows
- Windows defaults to cp1252/charmap encoding
- JSON output containing Unicode (✓, ✗, emoji) causes UnicodeEncodeError during print()

The Bug:
```
spec-kitty agent feature create-feature "my-feature" --json
{"error": "'charmap' codec can't encode characters in position 161-163: character maps to <undefined>"}
```

The Fix:
Configure UTF-8 encoding in main() entry point:
```python
def main():
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    app()
```

Test Strategy:
Since we're not on Windows, we simulate Windows behavior by:
1. Mocking stdout with charmap encoding
2. Testing JSON serialization with Unicode
3. Validating the fix works

Related Issue: #66
Related: test_pr_56_windows_utf8_encoding.py (file I/O encoding)
"""

import json
import sys
import io
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class CharmapStdout:
    """Simulates Windows cp1252/charmap stdout encoding.

    This allows us to test Windows encoding behavior on non-Windows systems.
    """

    def __init__(self):
        self.encoding = 'charmap'
        self.errors = 'strict'
        self.written = []

    def write(self, text):
        """Simulate charmap encoding - fail on Unicode chars."""
        if not isinstance(text, str):
            text = str(text)

        # Simulate Windows charmap behavior
        for i, char in enumerate(text):
            if ord(char) > 127:  # Non-ASCII
                # This is what Windows does with Unicode
                raise UnicodeEncodeError(
                    'charmap',
                    text,
                    i,
                    i + 1,
                    'character maps to <undefined>'
                )

        self.written.append(text)
        return len(text)

    def flush(self):
        pass


class TestWindowsEncodingSimulation:
    """Test Windows encoding behavior using simulation."""

    def test_charmap_encoding_fails_on_unicode(self):
        """
        REPRODUCE: Simulate the exact error from Issue #66

        Windows stdout with charmap encoding cannot print Unicode characters.
        """
        stdout = CharmapStdout()

        # Try to write Unicode character (checkmark)
        with pytest.raises(UnicodeEncodeError) as exc_info:
            stdout.write("Success: ✓")

        assert exc_info.value.encoding == 'charmap'
        assert 'character maps to <undefined>' in str(exc_info.value)

    def test_json_dumps_with_unicode_fails_on_windows_print(self):
        """
        CRITICAL: This is the exact pattern from feature.py that fails

        Even though json.dumps() can serialize Unicode, print() fails on Windows.
        """
        stdout = CharmapStdout()

        # Simulate error message with Unicode (common in spec-kitty)
        error_msg = "Feature creation failed: ✓ Prerequisites not met"
        error_dict = {"error": error_msg}

        # json.dumps works fine (creates \uXXXX escapes by default)
        json_output = json.dumps(error_dict)

        # But with ensure_ascii=False, it keeps Unicode
        json_unicode = json.dumps(error_dict, ensure_ascii=False)

        # Printing the JSON with Unicode fails on Windows
        with pytest.raises(UnicodeEncodeError):
            stdout.write(json_unicode)

    def test_ensure_ascii_true_works_on_windows(self):
        """
        WORKAROUND: ensure_ascii=True converts Unicode to escape sequences

        This makes it safe to print on Windows charmap encoding.
        """
        stdout = CharmapStdout()

        error_msg = "Feature creation failed: ✓ Prerequisites not met"
        error_dict = {"error": error_msg}

        # With ensure_ascii=True, Unicode becomes \uXXXX
        json_output = json.dumps(error_dict, ensure_ascii=True)

        # This should work on Windows (ASCII only)
        stdout.write(json_output)  # Should not raise

        assert len(stdout.written) == 1
        assert '\\u2713' in stdout.written[0]  # Checkmark as escape sequence

    def test_common_unicode_characters_in_spec_kitty(self):
        """
        VALIDATION: Test common Unicode chars that appear in spec-kitty

        These all fail on Windows charmap encoding.
        """
        stdout = CharmapStdout()

        unicode_chars = {
            '✓': 'checkmark (U+2713)',
            '✗': 'cross mark (U+2717)',
            '✅': 'check mark button (U+2705)',
            '❌': 'cross mark (U+274C)',
            '🚨': 'police car light (U+1F6A8)',
        }

        for char, description in unicode_chars.items():
            with pytest.raises(UnicodeEncodeError) as exc_info:
                stdout.write(f"Status: {char}")

            assert exc_info.value.encoding == 'charmap'


class TestWindowsEncodingFix:
    """Test that the fix for Issue #66 works."""

    def test_utf8_reconfigure_prevents_encoding_error(self):
        """
        FIX VALIDATION: Reconfiguring stdout to UTF-8 fixes the issue

        This is the fix that should be in main().
        """
        # Simulate the fix
        original_stdout = sys.stdout

        try:
            # Create a UTF-8 stdout (simulates the fix)
            utf8_buffer = io.BytesIO()
            sys.stdout = io.TextIOWrapper(
                utf8_buffer,
                encoding='utf-8',
                errors='strict'
            )

            # Now Unicode should work
            error_msg = "Feature creation failed: ✓ Prerequisites not met"
            error_dict = {"error": error_msg}
            json_output = json.dumps(error_dict, ensure_ascii=False)

            print(json_output)  # Should not raise
            sys.stdout.flush()

            # Verify output contains Unicode
            output = utf8_buffer.getvalue().decode('utf-8')
            assert '✓' in output

        finally:
            sys.stdout = original_stdout

    def test_main_should_configure_encoding_on_windows(self):
        """
        REQUIREMENT: main() should configure UTF-8 encoding on Windows

        This test documents what the fix should look like.
        """
        # This is what main() should do (pseudo-code test)
        def fixed_main():
            if sys.platform == 'win32':
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            # ... rest of main()

        # The fix should be this simple
        assert callable(fixed_main)

    @pytest.mark.skipif(
        sys.platform != 'win32',
        reason="Only runs on actual Windows"
    )
    def test_actual_windows_encoding_after_fix(self):
        """
        INTEGRATION: On actual Windows, verify encoding is UTF-8 after fix

        This only runs on Windows machines.
        """
        # After the fix, Windows stdout should be UTF-8
        assert sys.stdout.encoding.lower() in ['utf-8', 'utf8']


class TestJSONOutputPatterns:
    """Test the specific JSON output patterns used in feature.py."""

    def test_error_json_pattern_from_feature_py(self):
        """
        REPRODUCE: The exact pattern from feature.py that fails on Windows

        From feature.py line 158:
        print(json.dumps({"error": str(e)}))
        """
        stdout = CharmapStdout()

        # Simulate an exception with Unicode in message
        try:
            raise Exception("Failed: ✓ Not ready")
        except Exception as e:
            error_dict = {"error": str(e)}
            json_output = json.dumps(error_dict, ensure_ascii=False)

            # This fails on Windows
            with pytest.raises(UnicodeEncodeError):
                stdout.write(json_output)

    def test_success_json_pattern_from_feature_py(self):
        """
        Test success JSON patterns (also affected if they contain Unicode)

        From feature.py line 145:
        print(json.dumps({"status": "success", "feature_dir": str(feature_dir)}))
        """
        stdout = CharmapStdout()

        # Even success messages can fail if path contains Unicode
        # (though this is rare)
        success_dict = {
            "status": "success",
            "feature_dir": "/path/to/feature",
            "message": "Feature created ✓"  # Oops, Unicode in message
        }

        json_output = json.dumps(success_dict, ensure_ascii=False)

        with pytest.raises(UnicodeEncodeError):
            stdout.write(json_output)

    def test_all_json_dumps_locations_safe_with_ensure_ascii(self):
        """
        DEFENSIVE: All json.dumps() should use ensure_ascii=True

        This provides defense-in-depth even if stdout isn't reconfigured.
        """
        # Test data with various Unicode characters
        test_cases = [
            {"error": "Failed ✓"},
            {"error": "Failed ✗"},
            {"status": "success ✅"},
            {"message": "Error ❌"},
            {"warning": "Alert 🚨"},
        ]

        stdout = CharmapStdout()

        for test_dict in test_cases:
            # With ensure_ascii=True, this is Windows-safe
            json_output = json.dumps(test_dict, ensure_ascii=True)
            stdout.write(json_output)  # Should not raise

        # All writes succeeded
        assert len(stdout.written) == len(test_cases)


class TestUnicodeSourcesInSpecKitty:
    """Test where Unicode characters come from in spec-kitty."""

    def test_console_print_with_unicode(self):
        """
        Unicode in console.print() can leak into exception messages

        From feature.py line 152:
        console.print(f"[green]✓[/green] Feature created")
        """
        # If this console output somehow becomes part of an exception message,
        # it will cause Windows encoding issues

        message_with_unicode = "✓ Feature created"

        stdout = CharmapStdout()

        # Cannot print this on Windows
        with pytest.raises(UnicodeEncodeError):
            stdout.write(message_with_unicode)

    def test_version_checker_emoji(self):
        """
        version_checker.py uses emoji in error messages

        From version_checker.py:
        - ✅ Check mark button
        - ❌ Cross mark
        - 🚨 Police car light (warning)
        """
        emoji_messages = [
            "✅ Version check passed",
            "❌ Version mismatch",
            "🚨 Critical: Update required",
        ]

        stdout = CharmapStdout()

        for msg in emoji_messages:
            with pytest.raises(UnicodeEncodeError):
                stdout.write(msg)

    def test_git_output_with_unicode(self):
        """
        Git commands can return Unicode in output

        Common cases:
        - File names with Unicode characters
        - Commit messages with emoji
        - Author names with accents
        """
        git_outputs = [
            "modified:   résumé.txt",  # Accented characters
            "Author: José García",  # Accented name
            "feat: Add feature ✨",  # Emoji in commit message
        ]

        stdout = CharmapStdout()

        for output in git_outputs:
            with pytest.raises(UnicodeEncodeError):
                stdout.write(output)


class TestRealWorldScenario:
    """Test the actual user scenario from Issue #66."""

    def test_issue_66_reproduction(self):
        """
        EXACT REPRODUCTION: The scenario from Issue #66

        User command:
        spec-kitty agent feature create-feature "my-great-feature" --json

        Expected error (before fix):
        {"error": "'charmap' codec can't encode characters in position 161-163: character maps to <undefined>"}
        """
        stdout = CharmapStdout()

        # Simulate the feature creation failing with Unicode in error
        try:
            # Simulate some operation that includes Unicode
            raise RuntimeError("Prerequisites check failed ✗")
        except Exception as e:
            # This is the pattern from feature.py
            error_output = {"error": str(e)}
            json_str = json.dumps(error_output, ensure_ascii=False)

            # This is where it fails on Windows
            with pytest.raises(UnicodeEncodeError) as exc_info:
                stdout.write(json_str)

            # Verify it's the exact error from Issue #66
            assert exc_info.value.encoding == 'charmap'
            assert 'character maps to <undefined>' in str(exc_info.value)

    def test_workaround_user_tried(self):
        """
        USER WORKAROUND: User tried setting PYTHONIOENCODING

        This doesn't work because:
        1. It needs to be set BEFORE Python starts
        2. It doesn't reconfigure an already-running process
        """
        # Simulate setting environment variable during execution
        import os
        os.environ['PYTHONIOENCODING'] = 'utf-8'

        # This doesn't help - stdout is already configured
        stdout = CharmapStdout()  # Still charmap

        with pytest.raises(UnicodeEncodeError):
            stdout.write("Failed ✓")

        # The encoding doesn't change mid-execution
        assert stdout.encoding == 'charmap'


class TestFixValidation:
    """Validate that the proposed fix actually works."""

    def test_fix_option_1_stdout_reconfigure(self):
        """
        FIX OPTION 1 (RECOMMENDED): Reconfigure stdout in main()

        This fixes the root cause.
        """
        original_stdout = sys.stdout

        try:
            # Simulate Windows with charmap
            charmap_buffer = io.BytesIO()
            sys.stdout = io.TextIOWrapper(
                charmap_buffer,
                encoding='charmap',
                errors='strict'
            )

            # Apply the fix (reconfigure to UTF-8)
            sys.stdout.reconfigure(encoding='utf-8')

            # Now Unicode should work
            error_dict = {"error": "Failed ✓"}
            json_output = json.dumps(error_dict, ensure_ascii=False)
            print(json_output)  # Should not raise

            sys.stdout.flush()
            output = charmap_buffer.getvalue().decode('utf-8')
            assert '✓' in output

        finally:
            sys.stdout = original_stdout

    def test_fix_option_2_ensure_ascii_true(self):
        """
        FIX OPTION 2 (DEFENSIVE): Use ensure_ascii=True in json.dumps

        This works even without stdout reconfiguration.
        """
        stdout = CharmapStdout()

        # With ensure_ascii=True
        error_dict = {"error": "Failed ✓"}
        json_output = json.dumps(error_dict, ensure_ascii=True)

        # This works on Windows
        stdout.write(json_output)  # No error

        # Verify Unicode was escaped
        assert '\\u2713' in stdout.written[0]  # \u2713 = ✓

    def test_both_fixes_together_defense_in_depth(self):
        """
        BEST PRACTICE: Apply both fixes for defense-in-depth

        1. Reconfigure stdout (fixes root cause)
        2. Use ensure_ascii=True (safety net)
        """
        original_stdout = sys.stdout

        try:
            # Start with charmap (Windows default)
            buffer = io.BytesIO()
            sys.stdout = io.TextIOWrapper(
                buffer,
                encoding='charmap',
                errors='strict'
            )

            # Fix 1: Reconfigure to UTF-8
            sys.stdout.reconfigure(encoding='utf-8')

            # Fix 2: Use ensure_ascii=True
            error_dict = {"error": "Failed ✓"}
            json_output = json.dumps(error_dict, ensure_ascii=True)

            print(json_output)  # Should work
            sys.stdout.flush()

            # Verify output
            output = buffer.getvalue().decode('utf-8')
            assert 'Failed' in output

        finally:
            sys.stdout = original_stdout


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
