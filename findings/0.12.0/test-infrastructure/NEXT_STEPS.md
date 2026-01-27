# Next Steps for v0.12.0 Testing

**Date**: 2026-01-13
**Current Status**: Test plan complete, critical gaps identified
**Blocking Release**: YES - 96 critical tests missing

---

## Immediate Actions Required

### 1. Sparse-Checkout Infrastructure Tests (HIGHEST PRIORITY)

**Why**: Foundation of workspace-per-WP has ZERO test coverage
**Risk**: Silent failures, state divergence, data loss
**Blocking**: YES

**File**: `tests/functional/test_sparse_checkout_infrastructure.py`
**Status**: Structure created with 46 test skeletons
**Progress**: 2/46 tests implemented

**Tasks**:
- [x] Create test file structure
- [x] Implement first 2 tests (scaffold validation)
- [ ] Implement remaining 44 tests
- [ ] Fix test infrastructure (conftest.py fixtures for v0.12.0)
- [ ] Run full sparse-checkout test suite
- [ ] Verify all 46 tests pass

**Estimate**: 6-8 hours

**Implementation order**:
1. Test Suite 1: Worktree Creation (8 tests) - Basic functionality
2. Test Suite 3: Auto-Commit (10 tests) - Core synchronization
3. Test Suite 2: Path Resolution (6 tests) - Agent integration
4. Test Suite 4: Multi-Agent (8 tests) - Parallel development
5. Test Suite 5: Clean Merge (6 tests) - Git integration
6. Test Suite 6: Edge Cases (8 tests) - Error handling

### 2. Documentation Mission Distribution Tests (HIGH PRIORITY)

**Why**: Prevent repeat of Issues #62-64 (100% of PyPI users affected)
**Risk**: Template packaging bugs shipping to all users
**Blocking**: YES

**Files to create**:
- `tests/distribution/test_documentation_mission_distribution.py`
- `tests/distribution/test_doc_generators_distribution.py`
- `tests/distribution/test_documentation_mission_migration_distribution.py`
- `tests/functional/test_documentation_mission_end_to_end.py`

**Tasks**:
- [ ] Port unit tests from spec-kitty repo to distribution tests
- [ ] Ensure NO SPEC_KITTY_TEMPLATE_ROOT bypass
- [ ] Test pip-installed package, not dev environment
- [ ] Validate all command templates accessible
- [ ] Test generator detection (JSDoc, Sphinx, rustdoc)
- [ ] Run full documentation mission workflow

**Estimate**: 5-7 hours

### 3. Regression Testing (BLOCKING)

**Why**: Ensure v0.11.0→v0.12.0 upgrade doesn't break existing features
**Risk**: Breaking changes for existing users
**Blocking**: YES

**Tasks**:
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Identify failures caused by v0.12.0 changes
- [ ] Fix broken tests (template relocations, API changes)
- [ ] Document expected failures in findings/
- [ ] Achieve ≥95% pass rate

**Estimate**: 2-4 hours

---

## Post-Release Improvements (v0.12.1)

### 4. Workflow Improvements Tests

**Files to create**:
- `tests/functional/test_workflow_instructions_at_end.py`
- `tests/functional/test_review_feedback_automation.py`
- `tests/functional/test_agent_ownership_tracking.py`

**Estimate**: 2-3 hours

### 5. Migration Tests

**Files to create**:
- `tests/test_upgrade/test_migrations/test_m_0_12_0_documentation_mission.py`

**Estimate**: 2 hours

### 6. Cross-Platform Tests

**File to create**:
- `tests/functional/test_sparse_checkout_cross_platform.py`

**Estimate**: 1-2 hours

---

## Test Implementation Guide

### Running Tests

```bash
# Activate virtual environment
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate

# Verify spec-kitty version
spec-kitty --version
# Should show: spec-kitty-cli version 0.11.0

# Run specific test file
pytest tests/functional/test_sparse_checkout_infrastructure.py -v

# Run with verbose output and stop on first failure
pytest tests/functional/test_sparse_checkout_infrastructure.py -xvs

# Run only non-skipped tests
pytest tests/functional/test_sparse_checkout_infrastructure.py -v --ignore-skip

# Run all tests
pytest tests/ -v

# Run only distribution tests (critical for release)
pytest tests/distribution/ -v

# Run new tests only
pytest tests/ -v -k "sparse_checkout or documentation_mission"
```

### Test Implementation Pattern

Look at existing tests for patterns:
- `tests/functional/test_comprehensive_workspace_per_wp.py` - Workspace-per-WP examples
- `tests/distribution/test_workspace_per_wp_distribution.py` - Distribution testing pattern
- `tests/functional/test_planning_artifacts_auto_commit.py` - Auto-commit examples

Key fixtures:
- `spec_kitty_repo_root` - Path to spec-kitty source
- `temp_project_dir` - Temporary test directory
- `init_spec_kitty_project` - Initialize spec-kitty project
- `requires_v011` - Skip if spec-kitty < 0.11.0

### Common Issues

**Issue**: Tests fail with "spec-kitty init failed"
**Fix**: Check if using correct init syntax for v0.12.0 (no --mission flag)

**Issue**: Template files not found
**Fix**: Ensure SPEC_KITTY_TEMPLATE_ROOT set correctly (functional tests) or NOT set (distribution tests)

