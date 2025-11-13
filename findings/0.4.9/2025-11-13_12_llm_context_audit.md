# LLM Context Completeness Audit - Spec-Kitty Templates

**Date**: 2025-11-13
**Spec-Kitty Version**: ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (ed3f461)
**Auditor**: Claude (Sonnet 4.5)
**Scope**: All command templates in `templates/commands/`

---

## Executive Summary

**Purpose**: Audit all spec-kitty prompt templates to ensure LLMs have complete context about:
1. **Where am I?** (current location, branch, worktree)
2. **What files exist?** (available documents, paths)
3. **What's the workflow?** (what comes before/after, dependencies)

**Overall Assessment**: **GOOD with critical gaps in 3 templates**

- ✅ **Excellent**: implement.md, review.md, tasks.md (comprehensive context)
- ⚠️ **Good**: plan.md, accept.md (solid but could be clearer)
- ❌ **Critical gaps**: 8 templates missing essential context

---

## Findings by Template

### Category A: Excellent Context (No Changes Needed)

#### 1. **implement.md** ✅
**Score**: 10/10

**Strengths**:
- Comprehensive "Location Pre-flight Check" (lines 18-45)
- Explicit pwd/git branch verification
- Clear explanation of worktree isolation
- Warns against using `cd` (tools use original directory)
- Provides FEATURE_DIR from `{SCRIPT}` output
- Documents all available files via AVAILABLE_DOCS
- Full workflow context (review feedback, task lanes, completion flow)
- Shell PID tracking for multi-agent coordination

**Context Provided**:
- **Where**: Worktree path, branch name, absolute paths
- **What files**: FEATURE_DIR, AVAILABLE_DOCS list, tasks.md, plan.md, spec.md, etc.
- **Workflow**: Task lifecycle (planned → doing → for_review → done), review feedback loop

**No improvements needed.**

---

#### 2. **review.md** ✅
**Score**: 10/10

**Strengths**:
- Same comprehensive location pre-flight check
- Clear context loading (lines 56-60): frontmatter, supporting docs, code changes
- Documents review workflow completely
- Explains feedback insertion location
- Task state transitions clearly documented
- Shell PID coordination

**Context Provided**:
- **Where**: Worktree verification, branch check
- **What files**: FEATURE_DIR, AVAILABLE_DOCS, tasks.md, specific prompt file
- **Workflow**: Review → needs_changes (back to planned) OR approved (to done)

**No improvements needed.**

---

#### 3. **tasks.md** ✅
**Score**: 9/10

**Strengths**:
- Location pre-flight check present
- **CRITICAL PATH RULE** (lines 88-90) explicitly warns about FEATURE_DIR usage
- Multiple warnings about absolute paths
- Documents directory structure to create
- Explains relationship to other workflows (/spec-kitty.implement comes after)

**Minor improvement opportunity**:
- Could mention what files the script provides (it returns FEATURE_DIR + AVAILABLE_DOCS)

**Context Provided**:
- **Where**: Worktree check, absolute FEATURE_DIR from script
- **What files**: AVAILABLE_DOCS, plan.md, spec.md, data-model.md, contracts/, etc.
- **Workflow**: Comes after /plan, before /implement

---

### Category B: Good Context (Minor Improvements Recommended)

#### 4. **plan.md** ⚠️
**Score**: 7/10

**Strengths**:
- Has location pre-flight check
- Documents workflow phases
- Explains what script provides (FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH)

**Gaps**:
1. **Missing working directory context** - Doesn't explain which files exist yet
2. **No mention of what comes before** - Should reference /specify
3. **Constitution location unclear** - Says to load `.kittify/memory/constitution.md` but doesn't explain it's at repo root

**Recommended additions**:
```markdown
## What You Have Available

After running `{SCRIPT}`, you will have:
- **FEATURE_SPEC**: Absolute path to spec.md (your requirements)
- **IMPL_PLAN**: Absolute path to newly created plan.md (your template)
- **SPECS_DIR**: Absolute path to feature directory (kitty-specs/001-name/)
- **BRANCH**: Feature branch name (001-name)

Additional context files (load if present):
- **.kittify/memory/constitution.md** (from main repo root - project principles)
- **spec.md** (FEATURE_SPEC - what you're building)

---

## Workflow Context

**Before this**: You ran `/spec-kitty.specify` which created spec.md
**This command**: Creates plan.md and supporting docs (research.md, data-model.md, contracts/)
**After this**: Run `/spec-kitty.tasks` to break down into work packages
```

