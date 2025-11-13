# Script Execution UX Issues - Findings for Upstream Improvements

**Date:** 2025-11-13
**Category:** Script Execution Validation
**Spec-Kitty Version:** c02c2ad (2025-11-13)
**Test Results:** 10/15 passing (67%)
**Priority:** HIGH - Scripts are critical infrastructure

---

## Executive Summary

While testing script execution in Category 6, we discovered **5 major UX issues** that make spec-kitty harder to use for both humans and LLMs. These issues cause confusion, failed workflows, and require deep understanding of internal implementation details.

**Impact:**
- ❌ Scripts fail silently or with cryptic errors
- ❌ Agents can't reliably invoke scripts without trial-and-error
- ❌ Humans must read script source code to understand usage
- ❌ Documentation doesn't match actual behavior

**Recommendation:** Address these 5 issues before 1.0 release to improve adoption and reduce support burden.

---

## Issue 1: Mixed Output Streams Break JSON Parsing

### Problem

Scripts output both **informational messages** and **JSON data** to stdout, making programmatic parsing fragile:

```bash
$ .kittify/scripts/bash/create-new-feature.sh --json "Test feature"
[spec-kitty] Copied spec template from /path/to/template
{"BRANCH_NAME":"001-test","SPEC_FILE":"/path/spec.md","FEATURE_NUM":"001"}
```

**Why This Is Bad:**
- LLMs attempting to parse JSON must scan for `{` character
- Standard `json.loads(stdout)` fails - requires custom parsing
- Log messages may contain JSON-like text, causing false positives
- Silent failures if script adds new log line before JSON

### Evidence from Testing

```python
# What we expected to work:
output = subprocess.run([script, '--json', 'description'], capture_output=True)
data = json.loads(output.stdout)  # ❌ FAILS

# What we had to implement:
def extract_json_from_output(output: str) -> dict:
    """Scan output line-by-line looking for JSON"""
    for line in output.strip().split('\n'):
        if line.strip().startswith('{'):
            return json.loads(line)
    return None
```

**5 test failures** required this workaround.

### Recommendation: Separate Streams

**Option A: Use stderr for logs (RECOMMENDED)**
```bash
# Log to stderr, JSON to stdout
echo "[spec-kitty] Copied template" >&2
printf '{"BRANCH_NAME":"%s"}\n' "$BRANCH_NAME"
```

**Option B: --quiet flag**
```bash
if ! $QUIET_MODE; then
    echo "[spec-kitty] Copying template..."
fi
printf '{"BRANCH_NAME":"%s"}\n' "$BRANCH_NAME"
```

**Option C: Structured logging**
```bash
# All output is JSON
printf '{"type":"log","message":"Copying template"}\n'
printf '{"type":"result","data":{"BRANCH_NAME":"%s"}}\n' "$BRANCH_NAME"
```

**Impact:**
- ✅ Standard JSON parsing works
- ✅ LLMs can reliably extract data
- ✅ Scripts can be chained with `jq`
- ✅ Logs visible without breaking automation

**Effort:** Low (1-2 days to fix all scripts)

---

## Issue 2: Worktree Creation Location Undocumented and Surprising

### Problem

When `create-new-feature.sh` runs, features are created in **`.worktrees/{feature}/kitty-specs/`**, NOT directly in **`kitty-specs/`** as documentation and command templates suggest.

**What Documentation/Templates Say:**
```markdown
# From specify.md command template:
The script creates and checks out the new branch and initializes
the spec file before writing.

Parse its JSON output for BRANCH_NAME, SPEC_FILE, FEATURE_NUM
```

**What Actually Happens:**
```bash
$ ls -la
.worktrees/
  └── 001-test-feature/
      ├── .git             # Worktree link
      ├── .kittify/        # Symlink to main
      └── kitty-specs/
          └── 001-test-feature/
              └── spec.md

kitty-specs/               # Empty until feature merged!
```

### Evidence from Testing

