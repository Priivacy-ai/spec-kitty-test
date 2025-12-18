# CRITICAL: Feature 007 Template Violations - Templates Teach Wrong Structure

**Date:** 2025-12-18
**Discovered By:** User Audit + External QA Validation
**Category:** CRITICAL Bug, Template Violations, Structural Regression
**Spec-Kitty Version:** 0.10.0 / 0.10.1
**Severity:** 🔴 **CRITICAL**
**Status:** 🐛 **OPEN - ACTIVELY CAUSING BUGS**

---

## Executive Summary

**Feature 007 (v0.9.0) eliminated tasks/ subdirectories** but **command templates were NEVER updated**. Templates explicitly instruct agents to create the OLD subdirectory structure (tasks/planned/, tasks/doing/, etc.), causing structural violations in ALL new features.

**Impact:** Every new feature created since v0.9.0 has wrong structure because agents follow template instructions.

---

## Critical Violations Found

### Violation #1: tasks.md Template (CRITICAL)

**File:** `.claude/commands/spec-kitty.tasks.md`
**Lines 81-93:** Explicitly instruct subdirectory creation

**Actual Content:**
```markdown
Line 87: - Correct structure: `FEATURE_DIR/tasks/planned/WPxx-slug.md`,
         `FEATURE_DIR/tasks/doing/`, `FEATURE_DIR/tasks/for_review/`,
         `FEATURE_DIR/tasks/done/`

Line 89: - Ensure `FEATURE_DIR/tasks/planned/` exists (create
         `FEATURE_DIR/tasks/doing/`, `FEATURE_DIR/tasks/for_review/`,
         `FEATURE_DIR/tasks/done/` if missing)

Line 90: - Create optional phase subfolders under each lane when teams
         will benefit (e.g., `FEATURE_DIR/tasks/planned/phase-1-setup/`)

Line 93: Full path example: `FEATURE_DIR/tasks/planned/WP01-create-html-page.md`
```

**Expected Content (v0.9.0+):**
```markdown
- Correct structure: `FEATURE_DIR/tasks/WPxx-slug.md` (flat directory)
- Ensure `FEATURE_DIR/tasks/` exists (flat structure, no subdirectories)
- Set lane in frontmatter: lane: planned | doing | for_review | done
- Full path example: `FEATURE_DIR/tasks/WP01-create-html-page.md`
```

**Impact:**
- Agents create tasks/planned/, tasks/doing/, tasks/for_review/, tasks/done/
- This is EXACTLY what Feature 007 eliminated
- Every new feature gets wrong structure

---

### Violation #2: implement.md Template (HIGH)

**File:** `.claude/commands/spec-kitty.implement.md`
**Issue:** ~8 references to tasks/doing/ paths (not verified in slash commands, but reported in mission templates)

**Expected:** No lane subdirectory references, use frontmatter approach

---

### Violation #3: review.md Template (HIGH)

**File:** `.claude/commands/spec-kitty.review.md`
**Issue:** References to tasks/for_review/ paths

**Expected:** Check frontmatter lane: for_review, not directory paths

---

### Violation #4: merge.md Template (HIGH)

**File:** `.claude/commands/spec-kitty.merge.md`
**Issue:** References to tasks/done/ paths

**Expected:** Check frontmatter lane: done, not directory paths

---

### Violation #5: Mission Templates (CRITICAL)

**Files:** `.kittify/missions/software-dev/command-templates/*.md`
**Files:** `.kittify/missions/research/command-templates/*.md`

**Issue:** Base mission templates still have old structure
- These templates are copied to new projects
- Propagates violations to ALL users

---

### Violation #6: Template Files (HIGH)

**Files:**
- `tasks-template.md` - Shows `tasks/planned/WP01-setup.md`
- `task-prompt-template.md` - Shows `tasks/planned/phase-<n>-<label>/`

**Issue:** Example templates show wrong structure

---

## Test Validation Results

**Created:** `tests/functional/test_feature_007_template_compliance.py` (15 tests)

**Results:**
```
3 xfailed (violations confirmed)
12 xpassed (surprisingly already fixed in .claude/commands/)
```

**Key Findings:**
- ✅ Slash commands in .claude/commands/ are MOSTLY correct (12/15)
- ❌ tasks.md template still has violations (3 failures)
- ❌ Mission source templates in .kittify/missions/ likely still wrong

