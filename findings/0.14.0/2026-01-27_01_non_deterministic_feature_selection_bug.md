# Non-Deterministic Feature Selection Bug

**Date:** 2026-01-27
**Session ID:** feature-detection-refactor-validation
**Tested by:** Claude Sonnet 4.5
**Category:** Bug Report, Testing
**Spec-Kitty Version:** 0.13.7 (baseline) | main branch 89a3ca0 (partial fix)
**Analysis Date:** 2026-01-27
**Applies To:** spec-kitty ≤0.13.7, partially addressed in main branch

## Summary

When multiple features exist in kitty-specs/, commands like /spec-kitty.plan non-deterministically select the "highest numbered" feature instead of the intended one, causing agents to overwrite the wrong feature's plan.md.

## Observation

**Scenario Observed:**
1. User creates `020-feature-a` (no plan.md yet - wants to create it)
2. User creates `021-feature-b` (already has plan.md)
3. Agent runs `/spec-kitty.plan` expecting to work on feature 020
4. CLI auto-selects feature `021-feature-b` (highest number)
5. Agent creates/overwrites plan.md for wrong feature

**What Happened:**
The command used a "highest numbered" fallback heuristic when multiple features existed and no explicit feature was specified. This is non-deterministic from the user's perspective - they created 020 intending to work on it, but the system selected 021 arbitrarily.

**Testing Revealed:**
- Current code (0.13.7): 10 different implementations of feature detection
- Partial fix (main): Centralized module created, but migration 40% complete
- 6 orphaned functions still exist that may use old logic

## Impact

- **Severity:** High - Data corruption (wrong feature modified)
- **Scope:** All users with multi-feature repositories, especially LLM agents
- **Frequency:** Happens always when multiple features exist and no context provided

**User Impact:**
- Agents overwrite wrong feature's plan.md
- Manual recovery required (git revert)
- Loss of work if not caught immediately
- Confusion about which feature is "active"

**Agent Impact:**
- Templates don't guide agents to specify feature explicitly
- Agents unaware of multi-feature ambiguity
- No error message to guide correct behavior
- Silent wrong selection (no warning)

## Root Cause Analysis

**Systematic Problem:**
The codebase has 10 different implementations of feature detection scattered across multiple modules:

```
1. detect_feature_slug() in acceptance.py:226
2. detect_feature_slug() in scripts/tasks/acceptance_support.py:230 (DUPLICATE)
3. _detect_current_feature() in mission.py:159
4. detect_feature_context() in implement.py:40
5. find_feature_slug() in core/paths.py:192
6. _find_feature_slug() in agent/workflow.py:60
7. _find_feature_slug() in agent/tasks.py:41 (DUPLICATE)
8. detect_current_feature() in orchestrate.py:101
9. _find_feature_directory() in agent/context.py:31
10. _find_feature_directory() in agent/feature.py:104 (DUPLICATE NAME)
```

**Key Problems:**
- 3 pairs of exact duplicates (identical code in different files)
- 4 functions use non-deterministic heuristics (highest numbered, most recently modified)
- Inconsistent return types (str vs Path vs tuple vs Optional)
- Inconsistent error handling (raise vs return None vs typer.Exit)
- No single source of truth
- LLMs must "figure out" which function to use - undiscoverable, error-prone

**Specific Heuristics Found:**
```python
# core/paths.py - "highest numbered" selection
max_num = max(feature_numbers)
return f"{max_num:03d}-{feature_name}"

# orchestrate.py - "most recently modified" selection
sorted_worktrees = sorted(worktrees, key=lambda w: w.stat().st_mtime, reverse=True)
return sorted_worktrees[0]
```

**Why This Happens:**
Each module implemented its own detection logic independently, without coordination.
Over time, different heuristics emerged, creating inconsistent behavior.

## User/Agent Journey

**Human User Journey:**
1. Create new feature: `spec-kitty specify 020-new-api`
2. Create another feature: `spec-kitty specify 021-refactor-db`
3. Work on 020: `cd kitty-specs/020-new-api`
4. Run planning: `/spec-kitty.plan` (in feature directory)
5. **BUG:** Command selects 021 instead of 020 (highest number)
6. **Result:** plan.md created in wrong feature

**LLM Agent Journey:**
1. User says: "Create plan for the new API feature (020)"
2. Agent runs: `spec-kitty agent feature setup-plan` (no --feature flag)
3. **BUG:** CLI selects 021-refactor-db (highest numbered)
4. Agent receives success response
5. Agent believes it created plan for 020
6. **Result:** plan.md created in wrong feature, agent unaware

## What Could Have Helped

**For Discovery:**
- **Clear documentation** about feature detection priority order
- **Warning message** when multiple features exist
- **Require --feature flag** when ambiguous (instead of guessing)
- **Test coverage** for multi-feature scenarios (was missing)

**For Users:**
- **Error message listing** all available features
- **Example command** showing how to use --feature flag
- **Context detection debug** mode (show which feature was detected and why)

**For Agents:**
- **Template instructions** to detect feature from context (branch, cwd)
- **Explicit --feature usage** in template examples
- **Error handling** in template for ambiguous cases
- **Validation** that correct feature was selected

