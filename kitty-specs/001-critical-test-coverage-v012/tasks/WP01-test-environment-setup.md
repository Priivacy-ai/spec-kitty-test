---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Test Environment Setup"
phase: "Phase 0 - Foundation"
lane: "planned"
assignee: ""
agent: "codex"
shell_pid: "54244"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
dependencies: []
history:
  - timestamp: "2026-01-14T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Test Environment Setup

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-14

**Issue 1**: `scripts/setup-test-env.sh` exits with an error if `~/Code/spec-kitty` is missing, but the WP edge case explicitly says this should be a warning (the directory is for reference only). Change this check to emit a warning and continue so the script still passes when the repo is missing.

**Issue 2**: The setup script only warns when spec-kitty is installed from somewhere other than `~/Code/spec-kitty`, yet the WP success criteria requires the environment to be configured with spec-kitty installed from source. Either fail the script when the install is not from `~/Code/spec-kitty` (preferred), or update the output to make it clear the environment is NOT ready and exit non-zero.

**Issue 3**: The uninstall guidance in the non-source install warning uses `pip uninstall spec-kitty`, but the project dependency and the check use `spec-kitty-cli`. Align the uninstall instruction with the actual package name so the fix path is correct.


## Objectives & Success Criteria

**Primary Objective**: Establish test infrastructure foundations enabling adversarial testing of spec-kitty v0.12.0.

**Success Criteria**:
- ✅ Environment validation script passes (spec-kitty ≥v0.11.0, Git ≥2.25, Python 3.11+)
- ✅ Findings template created for documenting bugs discovered during testing
- ✅ Test environment fully configured (spec-kitty installed from source, dependencies ready)
- ✅ Test patterns reviewed and understood (existing fixture usage, distribution test approach)
- ✅ Fixtures verified/created (init_spec_kitty_project, clean_environment)
- ✅ Ready for parallel development: Track 1 (sparse-checkout) and Track 2 (documentation mission)

**Definition of Complete**: Running `./scripts/setup-test-env.sh` shows all ✅ checks pass, findings/test-infrastructure/v0.12.0-bugs-found.md exists, fixtures available in conftest.py or test files.

---

## Context & Constraints

### Related Documents
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (requirements for 96 tests)
- **Plan**: kitty-specs/001-critical-test-coverage-v012/plan.md (adversarial testing approach, parallel tracks)
- **Data Model**: kitty-specs/001-critical-test-coverage-v012/data-model.md (test entities)
- **Quickstart**: kitty-specs/001-critical-test-coverage-v012/quickstart.md (developer onboarding examples)

### Architectural Decisions
- **Adversarial philosophy**: Intentionally break spec-kitty to find bugs. Zero tolerance for test failures - fix bugs before continuing.
- **Parallel tracks**: Track 1 (sparse-checkout - 46 tests) and Track 2 (documentation mission - 50 tests) develop simultaneously after WP01
- **Risk-first testing**: Edge cases, concurrency, distribution packaging before happy paths
- **Test environment**: Tests execute against installed spec-kitty CLI (pip install -e ~/Code/spec-kitty), not source code directly

### Constraints
- Tests must be deterministic (zero flaky tests allowed)
- No external dependencies (fully offline-capable)
- Automatic cleanup (no orphaned processes or temp files)
- Test execution <15 minutes total for all 546 tests
- ≥95% pass rate required for v0.12.0 release

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create scripts/setup-test-env.sh validation script

**Purpose**: Automated environment validation script that checks all prerequisites before test development begins.

**Steps**:

1. Create scripts/ directory if it doesn't exist:
   ```bash
   mkdir -p scripts
   ```

2. Create scripts/setup-test-env.sh with executable permissions:
   ```bash
   touch scripts/setup-test-env.sh
   chmod +x scripts/setup-test-env.sh
   ```

3. Implement validation checks (see plan.md Phase 1 for complete script):
   - Check spec-kitty installed: `command -v spec-kitty`
   - Check version ≥0.11.0: Parse `spec-kitty --version` output
   - Check Git version ≥2.25: Parse `git --version` output
   - Check ~/Code/spec-kitty exists (for test writer reference)
   - Check git user.name and user.email configured

4. Script should exit with code 1 on any failure, print clear error with fix instructions

5. Script should print success summary with all ✅ checks and usage examples

**Files**:
- Create: `scripts/setup-test-env.sh` (~60 lines)

**Parallel?**: Yes [P] - Can proceed in parallel with T002

**Validation**:
- Run script: `./scripts/setup-test-env.sh`
- Should show all ✅ checks pass
- Should print: "Test environment ready!" with pytest command examples

