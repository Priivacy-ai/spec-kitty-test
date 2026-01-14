# Implementation Plan: Critical Test Coverage for v0.12.0

**Branch**: `001-critical-test-coverage-v012` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/001-critical-test-coverage-v012/spec.md`

## Summary

Implement 96 critical tests to unblock v0.12.0 release using adversarial red team approach. Two parallel tracks: (1) Sparse-checkout infrastructure tests (46 tests across 6 suites) validating git operations, auto-commit synchronization, and multi-agent workflows, and (2) Documentation mission distribution tests (50 tests across 3 files) validating PyPI package behavior without SPEC_KITTY_TEMPLATE_ROOT bypass. Risk-first testing prioritizes edge cases, concurrency scenarios, and distribution packaging to surface implementation bugs early. All tests must pass before v0.12.0 ships - zero tolerance for failures.

**Technical Approach**: Adversarial testing with fail-fast methodology. Tests execute against installed spec-kitty CLI (pip install -e ~/Code/spec-kitty). Test writer references implementation code at ~/Code/spec-kitty for understanding behavior but tests invoke commands and validate outcomes. Any test failure triggers immediate investigation, root cause analysis, and either test correction or spec-kitty bug fix in source repository. Implementation bugs are fixed before continuing test development.

**Key Innovation**: Distribution tests explicitly remove SPEC_KITTY_TEMPLATE_ROOT to simulate exact PyPI user environment, preventing repeat of Issues #62-64 (323 tests passed locally, 100% PyPI users failed due to template path divergence).

## Technical Context

**Language/Version**: Python 3.11+ (spec-kitty requirement)
**Primary Dependencies**: pytest ≥8.4.2, pytest-anyio ≥4.11.0, spec-kitty v0.11.0+ (installed via pip install -e ~/Code/spec-kitty)
**Storage**: File system (temporary test projects created in /tmp, auto-cleanup via tempfile.TemporaryDirectory)
**Testing**: pytest framework with existing fixtures from tests/conftest.py
**Target Platform**: macOS (Darwin 24.5.0) primary development, Linux CI/CD secondary
**Project Type**: Test suite (not application) - tests live in tests/functional/ and tests/distribution/
**Performance Goals**: Test execution <15 minutes total for all 546 tests (450 existing + 96 new), individual test suites <5 minutes
**Constraints**: Tests must be deterministic (zero flaky tests), no external dependencies (offline-capable), automatic cleanup (no orphaned processes/temp files)
**Scale/Scope**: 96 new tests (46 sparse-checkout + 50 documentation mission), integrating with ~450 existing tests, ≥95% pass rate required for release

**Testing Philosophy**: Adversarial red team approach - intentionally break spec-kitty implementation
- Fail fast: Any test failure stops progress, investigate immediately
- Root cause: Determine if spec-kitty bug vs test bug
- Fix upstream: Bugs in ~/Code/spec-kitty fixed before continuing
- Document findings: findings/test-infrastructure/v0.12.0-bugs-found.md
- Zero tolerance: All 96 tests must pass, no xfails, no workarounds

**Parallel Development Strategy**:
- Track 1: Sparse-checkout infrastructure (46 tests) - one developer/agent
- Track 2: Documentation mission distribution (50 tests) - another developer/agent
- Risk-first within tracks: Edge cases, concurrency, distribution packaging before happy paths
- Synchronization: Both tracks review findings/, coordinate on spec-kitty bug fixes

**Test Environment Setup**:
- Script: scripts/setup-test-env.sh
- Validates: spec-kitty installed (pip show spec-kitty), version ≥0.11.0, Git ≥2.25
- Fixtures: spec_kitty_repo_root (locates ~/Code/spec-kitty), spec_kitty_version (version gating)
- Cleanup: clean_env fixture restores environment after each test

## Constitution Check

**Status**: No constitution file exists at `.kittify/memory/constitution.md`

This section is skipped. No project-specific constraints or architectural principles to validate against.

## Project Structure

### Documentation (this feature)

```
kitty-specs/001-critical-test-coverage-v012/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 output (minimal - specs comprehensive)
├── data-model.md        # Phase 1 output (test entities)
├── quickstart.md        # Phase 1 output (developer onboarding)
├── checklists/
│   └── requirements.md  # Spec validation (completed, all passed)
└── tasks/               # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Test Files (repository root)