```python
# Test expectation (from documentation):
feature_dir = project_path / 'kitty-specs' / f"{feature_num}-test-feature"
assert feature_dir.exists()  # ❌ FAILS

# Actual location:
feature_dir = project_path / '.worktrees' / f"{feature_num}-test-feature" / 'kitty-specs' / f"{feature_num}-test-feature"
assert feature_dir.exists()  # ✅ WORKS
```

**Why This Is Bad:**
- Agents reading command templates expect `kitty-specs/` location
- No explanation in templates of worktree structure
- Path references in JSON use absolute paths, hiding the structure
- Humans confused when `ls kitty-specs/` shows nothing after running specify

### Recommendation: Document Worktree Model Explicitly

**Fix 1: Update Command Templates**

Add to `specify.md` command template:
```markdown
## Output and Feature Location

The script creates an **isolated worktree** for your feature at:
```
.worktrees/{feature-slug}/
├── .git                    # Git worktree link
├── .kittify/               # Symlink to main .kittify/
└── kitty-specs/
    └── {feature-slug}/
        └── spec.md         # Your feature spec
```

**All work happens in the worktree** until you merge to main.

JSON output includes:
- `BRANCH_NAME`: Feature branch name
- `SPEC_FILE`: Absolute path to spec.md in worktree
- `WORKTREE_PATH`: Path to worktree directory
- `FEATURE_NUM`: Feature number (e.g., "001")

After merge, feature moves to main repo's `kitty-specs/{feature-slug}/`.
```

**Fix 2: Add WORKTREE_PATH to JSON Output** (Already done! ✅)

**Fix 3: Dashboard Should Highlight Worktree Context**

When agent runs from worktree, dashboard should show:
```
📍 Current Context: .worktrees/001-test-feature
🌿 Branch: feature/001-test-feature
📂 Feature: 001-test-feature
```

**Impact:**
- ✅ Agents understand isolation model
- ✅ Humans know where their work is
- ✅ Reduced "where did my files go?" support issues

**Effort:** Medium (documentation updates + UI enhancement)

---

## Issue 3: Context-Dependent Scripts Fail with Unclear Errors

### Problem

Some scripts **silently fail** or provide **unhelpful errors** when run from wrong context:

```bash
# Running setup-plan from main branch:
$ .kittify/scripts/bash/setup-plan.sh 001-test-feature
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ ERROR: Command run from wrong location!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current location: /Users/robert/Code/test_project
Current branch: main
Required: Feature branch (e.g., 001-feature-name)

🔧 TO FIX THIS ISSUE:
1. List available worktrees: ls .worktrees/
2. Navigate to a worktree: cd .worktrees/001-test-feature
3. Retry the command
```

**Why This Is Good (Partially):**
- ✅ Error message is clear and actionable
- ✅ Suggests remediation steps
- ✅ Shows expected vs actual state

**Why This Is Still Bad:**
- ❌ Agents reading command templates don't know context requirements
- ❌ No way to invoke script from main branch with feature argument
- ❌ Requires cd into worktree (breaks automation)
- ❌ Command template doesn't mention context requirement

### Evidence from Testing

```python
# Test attempt (from main branch):
result = subprocess.run(
    [str(plan_script), feature_slug],
    cwd=project_path,  # Main branch context
    capture_output=True,
    text=True
)
assert result.returncode == 0  # ❌ FAILS - Exit code 1

# Error message good, but shouldn't require context switch
```

### Recommendation: Make Scripts Context-Agnostic

**Option A: Accept --worktree flag**
```bash
$ .kittify/scripts/bash/setup-plan.sh 001-test --worktree .worktrees/001-test
# Script changes to worktree, runs, returns to original location
```

**Option B: Auto-detect and execute in correct context**
```bash
#!/usr/bin/env bash
# setup-plan.sh

FEATURE_SLUG="$1"
REPO_ROOT=$(find_repo_root)
WORKTREE_PATH="$REPO_ROOT/.worktrees/$FEATURE_SLUG"

if [ "$(git branch --show-current)" != "$FEATURE_SLUG" ]; then
    if [ -d "$WORKTREE_PATH" ]; then
        # Execute in worktree context automatically
        (cd "$WORKTREE_PATH" && bash "$0" "$@")
        exit $?
    fi
fi

# Proceed with actual work...
```