**Edge Cases**:
- spec-kitty not installed → clear error: "Install with: pip install -e ~/Code/spec-kitty"
- Version too old → clear error with current version and minimum required
- Git user not configured → clear error with git config commands
- ~/Code/spec-kitty missing → warning (test writer needs this for code reference)

---

### Subtask T002 – Create findings/test-infrastructure/v0.12.0-bugs-found.md template

**Purpose**: Structured template for documenting bugs discovered during adversarial testing.

**Steps**:

1. Verify findings/test-infrastructure/ directory exists (should already exist from previous work)

2. Create findings/test-infrastructure/v0.12.0-bugs-found.md with template structure:

```markdown
# Bugs Found During v0.12.0 Adversarial Testing

**Testing Period**: 2026-01-14 to TBD
**Testing Approach**: Adversarial red team methodology
**Tracks**: Sparse-checkout infrastructure (46 tests) + Documentation mission distribution (50 tests)
**Philosophy**: Fail-fast, zero tolerance for failures, fix bugs before continuing

## Summary

Total bugs found: 0 (will be updated as testing progresses)
- Critical: 0 (data corruption, security issues)
- High: 0 (feature broken, workflow blocked)
- Medium: 0 (degraded experience, workarounds exist)
- Low: 0 (minor issues, cosmetic problems)

---

## Bug Template (use for each bug found)

### Bug #X: [Short Description]

**Test**: test_name_that_found_bug
**Severity**: CRITICAL | HIGH | MEDIUM | LOW
**Track**: Sparse-checkout | Documentation mission
**Found**: YYYY-MM-DD
**Fixed**: YYYY-MM-DD (or "Not yet fixed")

**Symptoms**:
- What happened when test ran
- Error messages, unexpected behavior
- Test failure output

**Root Cause**:
- Analysis of why bug occurred
- Code location: file.py:line-range
- Logic error, missing validation, race condition, etc.

**Fix Applied**:
- What changes made to ~/Code/spec-kitty
- Code snippets if relevant
- Commit hash if committed

**Verification**:
- Test now passes: Yes/No
- Additional tests added: Yes/No
- Regression risk: Low/Medium/High

**Files Changed**:
- ~/Code/spec-kitty/path/to/file.py (lines changed)
- ... (other files)

---

*[Additional bugs will be documented below using above template]*
```

3. Save template to findings/test-infrastructure/v0.12.0-bugs-found.md

**Files**:
- Create: `findings/test-infrastructure/v0.12.0-bugs-found.md` (~40 lines initial template)

**Parallel?**: Yes [P] - Can proceed in parallel with T001

**Validation**:
- File exists at correct location
- Template sections present (Summary, Bug Template)
- Ready for bug documentation during testing

---

### Subtask T003 – Set up test environment (install spec-kitty, validate versions)

**Purpose**: Install spec-kitty from source and validate all dependencies ready for testing.

**Steps**:

1. Verify Python version ≥3.11:
   ```bash
   python --version
   # Should show: Python 3.11.x or higher
   ```

2. Install spec-kitty in development mode from ~/Code/spec-kitty:
   ```bash
   pip install -e ~/Code/spec-kitty
   ```

3. Verify installation:
   ```bash
   spec-kitty --version
   # Should show: 0.11.0 (dev: v0.10.13-XXX-gYYYYYYY)
   ```

4. Verify pytest and dependencies installed:
   ```bash
   pip show pytest pytest-anyio
   # Should show both packages installed
   ```

5. Verify Git version ≥2.25:
   ```bash
   git --version
   # Should show: git version 2.25.0 or higher
   ```

6. Run validation script from T001:
   ```bash
   ./scripts/setup-test-env.sh
   # Should show all ✅ checks pass
   ```

**Files**:
- None created (environment setup only)

**Parallel?**: No - Must complete before T004 and T005

**Validation**:
- `spec-kitty --version` shows v0.11.0+
- `pip show spec-kitty` shows location: ~/Code/spec-kitty
- `./scripts/setup-test-env.sh` passes all checks

**Edge Cases**:
- spec-kitty already installed from PyPI (not source) → Uninstall first: `pip uninstall spec-kitty`, then reinstall from source
- Virtual environment not activated → Activate: `source venv/bin/activate`
- Dependencies missing → Install: `pip install -r requirements.txt`

---

### Subtask T004 – Review existing test patterns (test_comprehensive_workspace_per_wp.py, test_user_experience_simulation.py)

**Purpose**: Study existing test patterns to ensure new tests follow established conventions.

