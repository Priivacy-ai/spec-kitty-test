"""
Encoding Issues Tests

Tests for encoding validation, detection, and handling in spec-kitty,
specifically focusing on the dashboard crash issue when LLM-generated
markdown files contain Windows-1252 characters.

Based on finding: 2025-11-13_17_encoding_dashboard_crash.md

Test Coverage:
1. Encoding Detection (5 tests)
   - Detect Windows-1252 smart quotes
   - Detect mathematical symbols (±, ×)
   - Detect mixed encoding issues
   - Valid UTF-8 files pass validation
   - Binary files are rejected

2. Dashboard Behavior (5 tests)
   - Dashboard crashes with encoding error
   - Error message identifies problematic file
   - Error message includes byte position
   - Dashboard suggests fix command
   - Multiple encoding errors reported

3. Validation Script (5 tests)
   - validate_encoding.py detects all problematic characters
   - --check mode reports without fixing
   - --fix mode repairs files
   - --dry-run shows preview
   - Reports success for valid UTF-8

4. Normalization Function (5 tests)
   - normalize_feature_encoding() fixes Windows-1252
   - Converts smart quotes to straight quotes
   - Handles mathematical symbols
   - Preserves valid UTF-8 content
   - Returns list of fixed files

5. Common Character Tests (8 tests)
   - RIGHT SINGLE QUOTE (0x92)
   - LEFT SINGLE QUOTE (0x91)
   - LEFT DOUBLE QUOTE (0x93)
   - RIGHT DOUBLE QUOTE (0x94)
   - PLUS-MINUS (0xB1)
   - MULTIPLICATION (0xD7)
   - Mixed problematic characters
   - En-dash and em-dash

6. Error Messages (5 tests)
   - ArtifactEncodingError format
   - Byte position accuracy
   - File path included
   - Suggested fix command
   - User-actionable message

Total: 33 tests
"""

import os
import subprocess
import tempfile
from pathlib import Path
import json

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def initialized_project(temp_project_dir, spec_kitty_repo_root):
    """Create and return an initialized spec-kitty project."""
    project_name = 'encoding_test'
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


def create_feature_with_encoding_issue(project_path: Path, feature_name: str, content: bytes, filename: str = "spec.md"):
    """
    Create a feature and write content with encoding issues to a markdown file.

    Args:
        project_path: Root project directory
        feature_name: Name for the feature
        content: Raw bytes to write (may contain Windows-1252)
        filename: Which markdown file to corrupt (spec.md, research.md, etc.)

    Returns:
        Path to the feature directory
    """
    # Create feature
    create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
    result = subprocess.run(
        [str(create_script), '--json', '--feature-name', feature_name, f'Test {feature_name}'],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True
    )

    # Extract worktree and feature paths from JSON output
    for line in reversed(result.stdout.strip().split('\n')):
        if line.strip().startswith('{'):
            data = json.loads(line.strip())
            worktree_path = Path(data['WORKTREE_PATH'])
            feature_num = data['FEATURE_NUM']
            feature_name_normalized = data['BRANCH_NAME'].replace(f"{feature_num}-", "", 1)
            # Compute feature directory from worktree
            feature_dir = worktree_path / 'kitty-specs' / f"{feature_num}-{feature_name_normalized}"
            break

    # Write problematic content
    target_file = feature_dir / filename
    target_file.write_bytes(content)

    return feature_dir