---

#### 5. **accept.md** ⚠️
**Score**: 7/10

**Strengths**:
- Documents discovery phase well
- Explains script output structure
- Clear error handling

**Gaps**:
1. **No location pre-flight check** - Should verify worktree context
2. **Missing workflow context** - What comes before? (implement → review → accept)
3. **No file context** - Doesn't explain what files exist or where they are

**Recommended additions**:
```markdown
## Location Pre-flight Check

**BEFORE PROCEEDING:** Verify you are in the feature worktree.

```bash
pwd
git branch --show-current
```

Expected: `.worktrees/001-feature-name` and branch `001-feature-name`

---

## Workflow Context

**Before this command**:
1. `/spec-kitty.implement` - Completed implementation
2. `/spec-kitty.review` - All tasks reviewed and in done/ lane

**This command**: Validates feature readiness and prepares for merge

**After this**: `/spec-kitty.merge` to merge into main (or manual PR workflow)
```

---

### Category C: Critical Gaps (Urgent Improvements Needed)

The following templates are missing essential context that causes LLM confusion:

#### 6. **specify.md** ❌
**Score**: 5/10

**Gaps Identified**:
1. ✅ Runs `{SCRIPT}` which provides BRANCH_NAME, SPEC_FILE, FEATURE_NUM
2. ❌ **No location pre-flight check** - Doesn't verify where LLM is before starting
3. ❌ **No workflow context** - Doesn't explain this is the FIRST command
4. ❌ **After script runs, no clear statement of working directory** - Script creates worktree but template doesn't say "you're now in .worktrees/001-name"

**Why this matters**:
- LLM doesn't know if it's in main repo or worktree
- Doesn't know what files will exist after script runs
- Can't orient itself in the workflow

**Recommended fix**:
```markdown
## Location Context

**BEFORE running {SCRIPT}**: You are in the main repository
**AFTER running {SCRIPT}**: A new feature worktree is created at `.worktrees/001-name/`

The script output provides:
- BRANCH_NAME: Git branch (e.g., "001-name")
- SPEC_FILE: Absolute path to newly created spec.md
- FEATURE_NUM: Feature number (e.g., "001")
- WORKTREE_PATH: Absolute path to feature worktree

## Workflow Context

**This is the FIRST command** in the spec-kitty workflow.

**Before this**: Nothing (new feature)
**This command**: Creates feature branch, worktree, and spec.md
**After this**: Switch to worktree and run `/spec-kitty.plan`
```

---

#### 7-13. **Other Templates Missing Context** ❌

**Templates without location pre-flight checks**:
- analyze.md
- checklist.md
- clarify.md
- constitution.md
- dashboard.md
- merge.md
- research.md

**Impact Severity by Template**:

| Template | Severity | Why |
|----------|----------|-----|
| **merge.md** | 🔴 **CRITICAL** | Merges feature to main - MUST verify location |
| **clarify.md** | 🟡 **HIGH** | Updates spec.md - needs to know where it is |
| **research.md** | 🟡 **HIGH** | Creates research.md - needs worktree context |
| **analyze.md** | 🟡 **HIGH** | Reads multiple files - needs file discovery |
| **checklist.md** | 🟠 **MEDIUM** | Creates checklists - needs worktree context |
| **constitution.md** | 🟢 **LOW** | Creates global file - less critical |
| **dashboard.md** | 🟢 **LOW** | Read-only display - less critical |

---

## Detailed Findings for Critical Templates

### **merge.md** - CRITICAL MISSING CONTEXT 🔴

**Current state**: No location check, no workflow context

