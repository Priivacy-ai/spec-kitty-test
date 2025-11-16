# Task Approval System Tests

**Date**: 2025-11-15
**Test File**: `tests/functional/test_task_approval.py`
**Spec-Kitty Commits**: 0f3a16b (approve command), d18951f (review templates)

## Summary

✅ **17 comprehensive tests** for the task approval system
✅ **All tests passing** in 12.96 seconds
✅ **Prevents regression** of the reviewer attribution bug

## The Problem This Tests

### Before Fix (Using `move` command)

```bash
# Implementer creates task
agent: implementer-agent
shell_pid: 12345

# Reviewer approves using move command
$ python3 tasks_cli.py move 001-feature WP01 done --note "Approved"

# RESULT: Wrong attribution!
agent: implementer-agent     # ← Still shows implementer!
shell_pid: 12345             # ← Still implementer's PID!
Activity: implementer approved own work  # ← False audit trail!
```

**Impact**: No way to trace who actually approved the code. Breaks accountability.

### After Fix (Using `approve` command)

```bash
# Implementer creates task
agent: implementer-agent
shell_pid: 12345

# Reviewer approves using approve command
$ python3 tasks_cli.py approve 001-feature WP01 \
    --reviewer-agent "claude-reviewer" \
    --reviewer-shell-pid "$$"

# RESULT: Correct attribution!
agent: claude-reviewer           # ← Updated to reviewer!
shell_pid: 88888                 # ← Reviewer's PID!
review_status: approved          # ← Review outcome!
reviewed_by: claude-reviewer     # ← Who approved!
Activity:
  - implementer-agent created     # ← Implementer preserved
  - claude-reviewer approved      # ← Reviewer added
```

**Impact**: Full audit trail with clear accountability.

## Test Coverage (17 tests)

### 1. Basic Approval Flow (4 tests)

#### test_approve_moves_task_to_done
Tests task moves from `for_review → done`
- ✅ Source file removed from for_review
- ✅ Target file created in done
- ✅ Success message shows reviewer info

#### test_approve_sets_reviewer_frontmatter
Tests frontmatter fields are set correctly
- ✅ `review_status` field added
- ✅ `reviewed_by` field added
- ✅ YAML formatting handled (quoted vs unquoted)

#### test_approve_updates_agent_to_reviewer
Tests agent field is updated to reviewer
- ✅ `agent` changes from implementer to reviewer
- ✅ `shell_pid` changes to reviewer's PID
- ✅ Not implementer's identity anymore

#### test_approve_adds_reviewer_activity_log
Tests activity log gets reviewer entry
- ✅ Reviewer's agent ID in log
- ✅ Reviewer's shell PID in log
- ✅ Both implementer and reviewer preserved

### 2. Validation (3 tests)

#### test_approve_requires_for_review_lane
Tests that tasks must be in `for_review` lane
- ✅ Rejects tasks in `doing` lane
- ✅ Clear error message
- ✅ Shows current lane in error

#### test_approve_rejects_invalid_target_lane
Tests invalid target lanes are rejected
- ✅ Rejects `invalid_lane`
- ✅ Clear validation error
- ✅ Lists valid lanes

#### test_approve_handles_missing_work_package
Tests missing work packages are handled gracefully
- ✅ Returns error code
- ✅ Clear error message
- ✅ No crashes or stack traces

### 3. Reviewer Identity Preservation (3 tests)

#### test_reviewer_agent_recorded_not_implementer
Tests reviewer's agent ID is recorded (not implementer's)
- ✅ `agent: DIFFERENT-REVIEWER` (not implementer-agent)
- ✅ `reviewed_by: DIFFERENT-REVIEWER`
- ✅ Clear distinction between roles

#### test_reviewer_shell_pid_recorded_not_implementer
Tests reviewer's shell PID is recorded (not implementer's)
- ✅ `shell_pid: 44444` (not 12345)
- ✅ Activity log has correct PID
- ✅ No confusion between processes

#### test_implementer_preserved_in_activity_log
Tests original implementer entries are preserved
- ✅ Implementer's entries still in activity log
- ✅ Implementer's shell PID preserved
- ✅ Full history maintained

### 4. Custom Options (3 tests)

#### test_custom_review_status
Tests custom review status messages
- ✅ `--review-status "approved with suggestions"`
- ✅ Recorded in frontmatter
- ✅ Appears in activity log

#### test_custom_target_lane
Tests approving to non-default lanes
- ✅ `--target-lane doing` (needs rework)
- ✅ Task moves to specified lane
- ✅ Lane reflects review outcome

#### test_custom_activity_note
Tests custom notes in activity log
- ✅ `--note "Excellent implementation"`
- ✅ Note added to activity log
- ✅ Combines with auto-generated content

### 5. Dry-Run Mode (2 tests)

#### test_dry_run_shows_plan_without_modifying_files
Tests dry-run shows what would happen
- ✅ `[dry-run]` prefix in output
- ✅ Shows approval details
- ✅ No files modified

