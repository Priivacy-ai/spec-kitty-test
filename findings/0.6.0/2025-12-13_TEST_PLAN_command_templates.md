# Test Plan: Command Templates & Git Protection Changes

**Date:** 2025-12-13
**Version:** 0.6.0 (development)
**Category:** Testing
**Status:** Planning

## Summary

Test plan for four major changes to spec-kitty:
1. Rename `commands/` → `command-templates/` (fix duplicate slash command discovery)
2. Add git protection (pre-commit hooks, .gitignore verification)
3. Shared constitution via symlinks in worktrees
4. Generate .claudeignore to optimize AI scanning

## Changes Being Tested

### 1. Command Template Directory Rename

**Change:** `.kittify/templates/commands/` → `.kittify/templates/command-templates/`

**Reason:** Prevent Claude Code from discovering templates as executable commands.

**Breaking Change:** Yes - directory structure changes

**Files Affected:**
- `src/specify_cli/template/manager.py` - Path references
- `src/specify_cli/mission.py` - Property rename
- `src/specify_cli/manifest.py` - Path updates
- `src/specify_cli/cli/commands/init.py` - Variable renames
- `.kittify/templates/command-templates/` - Directory rename
- `.kittify/missions/*/command-templates/` - Directory renames

### 2. Git Protection Features

**Changes:**
- Pre-commit hook to block agent directory commits
- GitignoreManager verification
- Enhanced .gitignore with all agent directories

**Files Affected:**
- `.kittify/templates/git-hooks/pre-commit-agent-check` - New file
- `src/specify_cli/cli/commands/init.py` - Hook installation
- `src/specify_cli/gitignore_manager.py` - Add verification

### 3. Shared Constitution via Symlink

**Change:** `.kittify/memory/` in worktrees becomes symlink to main repo's memory

**Reason:** Ensure all feature branches share same constitution

**Files Affected:**
- `.kittify/scripts/bash/create-new-feature.sh` - Symlink creation
- Worktree structure

**Compatibility:** Falls back to copy on Windows if symlinks fail

### 4. .claudeignore Generation

**Changes:**
- New `.claudeignore` file generated during init
- Excludes `.kittify/templates/`, `.kittify/missions/`, agent dirs

**Files Affected:**
- `.kittify/templates/claudeignore-template` - New file
- `src/specify_cli/cli/commands/init.py` - Generation logic

## Test Coverage Plan

### Test File 1: test_command_template_rename.py (New)

**Purpose:** Verify command template directory rename doesn't break functionality

**Test Cases:**
1. **test_init_creates_command_templates_directory**
   - Fresh init creates `command-templates/` not `commands/`
   - Verify in both `.kittify/templates/` and `.kittify/missions/*/`

2. **test_no_commands_directory_created**
   - Ensure old `commands/` directory is NOT created
   - Verify templates are in correct location

3. **test_claude_discovers_single_command_set**
   - Init with `--ai=claude`
   - Count slash commands discovered
   - Should be exactly 13 commands (not 26, not 39)

4. **test_template_manager_finds_command_templates**
   - TemplateManager.get_command_templates() works
   - Returns correct paths to command-templates/

5. **test_mission_command_templates_property**
   - Mission object has `command_templates_dir` property
   - Property returns correct path
   - Old `commands_dir` property removed/deprecated

**Expected Results:**
- All template references use `command-templates/`
- No duplicate command discovery
- Claude Code finds only rendered commands in `.claude/commands/`

### Test File 2: test_git_protection.py (New)

**Purpose:** Verify git protection prevents accidental agent directory commits

**Test Cases:**
1. **test_gitignore_includes_all_agent_directories**
   - Fresh init creates .gitignore
   - Verify all 12 agent directories listed
   - Includes: `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.augment/`, `.roo/`, `.amazonq/`, `.github/copilot/`

2. **test_pre_commit_hook_installed**
   - Init creates `.git/hooks/pre-commit-agent-check`
   - Hook is executable (chmod 755)
   - Hook exists after init

3. **test_pre_commit_hook_blocks_agent_files**
   - Create test file in `.claude/`
   - `git add .claude/test.txt`
   - `git commit -m "test"` should FAIL
   - Error message should be clear and helpful