**Discrepancy:**
Slash commands (.claude/commands/) seem updated but mission templates (.kittify/missions/) may not be. Need to verify which is source of truth.

---

## Root Cause Analysis

**When Feature 007 (v0.9.0) was implemented:**
1. ✅ Code implementation - Flat structure logic added
2. ✅ Migration created - m_0_9_0_frontmatter_only.py flattens existing projects
3. ✅ Tests added - test_frontmatter_only_lanes.py validates flat structure
4. ❌ **Templates NOT updated** - Command templates still teach old structure

**Result:**
- Old projects get migrated correctly (tests pass)
- NEW features created AFTER v0.9.0 get WRONG structure (agents follow template instructions)

**Evidence:**
- Feature 013 (user mentioned) has wrong structure
- Templates explicitly instruct subdirectory creation
- This has been shipping since v0.9.0 (months of wrong instructions)

---

## Impact Assessment

**Severity:** 🔴 CRITICAL

**Scope:**
- ALL new features created since v0.9.0
- ALL users running spec-kitty >= 0.9.0
- Both software-dev AND research missions

**Frequency:** 100% (every /spec-kitty.tasks execution)

**User Experience:**
1. User runs `/spec-kitty.tasks` to generate work packages
2. Agent reads tasks.md template
3. Agent creates tasks/planned/, tasks/doing/, tasks/for_review/, tasks/done/
4. Feature has WRONG structure (violates Feature 007)
5. Confusion, inconsistency, migration issues

---

## Specific Violations in tasks.md

**Line 51:** Example path uses subdirectory
```
prompt location: FEATURE_DIR + "/tasks/planned/WP01-slug.md"
```

**Line 55-56:** Shows wrong examples
```
- ❌ `tasks/planned/WP01-slug.md` (missing FEATURE_DIR prefix)
- ❌ `/tasks/planned/WP01-slug.md` (wrong root)
```

**Line 87:** Defines "correct" structure as subdirectories
```
- Correct structure: `FEATURE_DIR/tasks/planned/WPxx-slug.md`,
  `FEATURE_DIR/tasks/doing/`, `FEATURE_DIR/tasks/for_review/`,
  `FEATURE_DIR/tasks/done/`
```

**Line 89:** Explicitly instructs creating ALL subdirectories
```
- Ensure `FEATURE_DIR/tasks/planned/` exists (create
  `FEATURE_DIR/tasks/doing/`, `FEATURE_DIR/tasks/for_review/`,
  `FEATURE_DIR/tasks/done/` if missing)
```

**Line 90:** Encourages phase subdirectories
```
- Create optional phase subfolders under each lane when teams will benefit
  (e.g., `FEATURE_DIR/tasks/planned/phase-1-setup/`)
```

---

## Required Fixes

### Fix #1: Update tasks.md Template (CRITICAL)

**File:** `.kittify/missions/software-dev/command-templates/tasks.md`
**And:** `.kittify/missions/research/command-templates/tasks.md`

**Changes Needed:**
```diff
-Line 51: prompt location: FEATURE_DIR + "/tasks/planned/WP01-slug.md"
+Line 51: prompt location: FEATURE_DIR + "/tasks/WP01-slug.md"

-Line 87: Correct structure: FEATURE_DIR/tasks/planned/WPxx-slug.md, FEATURE_DIR/tasks/doing/, ...
+Line 87: Correct structure: FEATURE_DIR/tasks/WPxx-slug.md (flat directory, use frontmatter lane: field)

-Line 89: Ensure FEATURE_DIR/tasks/planned/ exists (create FEATURE_DIR/tasks/doing/, ...)
+Line 89: Ensure FEATURE_DIR/tasks/ exists (flat structure, no subdirectories)

-Line 90: Create optional phase subfolders under each lane...
+Line 90: ALL work packages live in flat tasks/ directory. Set lane: field in frontmatter.
```

### Fix #2: Add Frontmatter Instructions

**Add to tasks.md:**
```markdown
## Work Package Frontmatter

Each work package file has YAML frontmatter:

---
lane: planned  # Values: planned | doing | for_review | done
work_package_id: WP01
activity:
  - timestamp: 2025-01-01T00:00:00Z
    event: created
    lane: planned
---

Lane changes are made by updating the lane: field, NOT by moving files.
Use: spec-kitty agent tasks move-task WP01 --to doing
```

