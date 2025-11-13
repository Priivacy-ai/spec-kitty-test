# CRITICAL: verify-setup crashes with ImportError in v0.4.12

**Date**: 2025-11-13
**Severity**: 🔴 **CRITICAL**
**Impact**: verify-setup command completely broken in PyPI release
**Spec-Kitty Version**: 0.4.12 (PyPI)
**Status**: Bug confirmed in released version

---

## Summary

`spec-kitty verify-setup` crashes with `ImportError` and `UnboundLocalError` in the published v0.4.12 on PyPI. The command tries to import `detect_feature_slug` and `AcceptanceError` from the wrong module location.

---

## Evidence

### Error Message

```python
ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
(/opt/homebrew/lib/python3.11/site-packages/specify_cli/__init__.py)

# Then cascades to:
UnboundLocalError: cannot access local variable 'AcceptanceError' where it is not associated with a value
```

### Location

**File**: `src/specify_cli/verify_enhanced.py:146`

**Problematic code**:
```python
# Line 146
from . import detect_feature_slug, AcceptanceError
```

**Problem**: Trying to import from `specify_cli.__init__` but these are in `specify_cli.acceptance`

**Correct import**:
```python
# Should be:
from .acceptance import detect_feature_slug, AcceptanceError
```

---

## Test Results

### Tests Created: 8 tests

**File**: `tests/functional/test_verify_setup.py`

### Results Against PyPI v0.4.12

```
✅ 2/8 tests PASSING
🔴 6/8 tests FAILING

FAILED: test_verify_setup_runs_without_crashing
FAILED: test_verify_setup_no_import_errors
FAILED: test_verify_setup_from_main_branch
FAILED: test_verify_setup_from_worktree
FAILED: test_verify_setup_with_features_present
FAILED: test_verify_setup_shows_actionable_errors
```

**All 6 failures show the same ImportError/UnboundLocalError**

---

## Root Cause

**File**: `src/specify_cli/verify_enhanced.py`

**Line 146**: Incorrect import statement
```python
try:
    from . import detect_feature_slug, AcceptanceError  # ❌ WRONG
    feature_slug = (feature or detect_feature_slug(repo_root, cwd=cwd)).strip()
    # ...
except AcceptanceError as exc:  # ❌ Undefined because import failed
    # ...
```

**Fix needed**:
```python
try:
    from .acceptance import detect_feature_slug, AcceptanceError  # ✅ CORRECT
    feature_slug = (feature or detect_feature_slug(repo_root, cwd=cwd)).strip()
    # ...
except AcceptanceError as exc:
    # ...
```

---

## Impact

**Who's affected**: 100% of users running `spec-kitty verify-setup` on v0.4.12

**What's broken**:
- Cannot run `spec-kitty verify-setup`
- Cannot diagnose project setup issues
- Cannot validate file integrity
- Command crashes with ugly traceback

**Workaround**: None (command completely broken)

---

## Reproduction Steps

1. Install spec-kitty-cli v0.4.12 from PyPI:
   ```bash
   pip install spec-kitty-cli==0.4.12
   ```

2. Create any project:
   ```bash
   spec-kitty init test-project
   cd test-project
   ```

3. Run verify-setup:
   ```bash
   spec-kitty verify-setup
   ```

4. **Result**: Crashes with ImportError

---

## Test Evidence

Our test suite catches this immediately:

```python
def test_verify_setup_runs_without_crashing(self, temp_project_dir, spec_kitty_repo_root):
    """Test: spec-kitty verify-setup runs without crashing on fresh project"""
    # Create project
    # Run verify-setup

    output = result.stdout + result.stderr

    assert 'ImportError' not in output  # ❌ FAILS
    assert 'UnboundLocalError' not in output  # ❌ FAILS
```

**Test result**: FAILED (catches the bug) ✅

---

## Fix

**File**: `src/specify_cli/verify_enhanced.py`
**Line**: 146

**Change**:
```diff
- from . import detect_feature_slug, AcceptanceError
+ from .acceptance import detect_feature_slug, AcceptanceError
```

**Verification**: This fix exists in local dev repo, just not in PyPI 0.4.12

---

## Recommendation

**Priority**: 🔴 **CRITICAL** - Publish v0.4.13 immediately

**Why**:
- verify-setup is diagnostic command users run when things break
- Command itself is broken (ironic)
- Simple one-line fix
- Already fixed in dev, just needs release

**Release checklist**:
1. ✅ Fix confirmed in local repo
2. ⏳ Publish v0.4.13 to PyPI
3. ⏳ Update our venv and retest
4. ⏳ Verify all 8 tests pass

---

## Test Suite Status

**Tests created**: 8 comprehensive tests for verify-setup command

**Against PyPI v0.4.12**: 6/8 failing (catches bug)
**Against local dev**: Expected to pass (fix is in repo)

**Test categories**:
1. Basic execution (3 tests) - Validates no crashes
2. Different contexts (3 tests) - Main branch, worktree, with features
3. Error handling (2 tests) - Missing .kittify, actionable errors

---

## Timeline

- **2025-11-13 16:00**: Bug discovered (user reported)
- **2025-11-13 16:20**: Tests created (8 tests)
- **2025-11-13 16:25**: Bug confirmed in PyPI v0.4.12 (6/8 tests failing)
- **Next**: Publish v0.4.13 with fix

---

**Status**: Bug confirmed, tests ready, fix ready for release