4. **test_pre_commit_hook_allows_normal_commits**
   - Create regular file
   - `git add file.txt`
   - `git commit -m "test"` should SUCCEED
   - Verify commit created

5. **test_pre_commit_hook_bypass_with_no_verify**
   - Stage agent file
   - `git commit --no-verify -m "test"` should SUCCEED
   - Verify warning in docs about this

6. **test_gitignore_manager_verify_protection**
   - GitignoreManager.verify_protection() exists
   - Returns ProtectionResult with status
   - Detects missing .gitignore entries
   - Detects staged agent files

**Expected Results:**
- Agent directories cannot be committed accidentally
- Clear error messages guide users
- Normal commits work fine
- Bypass available if needed

### Test File 3: test_worktree_constitution_symlink.py (New)

**Purpose:** Verify constitution sharing via symlinks in worktrees

**Test Cases:**
1. **test_worktree_memory_is_symlink**
   - Create worktree via create-new-feature.sh
   - Verify `.kittify/memory/` in worktree is symlink
   - Symlink points to `../../../.kittify/memory`
   - Use relative path (not absolute)

2. **test_constitution_shared_between_main_and_worktree**
   - Edit `constitution.md` in main repo
   - Verify change visible in worktree
   - Edit in worktree
   - Verify change visible in main

3. **test_multiple_worktrees_share_same_constitution**
   - Create 2 worktrees
   - Both should have symlinks to same memory/
   - Edit constitution
   - Change visible in both worktrees

4. **test_symlink_creation_uses_relative_path**
   - Check symlink target
   - Should be `../../../.kittify/memory`
   - NOT absolute path like `/Users/robert/.../memory`
   - Ensures repo can be moved/cloned

5. **test_windows_fallback_to_copy**
   - Simulate symlink failure
   - Verify falls back to directory copy
   - Warning message displayed
   - Copy contains constitution.md

6. **test_memory_directory_not_copied_anymore**
   - Old behavior: memory/ was copied
   - New behavior: memory/ is symlinked
   - Verify no duplicate memory/ directories

**Expected Results:**
- Constitution is shared across all worktrees
- Symlinks work on Unix/macOS
- Graceful fallback on Windows
- Single source of truth for constitution

### Test File 4: test_claudeignore_generation.py (New)

**Purpose:** Verify .claudeignore is generated and contains correct patterns

**Test Cases:**
1. **test_claudeignore_created_during_init**
   - Fresh init generates `.claudeignore`
   - File exists in project root
   - File is not executable

2. **test_claudeignore_excludes_kittify_internal**
   - Verify contains: `.kittify/templates/`
   - Verify contains: `.kittify/missions/`
   - Verify contains: `.kittify/scripts/`

3. **test_claudeignore_excludes_all_agent_directories**
   - Verify contains all 12 agent dirs
   - `.claude/`, `.codex/`, `.gemini/`, etc.
   - `.github/copilot/`

4. **test_claudeignore_excludes_git_metadata**
   - Verify contains: `.git/`
   - Standard patterns

5. **test_claudeignore_excludes_build_artifacts**
   - Verify contains: `__pycache__/`, `*.pyc`, `node_modules/`
   - Standard patterns