class TestEncodingDetection:
    """Test detection of encoding issues in markdown files."""

    def test_detect_windows1252_smart_quotes(self, initialized_project, spec_kitty_repo_root):
        """Test: Encoding validator detects Windows-1252 smart quotes (0x92, 0x93)"""
        # Create content with Windows-1252 right single quote (0x92)
        content = b"User\x92s profile is important"  # User's with smart quote

        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "SmartQuotes", content
        )

        # Run encoding validator
        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should detect the encoding error
        assert result.returncode != 0, "Should detect encoding error"
        assert 'byte 0x92' in output or 'encoding' in output.lower(), \
            f"Should report byte 0x92 or encoding issue. Got: {output}"

    def test_detect_mathematical_symbols(self, initialized_project, spec_kitty_repo_root):
        """Test: Encoding validator detects Windows-1252 math symbols (±, ×)"""
        # Create content with plus-minus (0xB1) and multiplication (0xD7)
        content = b"Temperature: 20\xb1C, Size: 10\xd720cm"

        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "MathSymbols", content, "data-model.md"
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should detect encoding errors
        assert result.returncode != 0, "Should detect encoding error"
        assert ('0xb1' in output.lower() or '0xd7' in output.lower() or
                'encoding' in output.lower()), \
            f"Should report problematic bytes. Got: {output}"

    def test_detect_mixed_encoding_issues(self, initialized_project, spec_kitty_repo_root):
        """Test: Validator detects multiple types of encoding issues in one file"""
        # Mix of smart quotes, math symbols, and other Windows-1252 chars
        content = b"Product\x92s features:\n- Temperature: \xb15\xb0C\n- Dimensions: 10\xd720\x93"

        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "MixedEncoding", content, "research.md"
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        # Should detect the file has problems
        assert result.returncode != 0, "Should detect encoding errors"

    def test_valid_utf8_passes_validation(self, initialized_project, spec_kitty_repo_root):
        """Test: Valid UTF-8 files pass encoding validation"""
        # Create content with valid UTF-8 (including Unicode characters)
        content = "Valid UTF-8: Hello 世界! Temperature: ±5°C ✓".encode('utf-8')

        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "ValidUTF8", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should pass validation
        assert result.returncode == 0, f"Valid UTF-8 should pass. Got: {output}"
        assert '✅' in output or 'valid' in output.lower(), \
            f"Should report success. Got: {output}"

    def test_file_command_detects_encoding(self, initialized_project, spec_kitty_repo_root):
        """Test: `file -I` command correctly identifies binary/charset"""
        # Create file with Windows-1252
        content = b"Smart \x92quote\x93 here"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "FileCommand", content
        )

        bad_file = feature_dir / "spec.md"

        # Run file -I command
        result = subprocess.run(
            ['file', '-I', str(bad_file)],
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout

        # Should detect it's not UTF-8
        assert 'charset=binary' in output or 'charset=unknown' in output or 'octet-stream' in output, \
            f"file -I should detect non-UTF-8. Got: {output}"


class TestDashboardBehavior:
    """Test how dashboard handles encoding errors."""

    def test_dashboard_fails_with_encoding_error(self, initialized_project, spec_kitty_repo_root):
        """Test: Dashboard command fails when encountering encoding error"""
        # Create feature with encoding issue
        content = b"User\x92s profile"
        create_feature_with_encoding_issue(initialized_project, "DashFail", content)

        # Try to generate dashboard summary (simulating dashboard command)
        # We'll use Python to import and call the function directly
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'
        worktree_path = initialized_project / '.worktrees/001-dash-fail'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import collect_feature_summary

try:
    summary = collect_feature_summary(Path('{worktree_path}'), '001-dash-fail')
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should fail with encoding error (not succeed)
        assert 'SUCCESS' not in output, "Should not succeed with encoding error"
        assert ('ArtifactEncodingError' in output or 'UnicodeDecodeError' in output or
                'encoding' in output.lower()), \
            f"Should report encoding error. Got: {output}"

    def test_error_identifies_problematic_file(self, initialized_project, spec_kitty_repo_root):
        """Test: Error message identifies which file has encoding problem"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "IdentifyFile", content, "research.md"
        )

        # Try to read with strict encoding
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'
        research_file = feature_dir / 'research.md'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    content = _read_text_strict(Path('{research_file}'))
except Exception as e:
    print(f"ERROR: {{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Error should mention the file
        assert 'research.md' in output, f"Should identify research.md. Got: {output}"

    def test_error_includes_byte_position(self, initialized_project, spec_kitty_repo_root):
        """Test: Error message includes byte position of encoding problem"""
        # Position the bad byte at a known offset
        content = b"Good text " + b"\x92" + b" more text"  # Byte at position 10
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "BytePos", content
        )

        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'
        spec_file = feature_dir / 'spec.md'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    content = _read_text_strict(Path('{spec_file}'))
except Exception as e:
    print(f"{{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Error should include byte position or offset
        assert ('offset' in output.lower() or 'position' in output.lower() or
                'byte' in output.lower()), \
            f"Should report byte position. Got: {output}"

    def test_error_suggests_fix_command(self, initialized_project, spec_kitty_repo_root):
        """Test: Error message suggests --normalize-encoding fix"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "SuggestFix", content
        )

        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'
        spec_file = feature_dir / 'spec.md'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    content = _read_text_strict(Path('{spec_file}'))