**Option C: Document context requirements prominently**

Update command templates to show:
```markdown
## Prerequisites

⚠️ **CONTEXT REQUIREMENT**: This command must run from a feature worktree.

```bash
# From main branch:
cd .worktrees/001-your-feature
/spec-kitty.plan

# Or use the agent to auto-detect context
```

Agents: Use `git branch --show-current` to verify context before running.
```

### Recommendation (BEST): Combination of B + C

1. **Scripts auto-detect and switch context** when possible
2. **Command templates document requirements** for transparency
3. **Error messages remain helpful** when auto-switch fails

**Impact:**
- ✅ Agents can invoke scripts from any location
- ✅ Humans don't need to remember context rules
- ✅ Automation doesn't break on cd requirements
- ✅ Still fail gracefully with clear errors

**Effort:** Medium (refactor 6 scripts, update templates)

---

## Issue 4: Inconsistent Script Argument Patterns

### Problem

Scripts have **inconsistent and undocumented** argument patterns that don't match command template examples:

| Script | Template Says | Actually Expects | Discovery Method |
|--------|---------------|------------------|------------------|
| `create-new-feature.sh` | `--json "{ARGS}"` | ✅ Works | Template correct |
| `setup-plan.sh` | `<feature_slug>` | ✅ Works (but context-dependent) | Trial and error |
| `move-task-to-doing.sh` | `<feature_slug> <wp_id>` | ❌ ERROR: "Feature directory not found: WP01" | Read script source |
| `accept-feature.sh` | `<feature_slug>` | ❌ ERROR: "unrecognized arguments" (uses tasks_cli.py internally) | Read script source |

### Evidence from Testing

```python
# Test based on template documentation:
result = subprocess.run(
    [str(move_script), feature_slug, 'WP01'],
    cwd=project_path,
    capture_output=True,
    text=True
)
# ❌ FAILS: "Feature directory not found: WP01"

# Actual signature (discovered by reading script):
# move-task-to-doing.sh takes WP_ID only, infers feature from context
```

**Why This Is Bad:**
- Agents can't invoke scripts without reading source code
- Command templates don't document actual arguments
- Trial-and-error required to discover correct invocation
- Scripts break silently when args are wrong

### Recommendation: Standardize and Document

**Fix 1: Consistent Argument Pattern**

All scripts should follow this pattern:
```bash
script-name.sh [--flags] <feature_slug> <specific_args>

# Examples:
create-new-feature.sh --json --feature-name "Title" <description>
setup-plan.sh <feature_slug>
move-task-to-doing.sh <feature_slug> <wp_id>
mark-task-status.sh <feature_slug> <wp_id> <status>
accept-feature.sh <feature_slug> [--mode local|ci]
```

**Feature slug ALWAYS first** (after flags), makes patterns predictable.

**Fix 2: Add --help to ALL Scripts**

```bash
#!/usr/bin/env bash

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <feature_slug> <wp_id>

Move a work package from 'planned' to 'doing' lane.

Arguments:
  feature_slug    Feature identifier (e.g., 001-test-feature)
  wp_id          Work package ID (e.g., WP01)

Options:
  --help, -h     Show this help message

Examples:
  $(basename "$0") 001-test WP01
  $(basename "$0") --help

Context: Must run from feature worktree or repo root.
EOF
}

case "$1" in
    --help|-h) show_help; exit 0 ;;
esac
```

**Fix 3: Update Command Templates with Examples**

```markdown
## Usage Examples

### From Feature Worktree (Recommended)
```bash
cd .worktrees/001-test-feature
/spec-kitty.plan
```

### From Repo Root (Auto-detects worktree)
```bash
.kittify/scripts/bash/setup-plan.sh 001-test-feature
```

### Script Arguments
- `feature_slug`: Feature identifier (from $BRANCH_NAME in specify output)
- Auto-detected from current git branch if in worktree
```

