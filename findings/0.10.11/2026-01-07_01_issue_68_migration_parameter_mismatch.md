# Issue #68: Migration Parameter Mismatch Bug

**Date:** 2026-01-07
**Session ID:** issue-68-investigation
**Tested by:** Claude Code Testing Agent
**Category:** Bug Report
**Spec-Kitty Version:** 0.10.11 (PyPI package)
**Analysis Date:** 2026-01-07
**Applies To:** v0.10.11
**Fixed In:** v0.10.12 ✅
**Fix Validated:** 2026-01-07 (see `findings/0.10.12/2026-01-07_01_issue_68_fix_validation.md`)

## Summary

The v0.10.9 repair templates migration (`m_0_10_9_repair_templates.py`) contains a parameter name mismatch when calling `generate_agent_assets()`. The migration code uses `ai=ai_config` but the function signature expects `agent_key=ai_config`, causing a TypeError that prevents the migration from completing successfully.

## Observation

When investigating GitHub Issue #68 (https://github.com/Priivacy-ai/spec-kitty/issues/68#issuecomment-3718786321), we discovered that the migration designed to repair broken templates from issues #62, #63, #64 itself contains a critical bug that prevents it from executing.

**Incorrect code (m_0_10_9_repair_templates.py:131-136):**
```python
generate_agent_assets(
    project_path=project_path,
    command_templates_dir=command_templates_dir,
    ai=ai_config,  # ❌ WRONG parameter name
    script_type="sh"
)
```

**Actual function signature (asset_generator.py:14):**
```python
def generate_agent_assets(
    command_templates_dir: Path,
    project_path: Path,
    agent_key: str,  # ← Expects 'agent_key', not 'ai'
    script_type: str
) -> None:
```

**Errors identified:**
1. Parameter name mismatch: `ai` vs `agent_key`
2. Parameter order inconsistency (though using keyword args mitigates this)

## Impact

- **Severity:** High
- **Scope:**
  - Any user running `spec-kitty upgrade` on v0.10.9-0.10.11 who has broken templates
  - Users affected by issues #62, #63, #64 attempting to repair their templates
  - Blocks automatic template repair for PyPI users
- **Frequency:** Happens always when migration executes (100% reproduction rate)

## Root Cause Analysis

The parameter name mismatch occurred during migration development. The `generate_agent_assets()` function uses `agent_key` as its parameter name (consistently named across the codebase), but the migration was written using the old parameter name `ai` which may have been used in an earlier version or was a developer error.

This bug went undetected because:
1. The migration may not have been fully tested in execution mode
2. No automated tests validated the migration execution path
3. The migration's detect() method may not trigger on common project states
4. Static type checking may not have been enforced on the migration code

## User/Agent Journey