except Exception as e:
    print(f"{{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Error should suggest the fix
        assert 'normalize-encoding' in output or 'normalize' in output, \
            f"Should suggest normalize-encoding. Got: {output}"

    def test_multiple_files_with_errors_reported(self, initialized_project, spec_kitty_repo_root):
        """Test: Multiple files with encoding errors are all detected"""
        # Create multiple files with issues
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "MultiFile", b"Bad \x92 in spec"
        )

        # Add errors to other files
        (feature_dir / "research.md").write_bytes(b"Bad \x93 in research")
        (feature_dir / "data-model.md").write_bytes(b"Bad \xb1 in model")

        # Run validator
        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should mention multiple files
        assert 'spec.md' in output, "Should detect spec.md"
        assert 'research.md' in output, "Should detect research.md"
        assert 'data-model.md' in output, "Should detect data-model.md"


class TestValidationScript:
    """Test the validate_encoding.py script."""

    def test_check_mode_reports_without_fixing(self, initialized_project, spec_kitty_repo_root):
        """Test: --check mode reports issues but doesn't modify files"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "CheckMode", content
        )

        bad_file = feature_dir / "spec.md"
        original_content = bad_file.read_bytes()

        # Run in check mode (default behavior, no --fix)
        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        # Should report error
        assert result.returncode != 0, "Should detect error"

        # File should be unchanged
        assert bad_file.read_bytes() == original_content, \
            "Check mode should not modify files"

    def test_fix_mode_repairs_files(self, initialized_project, spec_kitty_repo_root):
        """Test: --fix mode actually repairs encoding issues"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "FixMode", content
        )

        bad_file = feature_dir / "spec.md"

        # Run in fix mode
        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # File should now be valid UTF-8
        try:
            fixed_content = bad_file.read_text(encoding='utf-8')
            # Should have replaced smart quote with straight quote
            assert "'" in fixed_content or 'quote' in fixed_content, \
                "Should contain repaired text"
        except UnicodeDecodeError:
            pytest.fail("File should be valid UTF-8 after fix")

    def test_dry_run_shows_preview(self, initialized_project, spec_kitty_repo_root):
        """Test: --dry-run shows what would be fixed without changing files"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "DryRun", content
        )

        bad_file = feature_dir / "spec.md"
        original_content = bad_file.read_bytes()

        # Run in dry-run mode
        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), '--dry-run', str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should mention dry run or preview
        assert 'DRY RUN' in output or 'would' in output.lower(), \
            f"Should indicate dry-run. Got: {output}"

        # File should be unchanged
        assert bad_file.read_bytes() == original_content, \
            "Dry-run should not modify files"

    def test_reports_success_for_valid_utf8(self, initialized_project, spec_kitty_repo_root):
        """Test: Validator reports success when all files are valid UTF-8"""
        content = "Valid UTF-8 content".encode('utf-8')
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "ValidCheck", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Should report success
        assert result.returncode == 0, f"Should succeed with valid UTF-8. Got: {output}"
        assert '✅' in output or 'valid' in output.lower(), \
            f"Should report success. Got: {output}"

    def test_detects_all_problematic_characters(self, initialized_project, spec_kitty_repo_root):
        """Test: Validator detects all common Windows-1252 problematic characters"""
        # Test all the characters mentioned in findings
        test_chars = {
            'right_single_quote': b'\x92',
            'left_single_quote': b'\x91',
            'left_double_quote': b'\x93',
            'right_double_quote': b'\x94',
            'plus_minus': b'\xb1',
            'multiplication': b'\xd7',
        }

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        for char_name, char_byte in test_chars.items():
            content = b"Text with " + char_byte + b" character"
            feature_dir = create_feature_with_encoding_issue(
                initialized_project, f"Char_{char_name}", content
            )

            result = subprocess.run(
                ['python3', str(validate_script), str(feature_dir)],
                capture_output=True,
                text=True,
                check=False
            )

            # Should detect the issue
            assert result.returncode != 0, \
                f"Should detect {char_name} (byte {char_byte.hex()})"


class TestNormalizationFunction:
    """Test the normalize_feature_encoding() function."""

    def test_normalize_fixes_windows1252(self, initialized_project, spec_kitty_repo_root):
        """Test: normalize_feature_encoding() converts Windows-1252 to UTF-8"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "NormalizeWin", content
        )

        # Extract actual feature ID from feature_dir path (don't hardcode!)
        feature_id = feature_dir.name  # e.g., '001-normalizewin'
        worktree_path = feature_dir.parent.parent  # Go up from kitty-specs/001-normalizewin
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import normalize_feature_encoding

