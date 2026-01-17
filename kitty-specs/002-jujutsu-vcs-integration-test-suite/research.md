# Research: Jujutsu VCS Integration Test Suite

**Feature**: 002-jujutsu-vcs-integration-test-suite
**Research Date**: 2026-01-17
**Source Repo**: /Users/robert/Code/spec-kitty
**Source Feature**: 015-first-class-jujutsu-vcs-integration

## Executive Summary

The jujutsu VCS integration in spec-kitty is **FULLY IMPLEMENTED**. All 9 work packages (WP01-WP09) are complete with 111 existing tests. This research identifies testing gaps for our external QA test suite.

## Implementation Status

### Work Package Completion

| WP | Name | Status | Files |
|----|------|--------|-------|
| WP01 | VCS Types and Protocol | ✅ Complete | `types.py`, `protocol.py`, `exceptions.py` |
| WP02 | VCS Detection and Factory | ✅ Complete | `detection.py` |
| WP03 | Git VCS Implementation | ✅ Complete | `git.py` (1305 lines) |
| WP04 | Jujutsu VCS Implementation | ✅ Complete | `jujutsu.py` (1092 lines) |
| WP05 | Init Command Update | ✅ Complete | `commands/init.py` |
| WP06 | Implement Command Update | ✅ Complete | `commands/implement.py` |
| WP07 | Sync Command | ✅ Complete | `commands/sync.py` |
| WP08 | Ops Command | ✅ Complete | `commands/ops.py` |
| WP09 | Integration and Polish | ✅ Complete | `merge.py`, `worktree.py` |

### File Locations

```
/Users/robert/Code/spec-kitty/src/specify_cli/core/vcs/
├── __init__.py       # Public API exports
├── protocol.py       # VCSProtocol interface
├── types.py          # Dataclasses and enums
├── git.py            # GitVCS implementation
├── jujutsu.py        # JujutsuVCS implementation
├── detection.py      # Factory and tool detection
└── exceptions.py     # Exception hierarchy
```

## VCS Protocol API Surface

### Core Protocol Methods

**Workspace Operations**:
- `create_workspace(workspace_path, workspace_name, base_branch=None, base_commit=None) -> WorkspaceCreateResult`
- `remove_workspace(workspace_path) -> bool`
- `get_workspace_info(workspace_path) -> WorkspaceInfo | None`
- `list_workspaces(repo_root) -> list[WorkspaceInfo]`

**Synchronization Operations**:
- `sync_workspace(workspace_path) -> SyncResult`
- `is_workspace_stale(workspace_path) -> bool`

**Conflict Operations**:
- `detect_conflicts(workspace_path) -> list[ConflictInfo]`
- `has_conflicts(workspace_path) -> bool`

**Commit/Change Operations**:
- `get_current_change(workspace_path) -> ChangeInfo | None`
- `get_changes(repo_path, revision_range=None, limit=None) -> list[ChangeInfo]`
- `commit(workspace_path, message, paths=None) -> ChangeInfo | None`

**Repository Operations**:
- `init_repo(path, colocate=True) -> bool`
- `is_repo(path) -> bool`
- `get_repo_root(path) -> Path | None`

### Backend-Specific Functions

**Git-specific**:
- `git_get_reflog()` - Operation history via reflog
- `git_stash()` - Stash changes
- `git_stash_pop()` - Restore stashed changes

**jj-specific**:
- `jj_get_operation_log()` - Full operation log
- `jj_undo_operation()` - Undo with `jj op undo`
- `jj_get_change_by_id()` - Lookup by stable Change ID

## Capability Differences

| Capability | Git | jj |
|------------|-----|-----|
| `supports_auto_rebase` | ❌ | ✅ |
| `supports_conflict_storage` | ❌ | ✅ |
| `supports_operation_log` | ✅ (limited) | ✅ (full) |
| `supports_change_ids` | ❌ | ✅ |
| `supports_workspaces` | ✅ (worktrees) | ✅ (native) |
| `supports_colocated` | ❌ | ✅ |
| `supports_operation_undo` | ❌ | ✅ |

**Critical Semantic Difference**: jj sync operations ALWAYS succeed - conflicts are stored in commits, not blocking.

## Existing Test Coverage

### Test Location
`/Users/robert/Code/spec-kitty/tests/specify_cli/core/vcs/`

### Test Files and Coverage

| File | Tests | Focus |
|------|-------|-------|
| `test_detection.py` | 35 | Detection, factory, VCS locking |
| `test_git.py` | 45 | GitVCS implementation |
| `test_jujutsu.py` | 31 | JujutsuVCS implementation |
| **Total** | **111** | |

