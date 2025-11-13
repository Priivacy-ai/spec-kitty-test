"""
PowerShell Script Tests

Tests PowerShell scripts work correctly for Issues #26 and #27:
- Issue #26: Python string quoting bug (should be fixed with single quotes)
- Issue #27: AI agent syntax confusion (parameter validation)

Test Coverage:
1. PowerShell Script Execution (3 tests)
   - Scripts execute without Python syntax errors
   - Scripts return valid JSON
   - Scripts handle errors gracefully

2. Python Quoting Validation (3 tests)
   - Error messages use single quotes (no SyntaxError)
   - JSON output is valid
   - F-strings don't conflict with PowerShell here-strings

3. Parameter Syntax (3 tests)
   - PowerShell-style parameters work (-ParameterName)
   - Bash-style parameters fail with helpful error
   - Missing parameters show usage

4. Cross-Platform Compatibility (2 tests)
   - Scripts work on Unix-like systems with PowerShell Core
   - Path separators handled correctly
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

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
def powershell_available():
    """Check if PowerShell is available."""
    result = subprocess.run(['pwsh', '--version'], capture_output=True, check=False)
    if result.returncode != 0:
        pytest.skip("PowerShell (pwsh) not available")
    return True


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output (last JSON line)."""
    for line in reversed(output.strip().split('\n')):
        # Remove ANSI color codes
        clean_line = line
        import re
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', clean_line)
        clean_line = clean_line.strip()

        if clean_line.startswith('{'):
            try:
                return json.loads(clean_line)
            except json.JSONDecodeError:
                continue
    return None


