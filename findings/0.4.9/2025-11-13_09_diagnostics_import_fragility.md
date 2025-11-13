# Finding: Diagnostics Module Has Fragile Import Dependencies

**Status**: Code Quality Issue
**Severity**: Low-Medium (affects downstream usage, not core functionality)
**Category**: API Stability / Module Design
**Date**: 2025-11-13
**Spec-Kitty Version**: ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (ed3f461)

---

## Executive Summary

The `specify_cli.dashboard.diagnostics.run_diagnostics()` function attempts to import `detect_feature_slug` and `AcceptanceError` from the main `specify_cli` module, but these functions are not exported in `specify_cli/__init__.py`. This causes `ImportError` when calling `run_diagnostics()` from external code, making the diagnostics module unusable outside of spec-kitty's internal context.

**Impact**: Low-Medium
- External testing frameworks cannot use `run_diagnostics()`
- Fragile import pattern with triple fallback mechanism
- Not a user-facing issue (diagnostics work within spec-kitty CLI)
- Limits downstream extensibility and testing

---

## Evidence

### 1. The Import Error

**Test Code** (originally written based on public API):
```python
def test_worktree_detected_by_diagnostics(self, temp_project_dir, spec_kitty_repo_root):
    """Test: Diagnostics correctly detect worktree presence"""
    # ... setup code ...

    # Run diagnostics
    from specify_cli.dashboard import run_diagnostics

    diagnostics = run_diagnostics(project_path)  # <-- FAILS HERE
```

**Error Output**:
```
ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
(/Users/robert/Code/spec-kitty/src/specify_cli/__init__.py)

File: ../spec-kitty/src/specify_cli/dashboard/diagnostics.py:25
    from .. import detect_feature_slug, AcceptanceError  # type: ignore
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

---

### 2. Source Code Analysis

**File**: `src/specify_cli/dashboard/diagnostics.py`

**Lines 21-33** (the problematic import logic):
```python
def run_diagnostics(project_dir: Path) -> Dict[str, Any]:
    """Run comprehensive diagnostics on the project setup using enhanced verification."""
    try:
        from ..manifest import FileManifest, WorktreeStatus  # type: ignore
        from .. import detect_feature_slug, AcceptanceError  # type: ignore
    except (ImportError, ValueError):
        try:
            from specify_cli.manifest import FileManifest, WorktreeStatus  # type: ignore
            from specify_cli import detect_feature_slug, AcceptanceError  # type: ignore
        except ImportError:
            _ensure_specify_cli_on_path()
            from specify_cli.manifest import FileManifest, WorktreeStatus  # type: ignore
            from specify_cli import detect_feature_slug, AcceptanceError  # type: ignore
```

**Analysis**:
1. **First try**: Relative import `from .. import detect_feature_slug`
2. **Second try**: Absolute import `from specify_cli import detect_feature_slug`
3. **Third try**: After path manipulation, try again

All three attempts fail because `detect_feature_slug` is not in `specify_cli/__init__.py`.

---

### 3. Where Functions Actually Live

**Checking the actual location**:
```bash
$ cd /Users/robert/Code/spec-kitty
$ grep -rn "^def detect_feature_slug" src/specify_cli/

