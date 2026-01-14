# Quickstart: Critical Test Coverage for v0.12.0

## Overview

This guide gets you started implementing 96 critical tests using adversarial red team methodology. You'll validate spec-kitty v0.12.0 infrastructure with zero tolerance for bugs.

**Goal**: Unblock v0.12.0 release by implementing comprehensive tests for sparse-checkout (46 tests) and documentation mission (50 tests).

**Philosophy**: Intentionally break spec-kitty to find implementation bugs. Fix bugs immediately. All tests must pass before shipping.

---

## Prerequisites

### Required Software

- **Python 3.11+** - spec-kitty requirement
- **Git ≥2.25** - Sparse-checkout support
- **pytest ≥8.4.2** - Test framework
- **spec-kitty v0.11.0+** - Must be installed from source

### Environment Setup

**1. Clone spec-kitty repository** (if not already present):
```bash
cd ~/Code
git clone <spec-kitty-repo-url> spec-kitty
cd spec-kitty
```

**2. Install spec-kitty in development mode**:
```bash
pip install -e ~/Code/spec-kitty
```

**3. Verify installation**:
```bash
spec-kitty --version
# Should show: 0.11.0 (dev: v0.10.13-XXX-gYYYYYYY)
```

**4. Configure Git** (required for test commits):
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

**5. Run environment validation script**:
```bash
cd ~/Code/spec-kitty-test
./scripts/setup-test-env.sh
```

Expected output:
```
🔍 Validating test environment...
✅ spec-kitty version 0.11.0
✅ Git version 2.45.0
✅ ~/Code/spec-kitty found
✅ Git user configured
✅ Test environment ready!
```

---

## Project Structure

```
spec-kitty-test/
├── tests/
│   ├── conftest.py                    # Fixtures (existing - reuse)
│   ├── functional/                    # Development workflow tests
│   │   ├── test_sparse_checkout_infrastructure.py  # 46 tests (NEW)
│   │   └── test_documentation_mission_end_to_end.py # 15 tests (NEW)
│   └── distribution/                  # PyPI user workflow tests
│       ├── test_documentation_mission_distribution.py  # 20 tests (NEW)
│       └── test_doc_generators_distribution.py        # 15 tests (NEW)
│
├── kitty-specs/001-critical-test-coverage-v012/
│   ├── spec.md              # Feature specification
│   ├── plan.md              # This implementation plan
│   ├── data-model.md        # Test entities
│   └── quickstart.md        # This guide
│
├── findings/test-infrastructure/
│   └── v0.12.0-bugs-found.md  # Document bugs (CREATE THIS)
│
└── scripts/
    └── setup-test-env.sh    # Environment validation
```

---

## Development Tracks

### Track 1: Sparse-Checkout Infrastructure (46 tests)

**File**: `tests/functional/test_sparse_checkout_infrastructure.py`

**Risk-First Order**:
1. Suite 6: Edge Cases (8 tests) - Corruption, permissions, concurrency
2. Suite 4: Multi-Agent (8 tests) - Parallel synchronization
3. Suite 3: Auto-Commit (10 tests) - Core synchronization
4. Suite 1: Worktree Creation (8 tests) - Foundation
5. Suite 2: Path Resolution (6 tests) - Integration
6. Suite 5: Merge (6 tests) - Git operations

**Why risk-first?** Surface critical bugs (corruption, race conditions) before investing in happy-path tests.

**Start here**:
```bash
# Run existing test as template
pytest tests/functional/test_comprehensive_workspace_per_wp.py -xvs

# Study patterns, then implement Suite 6
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestEdgeCases -xvs
```

### Track 2: Documentation Mission Distribution (50 tests)

**Files**:
- `tests/distribution/test_doc_generators_distribution.py` (15 tests)
- `tests/distribution/test_documentation_mission_distribution.py` (20 tests)
- `tests/functional/test_documentation_mission_end_to_end.py` (15 tests)