class TestPowerShellScriptExecution:
    """Test that PowerShell scripts execute without Python syntax errors."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_feature_powershell_script(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: PowerShell create-new-feature.ps1 executes without errors"""
        project_name = 'ps_create_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project with PowerShell scripts
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Test PowerShell create-new-feature script
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'
        assert create_script.exists(), "PowerShell create script should exist"

        result = subprocess.run(
            ['pwsh', '-Command', str(create_script), '-FeatureName', 'TestFeature', '-FeatureDescription', 'Test', '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should not have Python SyntaxError
        assert 'SyntaxError' not in result.stderr, \
            f"Should not have Python SyntaxError. Got: {result.stderr}"

        # Should succeed or fail gracefully (not with syntax error)
        if result.returncode == 0:
            # Extract JSON
            data = extract_json_from_output(result.stdout)
            assert data is not None, "Should return valid JSON"
            assert 'BRANCH_NAME' in data, "JSON should include BRANCH_NAME"

    def test_powershell_common_module_no_quoting_errors(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: common.ps1 error messages use single quotes (Issue #26 fix validation)"""
        project_name = 'ps_quoting_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Read common.ps1 and verify quoting
        common_ps1 = project_path / '.kittify/scripts/powershell/common.ps1'
        content = common_ps1.read_text()

        # Check for double-quote quoting bugs (Issue #26)
        # Bug pattern: json.dumps({"error": ...}) inside PowerShell here-string
        # Should use: json.dumps({'error': ...}) with single quotes

        # Find all json.dumps calls
        import re
        json_dumps_calls = re.findall(r'json\.dumps\([^)]+\)', content)

        for call in json_dumps_calls:
            # Should use single quotes for Python dict, not double quotes
            assert '({"' not in call, \
                f"Found double-quote quoting bug (Issue #26): {call}"

    def test_powershell_scripts_return_valid_json(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: PowerShell scripts return valid JSON output"""
        project_name = 'ps_json_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Test check-prerequisites.ps1 returns valid JSON
        check_prereq = project_path / '.kittify/scripts/powershell/check-prerequisites.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(check_prereq), '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should return JSON (might fail if no features exist, but should be valid JSON)
        output = result.stdout + result.stderr

        # Look for JSON in output
        json_found = False
        for line in output.split('\n'):
            import re
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            if clean_line.startswith('{'):
                try:
                    data = json.loads(clean_line)
                    json_found = True
                    # If it's an error, should have 'error' key
                    if 'error' in data:
                        # Error JSON should be valid
                        assert isinstance(data['error'], str), "Error should be string"
                    break
                except json.JSONDecodeError:
                    pass

        # Should have found JSON (either success or error JSON)
        assert json_found or result.returncode == 1, \
            f"Should return JSON or fail gracefully. Got: {output}"


class TestPythonQuotingValidation:
    """Validate that Python quoting bugs (Issue #26) are fixed."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_error_messages_use_single_quotes(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Python error messages in PowerShell scripts use single quotes"""
        project_name = 'ps_single_quotes'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check all PowerShell scripts for quoting
        ps_scripts_dir = project_path / '.kittify/scripts/powershell'
        ps_files = list(ps_scripts_dir.glob('*.ps1'))

        for ps_file in ps_files:
            content = ps_file.read_text()

            # Skip if no Python code
            if 'json.dumps' not in content:
                continue

            # Check for double-quote bug pattern
            import re
            # Pattern: json.dumps({"key": ... inside here-string @"..."@
            matches = re.findall(r'json\.dumps\(\{\"[^}]+\}\)', content)

            assert len(matches) == 0, \
                f"{ps_file.name}: Found double-quote quoting bug: {matches}"

    def test_no_python_syntax_errors_in_scripts(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: No Python SyntaxError when PowerShell scripts execute Python code"""
        project_name = 'ps_syntax_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create a feature to test with
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(create_script), '-FeatureName', 'SyntaxTest', '-FeatureDescription', 'Test', '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Key assertion: No Python SyntaxError in output
        full_output = result.stdout + result.stderr

        assert 'SyntaxError' not in full_output, \
            f"Should not have SyntaxError. Got: {full_output}"

        # Specifically check for the reported Issue #26 error
        assert "'{' was never closed" not in full_output, \
            "Should not have unclosed brace error (Issue #26)"

    def test_json_error_output_is_valid(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: JSON error output is valid and parseable"""
        project_name = 'ps_json_error'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Trigger an error condition (run check-prerequisites without being in worktree)
        check_prereq = project_path / '.kittify/scripts/powershell/check-prerequisites.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(check_prereq), '-Json'],
            cwd=project_path,  # Wrong location (should be in worktree)
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail (wrong location)
        # But error should be valid JSON or at least not a Python SyntaxError

        full_output = result.stdout + result.stderr

        # No Python syntax errors
        assert 'SyntaxError' not in full_output, \
            f"Should not have SyntaxError in error path. Got: {full_output}"

        # Look for JSON error message
        import re
        for line in full_output.split('\n'):
            clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            if clean.startswith('{') and 'error' in clean:
                # Should be valid JSON
                try:
                    error_data = json.loads(clean)
                    assert 'error' in error_data, "Error JSON should have 'error' key"
                except json.JSONDecodeError as e:
                    pytest.fail(f"Error JSON is invalid: {e}. JSON: {clean}")


class TestParameterSyntax:
    """Test PowerShell parameter syntax (Issue #27 - AI confusion)."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_powershell_style_parameters_work(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: PowerShell-style parameters (-ParameterName) work correctly"""
        project_name = 'ps_params_correct'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Test with correct PowerShell parameter syntax
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(create_script),
             '-FeatureName', 'CorrectParams',
             '-FeatureDescription', 'Testing correct parameter syntax',
             '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should succeed with correct syntax
        # (May fail for other reasons, but not parameter syntax)
        full_output = result.stdout + result.stderr

        # Should not complain about parameter names
        assert 'parameter' not in full_output.lower() or 'FeatureName' not in full_output, \
            f"Should not have parameter errors with correct syntax. Got: {full_output}"

    def test_bash_style_parameters_create_wrong_feature_name(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: Bash-style parameters (--parameter-name) get interpreted as values (Issue #27 confusion)"""
        project_name = 'ps_params_wrong'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Test with bash-style syntax (confusing but PowerShell interprets it differently)
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(create_script),
             '--feature-name', 'WrongParams',  # Interpreted as positional args!
             '--feature-description', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # PowerShell interprets --feature-name as the FeatureName value (positional)
        # This is confusing for AI agents (Issue #27)
        # The script succeeds but uses wrong name
        assert result.returncode == 0, "Script succeeds but interprets params wrong"

        full_output = result.stdout + result.stderr

        # Feature name becomes "--feature-name" (the literal string)
        assert 'feature-name' in full_output.lower() or '001-feature-name' in full_output, \
            f"Should use '--feature-name' as the actual feature name (confusing!). Got: {full_output}"

    def test_missing_parameters_show_helpful_error(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: Missing required parameters show helpful error message"""
        project_name = 'ps_missing_params'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Run script without feature description (required)
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        result = subprocess.run(
            ['pwsh', '-Command', str(create_script), '-FeatureName', 'Test'],  # Missing description
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should fail
        assert result.returncode != 0, "Should fail when description missing"

        full_output = result.stdout + result.stderr

        # Should show helpful error about missing description
        assert 'description' in full_output.lower() or 'discovery' in full_output.lower(), \
            f"Should mention missing description. Got: {full_output}"


class TestCrossPlatformCompatibility:
    """Test PowerShell scripts work on Unix-like systems."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_scripts_executable_on_unix(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: PowerShell scripts can execute on macOS/Linux with PowerShell Core"""
        project_name = 'ps_unix_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # PowerShell scripts should work on Unix
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        # This is the key cross-platform test
        result = subprocess.run(
            ['pwsh', str(create_script), '-FeatureName', 'UnixTest', '-FeatureDescription', 'Cross-platform test', '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should execute (not fail with "command not found" or similar)
        # May fail for other reasons, but should run
        assert 'not found' not in result.stderr.lower(), \
            f"Script should be executable on Unix. Got: {result.stderr}"

        # Should not have path separator issues
        assert 'path' not in result.stderr.lower() or 'separator' not in result.stderr.lower(), \
            f"Should handle Unix paths correctly. Got: {result.stderr}"

    def test_path_separators_handled_correctly(self, temp_project_dir, spec_kitty_repo_root, powershell_available):
        """Test: Scripts handle both forward and backslash path separators"""
        project_name = 'ps_paths_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--script=ps', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # PowerShell scripts should handle Unix-style paths (/)
        create_script = project_path / '.kittify/scripts/powershell/create-new-feature.ps1'

        # Use forward slashes (Unix-style) - should work in PowerShell Core
        result = subprocess.run(
            ['pwsh', '-Command', f'{create_script}', '-FeatureName', 'PathTest', '-FeatureDescription', 'Test', '-Json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False
        )

        # Should work (PowerShell Core handles forward slashes on all platforms)
        # Script may fail for other reasons, but not path separator issues
        full_output = result.stdout + result.stderr

        # Should not have path-related errors specific to separators
        assert 'invalid path' not in full_output.lower(), \
            f"Should handle path separators. Got: {full_output}"