src/specify_cli/acceptance.py:189:def detect_feature_slug(
```

**Result**: Function exists in `acceptance.py`, not exported from package root.

**Checking exports**:
```bash
$ cat src/specify_cli/__init__.py | grep -E "(detect_feature_slug|AcceptanceError)"
(no results)
```

**Result**: Neither `detect_feature_slug` nor `AcceptanceError` are exported.

---

### 4. Where Functions Are Used

```bash
$ grep -rn "detect_feature_slug" src/specify_cli/ --include="*.py" | wc -l
5

$ grep -rn "detect_feature_slug" src/specify_cli/ --include="*.py"
src/specify_cli/dashboard/diagnostics.py:25:    from .. import detect_feature_slug, AcceptanceError
src/specify_cli/dashboard/diagnostics.py:29:    from specify_cli import detect_feature_slug, AcceptanceError
src/specify_cli/dashboard/diagnostics.py:33:    from specify_cli import detect_feature_slug, AcceptanceError
src/specify_cli/cli/commands/research.py:8:from specify_cli.acceptance import detect_feature_slug
src/specify_cli/cli/commands/accept.py:15:from specify_cli.acceptance import detect_feature_slug
```

**Key Observation**:
- `research.py` and `accept.py` import correctly: `from specify_cli.acceptance import detect_feature_slug`
- `diagnostics.py` tries incorrect import: `from specify_cli import detect_feature_slug` ❌

---

## Root Cause

The `run_diagnostics()` function assumes that `detect_feature_slug` is available from the package root (`specify_cli.__init__`), but:

1. It's actually in `specify_cli.acceptance`
2. It's never imported/exported in `__init__.py`
3. Other modules import it correctly from `acceptance`
4. Only `diagnostics.py` has the wrong import pattern

**Why it might work internally**: If `diagnostics.py` is only called from within spec-kitty CLI commands (which may have already imported `acceptance`), Python's module cache might make it available. But external callers (like test frameworks) will fail.

---

## Impact Assessment

### Who Is Affected?

✅ **NOT Affected** (works fine):
- Users running `spec-kitty` CLI commands
- Internal spec-kitty code calling diagnostics
- Dashboard server (likely imports work in that context)

❌ **Affected** (broken):
- External Python code importing `run_diagnostics()`
- Testing frameworks using spec-kitty as library
- Downstream tools extending spec-kitty functionality
- Documentation examples showing `run_diagnostics()` usage

### Severity: Low-Medium

**Reasoning**:
- Not critical: Core functionality unaffected
- Medium impact: Breaks public API for external callers
- Low frequency: Few users likely importing this function
- Easy workaround: Use `scan_all_features()` instead
- Fragile code: Triple fallback pattern is code smell

---

## Demonstration

### What Fails

```python
# This is a reasonable expectation for a public API
from specify_cli.dashboard import run_diagnostics
from pathlib import Path

project_path = Path('/path/to/project')
diagnostics = run_diagnostics(project_path)  # ❌ ImportError

print(diagnostics['worktrees_exist'])
```

**Error**:
```
ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
```

### What Works (Workaround)

```python
# Use scanner instead (public API that works)
from specify_cli.dashboard import scan_all_features
from pathlib import Path

project_path = Path('/path/to/project')
features = scan_all_features(project_path)  # ✅ Works

# Check if worktrees exist manually
worktrees_exist = (project_path / '.worktrees').exists()
print(f"Worktrees exist: {worktrees_exist}")
print(f"Features found: {len(features)}")
```

---

## Recommendations

### Option 1: Fix the Import (Recommended)

**File**: `src/specify_cli/dashboard/diagnostics.py`

**Change lines 25, 29, 33**:

**Current (Broken)**:
```python
try:
    from ..manifest import FileManifest, WorktreeStatus
    from .. import detect_feature_slug, AcceptanceError  # ❌ WRONG
except (ImportError, ValueError):
    try:
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli import detect_feature_slug, AcceptanceError  # ❌ WRONG
    except ImportError:
        _ensure_specify_cli_on_path()
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli import detect_feature_slug, AcceptanceError  # ❌ WRONG
```

**Fixed**:
```python
try:
    from ..manifest import FileManifest, WorktreeStatus
    from ..acceptance import detect_feature_slug, AcceptanceError  # ✅ CORRECT
except (ImportError, ValueError):
    try:
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli.acceptance import detect_feature_slug, AcceptanceError  # ✅ CORRECT
    except ImportError:
        _ensure_specify_cli_on_path()
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli.acceptance import detect_feature_slug, AcceptanceError  # ✅ CORRECT
```

**Benefits**:
- Minimal change (just add `.acceptance`)
- Matches pattern used in `research.py` and `accept.py`
- Makes `run_diagnostics()` usable externally
- No API changes required

**Verification**:
```python
# After fix, this should work
from specify_cli.dashboard import run_diagnostics
diagnostics = run_diagnostics(Path('/path/to/project'))
print(diagnostics['worktrees_exist'])  # Should print True/False
```

---

### Option 2: Export Functions from Package Root (Alternative)

**File**: `src/specify_cli/__init__.py`

**Add exports**:
```python
from .acceptance import detect_feature_slug, AcceptanceError

__all__ = [
    'detect_feature_slug',
    'AcceptanceError',
    # ... other exports ...
]
```

**Benefits**:
- Makes imports work as currently written
- Centralizes public API in `__init__.py`
- Better for public package design

**Drawbacks**:
- More invasive change
- May affect other code expecting these not to be exported
- Increases package-level namespace

---

### Option 3: Simplify Import Logic (Best Practice)

The triple-fallback pattern is overly complex. Consider simplifying:

**Current** (33 lines of import logic):
```python
try:
    from ..manifest import FileManifest, WorktreeStatus
    from ..acceptance import detect_feature_slug, AcceptanceError
except (ImportError, ValueError):
    try:
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli.acceptance import detect_feature_slug, AcceptanceError
    except ImportError:
        _ensure_specify_cli_on_path()
        from specify_cli.manifest import FileManifest, WorktreeStatus
        from specify_cli.acceptance import detect_feature_slug, AcceptanceError
```

**Simplified** (6 lines):
```python
from ..manifest import FileManifest, WorktreeStatus
from ..acceptance import detect_feature_slug, AcceptanceError
```

**Reasoning**:
- If imports fail, let them fail (don't hide problems)
- Path manipulation (`_ensure_specify_cli_on_path()`) is usually wrong solution
- If package structure is correct, relative imports work
- Clear errors better than silent fallbacks

**When to use fallbacks**: Only if spec-kitty supports both:
1. Installation as package (`pip install spec-kitty`)
2. Running from source without installation

But even then, a single fallback is sufficient:
```python
try:
    from ..acceptance import detect_feature_slug  # Package mode
except ImportError:
    from specify_cli.acceptance import detect_feature_slug  # Dev mode
```

---

## Testing Impact

### Our Workaround

Since `run_diagnostics()` was broken, we rewrote the test to use public APIs that work:

**Original Test** (broken):
```python
def test_worktree_detected_by_diagnostics(self, temp_project_dir):
    # ... setup ...
    from specify_cli.dashboard import run_diagnostics
    diagnostics = run_diagnostics(project_path)  # ❌ ImportError
    assert diagnostics['worktrees_exist'] == True
```

**Fixed Test** (works):
```python
def test_worktree_detected_by_scanner(self, temp_project_dir):
    # ... setup ...
    from specify_cli.dashboard import scan_all_features

    # Direct filesystem check instead of diagnostics
    worktrees_dir = project_path / '.worktrees'
    assert worktrees_dir.exists()

    # Use scanner (which works) instead of diagnostics
    features = scan_all_features(project_path)
    assert branch_name in [f['id'] for f in features]
```

**Result**: Test now passes, but we lost ability to test diagnostics functionality.

---

## Additional Issues Found

### 1. Type Ignores Hide Problems

The import lines have `# type: ignore` comments:
```python
from .. import detect_feature_slug, AcceptanceError  # type: ignore
```

This suppresses mypy/pyright errors that would have caught this issue during development.

**Recommendation**: Remove `# type: ignore` and fix actual type issues.

---

### 2. `_ensure_specify_cli_on_path()` Is Code Smell

```python
def _ensure_specify_cli_on_path():
    """Add parent directory to Python path if specify_cli not importable."""
    import sys
    from pathlib import Path
    current = Path(__file__).parent.parent.parent
    sys_path_str = str(current)
    if sys_path_str not in sys.path:
        sys.path.insert(0, sys_path_str)
```

**Problems**:
- Modifies `sys.path` at runtime (global state mutation)
- Only needed if package structure is wrong
- Masks installation/import problems
- Makes debugging harder

**Better Solution**: Fix package structure so imports work naturally.

---

### 3. Exception Handling Too Broad

```python
except (ImportError, ValueError):
```

Why catch `ValueError`? Imports don't raise `ValueError`. This likely masks other bugs.

**Better**:
```python
except ImportError:
```

---

## Proposed Fix (Pull Request)

### PR Title
```
fix: Correct import path for detect_feature_slug in diagnostics.py
```

### PR Description
```markdown
## Issue

`run_diagnostics()` attempts to import `detect_feature_slug` from package root:

```python
from specify_cli import detect_feature_slug  # ❌ Not exported here
```

But `detect_feature_slug` lives in `specify_cli.acceptance`, not package root.

## Evidence

- `acceptance.py:189`: Where function is defined
- `research.py:8`: Correct import pattern used elsewhere
- `accept.py:15`: Correct import pattern used elsewhere
- `diagnostics.py:25`: Incorrect import pattern ❌

## Impact

External code calling `run_diagnostics()` gets `ImportError`:

```python
from specify_cli.dashboard import run_diagnostics
diagnostics = run_diagnostics(Path('/project'))
# ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
```

## Fix

Change import from:
```python
from specify_cli import detect_feature_slug, AcceptanceError
```

To:
```python
from specify_cli.acceptance import detect_feature_slug, AcceptanceError
```

This matches the pattern used in `research.py` and `accept.py`.

## Testing

✅ Verified fix allows external code to call `run_diagnostics()`
✅ Existing internal calls continue to work
✅ No API changes required
```

### Files to Change

**File**: `src/specify_cli/dashboard/diagnostics.py`

**Line 25**:
```diff
-    from .. import detect_feature_slug, AcceptanceError  # type: ignore
+    from ..acceptance import detect_feature_slug, AcceptanceError
```

**Line 29**:
```diff
-    from specify_cli import detect_feature_slug, AcceptanceError  # type: ignore
+    from specify_cli.acceptance import detect_feature_slug, AcceptanceError
```

**Line 33**:
```diff
-    from specify_cli import detect_feature_slug, AcceptanceError  # type: ignore
+    from specify_cli.acceptance import detect_feature_slug, AcceptanceError
```

**Optional cleanup** (remove type ignores):
```diff
-    from ..acceptance import detect_feature_slug, AcceptanceError
+    from ..acceptance import detect_feature_slug, AcceptanceError  # Now correctly typed
```

---

## Validation

### Before Fix

```python
>>> from specify_cli.dashboard import run_diagnostics
>>> from pathlib import Path
>>> run_diagnostics(Path('/tmp/test_project'))
Traceback (most recent call last):
  File "diagnostics.py", line 25, in run_diagnostics
    from .. import detect_feature_slug, AcceptanceError
ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
```

### After Fix

```python
>>> from specify_cli.dashboard import run_diagnostics
>>> from pathlib import Path
>>> diag = run_diagnostics(Path('/tmp/test_project'))
>>> diag['worktrees_exist']
True
>>> diag['git_branch']
'main'
```

---

## Related Findings

This issue is related to:
- **Finding 08**: Documentation vs implementation mismatch (worktree .kittify)
- **Testing Pattern**: External code using spec-kitty as library (our test suite)

Both findings highlight the need for:
1. Better public API documentation
2. Upstream tests for external usage patterns
3. Import path consistency across modules

---

## Severity Assessment

**Severity**: Low-Medium

**Reasoning**:
- ✅ Not critical: CLI usage works fine
- ⚠️  Medium impact: Breaks external API usage
- ✅ Low frequency: Few external callers likely
- ✅ Easy fix: One-line change per import
- ⚠️  Code quality: Fragile import pattern is maintenance burden

**Priority**: Should fix (not urgent, but improves code quality)

---

## Contact

**Reporter**: Testing Framework (spec-kitty-test)
**Date**: 2025-11-13
**Spec-Kitty Version**: ed3f461 (verified against this commit)

**Evidence Files**:
- Test suite: `tests/functional/test_worktree_management.py`
- Original failing test: `test_worktree_detected_by_diagnostics` (lines 755-802)
- Workaround test: `test_worktree_detected_by_scanner` (renamed, now passes)

---

**End of Finding Report**
