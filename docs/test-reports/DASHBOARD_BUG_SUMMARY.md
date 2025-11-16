# Dashboard File Modification Bug - Test Summary

**Date**: 2025-11-15
**Bug Confirmed**: ✅ Yes, via automated tests
**Severity**: High
**Test Coverage**: 15+ tests

## The Bug

**User Report**: "Agent wrote spec.md, showed up in dashboard. Agent then wrote actual spec content. DID NOT show up until manual refresh."

**Test Confirmation**: ✅ **Bug reproduced and confirmed**

## What We Found

### Bug #1: No Modification Detection

**File**: `src/specify_cli/dashboard/scanner.py:145-157`

The scanner only checks if files **exist**, not if they've been **modified**:

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    return {
        "spec": (feature_dir / "spec.md").exists(),  # ← Returns True/False only
        # No mtime, no size, no hash
    }
```

**Impact**:
- File created (36 bytes) → API: `{"spec": true}`
- File modified (10KB) → API: `{"spec": true}` ← Same response!
- Dashboard has no way to know anything changed

### Bug #2: Constitution Not Tracked

**File**: Same location

Constitution.md is not checked at all:

```python
def get_feature_artifacts(feature_dir: Path):
    return {
        "spec": ...,
        "plan": ...,
        # ❌ "constitution": missing!
    }
```

**Impact**: Constitution cannot be shown in dashboard even if it exists.

## Test Evidence

### Test 1: API Modification Detection

**Test**: `test_dashboard_modification_api.py::test_api_detects_spec_modification`

**Result**: ✗ FAILED (bug confirmed)

```
Created spec.md: 36 bytes, mtime: 1763294203.86
Modified spec.md: 469 bytes, mtime: 1763294206.86

Polled /api/features for 15 seconds:
✗ API response: UNCHANGED

Baseline: {"spec": true}
Current:  {"spec": true}  ← Identical!
```

### Test 2: Browser UI Auto-Update

**Test**: `test_dashboard_file_modifications.py::test_browser_ui_reflects_modifications_without_refresh`

**Result**: ✗ FAILED (bug confirmed)

```
1. Created spec.md with INITIAL_MARKER ✓
2. Loaded dashboard (showed initial content) ✓
3. Modified spec.md with MODIFIED_MARKER ✓
4. Waited 15s without refresh ✓
5. UI did NOT show updated content ✗
6. Manual refresh showed updated content ✓

Conclusion: Manual refresh required!
```

### Test 3: Multiple Modifications

**Test**: `test_dashboard_file_modifications.py::test_multiple_rapid_modifications`

**Result**: ✗ FAILED (bug confirmed)

```
Created v1 → Modified to v2 → Modified to v3
Dashboard: Still shows v1 state
File system: Has v3 content

None of the modifications detected.
```

## Root Cause

The dashboard architecture has **no change detection mechanism**:

1. **No file system watching** - Doesn't monitor for file changes
2. **No mtime tracking** - Doesn't know when files were modified
3. **No content hashing** - Can't detect content changes
4. **No polling with change detection** - Even if polling, compares boolean existence only

The API structure is:
```json
{
  "artifacts": {
    "spec": true   // ← Just existence, no metadata
  }
}
```

Should be:
```json
{
  "artifacts": {
    "spec": {
      "exists": true,
      "mtime": 1763294206.86,
      "size": 469,
      "modified_at": "2025-11-15T14:32:15Z"
    }
  }
}
```

## Impact on Workflows

### Scenario 1: Iterative Spec Writing

```
Agent: "I'll write the spec now"
[Creates spec.md with outline]
Dashboard: Shows spec ✓

Agent: "Let me research and add details"
[Modifies spec.md with 50 requirements]
Dashboard: Shows same state ✗

User: "Did the agent finish?"
[Checks dashboard - sees placeholder]
[Has no idea full spec was written]
```

### Scenario 2: Review Workflow

```
Implementer: Writes plan.md
Reviewer: Checks dashboard - sees plan ✓
Implementer: Updates plan based on feedback
Dashboard: Still shows old plan ✗
Reviewer: Approves based on stale content
[Incorrect approval!]
```

### Scenario 3: Multi-Agent Coordination

```
Agent A: Creates spec.md outline
Agent B: Sees spec exists, starts planning
Agent A: Completes full spec (2000 lines)
Agent B: Still sees outline, creates incomplete plan
[Coordination failure]
```

## Test Suite Created

### Files

1. **test_dashboard_file_modifications.py** (13 tests with Playwright)
   - Tests browser UI updates
   - Tests content rendering
   - Tests user experience

2. **test_dashboard_modification_api.py** (2 tests, backend only)
   - Tests API /api/features response
   - Tests modification detection
   - Isolates backend from frontend

### Test Results

**All 15 tests confirm the bug:**
- 0 tests passing ✗
- 15 tests failing (expected - bug exists) ✓
- All failures have clear diagnostic output

### Running Tests

```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate

# Backend API tests (fast, no browser)
pytest tests/functional/test_dashboard_modification_api.py -v -s

# Full UI tests (requires Playwright/Chromium)
pytest tests/functional/test_dashboard_file_modifications.py -v -s

# Critical test (reproduces exact user scenario)
pytest tests/functional/test_dashboard_file_modifications.py::TestAPIvsUIConsistency::test_browser_ui_reflects_modifications_without_refresh -v -s
```

## Recommended Fix

### Priority 1: Add mtime Tracking (Quick)

**Effort**: 1-2 hours
**Impact**: High - enables detection
**Files**: `scanner.py`, update return types

### Priority 2: Frontend Polling Logic

**Effort**: 2-3 hours
**Impact**: Medium - requires mtime from P1
**Files**: `dashboard.js` (if exists), add polling

### Priority 3: File System Watching

**Effort**: 4-6 hours
**Impact**: High - real-time updates
**Dependencies**: `watchdog` library

## Verification

After fix, these tests should pass:

```bash
# Should change from 0/15 passing to 15/15 passing
pytest tests/functional/test_dashboard_file_modifications.py -v

============================= 15 passed in ~30s ==============================
```

## Summary

✅ **Bug Confirmed**: Dashboard does not detect file modifications
✅ **Root Cause Identified**: No mtime/size/hash tracking
✅ **Test Coverage**: 15 comprehensive tests
✅ **Fix Path**: Clear (add mtime → enhance polling → add watching)
✅ **User Impact**: High (affects all iterative workflows)

---

**Test Files**:
- `tests/functional/test_dashboard_file_modifications.py`
- `tests/functional/test_dashboard_modification_api.py`

**Findings**:
- `findings/0.5.3/2025-11-15_02_dashboard_modification_detection.md`
- `findings/0.5.3/2025-11-15_01_dashboard_artifact_tracking.md`