**What's missing**:
```markdown
## Location Pre-flight Check (CRITICAL for AI Agents)

**BEFORE PROCEEDING:** You MUST be in the feature worktree, NOT main repo.

```bash
pwd
git branch --show-current
```

**Expected output:**
- pwd: `/path/to/project/.worktrees/001-feature-name`
- Branch: `001-feature-name` (NOT `main`)

**If you see `main` branch:**

⛔ **STOP - DANGER!**

This command merges a feature INTO main. Running from main could cause:
- Merge conflicts
- Loss of work
- Repository corruption

**Instead:**
1. Navigate to feature worktree: cd .worktrees/001-feature-name
2. Verify you're on feature branch: git branch --show-current
3. Then re-run this command

## Workflow Context

**Before this command**:
1. `/spec-kitty.accept` - Feature validated and ready

**This command**: Merges feature branch into main and cleans up worktree

**After this**: Feature complete, can start new feature with `/spec-kitty.specify`
```

**Why this is CRITICAL**:
- Merge operations from wrong location can destroy work
- LLM needs absolute clarity about where it is
- No pre-flight check = high risk of data loss

---

### **clarify.md** - HIGH PRIORITY 🟡

**Current state**: No location check, no file context

**What's missing**:
```markdown
## Location Pre-flight Check

Verify you are in the feature worktree:

```bash
pwd
git branch --show-current
```

Expected: `.worktrees/001-feature-name` and branch `001-feature-name`

## What You Have Available

After running `{SCRIPT}` (if it exists), you will have paths to:
- spec.md (the file you'll be clarifying)
- Possibly plan.md, tasks.md (if they exist)

This command creates: clarify.md (structured clarification questions)

## Workflow Context

**Before this**: `/spec-kitty.specify` created spec.md (optional before plan)
**This command**: Identifies ambiguities in spec and creates clarify.md
**After this**: Update spec.md with answers, then `/spec-kitty.plan`
```

---

### **research.md** - HIGH PRIORITY 🟡

**Current state**: No location check, no explanation of what it creates

**What's missing**:
```markdown
## Location Pre-flight Check

Verify you are in the feature worktree:

```bash
git branch --show-current
```

Expected: Feature branch like `001-feature-name`

## What This Command Creates

**Files generated**:
- research.md - Research findings and decisions
- data-model.md - Entity definitions
- research-log.csv - Detailed research tracking

**Location**: All files go in `kitty-specs/001-feature-name/`

## Workflow Context

**Before this**: `/spec-kitty.plan` calls this as "Phase 0"
**This command**: Scaffolds research artifacts
**After this**: `/spec-kitty.plan` continues with design phase
```

---

### **analyze.md** - HIGH PRIORITY 🟡

**Current state**: No file discovery, no explanation of what it analyzes

**What's missing**:
```markdown
## Location Pre-flight Check

Verify you are in the feature worktree:

```bash
git branch --show-current
```

Expected: Feature branch like `001-feature-name`

## What This Command Analyzes

This command reads and cross-checks:
- spec.md (requirements)
- plan.md (technical design)
- tasks.md (work breakdown)
- contracts/ (API specs)
- data-model.md (entity definitions)

**Output**: analysis.md with consistency report

## Workflow Context

**Before this**: `/spec-kitty.tasks` has created work breakdown
**This command**: Validates consistency across all artifacts
**After this**: Fix inconsistencies, then `/spec-kitty.implement`
```

---

## Summary of Issues Found

### By Severity

| Severity | Count | Templates |
|----------|-------|-----------|
| 🔴 **CRITICAL** | 1 | merge.md |
| 🟡 **HIGH** | 3 | clarify.md, research.md, analyze.md |
| 🟠 **MEDIUM** | 2 | checklist.md, specify.md |
| 🟢 **LOW** | 2 | constitution.md, dashboard.md |
| ✅ **GOOD** | 2 | plan.md, accept.md |
| ✅ **EXCELLENT** | 3 | implement.md, review.md, tasks.md |

### Missing Elements Breakdown

| Element | Missing From | Impact |
|---------|--------------|--------|
| **Location pre-flight check** | 9/13 templates | LLMs don't know where they are |
| **File discovery via {SCRIPT}** | 7/13 templates | LLMs don't know what files exist |
| **Workflow context** | 8/13 templates | LLMs don't know what comes before/after |
| **Output explanation** | 6/13 templates | LLMs don't know what they're creating |

