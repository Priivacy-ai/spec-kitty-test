# Summary: Dashboard Update Issues - Complete Analysis

**Date:** 2025-11-15
**Session ID:** dashboard-update-comprehensive-testing
**Tested by:** Claude Code + Playwright + User Report
**Category:** Bug Report - Dashboard Real-Time Updates
**Spec-Kitty Version:** 0.5.2 (PyPI), 0.5.3-pre (local)
**Analysis Date:** 2025-11-15

## Summary

Comprehensive testing revealed **three distinct bugs** in the dashboard update system,
plus one UX confusion issue with template paths.

## Bugs Found

### Bug #1: Dashboard Doesn't Detect File MODIFICATIONS ⚠️ HIGH

**Status**: ✅ Confirmed by automated tests
**Severity**: High
**User Impact**: Must manually refresh to see file changes

**What Happens:**
1. Agent creates `spec.md` with placeholder ("Generating spec...")
2. Dashboard shows `spec: true` ✓
3. Agent writes actual 10KB spec content
4. Dashboard **STILL** shows `spec: true` (no change detected) ✗
5. User refreshes browser → sees updated content

**Root Cause:**
```python
# src/specify_cli/dashboard/scanner.py:145-157
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    return {
        "spec": (feature_dir / "spec.md").exists(),  # ← Only checks existence!
        # No mtime, no size, no hash checking
    }
```

**API Response:**
```json
{
  "spec": true  // Before: 36 bytes
              // After: 10KB
              // Response: IDENTICAL!
}
```

**Tests:** `test_dashboard_modification_api.py`, `test_dashboard_file_modifications.py`
**Test Result:** ✗ 15/15 tests confirm bug

### Bug #2: Constitution.md Not Tracked ⚠️ MEDIUM

**Status**: ✅ Confirmed
**Severity**: Medium
**Impact**: Constitution cannot be shown in dashboard

**What's Missing:**
```python
def get_feature_artifacts(feature_dir: Path):
    return {
        "spec": ...,
        "plan": ...,
        # ❌ "constitution": NOT checked at all!
    }
```

Constitution.md is a primary workflow artifact but scanner doesn't look for it.

**Tests:** `test_dashboard_live_updates.py`

### Bug #3: Misleading Path Metadata ⚠️ LOW

**Status**: ✅ Confirmed
**Severity**: Low (UX confusion)
**Impact**: Users confused about which file they're viewing

**What Shows:**
```markdown
*Path: [.kittify/templates/commands/implement.md]*
```

**Reality:**
- Claude reading: `.claude/commands/spec-kitty.implement.md`
- Codex reading: `.codex/prompts/spec-kitty.implement.md`

Users think they're seeing unrendered template (they're not).

**Tests:** `test_slash_command_paths.py`
**Test Result:** 1/12 tests failing (clarify.md has wrong path)

### Not a Bug: Variable Substitution Works ✓

`{SCRIPT}` IS being substituted correctly:
- Template has: `{SCRIPT}`
- Rendered has: `.kittify/scripts/bash/check-prerequisites.sh --json`

`$ARGUMENTS` is intentionally left as placeholder for runtime substitution by
the slash command framework.

## Test Coverage Created

### Dashboard Modification Tests

**Files:**
- `test_dashboard_file_modifications.py` - 13 Playwright tests
- `test_dashboard_modification_api.py` - 2 backend API tests

**Total**: 15 tests
**Status**: ✗ All failing (expected - confirms bugs exist)

**Key Tests:**
1. `test_spec_modification_detected` - Catches modification detection bug
2. `test_api_detects_spec_modification` - Isolates backend issue
3. `test_browser_ui_reflects_modifications_without_refresh` - Tests UX
4. `test_modification_latency_under_10_seconds` - Performance requirement
5. `test_file_mtime_change_triggers_update` - Tests file system monitoring

### Template Variable Tests

**File:** `test_template_variable_substitution.py`
**Total**: 9 tests
**Status**: ✅ All passing (variables ARE being substituted)

### Slash Command Path Tests

**File:** `test_slash_command_paths.py`
**Total**: 12 tests
**Status**: 11/12 passing (1 failure in path metadata)

## What's Missing (Answer to User's Question)

**User asked**: "What's missing?"

