**Date:** 2025-12-14
**Session ID:** upgrade-0.7.x-worktree-dedup
**Tested by:** Claude Agent
**Category:** Bug Fix
**Spec-Kitty Version:** 0.7.2 (migration released in 0.7.2, issue identified in 0.7.1)
**Analysis Date:** 2025-12-14
**Applies To:** Projects using git worktrees nested inside the main repository

## Summary

Fixed the "double slash command" problem where Claude Code discovered commands twice when running from a worktree nested inside the main repo.

## Observation

When running Claude Code from inside a worktree at:
```
/project/.worktrees/feature-branch/
```

Claude Code was finding 26 commands (13 duplicated) instead of 13 unique commands.

The duplication occurred because Claude Code:
1. Found `.claude/commands/` in the worktree (13 commands)
2. Traversed up the directory tree and found `.claude/commands/` in the main repo (13 more commands)

The worktree is physically nested inside the main repo:
```
project/                          <- main repo has .claude/commands/
└── .worktrees/
    └── feature-branch/           <- worktree ALSO has .claude/commands/
```

Claude Code's parent directory traversal found both locations.

## Impact

- **Severity:** Medium
- **Scope:** Users with git worktrees nested inside their main repository
- **Frequency:** Always happens when worktrees have their own .claude/commands/

## Root Cause Analysis

The initial implementation (in 0.7.1 development) incorrectly removed `.claude/commands/` from the main repo, reasoning that each worktree has its own copy. This was backwards - it prevented running slash commands from the main directory.

The correct fix (released in 0.7.2) removes `.claude/commands/` from worktrees instead. Since worktrees are physically nested inside the main repo, Claude Code will traverse up and find the main repo's commands automatically.

## User/Agent Journey

1. User creates a project with spec-kitty
2. User creates worktrees for feature branches at `.worktrees/`
3. spec-kitty copies `.claude/commands/` to each worktree
4. User runs Claude Code from within a worktree
5. Claude Code shows duplicate commands (e.g., "spec-kitty.implement.md" appears twice)

## What Could Have Helped

- Understanding Claude Code's command discovery algorithm earlier
- Testing with worktrees from the start of the project
- Clear documentation about how Claude Code traverses directories to find commands

## Suggested Improvements

The 0.7.2 migration implements the correct fix:
1. Detects if any worktrees have their own `.claude/commands/`
2. Verifies main repo has `.claude/commands/` before removing from worktrees
3. Removes `.claude/commands/` from all worktrees

After migration:
```
project/.claude/commands/                    <- KEPT (main repo)
project/.worktrees/
    feature-001/.claude/                     <- commands/ REMOVED
    feature-002/.claude/                     <- commands/ REMOVED
```

## Related Files

- `src/specify_cli/upgrade/migrations/m_0_7_2_worktree_commands_dedup.py` - Migration implementation
- `tests/test_upgrade/test_migrations/test_m_0_7_1_worktree_commands_dedup.py` - Comprehensive tests

## Test Coverage

14 tests covering:

### Detection (3 tests)
- Detects worktrees with `.claude/commands/`
- No detection when no worktrees exist
- No detection when worktrees don't have `.claude/commands/`

### Can Apply Validation (2 tests)
- Requires main repo to have `.claude/commands/`
- Fails gracefully if main repo missing commands

### Migration Execution (4 tests)
- Removes `.claude/commands/` from all worktrees
- Preserves main repo `.claude/commands/`
- Handles multiple worktrees (5+)
- Dry run shows changes without applying

### Edge Cases (3 tests)
- Worktree has `.claude/` but no `commands/` (no-op)
- Mixed worktrees (some with, some without commands/)
- Worktree has symlinked `.claude/commands/` (handled gracefully)

### Integration (2 tests)
- Migration is registered in registry
- Migration ordered after 0.6.7

---
**Notes:** The implementing team initially got the fix backwards (removing from main repo instead of worktrees), which prompted a version bump to 0.7.2 with the corrected implementation.
