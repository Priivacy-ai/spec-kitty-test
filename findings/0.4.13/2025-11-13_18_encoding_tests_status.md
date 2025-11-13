# Encoding Tests Status - 2025-11-13

**Date:** 2025-11-13
**Session ID:** encoding-tests-implementation
**Category:** Testing Infrastructure
**Spec-Kitty Version:** 8fb628b91042f6777bf80fda76715df8577349d8 (commit 8fb628b)
**Analysis Date:** 2025-11-13

## Summary

Created comprehensive encoding test suite (33 tests) and findings document for Windows-1252 encoding issues that crash the spec-kitty dashboard. Successfully installed spec-kitty from `../spec-kitty` in editable mode and partially refactored tests to use the `spec_kitty_repo_root` fixture.

## Current Status

###Files Created

1. **Findings Document** (Complete)
   - `/Users/robert/Code/spec-kitty-test/findings/0.4.13/2025-11-13_17_encoding_dashboard_crash.md`
   - 10KB comprehensive finding
   - Documents root cause, impact, user journey, and 6 suggested improvements

2. **Test Suite** (Partially Working)
   - `/Users/robert/Code/spec-kitty-test/tests/functional/test_encoding_issues.py`
   - 45KB, 33 tests across 6 test classes
   - Currently has syntax errors from incomplete refactoring

### Installation Status

✅ **Completed:** spec-kitty installed from ../spec-kitty
```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
pip install -e /Users/robert/Code/spec-kitty
```

**Result:**
- spec-kitty-cli 0.4.13 installed in editable mode
- Python path includes: `/Users/robert/Code/spec-kitty/src`
- Can import `specify_cli` modules directly
- Scripts path: `/Users/robert/Code/spec-kitty/scripts/tasks`

### Test Results (Before Refactoring)

**19 of 32 tests passing (59%)**

✅ **Passing Tests** (19):
- **TestEncodingDetection** (5/5): All passing
  - Detects Windows-1252 smart quotes
  - Detects mathematical symbols
  - Detects mixed encoding issues
  - Valid UTF-8 passes validation
  - `file -I` command detection

- **TestValidationScript** (5/5): All passing
  - Check mode reports without fixing
  - Fix mode repairs files
  - Dry-run shows preview
  - Reports success for valid UTF-8
  - Detects all problematic characters

- **TestCommonCharacters** (8/8): All passing
  - Tests each specific character (0x91, 0x92, 0x93, 0x94, 0xB1, 0xD7)
  - Tests mixed problematic characters
  - Tests en-dash and em-dash

- **TestDashboardBehavior** (1/5): 1 passing after refactoring
  - test_multiple_files_with_errors_reported (passing)

⚠️ **Failing Tests** (13):
- **TestDashboardBehavior** (4 failing):
  - test_dashboard_fails_with_encoding_error - Module import issue
  - test_error_identifies_problematic_file - Module import issue
  - test_error_includes_byte_position - Module import issue
  - test_error_suggests_fix_command - Module import issue

- **TestNormalizationFunction** (5 failing):
  - All 5 tests failing due to module import path issues

- **TestErrorMessages** (5 failing):
  - All 5 tests failing due to module import path issues

### Issue Encountered

**Problem:** Tests that execute Python subprocesses need to import from `scripts/tasks/acceptance_support.py`

**Root cause:** The failing tests use string-based Python scripts executed via `subprocess.run` with hardcoded paths and `.format()` strings. During refactoring to use `spec_kitty_repo_root` fixture, a regex-based bulk update created syntax errors.

**Syntax error location:**
```python
# Line 619 in test_encoding_issues.py
            initialized_project / '.worktrees/001-normalize-win'
```

This line is an orphaned fragment from a malformed `.format()` call after the bulk regex replacement.

## Next Steps

### To Fix Tests

1. **Manual refactoring approach** (recommended):
   - Remove all remaining `.format()` usage in test scripts
   - Use f-strings with fixture variables properly interpolated
   - Pattern to follow (already working in 4 tests):

```python
def test_example(self, initialized_project, spec_kitty_repo_root):
    """Test description"""
    scripts_path = spec_kitty_repo_root / 'scripts' / 'tasks'
    target_file = feature_dir / 'spec.md'

    test_script = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{scripts_path}')
from acceptance_support import _read_text_strict

try:
    content = _read_text_strict(Path('{target_file}'))
except Exception as e:
    print(f"{{e}}")
"""
```

