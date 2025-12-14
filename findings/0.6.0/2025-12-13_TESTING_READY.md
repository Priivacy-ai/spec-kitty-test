# Test Environment Ready for Command Templates Testing

**Date:** 2025-12-13
**Version:** spec-kitty 0.6.4 (development)
**Category:** Testing
**Status:** Ready for Testing

## Summary

Test environment is fully prepared to test the four major changes in spec-kitty v0.6.0:
1. ✅ Command template rename (`commands/` → `command-templates/`)
2. ✅ Git protection (pre-commit hooks, .gitignore)
3. ✅ Shared constitution via symlinks in worktrees
4. ✅ .claudeignore generation

All features are **already implemented** in the development version and ready to test.

## What's Been Prepared

### 1. Test Plan Document
**Location:** `findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md`

Comprehensive test plan covering:
- All 4 feature areas
- 30+ new test cases
- Migration testing strategy
- Success criteria
- Risk assessment

### 2. New Test Files Created

#### test_command_template_rename.py (9 tests)
Tests the directory rename from `commands/` to `command-templates/`:
- Directory structure validation
- No duplicate command discovery
- Template Manager API compatibility

**Key tests:**
- `test_init_creates_command_templates_directory` - Verifies new structure
- `test_no_commands_directory_created` - Ensures old paths gone
- `test_claude_discovers_single_command_set` - No duplicates (13 commands, not 26)

#### test_git_protection.py (9 tests)
Tests git protection features:
- .gitignore includes all 12 agent directories
- Pre-commit hook installation and execution
- Hook blocks agent files, allows normal commits
- Hook bypass with --no-verify

**Key tests:**
- `test_gitignore_includes_all_agent_directories` - All agents protected
- `test_pre_commit_hook_blocks_agent_files` - Prevents accidents
- `test_pre_commit_hook_allows_normal_commits` - Normal workflow works

#### test_worktree_constitution_symlink.py (8 tests)
Tests shared constitution via symlinks:
- Worktree memory/ is symlink to main
- Relative path used (repo can be moved)
- Edits in main visible in worktree and vice versa
- Multiple worktrees share same constitution
- Windows fallback to copy

**Key tests:**
- `test_worktree_memory_is_symlink` - Symlink created
- `test_edits_in_main_visible_in_worktree` - Sharing works
- `test_multiple_worktrees_share_constitution` - All worktrees unified

#### test_claudeignore_generation.py (7 tests)
Tests .claudeignore generation:
- File created during init
- Excludes .kittify/ internals
- Excludes all agent directories
- Excludes git, build artifacts, OS files

**Key tests:**
- `test_claudeignore_created_during_init` - File generated
- `test_excludes_kittify_internal_directories` - Templates excluded
- `test_excludes_all_agent_directories` - Agents excluded

### 3. Development Environment Configured

**Installed:** spec-kitty-cli 0.6.4 (development version from ~/Code/spec-kitty)
**Installation:** Editable mode (`pip install -e ~/Code/spec-kitty`)
**Environment:**
```bash
export SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty
export SPEC_KITTY_TEMPLATE_ROOT=/Users/robert/Code/spec-kitty
```

### 4. Features Verified Present

All changes confirmed in development version:

```bash
~/Code/spec-kitty/.kittify/
├── templates/
│   ├── command-templates/        # ✅ Renamed from commands/
│   ├── git-hooks/                # ✅ New git protection
│   │   ├── pre-commit-agent-check
│   │   └── pre-commit-encoding-check
│   └── claudeignore-template     # ✅ New .claudeignore
├── missions/
│   ├── software-dev/
│   │   └── command-templates/    # ✅ Renamed from commands/
│   └── research/
│       └── command-templates/    # ✅ Renamed from commands/
└── scripts/bash/
    └── create-new-feature.sh     # ✅ Includes symlink code
```

## How to Run Tests

### Run All New Tests (33 tests)
```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
export SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty
export SPEC_KITTY_TEMPLATE_ROOT=/Users/robert/Code/spec-kitty

pytest tests/functional/test_command_template_rename.py \
       tests/functional/test_git_protection.py \
       tests/functional/test_worktree_constitution_symlink.py \
       tests/functional/test_claudeignore_generation.py \
       -v
```

### Run Individual Test Suites

**Command Templates:**
```bash
pytest tests/functional/test_command_template_rename.py -v
```