6. **test_claudeignore_not_overwritten_if_exists**
   - Create custom `.claudeignore`
   - Run init again (shouldn't happen but test anyway)
   - Verify custom file not overwritten

7. **test_claude_code_respects_claudeignore**
   - Create project with templates
   - Verify Claude Code doesn't scan templates
   - (May need manual verification or Claude Code integration)

**Expected Results:**
- .claudeignore generated automatically
- Reduces token usage by excluding templates
- Doesn't break existing workflows

### Test File 5: Updates to Existing Tests

**File:** `test_slash_command_paths.py`

**Changes Needed:**
- Tests reference `templates/commands/` in checks
- Update to look for `command-templates/` instead
- Line 163-167: Update "commands/" checks
- Verify tests still pass after rename

**File:** `test_init_template_discovery.py`

**Changes Needed:**
- No changes required (tests PyPI version compatibility)
- May need to add test for command-templates/ path

**File:** `test_worktree_management.py`

**Changes Needed:**
- Line 102-144: `test_kittify_copied_to_worktree`
  - Currently verifies `.kittify` is copied (directory)
  - After change: `.kittify/memory` should be symlink
  - Update test to check symlink while rest is copied

- Add assertion: `.kittify/memory` is symlink
- Add assertion: symlink points to main memory

**File:** `test_worktree_missions.py` (if exists)

**Changes Needed:**
- Similar updates for memory/ symlink checks

## Migration Testing

**Test Case:** test_migration_from_old_structure

**Purpose:** Verify existing projects can migrate

**Steps:**
1. Create project with old structure (commands/)
2. Run migration (if migration tool provided)
3. Verify commands/ → command-templates/
4. Verify old projects still work

**Note:** May need migration script: `spec-kitty migrate-templates`

## Test Execution Plan

### Phase 1: Baseline (Before Changes)
1. Activate venv
2. Install current PyPI version (0.6.4)
3. Run full test suite
4. Record baseline results
5. Identify any existing failures

### Phase 2: Switch to Development Version
1. Uninstall PyPI version
2. Install development version: `pip install -e ~/Code/spec-kitty`
3. Verify version shows as development

### Phase 3: Create New Test Files
1. Write `test_command_template_rename.py`
2. Write `test_git_protection.py`
3. Write `test_worktree_constitution_symlink.py`
4. Write `test_claudeignore_generation.py`

### Phase 4: Update Existing Tests
1. Update `test_slash_command_paths.py`
2. Update `test_worktree_management.py`
3. Review other tests for references to old paths

### Phase 5: Incremental Testing
1. Run new tests (expect failures before implementation)
2. Track which changes are implemented in dev version
3. Re-run tests as changes are made
4. Document findings for any bugs discovered

### Phase 6: Full Suite Validation
1. Run entire test suite (all 323+ tests)
2. Verify no regressions
3. Confirm all new tests pass
4. Document any unexpected behavior

## Success Criteria

### Must Pass:
1. ✅ All command template tests pass
2. ✅ Git protection tests pass
3. ✅ Constitution symlink tests pass (Unix/macOS)
4. ✅ Constitution copy fallback works (Windows simulation)
5. ✅ .claudeignore tests pass
6. ✅ No regressions in existing tests
7. ✅ Fresh init creates correct structure

### Nice to Have:
- Migration tool tests
- Performance comparison (token usage with .claudeignore)
- Integration test with Claude Code
- Windows platform testing

## Risks & Mitigation

### High Risk: Directory Rename
**Risk:** Breaking change could fail existing projects

**Mitigation:**
- Comprehensive test coverage
- Test both fresh init and existing projects
- Provide migration path
- Clear documentation

### Medium Risk: Symlink Compatibility
**Risk:** Windows symlinks may not work

**Mitigation:**
- Fallback to directory copy
- Test fallback mechanism
- Document Windows behavior

### Low Risk: .claudeignore
**Risk:** May not reduce token usage significantly

**Mitigation:**
- This is additive, no breaking change
- Document expected behavior
- Measure token usage if possible

## Test Environment

**Python:** 3.11+
**Playwright:** 1.56.0+
**pytest:** 8.4.2+
**spec-kitty:** Development version from `~/Code/spec-kitty`

**Environment Variables:**
```bash
export SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty
export SPEC_KITTY_TEMPLATE_ROOT=/Users/robert/Code/spec-kitty
```

## Expected Test Count

**Current Suite:** 323 tests
**New Tests:** ~30-40 tests
**Updated Tests:** ~5-10 tests
**Final Suite:** ~355-375 tests

## Timeline

**Estimated Effort:** 4-6 hours

1. Setup & baseline: 30 minutes
2. Write new tests: 2-3 hours
3. Update existing tests: 1 hour
4. Test execution & debugging: 1-2 hours

## Notes

- Tests should be written BEFORE implementation (TDD)
- Some tests expected to fail until features implemented
- Use `@pytest.mark.xfail` for known failures
- Document findings in findings/ directory
- Keep test files under 500 lines each
- Use clear, descriptive test names
- Include docstrings explaining test coverage

## References

- [Main spec-kitty repo](https://github.com/Priivacy-ai/spec-kitty)
- [test-reports/](../docs/test-reports/)
- [findings/0.6.0/](./)