---

## Impact on LLM Agents

### Real-World Confusion Scenarios

#### Scenario 1: Lost in Review/Implement
**User report**: "Agents getting lost in review and implement, not knowing where they are"

**Root cause analysis**:
- ✅ **implement.md**: Has excellent pre-flight check (lines 18-45)
- ✅ **review.md**: Has excellent pre-flight check (lines 18-45)

**Verdict**: These templates are actually GOOD. Confusion likely comes from:
1. Agents not reading pre-flight instructions carefully
2. User starting session in wrong directory
3. Agent tools (cd) not working as expected

**But surrounding templates are weak**, so agents might get confused navigating TO implement/review.

---

#### Scenario 2: File Path Confusion
**Symptom**: Agents create files in wrong locations

**Root cause**:
- Templates that DON'T run `{SCRIPT}` have no file discovery
- Without FEATURE_DIR or SPECS_DIR, agents guess paths
- Guesses often wrong (creates in repo root instead of worktree)

**Templates with this problem**:
- clarify.md (no script, creates clarify.md - where?)
- checklist.md (no script, creates checklists/ - where?)
- constitution.md (creates in .kittify/memory/ - not stated clearly)

---

#### Scenario 3: Workflow Disorientation
**Symptom**: Agents don't know what command to run next

**Root cause**:
- Most templates don't say what comes before/after
- Agents can't build mental model of full workflow
- Result: Agents ask user "what should I do next?"

**Templates with this problem**: 8 out of 13

---

## Recommendations

### Priority 1: CRITICAL (merge.md)
Add location pre-flight check IMMEDIATELY. This command can cause data loss.

### Priority 2: HIGH (clarify, research, analyze)
Add location checks and file discovery. These are core workflow commands.

### Priority 3: MEDIUM (checklist, specify)
Add workflow context and output explanations.

### Priority 4: LOW (constitution, dashboard)
Add context when time permits.

### Template for Adding Context

**For all templates, add this section after User Input**:

```markdown
## Location Pre-flight Check (CRITICAL for AI Agents)

**BEFORE PROCEEDING:** Verify you are working from inside the feature worktree.

**Check current working directory and branch:**
```bash
pwd
git branch --show-current
```

**Expected output:**
- `pwd`: `/path/to/project/.worktrees/001-feature-name` (or similar)
- Branch: `001-feature-name` (NOT `main` or `release/x.x.x`)

**If you see `main` or `release/*` branch, OR if pwd shows the main repo:**

⛔ **STOP - You are in the wrong location!**

**DO NOT use `cd` to navigate to the worktree.** File creation tools (Write, Edit) will still use your original working directory.

**Instead:**
1. Tell the user: "This command must be run from inside the worktree at `.worktrees/<feature>/`"
2. Stop execution
3. Wait for the user to restart the session from the correct location

**Path reference rule:** Always use paths relative to the worktree root. When communicating with the user, mention absolute paths for clarity.

This is intentional - worktrees provide isolation for parallel feature development.

## What You Have Available

[List what {SCRIPT} provides or what files must exist]

## Workflow Context

**Before this**: [Previous command]
**This command**: [What this does]
**After this**: [Next command]
```

---

## Testing Recommendations

Create test suite to verify:
1. Each template has location pre-flight check
2. Each template documents {SCRIPT} output
3. Each template has workflow context
4. Instructions are clear for both humans and LLMs

---

## Conclusion

**Current State**: Mixed quality
- 3 templates are excellent (implement, review, tasks)
- 2 templates are good (plan, accept)
- 8 templates have critical gaps

**Impact**: LLMs get lost because:
1. They don't know where they are (no location check)
2. They don't know what files exist (no file discovery)
3. They don't know the workflow order (no context)

**Fix Priority**:
1. 🔴 merge.md - URGENT (data loss risk)
2. 🟡 clarify.md, research.md, analyze.md - HIGH (core workflow)
3. 🟠 specify.md, checklist.md - MEDIUM
4. 🟢 constitution.md, dashboard.md - LOW

**Effort**: ~2-4 hours to add context to all 8 templates using the standard template above.

**ROI**: Massive - fixes reported issue of "agents getting lost"