```
tests/
├── conftest.py                    # Global fixtures (existing - reuse)
│   ├── spec_kitty_repo_root       # Locates ~/Code/spec-kitty
│   ├── spec_kitty_version         # Version tuple (major, minor, patch)
│   ├── temp_project_dir           # Temporary directory with cleanup
│   ├── clean_env                  # Environment restoration (autouse)
│   └── requires_v011              # Skip if version < 0.11.0
│
├── functional/                    # Development workflow tests
│   ├── test_sparse_checkout_infrastructure.py  # 46 tests (NEW)
│   │   ├── TestWorktreeCreation                # Suite 1: 8 tests
│   │   ├── TestPathResolution                  # Suite 2: 6 tests
│   │   ├── TestAutoCommitSynchronization       # Suite 3: 10 tests
│   │   ├── TestMultiAgentParallel              # Suite 4: 8 tests
│   │   ├── TestCleanMergeBehavior              # Suite 5: 6 tests
│   │   └── TestEdgeCases                       # Suite 6: 8 tests
│   │
│   └── test_documentation_mission_end_to_end.py  # 15 tests (NEW)
│       ├── TestInitialMode                     # First-time documentation
│       ├── TestGapFillingMode                  # Existing docs analysis
│       ├── TestFrameworkDetection              # Sphinx/MkDocs/etc
│       ├── TestDivioClassification             # Tutorial/howto/reference/explanation
│       └── TestStatePersistence                # meta.json survival
│
└── distribution/                  # PyPI user workflow tests
    ├── test_documentation_mission_distribution.py  # 20 tests (NEW)
    │   ├── TestMissionLoading                  # Mission from package
    │   ├── TestWorkflowPhases                  # 6 phases correct
    │   ├── TestCommandTemplates                # 5 templates accessible
    │   └── TestDivioTemplates                  # 4 template types present
    │
    └── test_doc_generators_distribution.py     # 15 tests (NEW)
        ├── TestJSDocGenerator                  # JavaScript/TypeScript detection
        ├── TestSphinxGenerator                 # Python detection
        └── TestRustdocGenerator                # Rust detection

scripts/
└── setup-test-env.sh              # Environment validation (NEW)
    ├── Check spec-kitty installed
    ├── Validate version ≥0.11.0
    ├── Check Git ≥2.25
    └── Set up test project structure
```

**Structure Decision**: Test-centric repository. Tests organized by test type (functional vs distribution) and feature area (sparse-checkout vs documentation mission). Each test file is self-contained with class-based organization. Existing conftest.py fixtures reused for consistency. New tests follow patterns from test_comprehensive_workspace_per_wp.py (functional) and test_user_experience_simulation.py (distribution).

## Complexity Tracking

Not applicable - standard test implementation with no architectural violations.

---

## Phase 0: Research

**Status**: Minimal research required - specification already comprehensive

The specification was created with extensive codebase analysis:
- Sparse-checkout implementation analyzed: implement.py:596-642, tasks.py, workflow.py, paths.py
- Documentation mission structure documented: mission.yaml, generators, gap_analysis.py, doc_state.py
- Test infrastructure patterns reviewed: conftest.py, existing test patterns

### Outstanding Research Items

1. **Distribution Test Fixture Patterns**
   - **Question**: Verify clean_environment fixture pattern from test_user_experience_simulation.py
   - **Why**: Need to confirm exact env var removal pattern for distribution tests
   - **Resolution**: Read tests/distribution/test_user_experience_simulation.py and extract clean_environment fixture

2. **Sparse-Checkout Test Validation Approach**
   - **Question**: How to validate .git/info/sparse-checkout file contents without filesystem coupling
   - **Why**: Tests should validate behavior, not implementation details
   - **Resolution**: Run spec-kitty commands, verify kitty-specs/ absence in worktree, check git status output

3. **Multi-Agent Test Simulation Strategy**
   - **Question**: How to simulate concurrent agents without actual parallel test execution
   - **Why**: Need deterministic tests, not timing-dependent race conditions
   - **Resolution**: Sequential simulation: Agent A action → verify commit → Agent B action → verify sees A's commit

### Research Output

**Decision 1: Environment Fixture Pattern**
```python
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
**Rationale**: Explicitly remove all SPEC_KITTY_* vars except API_KEY. This simulates PyPI user who has no development environment variables.

**Decision 2: Sparse-Checkout Validation**
```python
# Don't read .git/info/sparse-checkout directly
# Instead, validate observable behavior:
assert not (worktree_path / 'kitty-specs').exists()
assert (main_repo / 'kitty-specs').exists()