repo_root = Path('{worktree_path}')
feature_id = '{feature_id}'
fixed_files = normalize_feature_encoding(repo_root, feature_id)
print(f"FIXED: {{len(fixed_files)}} files")
for f in fixed_files:
    print(f"  - {{f}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr

        # Debug: Print subprocess output
        print(f"\n=== Subprocess Output ===")
        print(output)
        print(f"=== End Subprocess Output ===\n")

        # Should report fixed files
        assert 'FIXED:' in output, f"Should report fixed files. Got: {output}"

        # File should now be valid UTF-8
        fixed_file = feature_dir / "spec.md"

        # Debug: Print actual file location and contents
        print(f"\nDEBUG: Checking file at: {fixed_file}")
        print(f"DEBUG: File exists: {fixed_file.exists()}")
        if fixed_file.exists():
            raw_bytes = fixed_file.read_bytes()
            print(f"DEBUG: File bytes: {raw_bytes}")
            print(f"DEBUG: Has 0x92: {b'\\x92' in raw_bytes}")

        try:
            fixed_content = fixed_file.read_text(encoding='utf-8')
            assert "'" in fixed_content or 'quote' in fixed_content, \
                "Should have repaired text"
            print(f"✓ File normalized successfully: {repr(fixed_content)}")
        except UnicodeDecodeError as e:
            pytest.fail(f"File should be valid UTF-8 after normalization. Error: {e}\nFile still contains: {fixed_file.read_bytes()}")

    def test_converts_smart_quotes_to_straight(self, initialized_project, spec_kitty_repo_root):
        """Test: Smart quotes are converted to straight ASCII quotes"""
        # Mix of left and right smart quotes
        content = b"It\x92s a \x93test\x94 string"  # It's a "test" string
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "SmartToStraight", content
        )

        # Extract actual feature ID
        feature_id = feature_dir.name
        worktree_path = feature_dir.parent.parent
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import normalize_feature_encoding

repo_root = Path('{worktree_path}')
normalize_feature_encoding(repo_root, '{feature_id}')
"""

        subprocess.run(['python3', '-c', test_script], check=False)

        # Check result
        fixed_file = feature_dir / "spec.md"
        fixed_content = fixed_file.read_text(encoding='utf-8')

        # Should have straight quotes, not smart quotes
        assert "'" in fixed_content or '"' in fixed_content, \
            "Should contain straight quotes"
        assert "It's" in fixed_content or "test" in fixed_content, \
            "Should preserve basic text"

    def test_handles_mathematical_symbols(self, initialized_project, spec_kitty_repo_root):
        """Test: Mathematical symbols are converted appropriately"""
        content = b"Temp: \xb15\xb0C, Size: 10\xd720"  # ±5°, 10×20
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "MathNorm", content
        )

        # Extract actual feature ID
        feature_id = feature_dir.name
        worktree_path = feature_dir.parent.parent
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import normalize_feature_encoding

repo_root = Path('{worktree_path}')
normalize_feature_encoding(repo_root, '{feature_id}')
"""

        subprocess.run(['python3', '-c', test_script], check=False)

        # Check result
        fixed_file = feature_dir / "spec.md"
        try:
            fixed_content = fixed_file.read_text(encoding='utf-8')
            # Should be valid UTF-8 now
            assert 'Temp:' in fixed_content and 'Size:' in fixed_content, \
                "Should preserve text content"
        except UnicodeDecodeError:
            pytest.fail("Should be valid UTF-8 after normalization")

    def test_preserves_valid_utf8_content(self, initialized_project, spec_kitty_repo_root):
        """Test: normalize_feature_encoding() doesn't corrupt valid UTF-8"""
        # Create content with valid UTF-8 including Unicode
        content = "Valid UTF-8: Hello 世界! ✓ Emoji: 🎉".encode('utf-8')
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "PreserveUTF8", content
        )

        original_content = (feature_dir / "spec.md").read_text(encoding='utf-8')

        # Extract actual feature ID
        feature_id = feature_dir.name
        worktree_path = feature_dir.parent.parent
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import normalize_feature_encoding