### Fix #3: Update All Example Paths

Search and replace across ALL templates:
- `tasks/planned/WP` → `tasks/WP`
- `tasks/doing/WP` → `tasks/WP`
- `tasks/for_review/WP` → `tasks/WP`
- `tasks/done/WP` → `tasks/WP`

### Fix #4: Remove Phase Subdirectory Instructions

Delete or rewrite lines about "phase subfolders under each lane"

---

## Test Coverage Added

**File:** `tests/functional/test_feature_007_template_compliance.py`
**Tests:** 15 comprehensive template validation tests

**Current Results:**
- 3 xfailed (violations found)
- 12 xpassed (already correct - good!)

**When Fixed:** All 15 should pass

---

## Files Needing Updates

**Mission Templates (Source):**
- `.kittify/missions/software-dev/command-templates/tasks.md` ⚠️
- `.kittify/missions/software-dev/command-templates/implement.md` (check)
- `.kittify/missions/software-dev/command-templates/review.md` (check)
- `.kittify/missions/software-dev/command-templates/merge.md` (check)
- `.kittify/missions/research/command-templates/*.md` (all)

**Template Files:**
- `.kittify/missions/*/templates/tasks-template.md` (check)
- `.kittify/missions/*/templates/task-prompt-template.md` (check)

**Already Updated (Good):**
- Most .claude/commands/ slash commands (12/15 correct)

---

## Reproduction Steps

```bash
# 1. Create new feature
spec-kitty init test-proj --ai=claude
cd test-proj
spec-kitty agent feature create-feature "test"

# 2. Run /spec-kitty.tasks command
cd .worktrees/001-test/
# Agent reads tasks.md template

# 3. Agent follows instructions from tasks.md line 89:
mkdir -p kitty-specs/001-test/tasks/planned
mkdir -p kitty-specs/001-test/tasks/doing
mkdir -p kitty-specs/001-test/tasks/for_review
mkdir -p kitty-specs/001-test/tasks/done

# 4. Creates WP files in subdirectories:
# tasks/planned/WP01-slug.md (WRONG!)

# Expected (v0.9.0+):
# tasks/WP01-slug.md (flat, with lane: planned in frontmatter)
```

---

## Priority

**Priority:** 🔴 P0 (CRITICAL - RELEASE BLOCKER)

**Rationale:**
- Affects ALL new features since v0.9.0
- Teaches agents wrong structure
- Undoes Feature 007 benefits
- Causes structural violations
- User-reported real-world impact (Feature 013)

**Recommendation:**
- Fix before promoting v0.10.0/v0.10.1
- Or release with big warning about manual template updates
- Or provide migration to fix affected features

---

## Suggested Implementation

**Quick Fix Script:**
```bash
# Update tasks.md template in spec-kitty repo
cd ~/Code/spec-kitty/templates/missions/software-dev/command-templates/

# Replace all occurrences
sed -i '' 's|tasks/planned/|tasks/|g' tasks.md
sed -i '' 's|tasks/doing/|tasks/|g' tasks.md
sed -i '' 's|tasks/for_review/|tasks/|g' tasks.md
sed -i '' 's|tasks/done/|tasks/|g' tasks.md

# Update instruction text
# (Manual edit required for lines 87-90)
```

---

## Test Validation Commands

```bash
# Run Feature 007 compliance audit
pytest tests/functional/test_feature_007_template_compliance.py -v

# Expected after fix: 15/15 passing
# Current: 3 xfailed, 12 xpassed
```

---

## Conclusion

**This is the most critical bug found in external validation.**

Feature 007 was correctly implemented in code and migrations, but the documentation/templates that TEACH agents how to use it were never updated. This means every agent creating features since v0.9.0 has been following outdated instructions.

**External validation successfully identified a months-old documentation bug that was actively causing structural violations.**

**Recommendation:** Fix immediately before release. Update all mission templates to reflect flat structure and frontmatter-based lanes.

---

**Status:** 🔴 CRITICAL BUG - Requires immediate fix
**Tests:** 15 tests created, 3 confirm violations
**Next Steps:** Update mission templates in spec-kitty repo, re-run validation