**Issue**: Git errors in tests
**Fix**: Ensure git user.name and user.email configured in test setup

**Issue**: Permission errors
**Fix**: Tests should use tmp_path fixture for isolated test directories

---

## Success Criteria

### For v0.12.0 Release

✅ **Sparse-checkout tests**: All 46 tests pass
✅ **Documentation mission tests**: All 50 distribution tests pass
✅ **Regression tests**: ≥95% of existing tests pass
✅ **No SPEC_KITTY_TEMPLATE_ROOT bypass**: Distribution tests validate real package
✅ **Findings documented**: All issues logged in findings/

### Quality Gates

1. **Zero critical test gaps**: All blocking tests implemented
2. **Distribution validation**: pip package tested, not just dev environment
3. **Cross-version compatibility**: Tests pass on v0.11.0 and v0.12.0
4. **Documentation complete**: All new features have test coverage

---

## Timeline Estimate

### Critical Path (Blocking v0.12.0)

- **Sparse-checkout tests**: 6-8 hours
- **Documentation mission tests**: 5-7 hours
- **Regression fixes**: 2-4 hours
- **Documentation**: 1 hour
- **Total**: **14-20 hours**

### Post-Release (v0.12.1)

- **Workflow tests**: 2-3 hours
- **Migration tests**: 2 hours
- **Cross-platform tests**: 1-2 hours
- **Total**: **5-7 hours**

### Grand Total: **19-27 hours**

---

## Key Contacts and Resources

**Documentation**:
- Test plan: `/Users/robert/.claude/plans/peaceful-popping-aho.md`
- Coverage analysis: `findings/test-infrastructure/v0.12.0-test-coverage-analysis.md`
- Testing philosophy: `CLAUDE.md` (test what you ship)

**Repositories**:
- spec-kitty (source): `/Users/robert/Code/spec-kitty`
- spec-kitty-test (tests): `/Users/robert/Code/spec-kitty-test`

**Key Files**:
- Sparse-checkout impl: `src/specify_cli/cli/commands/implement.py` (lines 596-642)
- Auto-commit (tasks): `src/specify_cli/cli/commands/agent/tasks.py`
- Auto-commit (workflow): `src/specify_cli/cli/commands/agent/workflow.py`
- Infrastructure fixes: `kitty-specs/012-documentation-mission/INFRASTRUCTURE-FIXES.md`

**Related Issues**:
- Issues #62, #63, #64: Template packaging bugs (why distribution tests are critical)
- Issue #46: Constitution worktree fix (related to sparse-checkout)
- Issue #68: Mission template script refs (template validation)
- Issue #70: Upgrade migration failures (migration testing)

---

## Risk Mitigation

### If Tests Fail During Implementation

**Scenario**: Sparse-checkout tests reveal bugs
**Action**: Document bugs in findings/, fix before release
**Timeline**: Add 2-4 hours for bug fixes

**Scenario**: Distribution tests find template packaging issues
**Action**: This is EXACTLY why we're testing - fix immediately
**Timeline**: Add 1-3 hours for packaging fixes

**Scenario**: Regression tests show breaking changes
**Action**: Evaluate if changes are acceptable, document in CHANGELOG
**Timeline**: Add 1-2 hours for analysis and documentation

### If Timeline Slips

**Option 1**: Ship v0.12.0 with warnings
- Document known limitations
- Mark documentation mission as "beta"
- Add warning about sparse-checkout

**Option 2**: Ship v0.11.1 as interim release
- Include only safe changes
- Defer documentation mission to v0.13.0
- Focus on sparse-checkout stability

**Option 3**: Delay v0.12.0 release
- Complete all blocking tests
- Ship when confident
- Better to delay than ship broken code

---

## Lessons Learned

### From Issues #62-64

**Mistake**: ALL 323 tests used SPEC_KITTY_TEMPLATE_ROOT bypass
**Result**: 100% of PyPI users broken for 8+ releases
**Lesson**: Distribution tests are MANDATORY

**Applied**: Documentation mission MUST have distribution tests

### From Sparse-Checkout Implementation

**Mistake**: Production code shipped with ZERO tests
**Risk**: Silent failures, state divergence, data loss
**Lesson**: Infrastructure code needs MORE tests, not fewer

**Applied**: Created 46 comprehensive tests before declaring feature "done"

### From Template Relocation

**Mistake**: Template sources moved but tests not updated
**Result**: Test failures on version upgrade
**Lesson**: Test updates are part of feature work

**Applied**: Regression testing is blocking for v0.12.0

---

## Final Checklist

Before declaring v0.12.0 ready:

- [ ] All 46 sparse-checkout tests pass
- [ ] All 50 documentation mission distribution tests pass
- [ ] Regression test suite ≥95% pass rate
- [ ] NO tests use SPEC_KITTY_TEMPLATE_ROOT bypass (except functional tests)
- [ ] Test results documented in findings/
- [ ] CHANGELOG updated with test coverage notes
- [ ] Migration guide includes testing recommendations
- [ ] Known issues documented with workarounds

**DO NOT SHIP** until all checkboxes complete.

---

**Created**: 2026-01-13
**Author**: Claude (Sonnet 4.5)
**Next Review**: After sparse-checkout tests complete
