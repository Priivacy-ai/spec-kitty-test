# Implementation Plan: Comprehensive Post-JJ-Rollback Test Suite

**Branch**: `006-comprehensive-post-jj-rollback-test-suite` | **Date**: 2026-01-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/006-comprehensive-post-jj-rollback-test-suite/spec.md`

## Summary

Create comprehensive adversarial test suite covering all spec-kitty changes since 2026-01-19, using three-tier testing strategy:
1. **Unit tests (functional)** - Fast tests with mocking for rapid iteration
2. **Integration tests** - Real orchestration against spec-kitty-git-test harness
3. **Distribution tests** - PyPI install validation without environment bypasses

The suite validates 5 equally-critical risk areas: orchestrator corruption, VCS abstraction bugs, data loss scenarios, distribution/packaging failures, and integration breakage. Testing philosophy is skeptical and protective: assume implementation team made mistakes and hunt for bugs before they reach users.

**Technical Approach**: Extend existing pytest infrastructure with new subdirectories for orchestrator, VCS abstraction, and data loss tests. Leverage spec-kitty's `detect_installed_agents()` for adaptive real agent testing. Use `/Users/robert/Code/spec-kitty-git-test` as repeatable integration test harness with reset capability.

## Technical Context

**Language/Version**: Python 3.11+ (matches existing test suite)
**Primary Dependencies**:
- pytest 8.4.2 (existing)
- pytest-playwright 0.7.1 (existing, for dashboard tests if needed)
- pytest-anyio 4.11.0 (existing)
- No new dependencies required

**Storage**: N/A (test data in temp directories, fixtures in conftest.py)

**Testing**: pytest with three-tier strategy:
- **Functional**: Unit tests with subprocess.run mocking, fast execution (<10 min)
- **Integration**: Real orchestration using spec-kitty-git-test harness
- **Distribution**: PyPI install validation without `SPEC_KITTY_TEMPLATE_ROOT` bypass

**Target Platform**: Unix-like systems (Linux, macOS) per constitution

**Project Type**: Test suite (extends existing tests/ directory structure)

**Performance Goals**:
- Functional tests complete in <10 minutes
- Distribution tests complete in <45 minutes
- Integration tests adaptive based on agent availability

**Constraints**:
- Must not modify spec-kitty source code (report bugs via findings/)
- Must use existing test infrastructure (no new frameworks)
- Must support agent auto-detection (tests run with whichever agents installed)

**Scale/Scope**:
- 67 acceptance scenarios across 10 user stories
- 57 functional requirements
- 30+ edge cases across 6 categories
- Coverage target: >85% for changed modules (detection.py, implement.py, orchestrator/*, merge.py, stale_detection.py)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Alignment with Constitution

✅ **Adversarial Testing Philosophy**: Suite designed to actively break spec-kitty with edge cases and failure scenarios

✅ **Separation of Concerns**: No edits to spec-kitty source; bugs reported via findings/ directory

✅ **Dual Testing Strategy**: Implements both functional and distribution tests per constitution requirements

✅ **Python 3.11+**: Matches existing suite requirements

✅ **pytest Framework**: Uses existing pytest 8.4.2 infrastructure

✅ **Findings Directory Canon**: Bug reports will use `findings/{version}/YYYY-MM-DD_NN_name.md` format

✅ **Platform Requirements**: Unix-like systems only (Linux, macOS)

### Constitution Compliance

**No violations detected.** This feature extends existing test infrastructure using established patterns and follows all constitutional principles.

## Project Structure

### Documentation (this feature)

```
kitty-specs/006-comprehensive-post-jj-rollback-test-suite/
├── spec.md              # Feature specification
├── plan.md              # This file (implementation plan)
├── data-model.md        # Phase 1: Test entities and fixtures
├── quickstart.md        # Phase 1: Running the tests
├── contracts/           # Phase 1: Fixture interfaces, marker definitions
│   ├── fixtures.py      # Test fixture protocols
│   └── markers.py       # pytest marker definitions
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks/               # Phase 2: Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/
├── conftest.py                          # Existing: Shared fixtures
├── functional/                          # Existing: Fast tests with TEMPLATE_ROOT bypass
│   ├── orchestrator/                    # NEW: Orchestrator unit tests
│   │   ├── conftest.py                  # Orchestrator-specific fixtures
│   │   ├── test_state_machine.py        # State transitions, idempotency
│   │   ├── test_agent_selection.py      # Agent detection, aliases, fallback
│   │   ├── test_dependency_graph.py     # Topological sort, circular detection
│   │   ├── test_parallel_execution.py   # Concurrency, race conditions
│   │   └── test_resume.py               # Interruption recovery
│   ├── vcs_abstraction/                 # NEW: VCS isolation unit tests
│   │   ├── conftest.py                  # VCS mocking fixtures
│   │   ├── test_git_path.py             # Git implementation path
│   │   ├── test_jj_disabled.py          # JJ detection always False
│   │   ├── test_vcs_factory.py          # VCS selection logic
│   │   └── test_mixed_features.py       # Multiple features, different VCS
│   ├── data_loss/                       # NEW: Data preservation unit tests
│   │   ├── test_worktree_cleanup.py     # Merge cleanup boundaries
│   │   ├── test_main_repo_usage.py      # kitty-specs path resolution
│   │   └── test_conflict_resolution.py  # Status file auto-resolution
│   └── [existing functional tests...]
│
├── integration/                         # NEW: Real orchestration tests
│   ├── conftest.py                      # spec-kitty-git-test fixtures
│   ├── test_real_orchestration.py       # Full orchestration cycles
│   ├── test_agent_integration.py        # Real agent invocations
│   └── test_state_persistence.py        # orchestration-state.json validation
│
├── distribution/                        # Existing: PyPI user experience tests
│   ├── conftest.py                      # Existing: no_template_bypass fixture
│   ├── orchestrator/                    # NEW: Orchestrator distribution tests
│   │   ├── test_fresh_install.py        # Init → orchestrate workflow
│   │   └── test_agent_detection.py      # Agent availability from package
│   ├── vcs_abstraction/                 # NEW: VCS distribution tests
│   │   ├── test_jj_rollback.py          # JJ never invoked despite install
│   │   └── test_legacy_conversion.py    # Auto jj→git conversion
│   ├── templates_migrations/            # NEW: Template/migration tests
│   │   ├── test_template_bundling.py    # Wheel contains all templates
│   │   ├── test_migration_execution.py  # All migrations run successfully
│   │   └── test_mission_templates.py    # Mission-specific templates
│   └── [existing distribution tests...]
│
├── test_upgrade/                        # Existing: Migration tests
└── agentic/                             # Existing: Agentic workflow tests
```

**Structure Decision**: Extends existing three-tier structure (functional, integration, distribution) with new subdirectories for orchestrator, VCS abstraction, and data loss scenarios. Integration tier is new, specifically for real orchestration against spec-kitty-git-test harness.

## Complexity Tracking

*No constitution violations - this section is not needed.*

## Phase 0: Research

### Research Questions

No significant research required. All technical decisions resolved during planning interrogation:

1. **Test organization** - RESOLVED: Option B (new subdirectories under existing structure)
2. **Mock strategy** - RESOLVED: Option C (hybrid real agents + mocks with auto-detection)
3. **Test harness** - RESOLVED: Use `/Users/robert/Code/spec-kitty-git-test` with reset capability

### Deferred Research

The following will be determined during implementation (WP-level decisions):
- Specific subprocess.run mocking patterns for VCS command logging
- JSON schema validation approach for orchestration-state.json
- pytest marker naming conventions for agent requirements

## Phase 1: Architecture & Design

### Overview

Three-tier test architecture with adaptive agent detection:

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Execution                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Functional  │  │ Integration  │  │  Distribution   │  │
│  │   (mocked)   │  │  (real run)  │  │  (PyPI pkg)     │  │
│  │   <10 min    │  │   adaptive   │  │   <45 min       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼──────────────────┼───────────────────┼───────────┘
          │                  │                   │
          ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Fixture Layer                            │
│  • spec_kitty_project (existing)                            │
│  • no_template_bypass (existing)                            │
│  • spec_kitty_git_test (NEW - points to test harness)       │
│  • reset_test_harness (NEW - runs cleanup script)           │
│  • mock_subprocess_run (NEW - VCS command logging)          │
│  • detect_available_agents (NEW - runtime detection)        │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Detection Layer                          │
│  from specify_cli.orchestrator.agents import                │
│     detect_installed_agents, AGENT_REGISTRY                 │
│                                                              │
│  Markers: @pytest.mark.requires_agent("claude")             │
│           @pytest.mark.requires_agent("opencode")           │
│           Auto-skip if agent not installed                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Agent Availability Detection**
   - Import `detect_installed_agents()` from spec-kitty orchestrator
   - Create `@pytest.mark.requires_agent(name)` marker
   - Auto-skip tests when required agent not available
   - Follows existing `@pytest.mark.jj` pattern

2. **VCS Command Logging**
   - Mock `subprocess.run` at test level
   - Log all invoked commands to list
   - Assert no `jj` commands when jj disabled
   - Assert only git commands in git-only paths

3. **Test Harness Integration**
   - Fixture provides path: `/Users/robert/Code/spec-kitty-git-test`
   - Reset fixture runs `cleanup-bookmarks.sh` before test
   - Validate orchestration-state.json after orchestration
   - Check worktrees, commits, git log for real outcomes

4. **State Machine Validation**
   - JSON schema validation for orchestration-state.json
   - State transition table verification
   - Idempotency tests (call same transition twice)

### Data Model

See `data-model.md` for detailed entity definitions.

### API Contracts

See `contracts/` directory for:
- `fixtures.py` - Pytest fixture protocols
- `markers.py` - Custom marker definitions

### Quickstart Guide

See `quickstart.md` for:
- Running functional tests
- Running integration tests (requires spec-kitty-git-test)
- Running distribution tests
- Agent-specific test execution

## Implementation Notes

### Work Package Strategy

Tests organized into work packages by risk area:
- **WP01-WP02**: Distribution test foundation (fresh install, templates, migrations)
- **WP03-WP04**: Orchestrator unit tests (state machine, agent selection)
- **WP05-WP06**: VCS abstraction tests (git/jj isolation, rollback validation)
- **WP07**: Data loss prevention tests
- **WP08-WP09**: Integration tests (real orchestration, spec-kitty-git-test harness)
- **WP10**: Test infrastructure (fixtures, markers, conftest updates)
- **WP11**: CI/CD integration and documentation

Each WP is independently testable and can be implemented in parallel where dependencies allow.

### Success Validation

Before marking suite complete, verify:
- ✅ All 12 success criteria from spec.md pass
- ✅ Code coverage >85% for changed modules
- ✅ At least 3 real bugs discovered (validates adversarial approach)
- ✅ Zero false negatives in preflight validation tests
- ✅ All edge cases have corresponding test cases

## Next Steps

1. **DO NOT** proceed to `/spec-kitty.tasks` yet
2. Review this plan for completeness
3. User explicitly invokes `/spec-kitty.tasks` when ready
4. Tasks will break down implementation into parallelizable WPs
