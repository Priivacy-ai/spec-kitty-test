# v0.11.0 Critical Bugs Summary

**Date**: 2026-01-11
**Version**: spec-kitty-cli 0.11.0
**Test Suite**: 264 tests (253 workspace-per-WP + 11 frontmatter validation)
**Status**: 🔴 **BLOCK MERGE**

## Critical Bugs Found (5)

### 🔴 Bug #1: Malformed Frontmatter in 8 Template Files
- **Severity**: CRITICAL - Breaks ALL agents
- **Impact**: 100% of agent commands fail with ConfigFrontmatterError
- **Files**: accept.md, analyze.md, checklist.md, clarify.md, merge.md (software-dev) + 3 research templates
- **Fix**: Add closing `---` after description field in each file
- **Test**: 11 frontmatter validation tests created
- **Time to fix**: 15 minutes

### 🔴 Bug #2: `build_dependency_graph()` Returns Empty Dict
- **Severity**: CRITICAL - Blocks all dependency features
- **Impact**: Dependency validation, cycle detection, topological sort all broken
- **Root cause**: Function doesn't scan directory for WP files
- **Fix**: Add file scanning with `tasks_dir.glob("WP*.md")`
- **Test**: 28 dependency graph tests fail
- **Time to fix**: 2-3 hours

### 🔴 Bug #3: Cannot Detect Feature Context from Main
- **Severity**: CRITICAL - Blocks workspace creation
- **Impact**: Cannot run `spec-kitty implement WP01` from main repo
- **Root cause**: Context detection doesn't scan `kitty-specs/`
- **Fix**: Add kitty-specs/ scanning, auto-select if only one feature
- **Test**: Multiple implement command tests fail
- **Time to fix**: 1-2 hours

### 🔴 Bug #4: `finalize-tasks` Command Missing
- **Severity**: CRITICAL - Required for workflow
- **Impact**: Cannot parse dependencies from tasks.md
- **Root cause**: Command not implemented
- **Fix**: Add command to tasks.py with dependency parsing logic
- **Test**: test_finalize_tasks_command_exists fails
- **Time to fix**: 3-4 hours

### 🔴 Bug #5: Plan Template Not Found
- **Severity**: CRITICAL - Blocks planning
- **Impact**: Cannot run setup-plan command
- **Root cause**: Template path resolution incorrect
- **Fix**: Update path to use repo_root instead of worktree_path
- **Test**: test_plan_no_worktree_created fails
- **Time to fix**: 1 hour

## Medium Priority Bug (1)

### 🟡 Bug #6: `implement` Command Missing `--json` Flag
- **Severity**: MEDIUM - Nice-to-have
- **Impact**: Cannot parse structured output in scripts
- **Fix**: Add --json flag parameter
- **Test**: test_implement_with_json_output fails
- **Time to fix**: 1 hour

---

## Total Bugs: 6 (5 critical, 1 medium)
## Estimated Fix Time: 8-11 hours development + validation
## Recommendation: **DO NOT MERGE** until all critical bugs fixed

---

## Quick Fix Priority

**Fix in this order for fastest path to working state:**

1. ⏱️ **15 min** - Fix frontmatter (Bug #1) - Unblocks agents
2. ⏱️ **2-3 hours** - Fix build_dependency_graph() (Bug #2) - Enables dependency system
3. ⏱️ **1-2 hours** - Fix context detection (Bug #3) - Enables implement command
4. ⏱️ **3-4 hours** - Add finalize-tasks (Bug #4) - Completes workflow
5. ⏱️ **1 hour** - Fix setup-plan (Bug #5) - Enables planning

**Total**: ~8-11 hours to core functionality

After fixes, expect:
- ✅ 200+ tests passing (out of 264)
- ✅ All critical workflows functional
- ✅ Ready for distribution testing

---

## Test Reports

See detailed reports:
- `2026-01-11_01_workspace_per_wp_validation_report.md` - Full validation results
- `2026-01-11_02_regression_analysis_v010_to_v011.md` - Version comparison
- `2026-01-11_03_implementation_feedback.md` - Detailed bug reports with fixes

---

**Report Generated**: 2026-01-11
**Test Coverage**: 264 comprehensive tests
**Bugs Found**: 6 critical issues preventing release
