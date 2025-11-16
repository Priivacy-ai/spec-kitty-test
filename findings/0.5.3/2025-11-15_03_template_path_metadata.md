# Finding: Misleading Path Metadata in Rendered Commands

**Date:** 2025-11-15
**Session ID:** template-rendering-investigation-001
**Tested by:** Claude Code (automated tests)
**Category:** UX Improvement - Command Rendering
**Spec-Kitty Version:** 0.5.2, 0.5.3-pre
**Analysis Date:** 2025-11-15
**Applies To:** All versions with current template rendering

## Summary

Rendered command files contain misleading path metadata that shows the SOURCE template location instead of the ACTUAL file location, confusing users and agents about which file they're viewing.

## Observation

When users/agents run slash commands like `/spec-kitty.implement`, the rendered command file shows:

```markdown
*Path: [.kittify/templates/commands/implement.md](.kittify/templates/commands/implement.md)*
```

But the user is ACTUALLY reading:
- Claude: `.claude/commands/spec-kitty.implement.md`
- Codex: `.codex/prompts/spec-kitty.implement.md`

NOT `.kittify/templates/commands/implement.md` (which is the source template).

### User's Experience

```
User runs: /spec-kitty.implement
Agent sees: *Path: [templates/commands/implement.md]*
Agent sees: {SCRIPT} placeholder (if old version)
Agent sees: $ARGUMENTS placeholder

Agent thinks: "I'm looking at the source template!"
Agent reports: "The command placeholder {SCRIPT} wasn't provided"
User confused: "Why is the agent seeing the template?"
```

### Reality

The agent IS looking at the rendered file (`.codex/prompts/spec-kitty.implement.md`).
Variables ARE substituted (in current version).
The path metadata is just WRONG/MISLEADING.

## Impact

- **Severity:** Medium (UX confusion, not functional bug)
- **Scope:** All users, all agents
- **Frequency:** Every slash command invocation

**User Impact:**
- Confusion about which file is being read
- Difficulty debugging template issues
- Misleading error reports ("template not rendered" when it is)
- Users may try to edit the wrong file

**Agent Impact:**
- Agents report incorrect file paths
- Harder to trace which file agent read
- Diagnostic information misleading

## Root Cause Analysis

### Current Behavior

When templates are rendered during `spec-kitty init`:

1. Source template: `templates/commands/implement.md`
2. Rendered to: `.codex/prompts/spec-kitty.implement.md`
3. **Header added**: `*Path: [.kittify/templates/commands/implement.md]*`

The header shows the SOURCE template location (possibly for attribution/tracing),
but users think this means they're viewing the template, not the rendered output.

### Why This Matters

**File locations**:
- Source templates: `templates/commands/` (spec-kitty repo only)
- Rendered Claude: `.claude/commands/` (user's project)
- Rendered Codex: `.codex/prompts/` (user's project)

When path says `templates/commands/implement.md`:
- Users look for that file (doesn't exist in their project!)
- Users think variables aren't substituted (they are!)
- Users report "seeing the template" (they're not!)

## User/Agent Journey

### What Actually Happens

1. User runs `/spec-kitty.implement` in Codex
2. Codex CLI reads `.codex/prompts/spec-kitty.implement.md`
3. File header says: `*Path: [.kittify/templates/commands/implement.md]*`
4. Agent sees this path and thinks "I'm reading the template"
5. Agent finds `$ARGUMENTS` in "User Input" section
6. Agent reports: "Placeholder not provided" (thinks it's unrendered)

### What User Expects

1. User runs `/spec-kitty.implement`
2. Path shown: `.codex/prompts/spec-kitty.implement.md` ✓
3. Agent knows it's reading rendered command ✓
4. Agent executes normally ✓

## What Could Have Helped

### Better Path Metadata

```markdown
<!-- Source: templates/commands/implement.md -->
<!-- Rendered: .codex/prompts/spec-kitty.implement.md -->
*Current File: .codex/prompts/spec-kitty.implement.md*
```

or

```markdown
---
description: Execute the implementation plan
source_template: templates/commands/implement.md
rendered_for: codex
current_path: .codex/prompts/spec-kitty.implement.md
---

## User Input
...
```

### Agent-Facing Clarity

```markdown
---
description: Execute the implementation plan
---

> **You are reading**: `.codex/prompts/spec-kitty.implement.md` (rendered command)
> **Variables**: All placeholders have been substituted
> **Last updated**: 2025-11-15

## User Input
...
```

## Suggested Improvements

### Option 1: Fix Path Metadata (Quick)

Update template rendering to show ACTUAL file location:

```diff
  # During rendering
- header = f"*Path: [{source_template}]({source_template})*"
+ header = f"*Path: [{rendered_path}]({rendered_path})*"
```

### Option 2: Add Both Paths (Better)

Show both source and rendered:

```markdown
---
description: Execute the implementation plan
rendered_from: templates/commands/implement.md
current_file: .codex/prompts/spec-kitty.implement.md
---

## User Input
```

### Option 3: Remove Path (Simplest)

Just remove the path line entirely. Users can check file path via their IDE.

## Related Files

- Template rendering logic (wherever templates are copied/rendered)
- All command files in:
  - `.claude/commands/spec-kitty.*.md`
  - `.codex/prompts/spec-kitty.*.md`
  - Other agent directories

## Example Output/Reproduction

```bash
# 1. Initialize project
spec-kitty init test --ai=codex

# 2. Check rendered file header
head -10 test/.codex/prompts/spec-kitty.implement.md
```

**Current Output:**
```markdown
*Path: [.kittify/templates/commands/implement.md]*
```

**Should Be:**
```markdown
*Path: [.codex/prompts/spec-kitty.implement.md]*
```

## Testing

**Test File**: `tests/functional/test_slash_command_paths.py`
**Tests**: 12 tests, 11 passing, 1 failing

**Failing Test**:
```bash
test_slash_commands_not_in_commands_directory
FAILED: Command file spec-kitty.clarify.md references templates/ directory
```

This confirms some commands still have incorrect path metadata.

## Priority

**Medium** - Not a functional bug, but causes significant confusion

## Verification

After fix, check that rendered files show correct paths:

```bash
# Claude
grep "Path:" .claude/commands/spec-kitty.implement.md
# Should show: .claude/commands/spec-kitty.implement.md

# Codex
grep "Path:" .codex/prompts/spec-kitty.implement.md
# Should show: .codex/prompts/spec-kitty.implement.md
```

---

**Notes:**
- Variables ARE being substituted correctly in current version
- The path metadata is just misleading, not indicating a rendering failure
- User's confusion is understandable given the incorrect path shown