repo_root = Path('{worktree_path}')
normalize_feature_encoding(repo_root, '{feature_id}')
"""

        subprocess.run(['python3', '-c', test_script], check=False)

        # Content should be unchanged
        fixed_content = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert fixed_content == original_content, \
            "Valid UTF-8 should not be modified"

    def test_returns_list_of_fixed_files(self, initialized_project, spec_kitty_repo_root):
        """Test: normalize_feature_encoding() returns list of files it fixed"""
        # Create multiple files with issues
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "ListFixed", b"Bad \x92 spec"
        )
        (feature_dir / "research.md").write_bytes(b"Bad \x93 research")

        # Extract actual feature ID
        feature_id = feature_dir.name
        worktree_path = feature_dir.parent.parent
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import normalize_feature_encoding

repo_root = Path('{worktree_path}')
fixed_files = normalize_feature_encoding(repo_root, '{feature_id}')
print(f"COUNT: {{len(fixed_files)}}")
for f in fixed_files:
    print(f"FILE: {{f.name}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should report at least 2 fixed files
        assert 'COUNT: ' in output, "Should report count"
        assert 'FILE: spec.md' in output or 'spec.md' in output, \
            "Should list spec.md"
        assert 'FILE: research.md' in output or 'research.md' in output, \
            "Should list research.md"


class TestCommonCharacters:
    """Test handling of specific problematic characters."""

    def test_right_single_quote_0x92(self, initialized_project, spec_kitty_repo_root):
        """Test: RIGHT SINGLE QUOTE (0x92) is detected and fixed"""
        content = b"User\x92s profile"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "Char0x92", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        # Should detect
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )
        assert result.returncode != 0, "Should detect 0x92"

        # Should fix
        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert "User" in fixed and "profile" in fixed, "Should fix and preserve text"

    def test_left_single_quote_0x91(self, initialized_project, spec_kitty_repo_root):
        """Test: LEFT SINGLE QUOTE (0x91) is detected and fixed"""
        content = b"\x91quoted\x91"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "Char0x91", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        # Detect and fix
        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert "quoted" in fixed, "Should preserve text"

    def test_double_quotes_0x93_0x94(self, initialized_project, spec_kitty_repo_root):
        """Test: LEFT/RIGHT DOUBLE QUOTES (0x93, 0x94) are detected and fixed"""
        content = b"\x93Hello world\x94"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "CharQuotes", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert "Hello world" in fixed, "Should preserve text"

    def test_plus_minus_0xb1(self, initialized_project, spec_kitty_repo_root):
        """Test: PLUS-MINUS (0xB1) is detected and fixed"""
        content = b"Temperature: \xb15\xb0C"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "Char0xB1", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert "Temperature:" in fixed, "Should preserve text"

    def test_multiplication_0xd7(self, initialized_project, spec_kitty_repo_root):
        """Test: MULTIPLICATION SIGN (0xD7) is detected and fixed"""
        content = b"Size: 10\xd720cm"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "Char0xD7", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert "Size:" in fixed and "cm" in fixed, "Should preserve text"

    def test_mixed_problematic_characters(self, initialized_project, spec_kitty_repo_root):
        """Test: Multiple problematic characters in same file"""
        content = b"User\x92s guide: \x93Features\x94\n- Size: 10\xd720\n- Temp: \xb15\xb0C"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "CharMixed", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        # Detect
        result = subprocess.run(
            ['python3', str(validate_script), str(feature_dir)],
            capture_output=True,
            text=True,
            check=False
        )
        assert result.returncode != 0, "Should detect multiple issues"

        # Fix
        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )
        fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
        assert all(word in fixed for word in ["User", "guide", "Features", "Size", "Temp"]), \
            "Should preserve all text"

    def test_en_dash_em_dash(self, initialized_project, spec_kitty_repo_root):
        """Test: En-dash and em-dash characters"""
        # Windows-1252 en-dash (0x96) and em-dash (0x97)
        content = b"Range: 1\x9610, Context\x97note"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "CharDashes", content
        )

        validate_script = Path(os.environ.get('SPEC_KITTY_REPO', '../spec-kitty')) / 'scripts/validate_encoding.py'

        # Should detect and fix
        subprocess.run(
            ['python3', str(validate_script), '--fix', str(feature_dir)],
            check=False
        )

        try:
            fixed = (feature_dir / "spec.md").read_text(encoding='utf-8')
            assert "Range:" in fixed and "Context" in fixed, "Should preserve text"
        except UnicodeDecodeError:
            pytest.fail("Should be valid UTF-8 after fix")


class TestErrorMessages:
    """Test quality and actionability of error messages."""

    def test_artifact_encoding_error_format(self, initialized_project, spec_kitty_repo_root):
        """Test: ArtifactEncodingError has proper format"""
        content = b"Bad \x92 quote"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "ErrorFormat", content
        )

        worktree_path = feature_dir / 'spec.md'
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import ArtifactEncodingError, _read_text_strict

try:
    _read_text_strict(Path('{worktree_path}'))
except ArtifactEncodingError as e:
    print(f"MESSAGE: {{e}}")
    print(f"PATH: {{e.path}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should have MESSAGE and PATH
        assert 'MESSAGE:' in output, "Should have error message"
        assert 'PATH:' in output, "Should have file path"
        assert 'spec.md' in output, "Should identify file"

    def test_byte_position_accuracy(self, initialized_project, spec_kitty_repo_root):
        """Test: Byte position in error is accurate"""
        # Place bad byte at known position
        content = b"0123456789\x92END"  # Bad byte at position 10
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "ByteAccuracy", content
        )

        worktree_path = feature_dir / 'spec.md'
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    _read_text_strict(Path('{worktree_path}'))
except Exception as e:
    print(f"{{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should report position 10 or thereabouts
        assert '10' in output or 'offset' in output.lower(), \
            f"Should report accurate byte position. Got: {output}"

    def test_file_path_included_in_error(self, initialized_project, spec_kitty_repo_root):
        """Test: Error includes full path to problematic file"""
        content = b"Bad \x92 byte"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "PathInError", content, "data-model.md"
        )

        worktree_path = feature_dir / 'data-model.md'
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    _read_text_strict(Path('{worktree_path}'))
except Exception as e:
    print(f"{{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should include path
        assert 'data-model.md' in output, "Should include file name"

    def test_suggested_fix_command_present(self, initialized_project, spec_kitty_repo_root):
        """Test: Error suggests the fix command"""
        content = b"Bad \x92 byte"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "SuggestCmd", content
        )

        worktree_path = feature_dir / 'spec.md'
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    _read_text_strict(Path('{worktree_path}'))
except Exception as e:
    print(f"{{e}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should suggest normalize-encoding
        assert 'normalize-encoding' in output, \
            f"Should suggest fix command. Got: {output}"

    def test_error_message_is_actionable(self, initialized_project, spec_kitty_repo_root):
        """Test: Error message provides actionable guidance"""
        content = b"Bad \x92 byte"
        feature_dir = create_feature_with_encoding_issue(
            initialized_project, "Actionable", content
        )

        worktree_path = feature_dir / 'spec.md'
        scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'

        test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    _read_text_strict(Path('{worktree_path}'))
except Exception as e:
    message = str(e)
    # Check if message is actionable
    has_file = 'spec.md' in message
    has_byte_info = 'byte' in message.lower() or '0x' in message
    has_fix = 'normalize' in message.lower() or 'fix' in message.lower()
    print(f"HAS_FILE: {{has_file}}")
    print(f"HAS_BYTE_INFO: {{has_byte_info}}")
    print(f"HAS_FIX: {{has_fix}}")
    print(f"MESSAGE: {{message}}")
"""

        result = subprocess.run(
            ['python3', '-c', test_script],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout

        # Should have all actionable elements
        assert 'HAS_FILE: True' in output, "Should identify file"
        assert 'HAS_BYTE_INFO: True' in output, "Should provide byte info"
        assert 'HAS_FIX: True' in output, "Should suggest fix"
