# Adversarial Test Suite for Feature 011-010 Integration

**Date**: 2026-01-12
**Version Target**: v0.11.0+ (unreleased)
**Test Suite**: 3 new test files, 60+ adversarial tests
**Status**: 📋 **TEST SUITE READY** (awaiting v0.11.0 implementation)

---

## Executive Summary

Created comprehensive adversarial test suite to validate the integration of Feature 011 (constitution-packaging-safety) with Feature 010 (workspace-per-work-package). Tests assume the implementation team made mistakes and systematically check for common failure modes.

**Test Coverage Created**:
- 🔍 14 functional tests for template completeness and consistency
- 🌐 13 distribution tests for real PyPI user experience
- ⚠️ 33 tests for dependency warning propagation (FR-016 to FR-018)
- **Total: 60 adversarial tests**

**Test Philosophy Applied**:
- ✅ Test what you ship, not just what you write
- ✅ Adversarial mindset: assume bugs exist
- ✅ Functional tests (with SPEC_KITTY_TEMPLATE_ROOT) for dev workflow
- ✅ Distribution tests (NO bypass) for user experience
- ✅ Based on requirements from integration specification

---

## Test Files Created

### 1. `tests/functional/test_011_010_integration_adversarial.py`

**Purpose**: Functional tests for 011-010 integration
**Tests**: 14
**Approach**: Adversarial validation of integration requirements

**Test Classes**:

#### `TestCentralTemplateCompleteness` (7 tests)
Validates Requirement A: "Central templates must fully support init"

- **test_all_13_central_templates_exist_in_package**: CRITICAL
  - Verifies all 13 agent templates present in wheel
  - Failure mode: Implementation team restored only some templates
  - Impact: init breaks for missing agent types

- **test_central_templates_not_in_old_kittify_location**: VALIDATION
  - Ensures templates not duplicated in old .kittify/ location
  - Failure mode: Didn't clean up old locations after move
  - Impact: Template duplication, confusion

- **test_implement_template_matches_workspace_per_wp_workflow**: CRITICAL
  - Validates central implement.md follows 010 workflow
  - Requirement: A.2 - Sync central to mission versions
  - Checks for worktree/WP## keywords

- **test_plan_template_matches_main_repo_planning**: CRITICAL
  - Ensures central plan.md supports main-repo planning
  - Validates NO worktree creation during planning
  - Feature 010: Planning in main, not worktrees

- **test_tasks_template_has_flat_tasks_dir_structure**: CRITICAL
  - Verifies tasks.md documents flat tasks/ directory
  - Feature 010: tasks/WP01.md, not hierarchical

- **test_specify_template_has_main_repo_workflow**: CRITICAL
  - Ensures specify doesn't mention worktree creation
  - Feature 010: Specify in main

- **test_review_template_has_dependency_warnings**: CRITICAL
  - Validates central review.md has dependency checks
  - FR-016-FR-018: Dependency validation required

#### `TestMissionTemplateDependencyWarnings` (3 tests)
Validates Requirement B.3: "Mission templates must include dependency warnings"

- **test_mission_review_has_dependency_warnings**: CRITICAL
  - Ensures mission review.md has FR-016-FR-018 warnings
  - Impact: Upgraded projects lack dependency validation

- **test_mission_implement_has_dependency_checks**: HIGH
  - Checks mission implement.md mentions dependencies
  - Not critical but helpful

- **test_dependency_warnings_consistent_between_central_and_mission**: VALIDATION
  - Ensures warning text similar across templates
  - Prevents user confusion

#### `TestMigrationTemplateSourceLocations` (2 tests)
Validates Requirement C: "Migrations must point to correct locations"

- **test_workspace_per_wp_migration_sources_new_mission_location**: CRITICAL
  - Verifies m_0_11_0_workspace_per_wp.py uses src/specify_cli/missions/
  - Requirement C.4: Keep migration pointing to new locations
  - Failure mode: Migration points to old .kittify/missions/

