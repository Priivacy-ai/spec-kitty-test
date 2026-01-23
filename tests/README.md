# Spec-Kitty Test Suite

This test suite validates the spec-kitty CLI tool, with a focus on preventing regressions
like the 0.10.8 catastrophe where 100% of PyPI users were affected despite 323 passing tests.

## Critical Testing Philosophy

**"Test what you ship, not just what you write."**

See `CLAUDE.md` in the repo root for the full story behind this testing philosophy.

## Structure

### Functional Tests (`tests/functional/`)

Fast unit tests with `SPEC_KITTY_TEMPLATE_ROOT` bypass for rapid iteration.
Target: **<10 minutes** total execution time.

#### Subdirectories (Feature 006):
- `orchestrator/` - State machine, agent selection, dependency graphs, parallelization
- `vcs_abstraction/` - Git/jj isolation, VCS factory, command logging
- `data_loss/` - Worktree cleanup, main repo usage, conflict resolution

### Integration Tests (`tests/integration/`) - NEW

Real orchestration against `spec-kitty-git-test` harness with actual agents.

**Requirements:**
- Path: `/Users/robert/Code/spec-kitty-git-test`
- Auto-skips if harness or agents unavailable
- Timing: Adaptive based on agent availability

### Distribution Tests (`tests/distribution/`)

PyPI user experience validation **without** environment bypasses.
Target: **<45 minutes** total execution time.

**CRITICAL:** These tests validate what real users experience when installing from PyPI.
They must NOT use `SPEC_KITTY_TEMPLATE_ROOT` or `SPEC_KITTY_REPO` bypasses.

#### Subdirectories (Feature 006):
- `orchestrator/` - Fresh install orchestration workflows
- `vcs_abstraction/` - JJ rollback validation, legacy conversion
- `templates_migrations/` - Template bundling, migration execution

## Test Markers

Feature 006 introduces these markers (defined in `kitty-specs/006-.../contracts/markers.py`):

| Marker | Description |
|--------|-------------|
| `@pytest.mark.functional` | Fast functional tests with mocked dependencies |
| `@pytest.mark.distribution` | Tests validating PyPI user experience (no TEMPLATE_ROOT bypass) |
| `@pytest.mark.integration` | Integration tests using real orchestration |
| `@pytest.mark.orchestrator` | Tests for orchestrator system |
| `@pytest.mark.vcs` | Tests for VCS abstraction |
| `@pytest.mark.data_loss` | Tests for data loss prevention |
| `@pytest.mark.jj` | Tests requiring jujutsu VCS |
| `@pytest.mark.adversarial` | Edge cases and corruption scenarios |
| `@pytest.mark.templates` | Tests for template bundling and resolution |
| `@pytest.mark.migrations` | Tests for migration execution and registry |
| `@pytest.mark.regression` | Regression tests for previously discovered bugs |
| `@pytest.mark.slow` | Test takes >30 seconds |
| `@pytest.mark.very_slow` | Test takes >2 minutes |
| `@pytest.mark.requires_agent("name")` | Requires specific agent (claude, opencode) |

## Running Tests

### Quick Start

```bash
# Run all functional tests (fast, <10 min)
pytest -m functional -v

# Run all distribution tests (validates PyPI experience, <45 min)
pytest -m distribution -v

# Run integration tests (real orchestration, auto-skips if unavailable)
pytest -m integration -v
```

### By Category

```bash
# Orchestrator tests only
pytest -m orchestrator -v

# VCS abstraction tests only
pytest -m vcs -v

# Data loss prevention tests only
pytest -m data_loss -v

# JJ-specific tests (skipped if jj not installed)
pytest -m jj -v
```

### By Directory

```bash
# Run specific test directory
pytest tests/functional/orchestrator/ -v
pytest tests/functional/vcs_abstraction/ -v
pytest tests/distribution/ -v
```

### Parallel Execution

```bash
# Run with parallel workers (requires pytest-xdist)
pytest -m functional -n auto -v

# Specify worker count
pytest -m functional -n 4 -v
```

### With Coverage

```bash
# Run with coverage report
pytest -m functional --cov --cov-report=term --cov-report=html

# Enforce coverage threshold (85%)
pytest -m functional --cov --cov-fail-under=85
```

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `SPEC_KITTY_REPO` | Path to spec-kitty source for functional tests | No (defaults to sibling dir) |
| `SPEC_KITTY_TEMPLATE_ROOT` | Template root bypass (functional tests only) | No |

**CRITICAL:** Distribution tests must NOT use these environment variables.

## CI/CD

GitHub Actions workflows are provided:
- `.github/workflows/test-functional.yml` - Functional tests (<10 min)
- `.github/workflows/test-distribution.yml` - Distribution tests (<45 min)
- `.github/workflows/test-integration.yml` - Integration tests (optional)

## Adding New Tests

1. **Functional tests**: Add to `tests/functional/` with `@pytest.mark.functional`
2. **Distribution tests**: Add to `tests/distribution/` with `@pytest.mark.distribution`
3. **Integration tests**: Add to `tests/integration/` with `@pytest.mark.integration`

Always ask yourself:
- Does this test validate what users experience?
- Should this also have a distribution test variant?
- Am I testing the package, or just the code?