**Risk-First Order**:
1. test_doc_generators_distribution.py - Generator packaging (catch Issues #62-64 pattern)
2. test_documentation_mission_distribution.py - Mission loading from package
3. test_documentation_mission_end_to_end.py - Full workflow

**Why risk-first?** Distribution tests catch packaging issues immediately (exact Issues #62-64 scenario).

**Start here**:
```bash
# Run existing distribution test as template
pytest tests/distribution/test_user_experience_simulation.py -xvs

# Study clean_environment fixture, then implement generator tests
pytest tests/distribution/test_doc_generators_distribution.py::TestJSDocGenerator -xvs
```

---

## Writing Your First Test

### Example: Sparse-Checkout Exclusion Test

**Location**: `tests/functional/test_sparse_checkout_infrastructure.py`

```python
import pytest
import subprocess
from pathlib import Path

class TestWorktreeCreation:
    """Validate sparse-checkout configuration during worktree creation."""

    def test_sparse_checkout_excludes_kitty_specs(
        self,
        temp_project_dir,
        init_spec_kitty_project
    ):
        """
        Test: kitty-specs/ excluded from worktree working directory

        Why: Sparse-checkout foundation. If kitty-specs/ present in worktree,
        auto-commit synchronization breaks (each worktree divergent state).

        Reference: implement.py:596-642 (sparse-checkout configuration)
        Related: Issues #62-64 (template divergence pattern)
        """
        # 1. Initialize test project
        project = init_spec_kitty_project("test-project")

        # 2. Create feature with spec-kitty
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Feature creation failed: {result.stderr}"

        # 3. Create worktree via spec-kitty implement
        result = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--agent=TestAgent'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60
        )
        assert result.returncode == 0, f"Implement failed: {result.stderr}"

        # 4. Find worktree directory
        worktrees = list((project / '.worktrees').glob('*'))
        assert len(worktrees) >= 1, f"No worktrees found: {list((project / '.worktrees').iterdir())}"
        worktree_path = worktrees[0]

        # 5. Validate sparse-checkout exclusion
        worktree_kitty_specs = worktree_path / 'kitty-specs'
        main_kitty_specs = project / 'kitty-specs'

        assert not worktree_kitty_specs.exists(), (
            f"kitty-specs/ should NOT exist in worktree\n"
            f"Worktree path: {worktree_path}\n"
            f"Expected: kitty-specs/ absent (sparse-checkout)\n"
            f"Actual contents: {list(worktree_path.glob('*'))}\n"
            f"This means sparse-checkout NOT working - CRITICAL BUG"
        )

        assert main_kitty_specs.exists(), (
            f"kitty-specs/ should exist in main repo\n"
            f"Main repo: {project}\n"
            f"Sparse-checkout should only exclude from worktrees, not main"
        )

        # 6. Validate via git ls-files (nothing tracked in worktree)
        result = subprocess.run(
            ['git', 'ls-files', 'kitty-specs/'],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == "", (
            f"git ls-files should return empty for kitty-specs/ in worktree\n"
            f"Worktree: {worktree_path}\n"
            f"Output: {result.stdout}\n"
            f"This means files tracked despite sparse-checkout - CRITICAL BUG"
        )
```

**Key Points**:
- **Docstring**: What tested, why matters, implementation reference
- **Assertions**: Include full context (paths, expected, actual, debugging info)
- **Failure messages**: Make it obvious this is a CRITICAL BUG if test fails
- **Timeout**: All subprocess calls have timeout (prevent hanging tests)

### Example: Distribution Test

**Location**: `tests/distribution/test_documentation_mission_distribution.py`

```python
import pytest
from specify_cli.mission import get_mission_by_name

class TestMissionLoading:
    """Validate documentation mission loads from installed pip package."""

    @pytest.fixture
    def clean_environment(self):
        """Clean environment simulating PyPI user (NO development overrides)."""
        import os
        env = os.environ.copy()

        # CRITICAL: Remove all SPEC_KITTY_* vars except API_KEY
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)
        to_remove = [k for k in env.keys()
                     if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
        for key in to_remove:
            env.pop(key, None)

        return env

    def test_documentation_mission_loads_from_package(self, clean_environment):
        """
        Distribution test: Mission loads from pip package (NO SPEC_KITTY_TEMPLATE_ROOT)

        Why: This is the EXACT test that would catch Issues #62-64. Local tests
        passed (used SPEC_KITTY_TEMPLATE_ROOT → correct templates), PyPI users
        failed (no env var → outdated templates). This test simulates PyPI user.

        Reference: missions/documentation/mission.yaml
        Related: Issues #62-64 (template bundling bug)
        """
        # CRITICAL: clean_environment fixture removed SPEC_KITTY_TEMPLATE_ROOT
        # If mission loads, templates are correctly bundled in package
        # If mission fails, templates NOT bundled → DO NOT SHIP v0.12.0

        mission = get_mission_by_name("documentation")

        assert mission is not None, (
            "❌ CRITICAL: Documentation mission failed to load from package\n"
            "\n"
            "This is the EXACT failure pattern from Issues #62-64:\n"
            "- Local tests pass (use SPEC_KITTY_TEMPLATE_ROOT)\n"
            "- PyPI users fail (no env var, templates missing from package)\n"
            "\n"
            "Environment:\n"
            "- SPEC_KITTY_TEMPLATE_ROOT: removed (simulates PyPI user)\n"
            "- Templates should load via importlib.resources\n"
            "\n"
            "Action: Fix template bundling in pyproject.toml before shipping\n"
            "DO NOT ship v0.12.0 with this failure - repeats Issues #62-64"
        )

        assert mission.name == "Documentation Kitty", (
            f"Mission name wrong: {mission.name}\n"
            f"Expected: 'Documentation Kitty'\n"
            f"Check missions/documentation/mission.yaml"
        )
```

**Key Points**:
- **clean_environment fixture**: Removes SPEC_KITTY_TEMPLATE_ROOT
- **Failure message**: Makes it CRYSTAL CLEAR this is the Issues #62-64 pattern
- **DO NOT SHIP language**: Emphasizes this is release-blocking if fails

---

## Running Tests

### Run Individual Test
```bash
# Run one test with verbose output
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestWorktreeCreation::test_sparse_checkout_excludes_kitty_specs -xvs

# -x: stop on first failure
# -v: verbose (show test names)
# -s: show print statements
```

### Run Test Class
```bash
# Run all tests in TestWorktreeCreation class
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestWorktreeCreation -xvs
```

### Run Test Suite
```bash
# Run all sparse-checkout tests
pytest tests/functional/test_sparse_checkout_infrastructure.py -xvs

# Run all documentation mission tests
pytest tests/distribution/test_documentation_mission_distribution.py -xvs
pytest tests/distribution/test_doc_generators_distribution.py -xvs
pytest tests/functional/test_documentation_mission_end_to_end.py -xvs
```

### Run Full Test Suite
```bash
# Run ALL tests (existing + new)
pytest tests/ -v

# Expected: ≥519/546 PASSED (≥95% pass rate)
```

---

## When Tests Fail (Adversarial Methodology)

### Step 1: Determine Root Cause

**Is this a spec-kitty bug or test bug?**

Check:
- Does spec-kitty behavior match spec requirements?
- If no: **spec-kitty bug** (good - you found it!)
- If yes: **test bug** (test has incorrect expectations)

### Step 2: Document Bug (if spec-kitty bug)

Create/update: `findings/test-infrastructure/v0.12.0-bugs-found.md`

```markdown
## Bug #1: Sparse-Checkout Not Excluding kitty-specs/

**Test**: test_sparse_checkout_excludes_kitty_specs
**Severity**: CRITICAL (data corruption risk)
**Found**: 2026-01-14

**Symptoms**:
- Worktree contains kitty-specs/ directory (should be excluded)
- git config core.sparseCheckout shows "true" but not working
- Multiple worktrees have divergent kitty-specs/ state

**Root Cause**:
- implement.py:630 writes patterns but doesn't apply them
- git read-tree command missing or failing silently

**Fix Applied**:
- Added error handling for git read-tree
- Verified sparse-checkout file written before applying
- Added validation that kitty-specs/ excluded after apply

**Verification**:
- Test now passes: kitty-specs/ absent from worktree
- Main repo still has kitty-specs/ (correct)
- git ls-files confirms no tracked files in kitty-specs/

**Files Changed**:
- ~/Code/spec-kitty/src/specify_cli/cli/commands/implement.py:633-638
```

### Step 3: Fix Bug

**Fix in spec-kitty repository**:
```bash
cd ~/Code/spec-kitty
# Edit src/specify_cli/cli/commands/implement.py
# Fix the bug
git add -p
git commit -m "fix: Apply sparse-checkout after writing patterns

Found by test_sparse_checkout_excludes_kitty_specs.
Sparse-checkout patterns were written but not applied to working tree.

Bug: git read-tree command missing error handling
Fix: Check returncode, raise clear error if application fails

Related: spec-kitty-test #001-critical-test-coverage-v012"
```

### Step 4: Verify Fix

**Re-run test**:
```bash
cd ~/Code/spec-kitty-test
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestWorktreeCreation::test_sparse_checkout_excludes_kitty_specs -xvs
```

**Expected**: Test now passes

### Step 5: Continue

Move to next test. Repeat fail-fast cycle.

---

## Parallel Development Coordination

### Track Coordination

If multiple developers/agents working in parallel:

**Track 1 (Sparse-Checkout)**: Developer/Agent A
**Track 2 (Documentation Mission)**: Developer/Agent B

**Synchronization**:
1. **Shared findings/** - Both tracks document bugs found
2. **Coordinate fixes** - "I'm fixing bug X in implement.py" before starting
3. **Daily sync** - Progress, blockers, shared learnings
4. **Final integration** - Both tracks complete → run full suite together

### Communication Protocol

**Before fixing spec-kitty bug**:
```
Track 1: "Found bug in implement.py:633. Fixing now."
Track 2: "Acknowledged. I'll wait to pull your fix."
```

**After fixing spec-kitty bug**:
```
Track 1: "Bug fixed in implement.py:633. Pushed to main."
Track 2: "Pulling fix. Re-running my tests."
```

**Test pattern sharing**:
```
Track 1: "Good way to validate sparse-checkout: check git ls-files output is empty"
Track 2: "Thanks! I'll use that pattern for distribution tests."
```

---

## Success Criteria

### Track 1 Complete
- ✅ All 46 sparse-checkout tests implemented
- ✅ `pytest tests/functional/test_sparse_checkout_infrastructure.py -v` shows 46/46 PASSED
- ✅ Execution time <5 minutes
- ✅ Zero xfails, zero skips
- ✅ All spec-kitty bugs found and fixed

### Track 2 Complete
- ✅ All 50 documentation mission tests implemented
- ✅ Distribution tests: 35/35 PASSED (test_doc_generators + test_documentation_mission)
- ✅ End-to-end tests: 15/15 PASSED (test_documentation_mission_end_to_end)
- ✅ Execution time <5 minutes total
- ✅ Zero xfails, zero skips
- ✅ All spec-kitty bugs found and fixed

### Overall Feature Complete
- ✅ Both tracks complete
- ✅ `pytest tests/ -v` shows ≥519/546 PASSED (≥95% pass rate)
- ✅ Test execution <15 minutes
- ✅ findings/test-infrastructure/v0.12.0-bugs-found.md complete
- ✅ **v0.12.0 release unblocked**

---

## Troubleshooting

### "spec-kitty not found"
```bash
pip install -e ~/Code/spec-kitty
```

### "Git version too old (need ≥2.25)"
```bash
# macOS
brew upgrade git

# Linux
sudo apt-get update && sudo apt-get install git
```

### "Test hangs forever"
- Check timeout values (30s for init, 60s for complex operations)
- Look for orphaned spec-kitty processes: `ps aux | grep spec-kitty`
- Kill if needed: `killall spec-kitty`

### "Temp directories not cleaned up"
- Normal: tempfile.TemporaryDirectory handles cleanup
- If accumulating: Check for test crashes (exceptions before cleanup)
- Manual cleanup: `rm -rf /tmp/tmp*` (careful!)

### "Test fails intermittently (flaky)"
- **Zero tolerance for flaky tests**
- Investigate: Are tests dependent on timing? Race conditions?
- Fix: Make tests deterministic (sequential simulation, not parallel)
- Never accept flakiness - root cause and fix

---

## Next Steps

1. **Choose your track**: Sparse-checkout (Track 1) or Documentation mission (Track 2)
2. **Review existing tests**: Study patterns in test_comprehensive_workspace_per_wp.py (functional) or test_user_experience_simulation.py (distribution)
3. **Start risk-first**: Implement edge cases/distribution tests first
4. **Fail fast**: When test fails, investigate immediately
5. **Document bugs**: Update findings/test-infrastructure/v0.12.0-bugs-found.md
6. **Fix bugs**: Fix in ~/Code/spec-kitty before continuing
7. **Verify fix**: Re-run test, ensure passes
8. **Continue**: Move to next test
9. **Synchronize**: Coordinate with other track, share learnings
10. **Complete**: All tests pass, v0.12.0 unblocked!

---

## Resources

- **Specification**: kitty-specs/001-critical-test-coverage-v012/spec.md
- **Implementation Plan**: kitty-specs/001-critical-test-coverage-v012/plan.md
- **Data Model**: kitty-specs/001-critical-test-coverage-v012/data-model.md
- **Existing Tests**: tests/functional/test_comprehensive_workspace_per_wp.py
- **Distribution Tests**: tests/distribution/test_user_experience_simulation.py
- **Fixtures**: tests/conftest.py
- **Findings Template**: findings/TEMPLATE.md

**Questions?** Review spec.md and plan.md for detailed requirements and approach.