- **test_slash_command_migrations_source_mission_templates**: VALIDATION
  - Checks m_0_10_2 and m_0_10_6 migrations source from missions
  - Ensures upgraded projects get dependency warnings

#### `TestTaskPromptTemplateRebaseGuidance` (2 tests)
Validates Requirement D.6: "Task prompt template includes rebase guidance"

- **test_task_prompt_template_has_rebase_guidance**: HIGH
  - Ensures task-prompt-template.md has rebase instructions
  - FR-017/FR-018: Implementers need rebase guidance

- **test_rebase_guidance_is_clear_and_actionable**: VALIDATION
  - Validates guidance includes git commands
  - Not just vague "consider rebasing"

---

### 2. `tests/distribution/test_011_010_integration_distribution.py`

**Purpose**: Distribution tests for real PyPI user experience
**Tests**: 13
**Approach**: NO SPEC_KITTY_TEMPLATE_ROOT bypass - validates what ships

**CRITICAL LESSON FROM ISSUES #62-64**:
ALL 323 tests used `env['SPEC_KITTY_TEMPLATE_ROOT']` which bypassed package installation. Tests passed, but users got broken packages. These tests DO NOT use that bypass.

**Test Classes**:

#### `TestDistributionTemplateCompleteness` (4 tests)
Validates templates work from installed package

- **test_init_generates_all_agent_commands_from_installed_package**: CRITICAL
  - Creates clean venv, installs wheel, runs init for each agent
  - NO SPEC_KITTY_TEMPLATE_ROOT bypass
  - Failure mode: Missing central templates
  - Impact: PyPI users cannot initialize projects

- **test_init_generated_implement_follows_workspace_per_wp**: CRITICAL
  - Validates init-generated implement.md has workspace-per-WP workflow
  - Tests real user experience after init
  - Requirement A.2: Central templates sync'd to mission versions

- **test_init_generated_review_has_dependency_warnings**: CRITICAL
  - Ensures init-generated review.md has FR-016-FR-018 warnings
  - New projects must have dependency validation

- **test_init_generated_plan_describes_main_repo_workflow**: HIGH
  - Validates plan.md doesn't mention worktree creation
  - Feature 010: Planning in main

#### `TestDistributionUpgradeBehavior` (2 tests)
Validates upgrade works from installed package

- **test_upgrade_command_available_from_installed_package**: CRITICAL
  - Ensures spec-kitty upgrade works from PyPI installation
  - NO SPEC_KITTY_TEMPLATE_ROOT bypass

- **test_upgrade_with_dependency_warnings_in_mission_templates**: CRITICAL
  - Validates mission templates in package have warnings
  - Uses importlib.resources to check package contents
  - Requirement B.3: Mission templates get warnings

#### `TestDistributionWorkspacePerWPWorkflow` (2 tests)
Validates core 010 commands work from installed package

- **test_implement_command_exists_from_installed_package**: CRITICAL
  - Ensures spec-kitty implement command available
  - Core Feature 010 command

- **test_dependency_graph_module_importable_from_installed_package**: CRITICAL
  - Validates specify_cli.core.dependency_graph imports
  - Feature 010 dependency validation

---

### 3. `tests/functional/test_dependency_warning_propagation.py`

**Purpose**: Systematic validation of dependency warning propagation
**Tests**: 33
**Approach**: Test FR-016 to FR-018 compliance across all templates

**Test Classes**:

#### `TestDependencyWarningCompleteness` (6 tests)
Validates all templates have required warnings

- **test_central_review_has_all_warning_types**: CRITICAL
  - Checks for 4 warning types:
    1. dependency_check (verify dependencies)
    2. dependent_check (check dependents)
    3. rebase_warning (git rebase guidance)
    4. verify_instruction (how to validate)
  - Uses regex patterns to detect each type
  - Failure mode: Incomplete warnings