**Impact:**
- ✅ Predictable argument patterns
- ✅ Self-documenting with --help
- ✅ Agents can invoke without trial-and-error
- ✅ Reduces support burden

**Effort:** High (refactor 11 scripts, add --help, update all templates)

---

## Issue 5: Silent Failures and Missing Validation

### Problem

Several scripts fail silently or with exit code 0 when they should error:

```bash
# Test: Try to move non-existent work package
$ .kittify/scripts/bash/move-task-to-doing.sh 001-test WP99
❌ ERROR: Feature directory not found: WP99
$ echo $?
1  # Good - returns error code

# But: Some operations succeed even when they shouldn't
$ .kittify/scripts/bash/refresh-kittify-tasks.sh 999-nonexistent
[spec-kitty] Refreshing tasks for 999-nonexistent...
$ echo $?
0  # ❌ Should fail - feature doesn't exist!
```

**Why This Is Bad:**
- Agents can't detect failures without parsing stderr
- Automation chains continue after errors
- Users think operation succeeded
- Debugging requires reading logs to find actual error

### Evidence from Testing

```python
# Test expected this to fail:
result = subprocess.run([script, 'nonexistent-feature'], check=False)
assert result.returncode != 0, "Should fail for nonexistent feature"
# ❌ Test fails - script returns 0 even though feature doesn't exist
```

### Recommendation: Validate Inputs and Fail Fast

**Fix 1: Add Input Validation to All Scripts**

```bash
#!/usr/bin/env bash
set -e  # Exit on error

validate_feature_exists() {
    local feature_slug="$1"
    local repo_root="$2"

    local feature_dir="$repo_root/kitty-specs/$feature_slug"
    local worktree_dir="$repo_root/.worktrees/$feature_slug"

    if [ ! -d "$feature_dir" ] && [ ! -d "$worktree_dir" ]; then
        echo "❌ ERROR: Feature '$feature_slug' not found" >&2
        echo "" >&2
        echo "Checked locations:" >&2
        echo "  - $feature_dir" >&2
        echo "  - $worktree_dir" >&2
        echo "" >&2
        echo "💡 TIP: Run 'spec-kitty dashboard' to see all features" >&2
        exit 1
    fi
}

# Use in scripts:
FEATURE_SLUG="$1"
REPO_ROOT=$(find_repo_root)
validate_feature_exists "$FEATURE_SLUG" "$REPO_ROOT"
```

**Fix 2: Consistent Error Codes**

Standardize exit codes across all scripts:
```bash
0   - Success
1   - Usage error (missing args, --help)
2   - Validation error (feature not found, not in worktree)
3   - Execution error (git command failed, file write failed)
4   - Precondition error (not in git repo, dependencies missing)
```

**Fix 3: Add --dry-run to Destructive Operations**

```bash
# For scripts that move/delete files:
move-task-to-doing.sh --dry-run 001-test WP01
# Output:
# [DRY RUN] Would move:
#   From: .worktrees/001-test/kitty-specs/001-test/tasks/planned/WP01.md
#   To:   .worktrees/001-test/kitty-specs/001-test/tasks/doing/WP01.md
#
# Run without --dry-run to execute
```

**Impact:**
- ✅ Automation can rely on exit codes
- ✅ Failures detected immediately
- ✅ Clear error messages for debugging
- ✅ Safer operations with --dry-run

**Effort:** Medium (add validation to 11 scripts, standardize errors)

---

## Summary of Recommendations

| Issue | Priority | Effort | Impact | Recommended Action |
|-------|----------|--------|--------|-------------------|
| 1. Mixed Output Streams | HIGH | Low | High | Use stderr for logs, stdout for JSON |
| 2. Worktree Location Undocumented | HIGH | Medium | High | Document worktree model in templates |
| 3. Context-Dependent Scripts | MEDIUM | Medium | High | Auto-detect context or document clearly |
| 4. Inconsistent Arguments | HIGH | High | Very High | Standardize patterns, add --help |
| 5. Silent Failures | CRITICAL | Medium | Critical | Add validation, consistent exit codes |