2. **Alternative approach**: Simplify tests to use installed package
   - Since spec-kitty is installed via `pip install -e`
   - Could refactor to test CLI commands directly instead of importing Python functions
   - Would be more realistic end-to-end tests

### Test Execution Commands

Once fixed, run tests with:

```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
export SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty

# Run all encoding tests
pytest tests/functional/test_encoding_issues.py -v

# Run working test classes only
pytest tests/functional/test_encoding_issues.py::TestEncodingDetection -v
pytest tests/functional/test_encoding_issues.py::TestValidationScript -v
pytest tests/functional/test_encoding_issues.py::TestCommonCharacters -v

# Run specific test
pytest tests/functional/test_encoding_issues.py::TestEncodingDetection::test_detect_windows1252_smart_quotes -xvs
```

## Test Coverage Analysis

### What Works (Validated by Passing Tests)

1. **Encoding Detection**: `validate_encoding.py` correctly detects:
   - Windows-1252 smart quotes (0x91, 0x92, 0x93, 0x94)
   - Mathematical symbols (0xB1, 0xD7)
   - Mixed encoding issues in same file
   - En-dash and em-dash

2. **Validation Modes**:
   - `--check`: Reports without modifying files ✅
   - `--fix`: Repairs files and converts to UTF-8 ✅
   - `--dry-run`: Shows preview without changes ✅

3. **Individual Character Handling**: All 8 common problematic characters tested and working

### What Needs Testing (Blocked by Syntax Errors)

1. **Dashboard Behavior**: How dashboard reacts to encoding errors
2. **Error Messages**: Quality and actionability of `ArtifactEncodingError`
3. **Normalization Function**: `normalize_feature_encoding()` behavior
4. **Multi-file scenarios**: Multiple files with different encoding issues

## Value of This Work

### For spec-kitty Project

1. **Comprehensive Documentation**: Detailed findings document explains:
   - Root cause of dashboard crashes
   - Impact on users and LLM agents
   - 6 concrete improvement suggestions
   - User journey analysis

2. **Test Infrastructure**: Once fixed, 33 tests will provide:
   - Regression prevention for encoding fixes
   - Validation that dashboard handles errors gracefully
   - Verification that fix commands work correctly
   - Character-by-character validation

3. **Reproducible Test Cases**: Each test creates exact scenarios:
   - Specific byte sequences that cause problems
   - Multiple file types (spec.md, research.md, data-model.md)
   - Various encoding combinations

### For spec-kitty Users

1. **Better Error Messages**: Tests validate that errors are actionable
2. **Reliable Dashboard**: Ensures dashboard doesn't crash silently
3. **Prevention**: Tests can catch encoding issues before users hit them

## Estimated Work to Complete

**Time to fix remaining tests**: 2-3 hours

**Steps:**
1. Read through TestNormalizationFunction class (lines ~596-790)
2. Manually update each test function signature to add `spec_kitty_repo_root`
3. Replace each test_script `.format()` with proper f-string interpolation
4. Test each class individually as fixed
5. Repeat for TestErrorMessages class (lines ~891-1113)

**Complexity:** Medium - Repetitive but straightforward

## Lessons Learned

1. ✅ **Good**: Using pytest fixtures (`spec_kitty_repo_root`) provides clean abstraction
2. ✅ **Good**: Installing with `pip install -e` makes imports reliable
3. ⚠️ **Caution**: Bulk regex replacements risky for complex Python code
4. ⚠️ **Caution**: F-strings need careful quoting when paths have special chars
5. 💡 **Alternative**: Could test via CLI commands instead of subprocess Python scripts

## Files and Paths

**Test file:**
```
/Users/robert/Code/spec-kitty-test/tests/functional/test_encoding_issues.py
```

**Findings document:**
```
/Users/robert/Code/spec-kitty-test/findings/0.4.13/2025-11-13_17_encoding_dashboard_crash.md
```

**Spec-kitty installation:**
```
/Users/robert/Code/spec-kitty  (installed via pip install -e)
```

**Key module:**
```
/Users/robert/Code/spec-kitty/scripts/tasks/acceptance_support.py
```

**Validation script:**
```
/Users/robert/Code/spec-kitty/scripts/validate_encoding.py
```

---

**Status**: ⏸️ **Paused - Needs Manual Refactoring**
**Last Updated**: 2025-11-13
**Completion**: 60% (findings 100%, tests 60%)