#### test_dry_run_no_git_operations
Tests dry-run doesn't touch git
- ✅ Git status unchanged
- ✅ No staged files
- ✅ Safe preview mode

### 6. Git Operations (2 tests)

#### test_approve_removes_source_file
Tests source file is removed
- ✅ File deleted from for_review
- ✅ Git registers removal (as 'R' rename or 'D' delete)
- ✅ Clean operation

#### test_approve_adds_target_file
Tests target file is added
- ✅ File created in done lane
- ✅ Git registers addition (as 'R' rename or 'A' add)
- ✅ Staged correctly

## Test Results

```bash
$ python -m pytest tests/functional/test_task_approval.py -v

============================= 17 passed in 12.96s ==============================
```

All tests pass! ✅

## What These Tests Prevent

### Regression Scenarios Covered

1. **Reviewer Attribution Loss**
   - Tests ensure reviewer identity is always recorded
   - Prevents reverting to implementer's agent ID

2. **Missing Review Metadata**
   - Tests ensure `review_status` and `reviewed_by` fields are set
   - Prevents incomplete approval records

3. **Lane Validation Bypass**
   - Tests ensure only `for_review` tasks can be approved
   - Prevents approving tasks still in progress

4. **Git Operation Failures**
   - Tests ensure files are moved correctly
   - Prevents orphaned files or git state corruption

5. **Activity Log Corruption**
   - Tests ensure both implementer and reviewer are preserved
   - Prevents lost audit trail

## Example Test Output

```bash
$ python -m pytest tests/functional/test_task_approval.py::TestBasicApprovalFlow::test_approve_moves_task_to_done -v

PASSED

Output from approve command:
✅ Approved WP01 → done
   Review status: approved without changes
   Reviewed by: claude-reviewer (shell_pid=88888)
   kitty-specs/001-test-feature/tasks/for_review/WP01.md → kitty-specs/001-test-feature/tasks/done/WP01.md
   Logged: - 2025-11-15T18:32:47Z – claude-reviewer – shell_pid=88888 – lane=done – Approved without changes
```

## Test Maintenance

### When to Run These Tests

1. **Before releases** - Ensure approval system works
2. **After any task system changes** - Detect regressions
3. **When modifying frontmatter handling** - Verify metadata integrity
4. **When updating git operations** - Ensure file moves work

### How to Extend

To add new approval system features:

1. Add test in appropriate class
2. Use `create_test_task_in_review()` helper
3. Verify frontmatter, activity log, and git operations
4. Use YAML-aware assertions (quoted vs unquoted strings)

### Example New Test

```python
def test_new_approval_feature(self, temp_project_dir, spec_kitty_repo_root):
    """Test: New feature description"""
    # Create project and task
    # Run approve with new option
    # Verify new behavior
    # Assert expected results
```

## Key Insights

### Why Git Shows 'R' (Rename)

Git detects that a file was deleted and an identical file was added, and
optimizes this as a rename operation:

```bash
# Instead of:
D  kitty-specs/001-feature/tasks/for_review/WP01.md
A  kitty-specs/001-feature/tasks/done/WP01.md

# Git shows:
R  kitty-specs/001-feature/tasks/for_review/WP01.md -> kitty-specs/001-feature/tasks/done/WP01.md
```

Tests account for both behaviors.

### Why YAML Formatting Matters

Python's YAML library may output:
- `lane: done` (unquoted)
- `lane: "done"` (quoted)

Both are valid YAML. Tests check for both formats.

### Why Implementer Preservation Matters

The activity log must show the FULL history:
1. Implementer created and developed
2. Reviewer approved

This is critical for:
- **Accountability**: Who did what
- **Debugging**: Trace decisions to specific agents
- **Compliance**: Full audit trail
- **Multi-agent coordination**: Clear role separation

## Files Created

```
tests/functional/test_task_approval.py     (+640 lines)  Test suite
TASK_APPROVAL_TESTS.md                     (created)     This doc
```

## Recommendations

### For Future Development

1. ✅ Keep these tests in CI/CD
2. ✅ Run before any task system changes
3. Consider adding:
   - Tests for reject/request-changes workflows
   - Tests for multiple reviewers
   - Tests for re-review scenarios

### For Users

When reviewing code:

```bash
# Always use approve, not move
python3 .kittify/scripts/tasks/tasks_cli.py approve <FEATURE> <WP_ID> \
  --reviewer-agent "$AGENT_ID" \
  --reviewer-shell-pid "$$" \
  --review-status "approved without changes"

# Or use the bash wrapper
.kittify/scripts/bash/tasks-approve.sh <WP_ID> --review-status "approved"
```

## Summary

✅ **17 comprehensive tests**
✅ **All tests passing**
✅ **Full coverage of approve command**
✅ **Prevents reviewer attribution bugs**
✅ **Fast execution (13 seconds)**
✅ **Clear documentation**

The task approval system is thoroughly tested and protected against regression!