### Implementation Priority

**Phase 1 (Critical - Week 1):**
1. Issue 5: Add input validation and consistent exit codes
2. Issue 1: Separate log output from JSON
3. Issue 4: Add --help to all scripts

**Phase 2 (High Priority - Week 2):**
4. Issue 2: Document worktree model in command templates
5. Issue 3: Auto-detect context where possible

**Phase 3 (Quality - Week 3):**
6. Update all command templates with examples
7. Add --dry-run to destructive operations
8. Integration testing with actual agents

---

## Testing Implications

These UX issues had direct impact on our test suite:

**Before Fixes:**
- 5/15 script tests failing (33% failure rate)
- Custom parsing required for JSON output
- Tests based on assumptions, not reality
- Fragile tests that break when scripts change

**After Fixes (Expected):**
- 15/15 script tests passing (0% failure rate)
- Standard JSON parsing works
- Tests match actual behavior
- Robust tests that catch regressions

**Test Benefits:**
- Discovered issues that block agent adoption
- Identified gaps between documentation and implementation
- Validated assumptions against reality
- Provided concrete examples for improvements

---

## Quotes from Test Failures (Evidence)

```python
# Issue 1 - Mixed output
E   json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)
# Fix: Use stderr for logs

# Issue 2 - Undocumented location
E   AssertionError: Feature directory should be created at .../kitty-specs/001-test-feature
# Fix: Document worktree model

# Issue 3 - Context errors
E   AssertionError: setup-plan.sh should succeed.
E   stderr: ❌ ERROR: Command run from wrong location!
# Fix: Auto-detect context

# Issue 4 - Wrong arguments
E   AssertionError: move-task-to-doing.sh should succeed.
E   stderr: ❌ ERROR: Feature directory not found: WP01
# Fix: Standardize arguments, add --help

# Issue 5 - Silent failures
E   FileNotFoundError: .../001-tasks-test/tasks.md
# Fix: Validate inputs, fail fast
```

---

## Recommendation for Spec-Kitty Maintainers

**Action Items:**

1. **Review this document** with product/eng team
2. **Prioritize fixes** based on Phase 1 / 2 / 3 above
3. **Create GitHub issues** for each of the 5 problems
4. **Assign ownership** to team members
5. **Target completion** before 1.0 release

**Why This Matters:**
- Scripts are the **automation layer** that makes spec-kitty programmable
- Poor script UX blocks **agent adoption** (LLMs can't reliably invoke)
- Inconsistencies force **trial-and-error** (frustrates humans)
- Silent failures cause **lost work** and debugging time

**ROI:**
- ✅ Reduced support burden (fewer "why doesn't this work?" issues)
- ✅ Increased agent reliability (LLMs can follow patterns)
- ✅ Better onboarding (humans can read --help and succeed)
- ✅ Fewer bugs (validation catches errors early)

**Estimated Total Effort:** 3-4 weeks (1 developer)
**Expected Impact:** 10x improvement in script usability

---

## Appendix: Test File Reference

**Location:** `tests/functional/test_script_execution.py`

**Test Classes:**
1. `TestScriptExistence` (3 tests) - ✅ All passing
2. `TestCoreScriptFunctionality` (6 tests) - ⚠️ 1/6 passing
3. `TestScriptErrorHandling` (3 tests) - ✅ All passing
4. `TestScriptContextAwareness` (3 tests) - ✅ All passing

**Failures Documented:**
- Lines 228: Issue 2 (worktree location)
- Lines 280: Issue 3 (context requirement)
- Lines 330: Issue 2 + 5 (location + validation)
- Lines 425: Issue 4 (argument pattern)
- Lines 550: Issue 4 + 5 (arguments + validation)

**Helper Function:**
- `extract_json_from_output()` - Workaround for Issue 1

---

**Document Status:** Ready for review
**Next Steps:** Share with spec-kitty maintainers, create GitHub issues
**Related:** UPDATED_TESTING_ROADMAP.md (Category 6 strategy)
