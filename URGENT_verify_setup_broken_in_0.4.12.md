# 🚨 URGENT: spec-kitty verify-setup is COMPLETELY BROKEN in v0.4.12

## For Immediate Attention

The `spec-kitty verify-setup` command **crashes on every invocation** in the published v0.4.12 release on PyPI.

**Severity**: 🔴 **CRITICAL - BLOCKER**
**Impact**: Command completely non-functional
**Users Affected**: 100% of v0.4.12 users trying to use verify-setup
**Fix Complexity**: Trivial (one-line import fix)

---

## The Problem

**File with bug**: `/Users/robert/Code/spec-kitty/src/specify_cli/verify_enhanced.py`
**Line number**: **146**

**Current (BROKEN) code**:
```python
from . import detect_feature_slug, AcceptanceError
```

**This is WRONG** because:
1. `detect_feature_slug` is NOT in `specify_cli/__init__.py`
2. `AcceptanceError` is NOT in `specify_cli/__init__.py`
3. They are BOTH in `specify_cli/acceptance.py`

**Correct code** (one character change):
```python
from .acceptance import detect_feature_slug, AcceptanceError
```

Just add `.acceptance` between `from` and `import`.

---

## Absolute Paths to Evidence

### 1. Test File That Catches This Bug

**Path**: `/Users/robert/Code/spec-kitty-test/tests/functional/test_verify_setup.py`

**Run this test**:
```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
pytest tests/functional/test_verify_setup.py -v
```

**Current result**: 6/8 tests FAILING with ImportError

**After fix**: All 8 tests should PASS

### 2. Detailed Bug Report

**Path**: `/Users/robert/Code/spec-kitty-test/findings/2025-11-13_16_verify_setup_import_error.md`

**Contains**:
- Full error message
- Exact line number
- Complete reproduction steps
- Impact assessment

### 3. File That Needs Fixing

**Path**: `/Users/robert/Code/spec-kitty/src/specify_cli/verify_enhanced.py`
**Line**: 146

**Current line**:
```python
from . import detect_feature_slug, AcceptanceError
```

**Change to**:
```python
from .acceptance import detect_feature_slug, AcceptanceError
```

### 4. Where The Functions Actually Live

**Path**: `/Users/robert/Code/spec-kitty/src/specify_cli/acceptance.py`

**Confirm they exist**:
```bash
grep -n "class AcceptanceError" /Users/robert/Code/spec-kitty/src/specify_cli/acceptance.py
# Line 29: class AcceptanceError(TaskCliError):

grep -n "def detect_feature_slug" /Users/robert/Code/spec-kitty/src/specify_cli/acceptance.py
# Line 189: def detect_feature_slug(
```

They ARE there, just not being imported from the correct module.

---

## How to Reproduce (30 seconds)

```bash
# 1. Install v0.4.12 from PyPI
pip install spec-kitty-cli==0.4.12

# 2. Create any project
cd /tmp
spec-kitty init crash-test
cd crash-test

# 3. Run the broken command
spec-kitty verify-setup

# RESULT: Crashes with:
# ImportError: cannot import name 'detect_feature_slug' from 'specify_cli'
# UnboundLocalError: cannot access local variable 'AcceptanceError'
```

---

## How to Fix (30 seconds)

```bash
cd /Users/robert/Code/spec-kitty

# Edit this file:
nano src/specify_cli/verify_enhanced.py

# Go to line 146
# Change:
#   from . import detect_feature_slug, AcceptanceError
# To:
#   from .acceptance import detect_feature_slug, AcceptanceError

# Save and exit
```

**That's it.** One word change: add `.acceptance`

---

## How to Verify Fix (2 minutes)

```bash
# 1. In spec-kitty repo
cd /Users/robert/Code/spec-kitty
# (make the fix above)

# 2. Install locally
pip install -e .

# 3. Run our test suite
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
pytest tests/functional/test_verify_setup.py -v

# EXPECTED: All 8 tests should PASS
```

---

## Publish Checklist for v0.4.13

- [ ] Make one-line fix in `verify_enhanced.py:146`
- [ ] Run test suite: `pytest tests/functional/test_verify_setup.py`
- [ ] Confirm: 8/8 tests passing
- [ ] Bump version to 0.4.13
- [ ] Publish to PyPI
- [ ] Verify published version works
- [ ] Close this as fixed

---

## Why This is Urgent

1. **verify-setup is a DIAGNOSTIC command** - users run it when they're already having problems
2. **It's completely broken** - 100% crash rate
3. **Fix is trivial** - literally 11 characters: `.acceptance`
4. **Already have tests** - validation is ready
5. **Users are blocked** - no workaround exists

The irony: Users run `verify-setup` to diagnose problems, and the diagnostic tool itself crashes.

---

## Evidence Summary

| Evidence | Absolute Path |
|----------|---------------|
| **Broken file** | `/Users/robert/Code/spec-kitty/src/specify_cli/verify_enhanced.py` (line 146) |
| **Correct module** | `/Users/robert/Code/spec-kitty/src/specify_cli/acceptance.py` (lines 29, 189) |
| **Test suite** | `/Users/robert/Code/spec-kitty-test/tests/functional/test_verify_setup.py` |
| **Bug report** | `/Users/robert/Code/spec-kitty-test/findings/2025-11-13_16_verify_setup_import_error.md` |

---

## One-Line Fix

**File**: `/Users/robert/Code/spec-kitty/src/specify_cli/verify_enhanced.py`

**Line 146**:
```diff
-        from . import detect_feature_slug, AcceptanceError
+        from .acceptance import detect_feature_slug, AcceptanceError
```

**Save. Publish. Done.**

---

**Your comprehensive test suite caught this within minutes of testing v0.4.12.**

Please fix and publish v0.4.13 immediately - users cannot diagnose their spec-kitty installations with a broken verify-setup command.
