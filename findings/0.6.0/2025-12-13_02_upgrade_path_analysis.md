# Upgrade Path Analysis: commands/ → command-templates/

**Date:** 2025-12-13
**Category:** Feature Analysis
**Status:** Testing

## Summary

Analyzing real-world upgrade scenario from agentfunc project which has doubled slash commands in Claude due to old project structure.

## Current State (Old Versions)

### agentfunc Structure (v0.5.x or earlier)

**WRONG - Has template pollution:**
```
.kittify/
├── templates/               ← Should NOT be in user projects!
│   ├── commands/            ← Old name, contains 13 command templates
│   └── git-hooks/           ← Template source files
├── missions/
│   └── research/
│       └── commands/        ← Old name, contains 4 mission commands
├── memory/
│   └── constitution.md
└── scripts/
```

**Problem:** Users have template SOURCE files (`.kittify/templates/`) that should only exist in the spec-kitty repo.

**Impact:**
- Unnecessary files in user projects
- Potential for confusion (editing templates vs rendered commands)
- If both `commands/` and `command-templates/` exist, potential for duplicates

## Desired State (v0.6.0+)

### Clean User Project Structure

**CORRECT - No template pollution:**
```
.kittify/
├── missions/
│   ├── research/
│   │   └── command-templates/   ← New name
│   └── software-dev/
│       └── command-templates/   ← New name
├── memory/
│   └── constitution.md
└── scripts/
    └── bash/
        └── create-new-feature.sh
```

**NO `.kittify/templates/` in user projects!**

Commands are rendered to:
```
.claude/commands/
├── spec-kitty.plan.md
├── spec-kitty.specify.md
└── ... (13 total)
```

## Upgrade Scenarios

### Scenario 1: Fresh Install (v0.6.0+)
- ✅ No `.kittify/templates/` directory
- ✅ Only `.kittify/missions/*/command-templates/`
- ✅ Clean structure from day one

### Scenario 2: Existing Project (Old → New)

**Before Upgrade:**
```
.kittify/templates/commands/        ← Old structure, shouldn't exist
.kittify/missions/*/commands/       ← Old name
```

**After Upgrade:**
```
.kittify/missions/*/command-templates/   ← New name
# NO .kittify/templates/!
```

**What Needs to Happen:**
1. Remove `.kittify/templates/` from user projects (cleanup)
2. Rename `.kittify/missions/*/commands/` → `.kittify/missions/*/command-templates/`
3. Preserve user data (memory/, kitty-specs/)

### Scenario 3: Mixed Structure (Partial Upgrade)

**Dangerous State:**
```
.kittify/templates/commands/            ← Old
.kittify/templates/command-templates/   ← New (if somehow both exist)
.kittify/missions/*/commands/           ← Old
.kittify/missions/*/command-templates/  ← New
```

**Risk:** Commands discovered from BOTH locations = duplicates in Claude

**Mitigation:**
- Command discovery should prefer `command-templates/` over `commands/`
- Old structure should be automatically removed
- If both exist, warn user and use only new structure

## Test Coverage Needed

### ✅ Implemented Tests (13 tests)

1. **Old Structure Tests (2)**
   - Old structure still works (if user hasn't upgraded)
   - No duplicates with old structure alone

2. **Mixed Structure Tests (3)**
   - Both structures can coexist temporarily
   - New structure takes precedence
   - No duplicate command discovery

3. **Migration Path Tests (2)**
   - Upgrade from old version preserves functionality
   - Old directories can be safely removed

4. **Clean Upgrade Tests (4)**
   - Upgrade removes old structure
   - No cruft files left behind
   - Final state matches fresh install
   - User data preserved during upgrade

5. **Real-World Tests (2)**
   - Replicate agentfunc structure
   - Verify no doubled commands

### Current Test Results

**8 passed, 5 failed (commit af680bd)**

**Failures indicate:**
- `.kittify/templates/` is correctly NOT being created in new projects ✅
- Tests were incorrectly expecting this directory to exist
- Need to update tests to reflect CORRECT behavior

## Expected vs Actual Behavior

### What We Expected (WRONG)
```
User projects have .kittify/templates/command-templates/
```

### What Actually Happens (CORRECT)
```
User projects have ONLY .kittify/missions/*/command-templates/
NO .kittify/templates/ at all!
```

This is actually the DESIRED state! The bug we're fixing is that OLD versions incorrectly copied `.kittify/templates/` to user projects.

## Upgrade Strategy

### For Existing Projects (like agentfunc)

**Manual Cleanup:**
```bash
# 1. Remove template pollution
rm -rf .kittify/templates/

# 2. Rename old command directories in missions
cd .kittify/missions
for mission in */; do
    if [ -d "$mission/commands" ]; then
        mv "$mission/commands" "$mission/command-templates"
    fi
done

# 3. Verify cleanup
# Should NOT exist:
ls .kittify/templates/  # Error: No such directory (good!)

# Should exist:
ls .kittify/missions/*/command-templates/  # Lists mission commands (good!)
```

**Automatic Cleanup (Future Feature):**
- spec-kitty could detect old structure on next command
- Offer to migrate: `spec-kitty migrate-structure`
- Preserve user customizations, remove template cruft

### For New Projects

No migration needed - clean structure from init.

## Risks & Mitigation

### Risk 1: User Edited Template Files
**Problem:** User customized `.kittify/templates/commands/plan.md` directly
**Mitigation:**
- Detect modifications before removing
- Warn user to move customizations to mission-specific commands
- Provide migration guide

### Risk 2: Scripts Referencing Old Paths
**Problem:** User scripts reference `.kittify/templates/commands/`
**Mitigation:**
- Check for references before cleanup
- Provide list of files that need updating
- Deprecation warning period

### Risk 3: Version Mismatch
**Problem:** Old spec-kitty CLI with new project structure
**Mitigation:**
- Backward compatibility: Old CLI can still read new structure
- Version detection in projects
- Clear error messages

## Testing Strategy

### Phase 1: Validate Current Implementation ✅
- [x] Create upgrade path tests (13 tests)
- [x] Run tests on commit af680bd
- [x] Document expected vs actual behavior

### Phase 2: Fix Test Expectations
- [ ] Update tests to expect NO `.kittify/templates/` in user projects
- [ ] Tests should verify cleanup happens correctly
- [ ] All 13 tests should pass

### Phase 3: Real-World Validation
- [ ] Test on actual agentfunc project
- [ ] Verify no doubled commands after cleanup
- [ ] Confirm user data preserved

## Next Steps

1. **Update Tests:** Modify upgrade tests to reflect correct expectations
2. **Document Migration:** Create user-facing migration guide
3. **Test on agentfunc:** Apply cleanup and verify results
4. **Create Migration Tool:** `spec-kitty migrate` command for automatic upgrade

## Related Files

**Test File:** `tests/functional/test_upgrade_path_commands_rename.py`
**Real Project:** `~/Code/agentfunc` (has old structure)
**Spec-Kitty Repo:** `~/Code/spec-kitty` (has correct templates/)

---

**Status:** 🟡 Tests Need Updates
**Blocker:** Test expectations don't match correct behavior
**Fix:** Update tests to expect NO `.kittify/templates/` in user projects