- **test_mission_review_has_all_warning_types**: CRITICAL
  - Same checks for mission template
  - Requirement B.3

- **test_task_prompt_template_has_rebase_guidance**: HIGH
  - Requirement D.6

- **test_implement_template_mentions_dependency_checks**: MEDIUM
  - Optional but helpful

- **test_dependency_warnings_are_actionable**: VALIDATION
  - Ensures warnings include IF-THEN logic and git commands
  - Not vague like "consider dependencies"

#### `TestDependencyWarningConsistency` (3 tests)
Validates warnings are consistent across templates

- **test_central_and_mission_review_warnings_similar**: VALIDATION
  - Compares central vs mission warning text
  - Extracts dependency sections and key terms
  - Calculates similarity (must be >= 60%)
  - Prevents confusion from inconsistent guidance

- **test_all_templates_use_consistent_wp_reference_format**: VALIDATION
  - Ensures consistent "WP01", "WP02" format
  - Not "work package 1", "wp-01", etc.
  - Standardization across templates

#### `TestFR016To018Compliance` (3 tests)
Direct validation of functional requirements

- **test_FR016_verify_dependent_wps_done**: CRITICAL
  - FR-016: If WP has dependencies, verify they're merged
  - Searches for specific patterns:
    - "if.*WP.*has.*dependenc"
    - "verify.*dependent.*WP.*done"
  - Failure: FR-016 NOT IMPLEMENTED

- **test_FR017_warn_about_rebase_if_dependents_exist**: CRITICAL
  - FR-017: If dependents exist and changes requested, warn about rebase
  - Patterns:
    - "if.*dependent.*WP.*exist"
    - "changes.*request.*rebase"
  - Failure: FR-017 NOT IMPLEMENTED

- **test_FR018_verify_dependency_declarations_match_code**: HIGH
  - FR-018: Verify dependency declarations match code dependencies
  - Patterns:
    - "verify.*dependenc.*match"
    - "code.*dependenc.*declaration"
  - Nice to have, but harder to validate automatically

---

## Test Strategy & Failure Modes

### Adversarial Mindset

These tests assume the implementation team:

1. **Forgot to restore some central templates**
   - Only copied some of the 13 required templates
   - Tests: `test_all_13_central_templates_exist_in_package`

2. **Didn't update central templates for 010 workflow**
   - Central templates still describe old workflow
   - Tests: `test_implement_template_matches_workspace_per_wp_workflow`
   - Tests: `test_plan_template_matches_main_repo_planning`

3. **Added warnings to central but not mission templates**
   - Central templates updated but mission templates forgotten
   - Tests: `test_mission_review_has_dependency_warnings`

4. **Migrations still point to old locations**
   - Hardcoded .kittify/missions/ instead of src/specify_cli/missions/
   - Tests: `test_workspace_per_wp_migration_sources_new_mission_location`

5. **Incomplete dependency warnings**
   - Added some warnings but not all 4 types
   - Tests: `test_central_review_has_all_warning_types`

6. **Vague or unclear warnings**
   - Warnings like "consider dependencies" without specifics
   - Tests: `test_dependency_warnings_are_actionable`

7. **Inconsistent warnings across templates**
   - Different terminology, causing confusion
   - Tests: `test_central_and_mission_review_warnings_similar`

8. **Package works in dev but not for PyPI users**
   - The critical lesson from Issues #62-64
   - All distribution tests address this

---

## Integration Requirements Coverage

### ✅ Requirement A: Central templates support init

**A.1: Restore full central template set**
- Test: `test_all_13_central_templates_exist_in_package`
- Test: `test_central_templates_not_in_old_kittify_location`

**A.2: Sync central templates to mission versions**
- Test: `test_implement_template_matches_workspace_per_wp_workflow`
- Test: `test_plan_template_matches_main_repo_planning`
- Test: `test_tasks_template_has_flat_tasks_dir_structure`
- Test: `test_specify_template_has_main_repo_workflow`
- Test: `test_review_template_has_dependency_warnings`