### Test Categories in spec-kitty

- **TestGitDetection**: Git availability, version, caching
- **TestJJDetection**: jj availability (with skip markers)
- **TestGetVCS**: Factory function, fallback, locking
- **TestLockedVCSFromMeta**: Feature-level VCS locking
- **TestWorkspaceOperations**: Create, remove, list, sparse-checkout
- **TestConflictOperations**: Detection, blocking behavior
- **TestSyncOperations**: Sync, staleness checking
- **TestJJSpecificFunctions**: Operation log, undo, Change ID

## Testing Gaps Identified

### 1. Distribution Testing (CRITICAL)

**Gap**: All spec-kitty tests use `SPEC_KITTY_TEMPLATE_ROOT` bypass
**Our Focus**: Test real PyPI user experience without bypass

Tests needed:
- VCS detection works from PyPI install
- Workspace creation from PyPI install
- All templates have Python CLI commands (no bash/PowerShell)
- No missing module errors in VCS abstraction

### 2. Edge Case Coverage

**Not tested in spec-kitty**:
- jj binary exists but broken/crashes
- jj version below minimum (< 0.20)
- PATH changes mid-session
- Concurrent sync operations
- Workspace corruption scenarios
- Disk full during operations
- 100+ workspace stress test

### 3. Upgrade Path Testing

**Not tested in spec-kitty**:
- Git-only project + jj install → new features use jj
- Existing git worktrees + jj features coexist
- jj uninstalled mid-project recovery
- Config.yaml migration for jj preference

### 4. Adversarial Scenarios

**Not tested in spec-kitty**:
- meta.json manual tampering detection
- VCS lock bypass attempts
- Malformed conflict markers
- Corrupted operation log
- Multi-sided conflict (3+ parents)
- Remote force-push during sync

### 5. Gitignore Bug (NEW)

**Discovered during spec creation**:
- spec-kitty adds `kitty-specs/` to .gitignore
- This incorrectly ignores kitty-specs in main repo
- Should only apply to worktrees

### 6. Integration Testing

**Limited in spec-kitty**:
- End-to-end workflow with multiple WPs
- 10+ WP dependency chain auto-rebase
- Diamond dependency resolution
- Review/merge blocking on conflicts

## Detection Factory Behavior

### `get_vcs()` Decision Tree

```
1. If backend explicitly specified:
   → Use that (check feature lock mismatch)

2. If path in feature directory:
   → Read meta.json for locked VCS
   → Raise VCSBackendMismatchError if mismatch

3. If prefer_jj=True and jj available:
   → Return JujutsuVCS

4. If git available:
   → Return GitVCS

5. Else:
   → Raise VCSNotFoundError
```

### Feature VCS Locking

- Stored in `kitty-specs/###-feature/meta.json`
- Field: `"vcs": "jj"` or `"vcs": "git"`
- Locked at feature creation
- Prevents mid-feature VCS switching

## Exception Hierarchy

```python
VCSError (base)
├── VCSNotFoundError          # Neither jj nor git available
├── VCSCapabilityError        # Operation not supported by backend
├── VCSBackendMismatchError   # Requested backend != locked VCS
├── VCSLockError              # Attempted VCS change after lock
├── VCSConflictError          # Operation blocked by conflicts
└── VCSSyncError              # Sync operation failed
```

## Open Questions

1. **Minimum jj version**: Spec says 0.20+, but what version does spec-kitty actually require?
2. **Colocated mode default**: Is colocated mode always used when both tools available?
3. **Sparse-checkout with jj**: Does jj honor the same sparse-checkout patterns as git?
4. **Operation log size limits**: Any practical limits on operation log?

## Recommendations for Test Suite

### Priority 1 (P0) - Must Have

1. **Distribution tests for VCS detection** - No template bypass
2. **VCS lock enforcement tests** - meta.json tampering, lock bypass
3. **Conflict blocking tests** - Review/merge blocked correctly

### Priority 2 (P1) - Should Have

4. **Upgrade path tests** - Git-only to jj transition
5. **Gitignore bug tests** - kitty-specs tracking in main
6. **Workspace parity tests** - Same behavior git vs jj
7. **Dependency chain tests** - Auto-rebase propagation

### Priority 3 (P2) - Nice to Have

8. **Adversarial tests** - Corruption, tampering, edge cases
9. **Performance tests** - 100+ workspaces
10. **Recovery tests** - jj uninstall, workspace corruption

## Evidence References

See `research/evidence-log.csv` for source file analysis
See `research/source-register.csv` for all referenced files
