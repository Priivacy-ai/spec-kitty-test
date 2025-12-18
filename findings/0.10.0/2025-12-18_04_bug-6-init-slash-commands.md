# Bug Report: spec-kitty v0.10.0 Bug #6 - Init Doesn't Create Slash Commands

**Date:** 2025-12-18
**Discovered By:** External QA (User Report)
**Category:** Critical Bug, Initialization, User Experience
**Spec-Kitty Version:** 0.10.0
**Severity:** HIGH
**Status:** ✅ **NOT REPRODUCIBLE / ALREADY FIXED**

---

## Summary

**Initial Report:** `spec-kitty init` creates mission templates but fails to copy to `.claude/commands/`

**Validation Result:** ✅ Cannot reproduce - slash commands ARE created correctly

**Test Result:** XPASS (expected to fail but PASSES) - All 13 commands created properly

---

## Observation

After running `spec-kitty init project-name --ai=claude`:
- ✅ Project structure created
- ✅ `.kittify/missions/software-dev/command-templates/` exists with templates
- ❌ `.claude/commands/` is empty or missing `spec-kitty.*.md` files
- ❌ Claude Code shows no `/spec-kitty.` slash commands

**Expected:** 11-13 slash commands available: `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.implement`, etc.

**Actual:** Commands missing, must be manually copied

---

## Impact

**Severity:** HIGH
**Scope:** All new users initializing v0.10.0 projects
**Frequency:** 100% of new init calls

**User Impact:**
- Cannot use spec-kitty workflows without manual file copying
- Confusing UX - templates exist but aren't accessible
- Agents can't discover commands
- Breaks the "just run init and go" experience

---

## Root Cause Analysis

The init command or a post-init step should:
1. Copy `.kittify/missions/*/command-templates/*.md` files
2. To `.claude/commands/spec-kitty.*.md`
3. With appropriate variable substitution

**Current Behavior:**
- Mission templates are created in `.kittify/missions/software-dev/command-templates/`
- Files like `implement.md`, `specify.md`, `review.md` exist
- But they're NOT copied to `.claude/commands/`

**Expected Behavior:**
- After init, `.claude/commands/` should contain:
  - spec-kitty.specify.md
  - spec-kitty.plan.md
  - spec-kitty.implement.md
  - spec-kitty.review.md
  - spec-kitty.accept.md
  - spec-kitty.merge.md
  - ... (11-13 commands total)

---

## User Journey

1. User runs: `spec-kitty init my-project --ai=claude`
2. Init succeeds, creates project structure
3. User opens Claude Code
4. User tries: `/spec-kitty.specify "Add new feature"`
5. **ERROR:** Command not found
6. User confused - spec-kitty installed but doesn't work
7. Must manually discover templates are in `.kittify/missions/` and copy them

---

## What Could Have Helped

**Better Error Detection:**
- Init should verify slash commands were created
- Post-init validation check
- Warning if .claude/commands/ is empty

**Better Documentation:**
- Init output should confirm: "✓ Created 13 slash commands in .claude/commands/"
- If commands missing, suggest fix command

**Better Implementation:**
- Init should atomically: create templates AND copy to slash commands
- Or provide: `spec-kitty setup-commands` to populate from templates

---

## Suggested Improvements

### Option 1: Fix Init Command (Recommended)
Add post-init step to init.py:
```python
def _setup_slash_commands(project_path, ai_type):
    """Copy mission command templates to agent slash commands directory."""
    mission_templates = project_path / '.kittify' / 'missions' / 'software-dev' / 'command-templates'
    commands_dir = project_path / f'.{ai_type}' / 'commands'

    if mission_templates.exists():
        for template in mission_templates.glob('*.md'):
            dest = commands_dir / f'spec-kitty.{template.stem}.md'
            shutil.copy2(template, dest)
```

### Option 2: Create Migration (Alternative)
Add `m_0_10_0_setup_commands.py` migration to fix existing projects

### Option 3: Add Verification Command
Create: `spec-kitty verify-setup` to check and fix command setup

---

## Test Coverage Added

**Test:** `test_init_creates_slash_commands`
**File:** `tests/functional/test_v0_10_0_agent_commands.py`
**Status:** ⚠️ XFAIL (marked as expected failure until fix)

```python
def test_init_creates_slash_commands(self, spec_kitty_repo_root):
    """Verify init copies templates to .claude/commands/"""
    # Run init
    result = subprocess.run(['spec-kitty', 'init', ...])

    # Check slash commands exist
    commands_dir = project_path / '.claude' / 'commands'
    spec_kitty_commands = list(commands_dir.glob('spec-kitty.*.md'))

    # Should have 11-13 commands
    assert len(spec_kitty_commands) >= 11
```

**Current Result:** XFAIL (test fails as expected - bug not fixed yet)

---

## Reproduction Steps

```bash
# 1. Create new project
spec-kitty init test-project --ai=claude

# 2. Check slash commands
ls test-project/.claude/commands/spec-kitty.*.md

# Expected: 11-13 files
# Actual: 0 files (or directory doesn't exist)

# 3. Check mission templates (these DO exist)
ls test-project/.kittify/missions/software-dev/command-templates/

# Shows: implement.md, specify.md, review.md, etc.
```

---

## Workaround

**Manual Fix:**
```bash
cd test-project
cp .kittify/missions/software-dev/command-templates/*.md .claude/commands/
cd .claude/commands
for f in *.md; do mv "$f" "spec-kitty.$f"; done
```

---

## Related Files

**Init Command:**
- `~/Code/spec-kitty/src/specify_cli/cli/commands/init.py`

**Mission Templates:**
- `.kittify/missions/software-dev/command-templates/*.md` (created but not copied)

**Target Location:**
- `.claude/commands/spec-kitty.*.md` (should exist but doesn't)

**Test File:**
- `tests/functional/test_v0_10_0_agent_commands.py::test_init_creates_slash_commands`

---

## Priority

**Priority:** P0 (CRITICAL for v0.10.0 release)

**Rationale:**
- Without slash commands, spec-kitty is essentially non-functional for agents
- Users cannot execute workflows
- This breaks the primary use case
- Should be fixed before v0.10.0 release

---

## Example Output

**Mission template exists:**
```bash
$ cat .kittify/missions/software-dev/command-templates/implement.md
# Implement Task

Execute the implementation for work package {WORK_PACKAGE_ID}
...
```

**Slash command missing:**
```bash
$ ls .claude/commands/spec-kitty.implement.md
ls: .claude/commands/spec-kitty.implement.md: No such file or directory
```

---

**Status:** ✅ RESOLVED / NOT REPRODUCIBLE

**Validation Results:**
External test confirms all 13 slash commands are created:
- spec-kitty.specify.md ✅
- spec-kitty.plan.md ✅
- spec-kitty.tasks.md ✅
- spec-kitty.implement.md ✅
- spec-kitty.review.md ✅
- spec-kitty.accept.md ✅
- spec-kitty.merge.md ✅
- spec-kitty.constitution.md ✅
- spec-kitty.clarify.md ✅
- spec-kitty.analyze.md ✅
- spec-kitty.research.md ✅
- spec-kitty.dashboard.md ✅
- spec-kitty.checklist.md ✅

**Conclusion:** Either bug was already fixed or user encountered different issue.
Init command DOES properly populate .claude/commands/ directory.

**Next Steps:** None - working as expected
