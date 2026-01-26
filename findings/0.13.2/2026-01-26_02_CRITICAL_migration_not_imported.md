# CRITICAL: Migration m_0_13_1_exclude_worktrees Not Imported

**Date:** 2026-01-26
**Session ID:** adversarial-testing-pre-release
**Tested by:** Claude Sonnet 4.5 (1M context) - Adversarial Testing
**Category:** Bug Report (CRITICAL)
**Spec-Kitty Version:** 0.13.2 (release/0.13.2 branch)
**Analysis Date:** 2026-01-26
**Applies To:** spec-kitty 0.13.2 release candidate

## Summary

CRITICAL packaging bug discovered during pre-release adversarial testing:
Migration file `m_0_13_1_exclude_worktrees.py` exists in source code and was
committed (b2d9b00), but is NOT imported in `__init__.py`, causing it to never
register with MigrationRegistry and never run during `spec-kitty upgrade`.

**Impact:** 100% of users upgrading from 0.13.0 or earlier will NOT get the
.worktrees/ exclusion, leaving them vulnerable to accidental git commits.

## Observation

### Discovery Process
1. Ran adversarial distribution test: `test_upgrade_adds_exclusion_to_existing_project`
2. Test FAILED: Migration didn't add .worktrees/ to .git/info/exclude
3. Verified migration file exists: ✅ Present in source
4. Verified migration code works: ✅ Direct call succeeds
5. Verified migration is registered: ❌ NOT in MigrationRegistry
6. Root cause: **Migration not imported in migrations/__init__.py**

### Evidence

**Migration File Status:**
```bash
$ ls src/specify_cli/upgrade/migrations/m_0_13_1_exclude_worktrees.py
-rw-r--r--  1 robert  staff  3093 Jan 26 07:27 m_0_13_1_exclude_worktrees.py
✓ File exists
```

**Migration Works When Called Directly:**
```python
from specify_cli.upgrade.migrations.m_0_13_1_exclude_worktrees import ExcludeWorktreesMigration

migration = ExcludeWorktreesMigration()
result = migration.apply(project_path)

# Result:
# - success: True
# - changes: ['Added .worktrees/ to .git/info/exclude']
# - .worktrees/ actually added to file ✓
```

**Migration NOT in Registry:**
```python
from specify_cli.upgrade.registry import MigrationRegistry

migrations = MigrationRegistry.get_all()
migration_ids = [m.migration_id for m in migrations]

# Result:
# - Total migrations: 27
# - '0.13.1_exclude_worktrees' in migration_ids: False ✗
# - 0.13.x migrations: [] (empty!)
```

**Root Cause - Missing Import:**
```python
# src/specify_cli/upgrade/migrations/__init__.py

# ... imports for migrations 0.2.0 through 0.12.1 ...
from . import m_0_12_1_remove_kitty_specs_from_gitignore

# ❌ MISSING: from . import m_0_13_1_exclude_worktrees
# ❌ MISSING: from . import m_0_13_0_* (3 migrations also missing!)

__all__ = [
    # ... list of migration modules ...
    "m_0_12_1_remove_kitty_specs_from_gitignore",
    # ❌ MISSING: "m_0_13_1_exclude_worktrees",
]
```

## Impact

### Severity: **CRITICAL**

**Scope:**
- **Affected Users:** 100% of users upgrading from 0.13.0 or earlier
- **Affected Workflow:** `spec-kitty upgrade` command
- **Impact:** Migration never runs, .worktrees/ exclusion never added

### Consequences

**For Existing Projects:**
1. User upgrades from 0.12.x to 0.13.2
2. Migration 0.13.1_exclude_worktrees doesn't run (not registered)
3. .worktrees/ NOT added to .git/info/exclude
4. User runs `git add .` (common workflow)
5. **BUG:** .worktrees/ gets staged and committed
6. Repository corrupted with worktree metadata

**For New Projects:**
- ✅ NEW projects are fine (init adds exclusion directly)
- ❌ EXISTING projects remain vulnerable

### Frequency
- **Happens:** 100% of the time for users upgrading
- **Scope:** All platforms (Windows, macOS, Linux)
- **Duration:** Will persist in 0.13.2 release if not fixed

## Root Cause Analysis

### The Pattern
Migrations in spec-kitty follow this pattern:
1. Create migration file: `m_X_Y_Z_description.py`
2. Add `@Migration Registry.register` decorator
3. **CRITICAL:** Import in `__init__.py` to trigger registration
4. Add to `__all__` list

### What Went Wrong
The implementing team:
- ✅ Created migration file (step 1)
- ✅ Added decorator (step 2)
- ❌ **FORGOT** step 3 (import in __init__.py)
- ❌ **FORGOT** step 4 (add to __all__)

Python's import system requires explicit imports. The @register decorator
only runs when the module is imported. Without the import in __init__.py,
the module never loads, the decorator never runs, the migration never registers.

### Why Tests Missed It

**Spec-kitty repo tests:**
- Unit tests call migration directly (import it explicitly)
- Direct import works, so tests pass ✓
- But this bypasses the discovery issue

**Why adversarial test caught it:**
- Tests real `spec-kitty upgrade` command (end-to-end)
- Uses MigrationRegistry the same way upgrade does
- Discovers that migration is not registered

## User/Agent Journey

### Scenario: User Upgrading from 0.12.0

**Expected (if migration worked):**
1. User: `spec-kitty upgrade`
2. Migration 0.13.1_exclude_worktrees runs
3. .worktrees/ added to .git/info/exclude
4. User protected from accidental commits ✅

