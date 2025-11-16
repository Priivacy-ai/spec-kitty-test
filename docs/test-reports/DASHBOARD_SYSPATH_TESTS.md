# Dashboard sys.path Priority Tests

**Date**: 2025-11-15
**Test File**: `tests/functional/test_dashboard_syspath.py`
**Spec-Kitty Commit**: c989f9a (Dashboard subprocess import fix)

## Purpose

These tests ensure the dashboard subprocess startup fix (commit c989f9a) doesn't regress. The fix prevents `ModuleNotFoundError` when starting dashboards in Python environments with complex PYTHONPATH/.pth file configurations.

## The Bug (Before Fix)

### Scenario
User's Python environment has multiple project paths in sys.path:
```python
sys.path = [
    '',  # empty string
    '/usr/lib/python3.14',  # stdlib
    '/Users/robert/Code/priivacy_benchmark/pipeline/src',  # other project
    '/Users/robert/Code/vds/vds-dhl-mcp/src',  # other project
    '/Users/robert/Code/claude-swarm-coordinator/src',  # other project
    '/Users/robert/Code/spec-kitty/src',  # ← spec-kitty at position 8!
]
```

### Old Code (Broken)
```python
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
```

### What Happened
1. Dashboard subprocess starts with user's polluted sys.path
2. spec-kitty path is already in sys.path at position [8]
3. Conditional check returns False → insertion skipped
4. Python tries to import `specify_cli.dashboard`
5. Searches positions [0-7] first → module not found
6. **ModuleNotFoundError: No module named 'specify_cli.dashboard'**

### New Code (Fixed)
```python
# Always insert at position 0 to ensure correct spec-kitty version takes priority
# over any other paths in PYTHONPATH or .pth files
sys.path.insert(0, str(repo_root))
```

## Test Coverage

### Test 1: `test_dashboard_starts_with_polluted_syspath`
**What it tests**: Dashboard starts successfully when PYTHONPATH contains multiple fake project paths.

**How it works**:
1. Creates test project
2. Creates 3 fake project directories with `/src` paths
3. Sets `PYTHONPATH` to include all fake paths
4. Attempts to start dashboard
5. Verifies no `ModuleNotFoundError` or `ImportError`

**Why it's important**: Simulates the exact environment that caused the original bug.

### Test 2: `test_dashboard_health_check_with_polluted_syspath`
**What it tests**: Dashboard health endpoint works correctly with polluted sys.path.

**How it works**:
1. Creates test project
2. Pollutes PYTHONPATH with interference paths
3. Starts dashboard
4. Calls `/api/health` endpoint
5. Verifies correct project_path is returned

**Why it's important**: Ensures the correct spec-kitty modules are loaded, not modules from other paths.

### Test 3: `test_dashboard_regression_clean_environment`
**What it tests**: Dashboard still works in clean environments without PYTHONPATH pollution.

**How it works**:
1. Removes PYTHONPATH from environment
2. Starts dashboard
3. Verifies it works normally

**Why it's important**: Regression test to ensure the fix doesn't break normal operation.

### Test 4: `test_threaded_mode_unaffected_by_syspath`
**What it tests**: Threaded mode (background_process=False) works regardless of sys.path.

**How it works**:
1. Uses lifecycle API directly with threaded mode
2. Verifies health check works
3. Documents that threaded mode doesn't have the subprocess issue

**Why it's important**: Demonstrates the bug was specific to subprocess mode, not threading mode.

## Test Results

```bash
$ python -m pytest tests/functional/test_dashboard_syspath.py -v

============================== 4 passed in 6.09s ==============================
```

✅ All tests pass with the fix in place (commit c989f9a)

## How to Verify the Fix

### Without the fix (would fail):
```bash
# Go to priivacy_rust or any project with complex environment
cd ~/Code/priivacy_rust
spec-kitty dashboard

# ERROR: ModuleNotFoundError: No module named 'specify_cli.dashboard'
```

### With the fix (works):
```bash
cd ~/Code/priivacy_rust
spec-kitty dashboard

# ✅ Spec Kitty Dashboard
# ✅ URL: http://127.0.0.1:9237
# ✅ Status: Started new dashboard instance
```

## Test Environment Simulation

The tests simulate these common Python environment scenarios:

1. **Developer workstation** with multiple projects
2. **PYTHONPATH entries** from .bashrc/.zshrc
3. **.pth files** in site-packages
4. **Virtual environments** with extra paths
5. **IDE configurations** that modify sys.path

All of these can cause spec-kitty's path to be present but not at position 0.

## Key Insights

### Why the Bug Was Hard to Catch

1. **Environment-dependent**: Only happens with specific sys.path configurations
2. **Works in clean test environments**: CI/CD with fresh venvs won't catch it
3. **Works for simple projects**: Only fails when user has complex Python setup
4. **Intermittent**: Depends on which other projects user has

### Why These Tests Are Valuable

1. **Explicit PYTHONPATH pollution**: Tests actively create the problematic scenario
2. **Reproducible**: Anyone can run these tests, not just in specific environments
3. **Fast**: Complete in 6 seconds
4. **Comprehensive**: Cover both subprocess and threaded modes

## Recommendations

### For Future Development

1. ✅ Keep these tests in the suite
2. ✅ Run before releasing any dashboard changes
3. Consider adding similar tests for other subprocess-based features
4. Document sys.path handling in dashboard architecture docs

### For Users

If you encounter dashboard startup issues:

1. Check `python -c "import sys; print(sys.path)"`
2. Look for spec-kitty path position
3. Verify it's at position [0] or [1]
4. Update to version with commit c989f9a or later

## Files

```
tests/functional/test_dashboard_syspath.py          (+350 lines)  New test file
DASHBOARD_SYSPATH_TESTS.md                          (created)     This doc
```

## Summary

✅ **4 comprehensive tests added**
✅ **All tests pass**
✅ **Covers polluted and clean environments**
✅ **Fast execution (6 seconds)**
✅ **Prevents regression of critical bug**

These tests ensure that users with complex Python environments can successfully start dashboards, regardless of their PYTHONPATH/.pth file configurations.