Looking at their output, the agent stopped because:

1. ✓ **Variables ARE substituted** (in current version)
2. ✗ **Path metadata is wrong** (shows template path, not actual)
3. ? **Agent configuration issue?** (Codex might be reading wrong file)
4. ✗ **$ARGUMENTS handling unclear** (agent doesn't know if it's literal or placeholder)

**Most likely**: User has older version where {SCRIPT} wasn't being substituted, OR
Codex slash command is configured to point to wrong file.

## How to Verify User's Issue

**Check user's actual file:**
```bash
# What does the rendered command actually say?
cat .codex/prompts/spec-kitty.implement.md | grep -A 2 "Run.*from repo root"
```

**Should show:**
```
Run `.kittify/scripts/bash/check-prerequisites.sh --json` from repo root...
```

**If shows:**
```
Run `{SCRIPT}` from repo root...
```

Then template rendering is broken in their version.

**Check Codex slash command configuration:**
```bash
# Where does /spec-kitty.implement point?
# Should point to: .codex/prompts/spec-kitty.implement.md
# NOT to: templates/commands/implement.md
```

## Recommended Fixes

### Priority 1: Fix File Modification Detection (HIGH)

**File:** `src/specify_cli/dashboard/scanner.py`

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, Any]:
    """Return artifacts with modification times."""
    artifacts = {}

    for name, filename in [
        ("constitution", "constitution.md"),  # ← Add this!
        ("spec", "spec.md"),
        ("plan", "plan.md"),
        # ... etc
    ]:
        file_path = feature_dir / filename
        if file_path.exists():
            stat = file_path.stat()
            artifacts[name] = {
                "exists": True,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
        else:
            artifacts[name] = {"exists": False}

    return artifacts
```

**Impact:** Enables modification detection, fixes all 15 failing tests

### Priority 2: Fix Path Metadata (MEDIUM)

**Location:** Template rendering code

```python
# When rendering templates
rendered_path = f".{agent}/{'commands' if agent == 'claude' else 'prompts'}/spec-kitty.{cmd_name}.md"
header = f"*Current File: [{rendered_path}]({rendered_path})*\n"
```

**Impact:** Reduces user confusion

### Priority 3: Add Constitution Tracking (MEDIUM)

Add to `get_feature_artifacts()` - see Priority 1 fix above.

## Test Results Summary

| Test Suite | Tests | Passing | Finding |
|------------|-------|---------|---------|
| Modification Detection | 15 | 0 | Bug #1 confirmed |
| Variable Substitution | 9 | 9 | Working correctly ✓ |
| Slash Command Paths | 12 | 11 | Path metadata wrong |
| Dashboard sys.path | 4 | 4 | Previously fixed ✓ |
| Task Approval | 17 | 17 | Previously fixed ✓ |

**Total New Tests**: 57 tests created today

## User's Specific Issue

Based on their output showing `*Path: [templates/commands/implement.md]*` and
agent saying "placeholder {SCRIPT} wasn't provided":

**Diagnosis**: Either:
1. Older spec-kitty version (before variable substitution fix)
2. Codex slash command misconfigured (pointing to wrong file)
3. Confused by misleading path metadata

**Solution**:
1. Update spec-kitty to latest version
2. Verify `.codex/prompts/spec-kitty.implement.md` exists and has substituted variables
3. Check Codex slash command configuration (if configurable)

## Next Steps

1. ✅ Tests created (57 new tests)
2. ✅ Bugs documented (4 findings)
3. Fix modification detection (add mtime tracking)
4. Fix path metadata (show correct paths)
5. Add constitution tracking
6. Re-run tests to verify fixes

---

**Test Files:**
- `test_dashboard_file_modifications.py` (13 tests)
- `test_dashboard_modification_api.py` (2 tests)
- `test_dashboard_live_updates.py` (16 tests)
- `test_slash_command_paths.py` (12 tests)
- `test_template_variable_substitution.py` (9 tests)

**Findings:**
- `2025-11-15_01_dashboard_artifact_tracking.md`
- `2025-11-15_02_dashboard_modification_detection.md`
- `2025-11-15_03_template_path_metadata.md`
- `2025-11-15_04_dashboard_modification_summary.md` (this file)