**For Developers:**
- **Single source of truth** - one canonical implementation
- **Import guidelines** - always use centralized module
- **Code review checks** - reject new detection implementations
- **Test requirements** - multi-feature scenarios mandatory

## Suggested Improvements

**1. Centralized Feature Detection Module (IN PROGRESS)**
```python
# Create: src/specify_cli/core/feature_detection.py
# Status: ✅ Created (493 lines)

from specify_cli.core.feature_detection import detect_feature

# Priority order:
# 1. Explicit --feature parameter
# 2. SPECIFY_FEATURE env var
# 3. Git branch name
# 4. Current directory path
# 5. Single feature auto-detect (only if exactly one)
# 6. Error with guidance (if ambiguous)
```

**2. Remove All Duplicate Implementations (PARTIAL)**
- Status: 4/10 migrated, 6/10 orphaned functions remain
- Action: Delete remaining 6 functions, use centralized module

**3. Update CLI Commands (PARTIAL)**
- Add --feature parameter to all commands
- Status: Some commands have it, some don't
- Action: Ensure all commands accept --feature

**4. Update Agent Templates (NOT DONE)**
- Source template: ✅ Updated
- Agent templates: ❌ 11/12 not regenerated
- Action: Run migration to regenerate all templates

**5. Improve Error Messages (PARTIAL)**
- Status: Some commands error, but messages inconsistent
- Action: Standardize error format, list available features

**6. Add Multi-Feature Tests (DONE)**
- Status: ✅ 33 tests created
- Coverage: Core logic, migration, E2E scenarios

## Related Files

**Core Implementation:**
- `src/specify_cli/core/feature_detection.py` - Centralized module (NEW)
- `src/specify_cli/core/paths.py:192` - Old find_feature_slug() (DELETE)

**CLI Commands:**
- `src/specify_cli/cli/commands/agent/feature.py:109` - Orphaned _find_feature_directory()
- `src/specify_cli/cli/commands/agent/context.py:31` - Duplicate _find_feature_directory()
- `src/specify_cli/cli/commands/agent/workflow.py:60` - Orphaned _find_feature_slug()
- `src/specify_cli/cli/commands/agent/tasks.py:41` - Duplicate _find_feature_slug()
- `src/specify_cli/cli/commands/orchestrate.py:105` - Orphaned detect_current_feature()
- `src/specify_cli/cli/commands/mission.py:163` - Orphaned _detect_current_feature()

**Templates:**
- `src/specify_cli/missions/software-dev/command-templates/plan.md` - Source template (UPDATED)
- `.claude/commands/spec-kitty.plan.md` - Agent template (needs regeneration)
- 11 other agent template copies (need regeneration)

**Tests:**
- `tests/distribution/test_feature_detection_refactor.py` - Core logic tests
- `tests/distribution/test_feature_detection_migration.py` - Migration validation
- `tests/distribution/test_feature_detection_e2e.py` - End-to-end scenarios

## Example Output/Reproduction

**Reproduce the Bug (0.13.7):**

```bash
# Setup: Create two features
mkdir -p kitty-specs/020-feature-a
mkdir -p kitty-specs/021-feature-b
echo '{"feature_id": "020-feature-a"}' > kitty-specs/020-feature-a/meta.json
echo '{"feature_id": "021-feature-b"}' > kitty-specs/021-feature-b/meta.json

# Create plan.md in 021 (already planned)
echo "# Plan B" > kitty-specs/021-feature-b/plan.md

# From main branch, try to plan feature 020
git checkout main
spec-kitty agent feature setup-plan --json

# BUG: Selects 021-feature-b (highest numbered) instead of erroring
# Expected: Error "Multiple features found: 020-feature-a, 021-feature-b. Use --feature flag"
# Actual: Creates/modifies plan.md in 021-feature-b
```

**Test Reproduction:**

```python
def test_multiple_features_no_auto_select_highest():
    # Create 020 (no plan) and 021 (has plan)
    feature_020.mkdir()
    feature_021.mkdir()
    (feature_021 / "plan.md").write_text("Existing plan")

    # Run without --feature
    result = subprocess.run(["spec-kitty", "agent", "feature", "setup-plan", "--json"])

    # Should ERROR, not auto-select 021
    assert result.returncode != 0, "Should error when ambiguous"
    assert "021-feature-b" not in (feature_021 / "plan.md").read_text(), \
        "Should NOT modify wrong feature"
```

**Current Test Results:**
```
Test: test_multiple_features_no_auto_select_highest
Status: ❌ FAILING (command errors but test assertion issue)
Issue: Test checks stderr, but JSON errors in stdout
```

---

## Notes

**Implementation Progress:**
- Core module created (feature_detection.py)
- 40% migration complete (4/10 functions)
- Source template updated
- 16/33 tests passing (48%)

**Remaining Work:**
- Complete migration (6 orphaned functions)
- Regenerate agent templates (11/12)
- Fix detection edge cases
- Achieve 100% test pass rate

**Test Suite Effectiveness:**
Created 33 adversarial tests that:
- ✅ Reproduce the exact bug scenario
- ✅ Validate migration completeness
- ✅ Catch orphaned code
- ✅ Test all detection methods
- ✅ Guide implementation to completion

**Estimated Time to Fix:** 3-4 hours additional work