**Git Protection:**
```bash
pytest tests/functional/test_git_protection.py -v
```

**Worktree Symlinks:**
```bash
pytest tests/functional/test_worktree_constitution_symlink.py -v
```

**.claudeignore:**
```bash
pytest tests/functional/test_claudeignore_generation.py -v
```

### Run Specific Tests

Example - test command template structure:
```bash
pytest tests/functional/test_command_template_rename.py::TestCommandTemplateDirectoryStructure::test_init_creates_command_templates_directory -v -s
```

Example - test symlink creation:
```bash
pytest tests/functional/test_worktree_constitution_symlink.py::TestSymlinkCreation::test_worktree_memory_is_symlink -v -s
```

## Expected Results

### All Tests Should Pass ✅

Since all features are implemented in the development version, all 33 tests should pass:

- ✅ 9 command template tests
- ✅ 9 git protection tests
- ✅ 8 worktree symlink tests
- ✅ 7 .claudeignore tests

### If Tests Fail

If any tests fail, create a finding document:

```bash
cp findings/TEMPLATE.md findings/0.6.0/2025-12-13_XX_<description>.md
```

Document:
- Which test failed
- Error message
- Expected vs actual behavior
- Impact on users
- Suggested fix

## Next Steps

### 1. Run Initial Test Suite ✅
```bash
pytest tests/functional/test_command_template_rename.py \
       tests/functional/test_git_protection.py \
       tests/functional/test_worktree_constitution_symlink.py \
       tests/functional/test_claudeignore_generation.py \
       -v --tb=short
```

### 2. Document Any Failures
Create findings for any bugs discovered during testing.

### 3. Update Existing Tests (Optional)
Some existing tests may need updates:
- `test_slash_command_paths.py` - May reference old `commands/` paths
- `test_worktree_management.py` - May need symlink assertions

### 4. Run Full Test Suite
Once new tests pass, run the entire suite to check for regressions:
```bash
pytest tests/functional/ -v
```

## Test Statistics

**Before:**
- Total tests: 323
- Test files: 28

**After:**
- New tests: +33
- New test files: +4
- Updated tests: ~5-10 (estimated)
- Total tests: ~355-375
- Total test files: 32

## Files Created

### Test Files
1. `/Users/robert/Code/spec-kitty-test/tests/functional/test_command_template_rename.py`
2. `/Users/robert/Code/spec-kitty-test/tests/functional/test_git_protection.py`
3. `/Users/robert/Code/spec-kitty-test/tests/functional/test_worktree_constitution_symlink.py`
4. `/Users/robert/Code/spec-kitty-test/tests/functional/test_claudeignore_generation.py`

### Documentation
1. `/Users/robert/Code/spec-kitty-test/findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md`
2. `/Users/robert/Code/spec-kitty-test/findings/0.6.0/2025-12-13_TESTING_READY.md` (this file)

## Configuration

**Python:** 3.14
**pytest:** 8.4.2
**Playwright:** 1.56.0
**spec-kitty-cli:** 0.6.4 (editable install from ~/Code/spec-kitty)

**Environment Variables:**
```bash
SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty
SPEC_KITTY_TEMPLATE_ROOT=/Users/robert/Code/spec-kitty
```

## Notes

- All tests use temporary directories for isolation
- Tests clean up after themselves (shutil.rmtree)
- Tests use --ignore-agent-tools to speed up initialization
- Symlink tests skip on Windows if symlinks unavailable
- Some API tests may skip if internal classes change

## Success Criteria

For testing to be considered complete and successful:

✅ **Must Have:**
1. All 33 new tests pass
2. No regressions in existing test suite
3. Fresh init creates correct structure
4. Command discovery shows exactly 13 commands (no duplicates)
5. Git protection blocks agent file commits
6. Constitution sharing works via symlinks
7. .claudeignore is generated with correct patterns

✅ **Nice to Have:**
- Windows compatibility tests (symlink fallback)
- Performance measurements (token usage with .claudeignore)
- Integration with Claude Code CLI
- Migration path for existing projects

## Contact & Support

**Issues:** Create findings in `findings/0.6.0/`
**Test Questions:** Review test plan at `findings/0.6.0/2025-12-13_TEST_PLAN_command_templates.md`
**Spec-Kitty Repo:** ~/Code/spec-kitty

---

**Status:** 🟢 Ready for Testing
**Last Updated:** 2025-12-13
**Prepared By:** Claude Code Testing Agent