# Validate via git commands:
result = subprocess.run(['git', 'ls-files', 'kitty-specs/'],
                       cwd=worktree_path, capture_output=True)
assert result.stdout == b''  # No kitty-specs files tracked in worktree
```
**Rationale**: Test behavior, not implementation. If kitty-specs/ doesn't exist in worktree and isn't tracked by git, sparse-checkout is working regardless of .git/info/sparse-checkout format.

**Decision 3: Multi-Agent Simulation**
```python
# Sequential simulation with verification between steps:
# 1. Agent A claims WP01
subprocess.run(['spec-kitty', 'workflow', 'implement', 'WP01', '--agent=AgentA'],
               cwd=worktree_a, check=True)

# 2. Verify commit to main
commits = subprocess.run(['git', 'log', '-1', '--format=%s'],
                        cwd=main_repo, capture_output=True, text=True)
assert 'AgentA' in commits.stdout

# 3. Agent B reads from main (not their worktree)
tasks_content = (main_repo / 'kitty-specs' / 'feature' / 'tasks.md').read_text()
assert 'WP01' in tasks_content
assert 'in_progress' in tasks_content
```
**Rationale**: Deterministic, no timing dependencies. Validates actual synchronization mechanism (auto-commit to main, read from main) without race conditions.

---

## Phase 1: Design

### Data Model

**Primary Entities** (from spec.md Key Entities section):

**Test Suite**
```
Attributes:
- suite_name: string (e.g., "Suite 1: Worktree Creation")
- test_count: integer (e.g., 8)
- test_file: Path (e.g., tests/functional/test_sparse_checkout_infrastructure.py)
- priority: enum(CRITICAL, HIGH, MEDIUM)
- status: enum(not_started, in_progress, complete)
- pass_rate: float (0.0-1.0)

Relationships:
- Contains many Test Cases (composition)
- Part of Test Phase (Phase 1 or Phase 2)
- Validates Implementation Code (references ~/Code/spec-kitty files)

Example:
Suite 1: Worktree Creation
- 8 tests in TestWorktreeCreation class
- Priority: CRITICAL (blocks release)
- Validates: implement.py:596-642 (sparse-checkout config)
```

**Test Case**
```
Attributes:
- test_name: string (e.g., "test_sparse_checkout_excludes_kitty_specs")
- docstring: string (what tested, why matters, related issues)
- implementation_reference: string (e.g., "implement.py:596-642")
- expected_behavior: string (what should happen)
- assertion_count: integer (number of assertions)
- execution_time: float (seconds)

Relationships:
- Part of Test Suite (aggregation)
- Validates Functional Requirement (FR-001 through FR-007)
- Uses Test Fixtures (spec_kitty_repo_root, temp_project_dir, etc.)

Example:
test_sparse_checkout_excludes_kitty_specs
- Validates: FR-001 Suite 1
- Uses: temp_project_dir, init_spec_kitty_project fixtures
- Asserts: kitty-specs/ not in worktree, present in main repo
- Reference: implement.py:596-642 (where sparse-checkout configured)
```

**Test Fixture**
```
Attributes:
- fixture_name: string (e.g., "spec_kitty_repo_root")
- scope: enum(session, function, class, module)
- cleanup_required: boolean
- dependencies: list[string] (other fixtures required)

Relationships:
- Defined in conftest.py (central location)
- Used by many Test Cases (shared dependency)
- May depend on other Fixtures (fixture chain)

Example:
init_spec_kitty_project (function scope)
- Returns: Factory function for creating test projects
- Cleanup: Handled by temp_project_dir fixture
- Dependencies: [spec_kitty_repo_root, temp_project_dir]
- Usage: project = init_spec_kitty_project("test-project")
```

**Implementation Code** (reference only, not created by tests)
```
Attributes:
- file_path: string (e.g., "~/Code/spec-kitty/src/specify_cli/cli/commands/implement.py")
- line_range: string (e.g., "596-642")
- function_name: string (e.g., "create_feature_worktree")
- behavior: string (description of what code does)
- version: string (e.g., "v0.12.0")

Relationships:
- Tested by Test Cases (validation target)
- Located in spec-kitty repository (read-only for test writer)
- Part of Feature Release (v0.12.0)

Example:
implement.py:596-642
- Function: create_feature_worktree (sparse-checkout config)
- Behavior: Sets git config, writes sparse-checkout patterns, applies to worktree
- Tested by: Suite 1 (8 tests), Suite 5 (6 tests)
```

**Distribution Test** (specialized Test Case subtype)
```
Attributes (inherited + specialized):
- test_name: string
- environment_clean: boolean (SPEC_KITTY_TEMPLATE_ROOT removed - MUST be true)
- package_mode: boolean (tests pip package, not local repo)
- template_source: enum(package, local_repo) - MUST be package for distribution tests
- simulates_pypi_user: boolean (MUST be true)