**Steps**:

1. Read and analyze tests/functional/test_comprehensive_workspace_per_wp.py:
   - Fixture usage: init_spec_kitty_project factory pattern
   - Git operations: subprocess.run with cwd parameter
   - Assertion patterns: Clear failure messages with context
   - Class organization: Multiple test classes per file
   - Test size: ~150KB file with comprehensive coverage

2. Extract key patterns from test_comprehensive_workspace_per_wp.py:
   ```python
   # Pattern 1: Project initialization
   @pytest.fixture
   def init_spec_kitty_project(temp_project_dir, spec_kitty_repo_root):
       def _init(project_name="test-project"):
           env = os.environ.copy()
           env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
           result = subprocess.run(
               ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
               cwd=temp_project_dir,
               env=env,
               input='y\n',
               capture_output=True,
               text=True,
               timeout=30
           )
           assert result.returncode == 0, f"Init failed: {result.stderr}"
           return temp_project_dir / project_name
       return _init
   ```

3. Read and analyze tests/distribution/test_user_experience_simulation.py:
   - clean_environment fixture: Removes SPEC_KITTY_TEMPLATE_ROOT
   - Distribution testing: Simulates PyPI user environment
   - Failure messages: Emphasizes "This would catch Issues #62-64"
   - Test philosophy: Validates package, not just code

4. Extract distribution test pattern:
   ```python
   # Pattern 2: Clean environment for distribution tests
   @pytest.fixture
   def clean_environment(self):
       env = os.environ.copy()
       env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
       env.pop('SPEC_KITTY_REPO', None)
       to_remove = [k for k in env.keys()
                    if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
       for key in to_remove:
           env.pop(key, None)
       return env
   ```

5. Read tests/conftest.py to understand global fixtures:
   - spec_kitty_repo_root (session scope)
   - spec_kitty_version (session scope)
   - temp_project_dir (typically function scope in test classes)
   - clean_env (autouse, restores environment)

**Files**:
- Read: tests/functional/test_comprehensive_workspace_per_wp.py
- Read: tests/distribution/test_user_experience_simulation.py
- Read: tests/conftest.py

**Parallel?**: Yes [P] - Can proceed in parallel with T005 after T003 completes

**Validation**:
- Understand fixture patterns (factory, clean_environment, temp_project_dir)
- Understand subprocess.run usage (cwd, env, timeout, capture_output)
- Understand assertion patterns (context in failure messages)
- Understand class organization (group related tests)

---

### Subtask T005 – Create/verify init_spec_kitty_project and clean_environment fixtures

**Purpose**: Ensure required fixtures available for new tests (reuse existing or create if missing).

**Steps**:

1. Check if init_spec_kitty_project fixture exists in tests/conftest.py or tests/functional/conftest.py:
   ```bash
   grep -n "def init_spec_kitty_project" tests/conftest.py tests/functional/conftest.py
   ```

2. If fixture doesn't exist globally, it should be created as a local fixture in test classes or in tests/functional/conftest.py:
   ```python
   # Location: tests/functional/conftest.py (if creating new)
   import pytest
   import subprocess
   from pathlib import Path

   @pytest.fixture
   def init_spec_kitty_project(temp_project_dir, spec_kitty_repo_root):
       """Initialize spec-kitty project with SPEC_KITTY_TEMPLATE_ROOT set."""
       def _init(project_name="test-project"):
           env = os.environ.copy()
           env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
           result = subprocess.run(
               ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
               cwd=temp_project_dir,
               env=env,
               input='y\n',
               capture_output=True,
               text=True,
               timeout=30
           )
           assert result.returncode == 0, f"Init failed: {result.stderr}"
           return temp_project_dir / project_name
       return _init
   ```

3. Check if clean_environment fixture exists in tests/distribution/conftest.py or tests/distribution/ test files:
   ```bash
   grep -n "def clean_environment" tests/distribution/*.py
   ```

4. If fixture doesn't exist, create in tests/distribution/conftest.py:
   ```python
   # Location: tests/distribution/conftest.py (if creating new)
   import pytest
   import os

   @pytest.fixture
   def clean_environment(self):
       """Clean environment simulating PyPI user (NO development overrides)."""
       env = os.environ.copy()
       env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
       env.pop('SPEC_KITTY_REPO', None)
       to_remove = [k for k in env.keys()
                    if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
       for key in to_remove:
           env.pop(key, None)
       return env
   ```

5. Verify fixtures work:
   ```bash
   # Test that fixtures are discoverable
   pytest tests/functional/ --fixtures | grep init_spec_kitty_project
   pytest tests/distribution/ --fixtures | grep clean_environment
   ```