1. User installs spec-kitty v0.10.11 from PyPI
2. User has project with broken templates (bash script references from #62, #63, #64)
3. User runs `spec-kitty upgrade` to repair templates
4. Migration detects broken templates
5. Migration begins repair process
6. Migration attempts to call `generate_agent_assets()` with incorrect parameters
7. **TypeError raised:** `unexpected keyword argument 'ai'`
8. Migration fails, templates remain broken
9. User stuck in broken state

## What Could Have Helped

1. **Automated Testing:** No tests validated the migration execution path with actual function calls
2. **Static Type Checking:** mypy or similar tools should catch parameter mismatches
3. **Integration Tests:** End-to-end migration tests that actually execute the migration
4. **Code Review:** Function signature validation during review
5. **CI/CD Validation:** Type checking and integration tests in CI pipeline
6. **Parameter Validation:** Runtime parameter validation could detect this earlier

## Suggested Improvements

### Immediate Fix
```python
# In m_0_10_9_repair_templates.py line 131-136
generate_agent_assets(
    command_templates_dir=command_templates_dir,
    project_path=project_path,
    agent_key=ai_config,  # ✅ Fixed: 'agent_key' instead of 'ai'
    script_type="sh"
)
```

### Long-term Improvements

1. **Comprehensive Test Suite:** Add test coverage for migration execution paths
   - Created: `tests/test_upgrade/test_migrations/test_m_0_10_9_repair_templates.py`
   - Includes parameter validation tests that catch this bug

2. **Static Type Checking:** Enable mypy in CI/CD pipeline
   ```bash
   mypy src/specify_cli/upgrade/migrations/
   ```

3. **Migration Testing Framework:**
   - Test migration detection
   - Test migration execution (not just dry-run)
   - Validate function calls and parameters
   - Test idempotency

4. **Code Review Checklist:**
   - Verify all function calls use correct parameter names
   - Check function signatures match call sites
   - Validate parameter order when using keyword arguments

5. **Runtime Validation:**
   ```python
   import inspect
   sig = inspect.signature(generate_agent_assets)
   # Validate parameters before calling
   ```

## Related Files

- **Bug Location:** `venv/lib/python3.14/site-packages/specify_cli/upgrade/migrations/m_0_10_9_repair_templates.py` (lines 131-136)
- **Function Definition:** `venv/lib/python3.14/site-packages/specify_cli/template/asset_generator.py` (line 14)
- **Test File:** `tests/test_upgrade/test_migrations/test_m_0_10_9_repair_templates.py` (NEW)
- **GitHub Issue:** https://github.com/Priivacy-ai/spec-kitty/issues/68

## Example Output/Reproduction

### Test Results

**Parameter Validation Test (CAUGHT THE BUG):**
```
FAILED tests/test_upgrade/test_migrations/test_m_0_10_9_repair_templates.py::TestParameterValidation::test_migration_call_parameters_correct

AssertionError: BUG DETECTED: Migration uses 'ai=' parameter but function expects 'agent_key='
Call found:
generate_agent_assets(
                        project_path=project_path,
                        command_templates_dir=command_templates_dir,
                        ai=ai_config,
                        script_type="sh"
                    )

Fix: Change 'ai=ai_config' to 'agent_key=ai_config'
```

### Expected Runtime Error (when migration executes)

```python
TypeError: generate_agent_assets() got an unexpected keyword argument 'ai'
```

## Test Coverage Added

Created comprehensive test suite: `test_m_0_10_9_repair_templates.py`

**Test Classes:**
1. `TestMigrationDetection` (3 tests)
   - Detects bash script references in templates
   - Validates clean projects don't trigger migration
   - Checks all agent directories

2. `TestMigrationExecution` (4 tests)
   - Tests template removal
   - Tests template copying
   - **BUG TEST:** Documents expected TypeError failure
   - Tests repair verification

3. `TestParameterValidation` (2 tests) ⭐ **CRITICAL**
   - ✅ `test_generate_agent_assets_signature_match` - PASSED
   - ❌ `test_migration_call_parameters_correct` - **CAUGHT THE BUG**

### Key Test That Catches Bug

```python
def test_migration_call_parameters_correct(self):
    """Validates migration calls generate_agent_assets correctly"""
    import specify_cli.upgrade.migrations.m_0_10_9_repair_templates as migration_module
    migration_file = Path(migration_module.__file__)
    source = migration_file.read_text()

    call_start = source.find('generate_agent_assets(')
    call_end = source.find(')', call_start)
    call_text = source[call_start:call_end + 1]

    # BUG CHECK: Should use 'agent_key', not 'ai'
    assert 'ai=' not in call_text, (
        f"BUG DETECTED: Migration uses 'ai=' parameter but function expects 'agent_key='\n"
        f"Fix: Change 'ai=ai_config' to 'agent_key=ai_config'"
    )
```

## Validation Against PyPI Release

**Version Tested:** spec-kitty v0.10.11 (from PyPI)
**Test Result:** ✅ **Bug confirmed** - Test successfully caught parameter mismatch
**Test Command:**
```bash
python -m pytest tests/test_upgrade/test_migrations/test_m_0_10_9_repair_templates.py::TestParameterValidation -v
```

## CI Status - v0.10.12 Release Blocked

**GitHub Actions Run:** 20784002290 (FAILED)
**Issue:** Test suite expects 12 gitignore entries, but now has 13 after adding `.kittify/.dashboard`

**Failing Test:**
```
tests/integration/test_init_flow.py::test_init_flow_fresh_project FAILED
assert 13 == 12
```

**Root Cause:** Issue #22 fix added `.kittify/.dashboard` to gitignore protection, but tests weren't updated.

**Status:** This is a SEPARATE issue from the Issue #68 parameter mismatch bug. The v0.10.12 release is blocked by this test failure, not by the migration bug we documented here.

**Note:** My local test suite (`tests/functional/test_git_protection.py`) checks for specific directories rather than hard-coded counts, so it's not affected by this issue. All 9 tests pass locally.

## Resolution

**✅ FIXED IN v0.10.12** (2026-01-07)

The bug has been successfully fixed and validated. See complete validation report:
`findings/0.10.12/2026-01-07_01_issue_68_fix_validation.md`

## Next Steps

1. ✅ **Completed:** Comprehensive test suite created
2. ✅ **Completed:** Bug validated against PyPI v0.10.11
3. ✅ **Completed:** Local tests pass (not affected by gitignore count issue)
4. ✅ **Completed:** Implementation team fixed migration code (v0.10.12)
5. ✅ **Completed:** Fix validated against PyPI v0.10.12
6. ✅ **Completed:** Test suite confirms fix (7/9 tests passing)
7. 📝 **Recommended:** Update 2 tests to expect success instead of failure
8. 📝 **Recommended:** Add static type checking to CI/CD
9. 📝 **Recommended:** Keep regression tests in place

## Related Issues

- **Primary:** Issue #68 - CLI Path Resolution Bug (this finding)
- **Duplicate:** Issue #69 - Upgrade Failure (**SAME BUG** - user report of this issue)
- **Related:** Issue #62 - PyPI package missing templates
- **Related:** Issue #63 - Template distribution failure
- **Related:** Issue #64 - Bash script references in templates
- **Related:** Migration `m_0_10_9_repair_templates` - Designed to fix #62, #63, #64 but has this bug

**Note:** Issue #69 is a duplicate report of this bug from a user experiencing upgrade failure.
See: `findings/0.10.12/2026-01-07_02_issues_68_69_duplicate_analysis.md`

---

**Notes:**

This bug is particularly impactful because it prevents the migration that was designed to fix issues #62, #63, #64. Users affected by those issues cannot automatically repair their templates until this bug is fixed.

The test suite created for this bug follows the new testing philosophy (see CLAUDE.md) and provides both functional and validation testing to prevent similar bugs in future migrations.

**Testing Philosophy Applied:**
- Distribution test approach (no `SPEC_KITTY_TEMPLATE_ROOT` bypass in critical tests)
- Tests what ships to users (PyPI package validation)
- Caught real bug in real PyPI release
- Validates parameter signatures statically