Relationships:
- Subtype of Test Case (is-a relationship)
- Validates Package Behavior (not just code correctness)
- Prevents Path-Based Divergence (Issues #62-64 scenario)

Example:
test_documentation_mission_loads_from_package
- Environment: clean_environment fixture (no SPEC_KITTY_TEMPLATE_ROOT)
- Validates: Templates load via importlib.resources
- Would catch: Issues #62-64 (local works, package fails)
```

**Test Phase**
```
Attributes:
- phase_number: integer (1 or 2)
- phase_name: string (e.g., "Phase 1: Critical - Blocking Release")
- test_count: integer (e.g., 96 for Phase 1)
- priority: enum(CRITICAL, HIGH, MEDIUM)
- estimated_effort: string (e.g., "13-19 hours")
- completion_criteria: string (e.g., "46/46 sparse-checkout + 50/50 documentation tests passing")

Relationships:
- Contains multiple Test Suites (composition)
- Blocks Release if Phase 1 (critical dependency)
- Has Completion Criteria (quality gate)

Example:
Phase 1: Critical
- 96 tests total: sparse-checkout (46) + documentation (50)
- Priority: CRITICAL (blocks v0.12.0 release)
- Completion: All tests pass, no xfails, bugs fixed in spec-kitty
```

### API Contracts

Not applicable - tests do not expose APIs. Tests invoke spec-kitty CLI commands via subprocess.run() and validate outcomes.

**Command Contracts** (what tests execute):

1. **spec-kitty init** - Creates new project
   - Input: project name, --ai=agent, --ignore-agent-tools
   - Output: Exit code 0, .kittify directory created, templates installed
   - Validation: Assert returncode == 0, assert paths exist

2. **spec-kitty workflow implement WP##** - Claims work package
   - Input: WP ID, --agent=name
   - Output: Exit code 0, commit to main branch, activity log updated
   - Validation: Assert commit message contains agent name, assert WP status in_progress

3. **spec-kitty agent task move-task WP## to for_review** - Moves WP between lanes
   - Input: WP ID, target lane
   - Output: Exit code 0, WP file updated in main repo, commit created
   - Validation: Assert WP file location changed, assert commit message correct

4. **git** commands - Validate sparse-checkout and worktree state
   - git ls-files kitty-specs/ (should return empty in worktree)
   - git config core.sparseCheckout (should return true)
   - git log -1 --format=%s (validate commit messages)

### Test Execution Flow

**Parallel Track Structure**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Track 1: Sparse-Checkout                  │
│                    Developer/Agent A                          │
├─────────────────────────────────────────────────────────────┤
│ Suite 6 (Edge Cases)         [Risk-first: 8 tests]          │
│   ├─ Corrupted sparse-checkout file                          │
│   ├─ Permission errors                                       │
│   ├─ Concurrent commits                                      │
│   └─ Migration scenarios                                     │
│                                                               │
│ Suite 4 (Multi-Agent)         [Risk-first: 8 tests]         │
│   ├─ Parallel agent synchronization                          │
│   ├─ Status visibility                                       │
│   └─ PID tracking                                            │
│                                                               │
│ Suite 3 (Auto-Commit)         [Core: 10 tests]              │
│   ├─ move-task commits                                       │
│   ├─ mark-status commits                                     │
│   └─ workflow commands commit                                │
│                                                               │
│ Suite 1 (Worktree Creation)  [Foundation: 8 tests]          │
│   ├─ Sparse-checkout config                                  │
│   ├─ kitty-specs/ exclusion                                  │
│   └─ Git config settings                                     │
│                                                               │
│ Suite 2 (Path Resolution)    [Integration: 6 tests]         │
│   └─ Main repo detection from worktrees                      │
│                                                               │
│ Suite 5 (Merge)               [Git ops: 6 tests]            │
│   └─ Clean merges without conflicts                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               Track 2: Documentation Mission                 │
│                    Developer/Agent B                          │
├─────────────────────────────────────────────────────────────┤
│ test_doc_generators_distribution.py [Risk-first: 15 tests]  │
│   ├─ JSDoc from package (not local)                         │
│   ├─ Sphinx from package                                     │
│   ├─ rustdoc from package                                    │
│   └─ No template path leakage                                │
│                                                               │
│ test_documentation_mission_distribution.py [Core: 20 tests]  │
│   ├─ Mission loads from package                              │
│   ├─ Templates via importlib.resources                       │
│   ├─ NO SPEC_KITTY_TEMPLATE_ROOT                            │
│   └─ Would catch Issues #62-64                               │
│                                                               │
│ test_documentation_mission_end_to_end.py [E2E: 15 tests]    │
│   ├─ Initial mode workflow                                   │
│   ├─ Gap-filling mode                                        │
│   ├─ Framework detection                                     │
│   └─ State persistence                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Synchronization Points                     │
├─────────────────────────────────────────────────────────────┤
│ 1. findings/ directory - both tracks document bugs found     │
│ 2. spec-kitty bug fixes - coordinate fixes, both re-test     │
│ 3. Daily sync - progress, blockers, shared learnings         │
│ 4. Final integration - both tracks complete, run full suite  │
└─────────────────────────────────────────────────────────────┘
```

**Risk-First Rationale**:
- Track 1 starts with edge cases (Suite 6) to surface corruption scenarios early
- Track 1 then tests multi-agent (Suite 4) to catch synchronization bugs
- Track 2 starts with distribution tests (generators, mission loading) to catch packaging issues immediately
- Both tracks hit highest-risk areas first before investing in happy-path tests

**Fail-Fast Checkpoints**:
- After Suite 6 (Edge Cases): Verify corruption recovery works before trusting auto-commit
- After Suite 4 (Multi-Agent): Verify synchronization works before assuming Suite 3 auto-commits are visible
- After distribution tests: Verify packaging correct before testing workflows that depend on templates

### Development Environment Setup

**Script**: `scripts/setup-test-env.sh`

```bash
#!/bin/bash
# Test environment validation and setup
set -e

echo "🔍 Validating test environment..."

# 1. Check spec-kitty installed
if ! command -v spec-kitty &> /dev/null; then
    echo "❌ spec-kitty not found. Install with: pip install -e ~/Code/spec-kitty"
    exit 1
fi

# 2. Check version ≥0.11.0
VERSION=$(spec-kitty --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo $VERSION | cut -d. -f1)
MINOR=$(echo $VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 0 ] || { [ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 11 ]; }; then
    echo "❌ spec-kitty version $VERSION too old (need ≥0.11.0)"
    exit 1
fi

echo "✅ spec-kitty version $VERSION"

# 3. Check Git version ≥2.25 (sparse-checkout support)
GIT_VERSION=$(git --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
GIT_MAJOR=$(echo $GIT_VERSION | cut -d. -f1)
GIT_MINOR=$(echo $GIT_VERSION | cut -d. -f2)

if [ "$GIT_MAJOR" -lt 2 ] || { [ "$GIT_MAJOR" -eq 2 ] && [ "$GIT_MINOR" -lt 25 ]; }; then
    echo "❌ Git version $GIT_VERSION too old (need ≥2.25 for sparse-checkout)"
    exit 1
fi

echo "✅ Git version $GIT_VERSION"

# 4. Check ~/Code/spec-kitty exists (for test writer reference)
if [ ! -d "$HOME/Code/spec-kitty" ]; then
    echo "⚠️  ~/Code/spec-kitty not found. Test writer needs this for code reference."
    echo "   Clone with: git clone <repo-url> ~/Code/spec-kitty"
    exit 1
fi

echo "✅ ~/Code/spec-kitty found"

# 5. Check git user config (required for commits in tests)
if [ -z "$(git config user.name)" ] || [ -z "$(git config user.email)" ]; then
    echo "❌ Git user.name/email not configured. Set with:"
    echo "   git config --global user.name 'Your Name'"
    echo "   git config --global user.email 'you@example.com'"
    exit 1
fi

echo "✅ Git user configured"

echo ""
echo "✅ Test environment ready!"
echo ""
echo "Run tests with:"
echo "  pytest tests/functional/test_sparse_checkout_infrastructure.py -xvs"
echo "  pytest tests/distribution/test_documentation_mission_distribution.py -xvs"
echo "  pytest tests/ -v  # Full suite"
```

**Quickstart Documentation**: See `quickstart.md` (generated in next step)

---

## Phase 2: Task Generation

**NOT EXECUTED BY THIS COMMAND**

Tasks will be generated by running `/spec-kitty.tasks` after plan approval.

Task structure will include:
- Work Package 01: Test environment setup + Suite 6 (Edge Cases - risk first)
- Work Package 02: Suite 4 (Multi-Agent) + Suite 3 (Auto-Commit)
- Work Package 03: Suite 1 (Worktree Creation) + Suite 2 (Path Resolution)
- Work Package 04: Suite 5 (Merge)
- Work Package 05: Documentation mission distribution tests (test_doc_generators_distribution.py)
- Work Package 06: Documentation mission loading tests (test_documentation_mission_distribution.py)
- Work Package 07: Documentation mission end-to-end tests (test_documentation_mission_end_to_end.py)
- Work Package 08: Regression testing + findings documentation

---

## Implementation Notes

### Test Writing Guidelines

**1. Every test must include**:
```python
def test_sparse_checkout_excludes_kitty_specs(temp_project_dir, init_spec_kitty_project):
    """
    Test: kitty-specs/ excluded from worktree working directory

    Why: Sparse-checkout foundation - if kitty-specs/ present in worktree,
    auto-commit synchronization breaks (each worktree has divergent state).

    Reference: implement.py:596-642 (sparse-checkout configuration)
    Related: Issues #62-64 (template divergence pattern)
    """
    # Test implementation...
```

**2. Assertion messages with context**:
```python
assert not worktree_kitty_specs.exists(), (
    f"kitty-specs/ should not exist in worktree\n"
    f"Worktree path: {worktree_path}\n"
    f"Expected: kitty-specs/ absent (sparse-checkout)\n"
    f"Actual: {list(worktree_path.glob('*'))}\n"
    f"Git config: {git_config_output}"
)
```

**3. Distribution test pattern**:
```python
def test_documentation_mission_loads_from_package(clean_environment):
    """Distribution test - simulates PyPI user (NO SPEC_KITTY_TEMPLATE_ROOT)"""
    # CRITICAL: clean_environment fixture removes SPEC_KITTY_TEMPLATE_ROOT
    # This simulates exact PyPI user experience
    # Would catch Issues #62-64 (local works, package fails)

    from specify_cli.mission import get_mission_by_name

    mission = get_mission_by_name("documentation")
    assert mission is not None, (
        "Documentation mission should load from installed package\n"
        "Environment vars removed: SPEC_KITTY_TEMPLATE_ROOT, SPEC_KITTY_REPO\n"
        "This simulates PyPI user without local repo\n"
        "If this fails, templates not bundled in package (Issues #62-64 repeat)"
    )
```

**4. Fail-fast investigation**:
```python
# When test fails:
# 1. Determine root cause: spec-kitty bug or test bug?
# 2. If spec-kitty bug:
#    - Document in findings/test-infrastructure/v0.12.0-bugs-found.md
#    - Fix in ~/Code/spec-kitty
#    - Verify fix works
#    - Continue test development
# 3. If test bug:
#    - Fix test
#    - Ensure test validates correct behavior
#    - Continue
```

### Synchronization Between Tracks

**Shared Resources**:
- `findings/test-infrastructure/v0.12.0-bugs-found.md` - Both tracks document bugs
- `~/Code/spec-kitty` - Both tracks may fix bugs here (coordinate to avoid conflicts)

**Communication Protocol**:
- Daily sync: Progress, blockers, bugs found, shared learnings
- Bug coordination: "I'm fixing bug X in implement.py" before starting
- Test pattern sharing: "I found a good way to validate Y"
- Final integration: Both tracks complete → run full suite together

### Success Validation

**Track 1 Complete When**:
- All 46 sparse-checkout tests implemented
- pytest tests/functional/test_sparse_checkout_infrastructure.py -v shows 46/46 PASSED
- Execution time <5 minutes
- Zero xfails, zero skips
- All spec-kitty bugs found during testing are fixed

**Track 2 Complete When**:
- All 50 documentation mission tests implemented
- pytest tests/distribution/test_documentation_mission_*.py -v shows 50/50 PASSED
- pytest tests/functional/test_documentation_mission_end_to_end.py -v shows 15/15 PASSED
- Execution time <3 minutes for distribution, <2 minutes for end-to-end
- Zero xfails, zero skips
- All spec-kitty bugs found during testing are fixed

**Overall Feature Complete When**:
- Both tracks complete
- pytest tests/ -v shows ≥519/546 PASSED (≥95% pass rate)
- Test execution time <15 minutes
- findings/test-infrastructure/v0.12.0-bugs-found.md documents all bugs found and fixed
- v0.12.0 release unblocked - implementation robust under adversarial testing