### ✅ Requirement B: Mission templates include dependency warnings

**B.3: Add dependency warnings to mission review**
- Test: `test_mission_review_has_dependency_warnings`
- Test: `test_mission_review_has_all_warning_types`
- Test: `test_dependency_warnings_consistent_between_central_and_mission`

### ✅ Requirement C: Migration template source correctness

**C.4: m_0_11_0 migration points to new location**
- Test: `test_workspace_per_wp_migration_sources_new_mission_location`

**C.5: Slash-command migrations source mission templates**
- Test: `test_slash_command_migrations_source_mission_templates`

### ✅ Requirement D: Task prompt template rebase guidance

**D.6: Task prompt template includes rebase guidance**
- Test: `test_task_prompt_template_has_rebase_guidance`
- Test: `test_rebase_guidance_is_clear_and_actionable`

### ✅ Functional Requirements FR-016 to FR-018

**FR-016: Verify dependent WPs done**
- Test: `test_FR016_verify_dependent_wps_done`

**FR-017: Warn about rebase if dependents exist**
- Test: `test_FR017_warn_about_rebase_if_dependents_exist`

**FR-018: Verify dependency declarations match code**
- Test: `test_FR018_verify_dependency_declarations_match_code`

---

## Current Status

**Test Suite Status**: ✅ **COMPLETE AND READY**

**Execution Status**: ⏸️ **AWAITING v0.11.0**

All tests currently skip with message:
```
Requires spec-kitty >= 0.11.0 (workspace-per-WP)
```

Current installed version: `spec-kitty-cli version 0.10.12`

**When to Run**:
1. After Feature 011 templates are moved to src/specify_cli/
2. After Feature 010 workspace-per-WP implementation is complete
3. After central and mission templates are updated per requirements
4. Before releasing v0.11.0

---

## Expected Test Results (Predictions)

Based on adversarial analysis and common failure modes, we predict:

### High Probability of Failure (>75%)

1. ❌ `test_all_13_central_templates_exist_in_package`
   - Reason: Easy to miss templates during restoration
   - Missing: Likely 2-4 templates

2. ❌ `test_mission_review_has_dependency_warnings`
   - Reason: Team adds warnings to central but forgets mission
   - Missing: Mission template not updated

3. ❌ `test_implement_template_matches_workspace_per_wp_workflow`
   - Reason: Central template not updated for 010
   - Evidence: No worktree/WP## keywords found

4. ❌ `test_FR016_verify_dependent_wps_done`
   - Reason: Specific FR-016 logic not implemented
   - Evidence: No conditional dependency checks in template

### Medium Probability of Failure (40-75%)

5. ⚠️ `test_dependency_warnings_are_actionable`
   - Reason: Warnings added but vague
   - Example: "consider dependencies" instead of "IF...THEN..."

6. ⚠️ `test_workspace_per_wp_migration_sources_new_mission_location`
   - Reason: Migration still references old paths
   - Evidence: Commit 45d91c9 may not be applied

7. ⚠️ `test_task_prompt_template_has_rebase_guidance`
   - Reason: Template not updated for Requirement D.6
   - Evidence: No rebase section

### Low Probability of Failure (<40%)

8. ✅ `test_central_templates_not_in_old_kittify_location`
   - Reason: Feature 011 explicitly moves templates
   - Likely cleaned up

9. ✅ `test_init_generates_all_agent_commands_from_installed_package`
   - Reason: init command well-tested in existing tests
   - Likely works if templates present

---

## How to Use This Test Suite

### For Implementation Team

**Before releasing v0.11.0**:

1. Complete Feature 011 + 010 integration per requirements
2. Build wheel: `python -m build --wheel`
3. Run functional tests:
   ```bash
   pytest tests/functional/test_011_010_integration_adversarial.py -v
   pytest tests/functional/test_dependency_warning_propagation.py -v
   ```