**Actual (current bug):**
1. User: `spec-kitty upgrade`
2. Migration 0.13.1_exclude_worktrees does NOT run (not registered)
3. .worktrees/ NOT added
4. User runs `git add .` later
5. .worktrees/ gets committed ❌
6. Repository corrupted

## What Could Have Helped

### Development Process
1. **Checklist:** After creating migration, add to __init__.py
2. **Linting:** Check that all migration files are imported
3. **Registry validation:** Assert migration count matches file count

### Testing Process
1. ✅ **Adversarial distribution tests** - Caught this bug!
2. **Integration test:** Run actual `spec-kitty upgrade`, check registered migrations
3. **Discovery test:** List all migration files, verify all are in registry

## Suggested Improvements

### Immediate Fix (0.13.2)
```python
# src/specify_cli/upgrade/migrations/__init__.py

# Add missing imports:
from . import m_0_13_0_research_csv_schema_check
from . import m_0_13_0_update_constitution_templates
from . import m_0_13_0_update_research_implement_templates
from . import m_0_13_1_exclude_worktrees  # ← ADD THIS

__all__ = [
    # ... existing ...
    "m_0_12_1_remove_kitty_specs_from_gitignore",
    "m_0_13_0_research_csv_schema_check",  # ← ADD THIS
    "m_0_13_0_update_constitution_templates",  # ← ADD THIS
    "m_0_13_0_update_research_implement_templates",  # ← ADD THIS
    "m_0_13_1_exclude_worktrees",  # ← ADD THIS
]
```

### Process Improvements
1. **Add CI check:** Verify all m_*.py files are imported in __init__.py
2. **Add registry test:** Assert len(registry) == len(migration_files)
3. **Add documentation:** Migration creation checklist
4. **Add linter:** Detect migration files not in __init__.py

## Related Files

### Bug Location
- `src/specify_cli/upgrade/migrations/__init__.py:1-65` - Missing imports
- `src/specify_cli/upgrade/migrations/m_0_13_1_exclude_worktrees.py` - Orphaned migration
- `src/specify_cli/upgrade/migrations/m_0_13_0_*.py` - Also orphaned (3 files!)

### Adversarial Test That Found It
- `tests/distribution/test_worktree_git_exclusion.py:test_upgrade_adds_exclusion_to_existing_project`

### Spec-Kitty Implementation
- Commit b2d9b00: Added migration file
- Commit b2d9b00: **Forgot to update __init__.py**

## Example Output/Reproduction

### Reproduce the Bug
```bash
# Setup
cd ~/Code/spec-kitty
pip install -e .

# Check registry
python -c "
from specify_cli.upgrade.registry import MigrationRegistry
migrations = MigrationRegistry.get_all()
print('Total:', len(migrations))
print('Has 0.13.1_exclude_worktrees:',
      '0.13.1_exclude_worktrees' in [m.migration_id for m in migrations])
"

# Output:
# Total: 27
# Has 0.13.1_exclude_worktrees: False  ← BUG!
```

### Verify Migration Works When Imported
```bash
python -c "
# Import migration directly (triggers registration)
import specify_cli.upgrade.migrations.m_0_13_1_exclude_worktrees

from specify_cli.upgrade.registry import MigrationRegistry
migrations = MigrationRegistry.get_all()
print('After direct import:', len(migrations))
print('Has 0.13.1_exclude_worktrees:',
      '0.13.1_exclude_worktrees' in [m.migration_id for m in migrations])
"

# Output:
# After direct import: 28
# Has 0.13.1_exclude_worktrees: True  ← Works when imported!
```

### Test Upgrade (Shows Bug)
```bash
# Create test project at version 0.12.0
mkdir test_upgrade && cd test_upgrade
git init
mkdir .kittify
echo "spec_kitty:
  version: '0.12.0'
  initialized_at: '2026-01-01T00:00:00'" > .kittify/metadata.yaml

# Run upgrade
spec-kitty upgrade --force

# Check if .worktrees/ was added
cat .git/info/exclude | grep ".worktrees"
# Output: (empty) ← BUG: Migration didn't run!
```

## Additional Discovery

### Other Orphaned Migrations
The __init__.py is also missing imports for **THREE 0.13.0 migrations**:
- `m_0_13_0_research_csv_schema_check.py`
- `m_0_13_0_update_constitution_templates.py`
- `m_0_13_0_update_research_implement_templates.py`

**Total Orphaned:** 4 migrations (3 from 0.13.0 + 1 from 0.13.1)

These migrations exist, are committed, but will **NEVER RUN** because they're
not imported.

## Validation

### Adversarial Test Results
```bash
$ pytest tests/distribution/test_worktree_git_exclusion.py::TestMigrationAddsExclusion -v

FAILED test_upgrade_adds_exclusion_to_existing_project
  AssertionError: BUG: Migration didn't add .worktrees/ exclusion!

✓ Adversarial test successfully detected the bug before release
```

### After Fix (Expected)
Once imports are added to __init__.py:
```bash
$ pytest tests/distribution/test_worktree_git_exclusion.py::TestMigrationAddsExclusion -v

PASSED test_upgrade_adds_exclusion_to_existing_project ✓
```

---

**Notes:**

This is a **perfect example** of why adversarial distribution testing is critical:

- **Implementing team's tests:** Call migration directly → Tests pass ✓
- **Adversarial tests:** Use actual `spec-kitty upgrade` command → Bug found ✗

The dual testing strategy (unit tests + distribution tests) provides complete
coverage and prevents bugs like this from shipping to users.

**Status:** 🚨 BLOCKING BUG - Must fix before 0.13.2 release