**Files**:
- Create if needed: `tests/functional/conftest.py` (init_spec_kitty_project fixture)
- Create if needed: `tests/distribution/conftest.py` (clean_environment fixture)

**Parallel?**: Yes [P] - Can proceed in parallel with T004 after T003 completes

**Validation**:
- Fixtures discoverable by pytest
- init_spec_kitty_project returns factory function that creates test projects
- clean_environment returns dict with SPEC_KITTY_TEMPLATE_ROOT removed
- Both fixtures follow patterns from existing tests

**Edge Cases**:
- Fixtures already exist in test files (not conftest.py) → Document location, don't duplicate
- temp_project_dir fixture might be local to test classes → Check if needed globally

---

## Test Strategy

**No tests required for this WP** - This WP sets up infrastructure for testing in subsequent WPs.

**Validation Approach**:
- Run setup script manually: `./scripts/setup-test-env.sh` → all checks pass
- Verify fixtures: `pytest tests/ --fixtures` → init_spec_kitty_project and clean_environment listed
- Test fixture usage: Create a simple test that uses both fixtures to verify they work

---

## Risks & Mitigations

**Risk 1: Environment setup fails on CI/CD (different OS, Python version)**
- **Likelihood**: Medium
- **Impact**: High (blocks automated testing)
- **Mitigation**: Test script on macOS (primary) and document platform-specific requirements. Add CI/CD-specific checks if needed.

**Risk 2: Fixtures break existing tests**
- **Likelihood**: Low
- **Impact**: High (regression in existing test suite)
- **Mitigation**: Run existing test suite before and after fixture changes: `pytest tests/ -v --tb=line`. If any failures, revert fixture changes.

**Risk 3: spec-kitty install from source fails (missing dependencies, conflicts)**
- **Likelihood**: Low
- **Impact**: High (can't run tests at all)
- **Mitigation**: Follow spec-kitty installation guide. Use virtual environment for isolation. Document any conflicts encountered.

---

## Definition of Done Checklist

- [ ] scripts/setup-test-env.sh created with executable permissions
- [ ] Setup script validates all prerequisites (spec-kitty, Git, Python, user config)
- [ ] Setup script exits with code 1 on failure, prints clear error messages
- [ ] Setup script exits with code 0 on success, prints all ✅ checks
- [ ] findings/test-infrastructure/v0.12.0-bugs-found.md created with template structure
- [ ] Test environment configured: spec-kitty installed from ~/Code/spec-kitty
- [ ] spec-kitty --version shows v0.11.0+ (dev version)
- [ ] Existing test patterns reviewed (fixture usage, assertion patterns, class organization)
- [ ] init_spec_kitty_project fixture available (either in conftest.py or documented location)
- [ ] clean_environment fixture available (either in conftest.py or documented location)
- [ ] Fixtures tested: Both work when used in simple test
- [ ] No regressions: Existing test suite still passes after any fixture changes

---

## Review Guidance

**For Reviewer**:

1. **Validate setup script** (`./scripts/setup-test-env.sh`):
   - Run script in clean environment → all checks should pass
   - Try with missing deps → should fail with clear instructions
   - Check script is executable: `ls -l scripts/setup-test-env.sh`

2. **Validate findings template** (`findings/test-infrastructure/v0.12.0-bugs-found.md`):
   - Template sections present (Summary, Bug Template)
   - Markdown formatting correct
   - Ready for bug documentation

3. **Validate fixtures**:
   - Check fixture location (conftest.py or documented)
   - Verify fixture signatures correct (parameters, return types)
   - Confirm fixtures follow existing patterns

4. **Validate environment**:
   - spec-kitty --version shows development version from ~/Code/spec-kitty
   - Existing test suite passes: `pytest tests/ -v --co` (collection succeeds)

**Key Questions**:
- Can another developer use setup script to validate their environment?
- Are fixtures ready for use in WP02-WP12?
- Is findings template ready for bug documentation?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T11:57:54Z – claude-sonnet-4-5 – shell_pid=52683 – lane=doing – Started implementation via workflow command
- 2026-01-14T12:07:50Z – claude-sonnet-4-5 – shell_pid=52683 – lane=for_review – Ready for review: All 5 subtasks complete - validation script passes, findings template created, environment validated, test patterns reviewed, fixtures documented
- 2026-01-14T12:08:54Z – codex – shell_pid=54244 – lane=doing – Started review via workflow command
- 2026-01-14T12:10:30Z – codex – shell_pid=54244 – lane=planned – Moved to planned