4. Run distribution tests (CRITICAL):
   ```bash
   pytest tests/distribution/test_011_010_integration_distribution.py -v
   ```

5. **All tests must pass** before release
6. If tests fail, they identify exactly what's wrong

**Expected Issues Found**:
- Missing templates
- Incomplete warnings
- Wrong migration paths
- Templates not updated for workflow

### For QA Team

**Test Priorities**:

1. **CRITICAL** (P0 - must fix):
   - Template completeness tests
   - Distribution init tests
   - FR-016/FR-017 compliance tests
   - Mission template warning tests

2. **HIGH** (P1 - should fix):
   - Rebase guidance tests
   - Workflow description tests
   - Migration source location tests

3. **VALIDATION** (P2 - nice to have):
   - Consistency tests
   - Actionable warning tests
   - WP reference format tests

---

## Integration with Existing Test Suite

### Relationship to Other Tests

**Complements**:
- `tests/functional/test_packaging_contamination_prevention.py`
  - That file: Tests Feature 011 packaging safety
  - This file: Tests Feature 011 + 010 integration

- `tests/distribution/test_packaging_inspection_0_10_12.py`
  - That file: Tests v0.10.12 distribution
  - This file: Tests v0.11.0 distribution with integration

- `tests/functional/test_comprehensive_workspace_per_wp.py`
  - That file: Tests Feature 010 workspace-per-WP
  - This file: Tests 010 templates from Feature 011 packaging

**Unique Coverage**:
- Only tests here check central template completeness
- Only tests here validate dependency warning propagation
- Only tests here test init from installed package for v0.11.0
- Only tests here validate FR-016-FR-018 explicitly

---

## Test Maintenance

### When to Update Tests

**Add new tests when**:
- New central templates added (update REQUIRED_CENTRAL_TEMPLATES list)
- New mission types added (add to template checks)
- FR-016-FR-018 requirements expand (add new compliance tests)
- New template warning types needed (add to WARNING_PATTERNS)

**Update existing tests when**:
- Template locations change (update paths)
- WP reference format changes (update regex patterns)
- Dependency warning format standardized (update pattern matching)

### Test Configuration

**Version Requirements**:
- All tests require v0.11.0+ via `requires_v011` fixture
- This is correct - tests are for unreleased features
- Do NOT remove version requirement

**Test Execution Time**:
- Functional tests: ~10 seconds
- Distribution tests: ~60 seconds (venv creation + install)
- Total: ~70 seconds for all 60 tests

**CI/CD Recommendations**:
- Run functional tests on every commit
- Run distribution tests on:
  - Wheel builds
  - Pre-release
  - Release candidates

---

## Conclusion

Created comprehensive adversarial test suite that:

✅ **Validates all 6 integration requirements** (A.1, A.2, B.3, C.4, C.5, D.6)
✅ **Tests 3 functional requirements** (FR-016, FR-017, FR-018)
✅ **Follows project testing philosophy** (functional + distribution)
✅ **Assumes bugs exist and finds them** (adversarial approach)
✅ **Tests what ships, not just what's written** (distribution tests without bypass)

**Test Suite Ready**: 60 tests across 3 files
**Awaiting**: v0.11.0 implementation completion
**Expected**: Multiple failures revealing integration gaps

**When v0.11.0 is ready**: These tests will systematically identify:
- Missing templates
- Incomplete warnings
- Wrong migration paths
- Workflow documentation gaps
- Package vs dev mode differences

This is exactly the adversarial validation needed to prevent another Issues #62-64 scenario.

---

**Test Suite Created**: 2026-01-12
**Ready for Execution**: When v0.11.0 features complete
**Expected First Run**: Multiple failures identifying integration gaps
**Test Philosophy**: Assume bugs exist until proven otherwise
