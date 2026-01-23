# Test Suite Quickstart Guide

**Feature**: Comprehensive Post-JJ-Rollback Test Suite
**Version**: 1.1.0
**Date**: 2026-01-23

## CI Status

![Functional Tests](https://github.com/anthropics/spec-kitty-test/workflows/Functional%20Tests/badge.svg)
![Distribution Tests](https://github.com/anthropics/spec-kitty-test/workflows/Distribution%20Tests/badge.svg)
![Integration Tests](https://github.com/anthropics/spec-kitty-test/workflows/Integration%20Tests/badge.svg)

## Overview

This guide explains how to run the comprehensive test suite covering spec-kitty changes since 2026-01-19. The suite uses a three-tier testing strategy:

1. **Functional Tests** - Fast unit tests with mocking (<10 minutes)
2. **Integration Tests** - Real orchestration using spec-kitty-git-test harness (adaptive timing)
3. **Distribution Tests** - PyPI install validation (<45 minutes)

## Prerequisites

### Required

- Python 3.11+
- Git installed and configured
- pytest 8.4.2+ (install via `pip install -r requirements.txt`)
- pytest-xdist 3.5.0+ (for parallel execution)
- pytest-cov 4.1.0+ (for coverage reporting)

### Optional (for specific test categories)

- **Integration tests**: Access to `/Users/robert/Code/spec-kitty-git-test`
- **Agent tests**: One or more AI coding agents installed (Claude, OpenCode, Codex, Copilot, Gemini, etc.)
- **JJ tests**: Jujutsu VCS installed (jj 0.20+)

## Quick Start

### 1. Install Dependencies

```bash
# From repository root
cd /Users/robert/Code/spec-kitty-test

# Install test dependencies
pip install -r requirements.txt

# Verify installation
pytest --version  # Should show 8.4.2+
```

### 2. Run Quick Smoke Test (Recommended First Run)

```bash
# Run functional tests only (fast, ~5-10 minutes)
pytest tests/functional/orchestrator/ \
       tests/functional/vcs_abstraction/ \
       tests/functional/data_loss/ \
       -v

# Expected: All tests pass or skip (if agents/jj not installed)
```

### 3. Run Full Functional Suite

```bash
# All functional tests (<10 minutes)
pytest -m functional -v

# With parallel execution (faster, requires pytest-xdist)
pytest -m functional -n auto -v

# With coverage report
pytest -m functional --cov=../spec-kitty/src/specify_cli --cov-report=html

# With coverage threshold enforcement (>85%)
pytest -m functional --cov=../spec-kitty/src/specify_cli --cov-fail-under=85
```

### 4. Run Distribution Tests

```bash
# All distribution tests (<45 minutes)
pytest -m distribution -v

# Critical distribution tests only (faster)
pytest tests/distribution/orchestrator/test_fresh_install.py \
       tests/distribution/vcs_abstraction/test_jj_rollback.py \
       tests/distribution/templates_migrations/ \
       -v
```

### 5. Run Integration Tests (Requires spec-kitty-git-test)

```bash
# Verify test harness exists
ls /Users/robert/Code/spec-kitty-git-test

# Run integration tests (timing varies by agent availability)
pytest -m integration -v

# Run specific integration test
pytest tests/integration/test_real_orchestration.py -v
```

## Test Organization

### By Test Tier

```bash
# Functional (unit tests, mocked)
pytest -m functional

# Integration (real orchestration)
pytest -m integration

# Distribution (PyPI user experience)
pytest -m distribution
```

### By Feature Area

```bash
# Orchestrator tests (all tiers)
pytest -m orchestrator

# VCS abstraction tests (all tiers)
pytest -m vcs

# Data loss prevention tests
pytest -m data_loss

# Template/migration tests
pytest -m "templates or migrations"
```

### By Agent Availability

```bash
# Tests requiring Claude Code
pytest -m requires_claude

# Tests requiring OpenCode
pytest -m requires_opencode

# Tests requiring any agent
pytest -m requires_agent
```

## Common Test Scenarios

### Scenario 1: Quick Development Iteration

**Use case**: Rapid feedback during test development

```bash
# Run only new tests in current file
pytest tests/functional/orchestrator/test_state_machine.py -v

# Run only failed tests from last run
pytest --lf -v

# Run tests matching name pattern
pytest -k "test_idempotent" -v
```

### Scenario 2: Pre-Commit Validation

**Use case**: Verify changes before committing

```bash
# Run functional + distribution (skip slow integration)
pytest -m "functional or distribution" -v

# With coverage check (>85% target)
pytest -m functional --cov=../spec-kitty/src/specify_cli \
       --cov-fail-under=85
```

### Scenario 3: Full CI/CD Validation

**Use case**: Complete test suite for CI pipeline

```bash
# Run everything
pytest -m "functional or integration or distribution" -v \
       --cov=../spec-kitty/src/specify_cli \
       --cov-report=html \
       --cov-report=term

# Generate JUnit XML for CI
pytest -m "functional or integration or distribution" \
       --junitxml=test-results.xml
```

### Scenario 4: Agent-Specific Testing

**Use case**: Test with specific agent installation

```bash
# Detect which agents are installed
python -c "from specify_cli.orchestrator.agents import detect_installed_agents; print(detect_installed_agents())"

# Run tests for installed agents only
pytest -m "requires_claude or requires_opencode" -v

# Skip agent tests entirely
pytest -m "not requires_agent" -v
```

### Scenario 5: Adversarial Testing Only

**Use case**: Focus on edge cases and corruption scenarios

```bash
# Run all adversarial tests
pytest -m adversarial -v

# Adversarial orchestrator tests only
pytest -m "adversarial and orchestrator" -v
```

## Environment Configuration

### Functional Tests

Functional tests use `SPEC_KITTY_TEMPLATE_ROOT` bypass for fast local testing:

```bash
# Set spec-kitty repo location (default: ../spec-kitty)
export SPEC_KITTY_REPO=/path/to/spec-kitty

# Run functional tests
pytest -m functional
```

### Distribution Tests

Distribution tests **must not** use environment bypasses:

```bash
# Ensure no bypass environment variables
unset SPEC_KITTY_TEMPLATE_ROOT
unset SPEC_KITTY_REPO

# Run distribution tests (validates real PyPI experience)
pytest -m distribution
```

### Integration Tests

Integration tests require access to spec-kitty-git-test harness:

```bash
# Verify harness exists
ls /Users/robert/Code/spec-kitty-git-test

# Tests will auto-skip if harness not found
pytest -m integration
```

## Filtering and Selection

### Exclude Slow Tests

```bash
# Exclude tests marked as slow
pytest -m "not slow and not very_slow"

# Run only fast functional tests
pytest -m "functional and not slow"
```

### Run Specific Risk Area

```bash
# Only orchestrator corruption tests
pytest tests/functional/orchestrator/ tests/integration/ -v

# Only VCS abstraction tests
pytest tests/functional/vcs_abstraction/ tests/distribution/vcs_abstraction/ -v

# Only data loss prevention tests
pytest tests/functional/data_loss/ -v
```

### Combine Multiple Criteria

```bash
# Functional orchestrator tests, not slow
pytest -m "functional and orchestrator and not slow" -v

# Distribution tests excluding templates
pytest -m "distribution and not templates" -v

# Integration tests requiring Claude
pytest -m "integration and requires_claude" -v
```

## Debugging Failed Tests

### Verbose Output

```bash
# Show detailed output
pytest -vv

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

### Capture Control

```bash
# Show print statements
pytest -s

# Show live log output
pytest --log-cli-level=DEBUG
```

### Selective Re-runs

```bash
# Re-run only failed tests
pytest --lf

# Re-run failed tests first, then others
pytest --ff
```

## Coverage Analysis

### Generate Coverage Report

```bash
# HTML report (opens in browser)
pytest -m functional --cov=../spec-kitty/src/specify_cli \
       --cov-report=html
open htmlcov/index.html

# Terminal report
pytest -m functional --cov=../spec-kitty/src/specify_cli \
       --cov-report=term-missing

# Focus on specific modules
pytest -m functional --cov=../spec-kitty/src/specify_cli/orchestrator \
       --cov-report=term
```

### Coverage Targets (from spec.md SC-008)

- **Overall**: >85% for changed modules
- **Critical modules**:
  - `detection.py` - VCS detection logic
  - `implement.py` - VCS abstraction paths
  - `orchestrator/*` - All orchestrator modules
  - `merge.py` - Merge preflight and cleanup
  - `stale_detection.py` - Staleness calculation

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  functional:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run functional tests
        run: pytest -m functional --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  distribution:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run distribution tests
        run: pytest -m distribution
        env:
          SPEC_KITTY_TEMPLATE_ROOT: ''
          SPEC_KITTY_REPO: ''

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Install agents (optional)
        run: |
          # Install available agents for integration testing
          # pip install claude-code opencode
      - name: Run integration tests
        run: pytest -m integration
        # Tests auto-skip if agents not installed
```

## Troubleshooting

### "No such file or directory: spec-kitty"

**Problem**: spec-kitty repo not found

**Solution**:
```bash
# Set SPEC_KITTY_REPO environment variable
export SPEC_KITTY_REPO=/path/to/spec-kitty

# Or clone spec-kitty to default location
git clone <repo-url> ../spec-kitty
```

### "spec-kitty-git-test not found"

**Problem**: Integration test harness not available

**Solution**:
```bash
# Integration tests will auto-skip if harness not found
# To run them, ensure harness exists:
ls /Users/robert/Code/spec-kitty-git-test

# Or skip integration tests:
pytest -m "not integration"
```

### "Agent X not installed" skips

**Problem**: Tests requiring specific agents are skipped

**Solution**:
```bash
# Check which agents are installed
python -c "from specify_cli.orchestrator.agents import detect_installed_agents; print(detect_installed_agents())"

# Install required agents, or skip agent tests:
pytest -m "not requires_agent"
```

### All distribution tests fail

**Problem**: Environment bypasses still active

**Solution**:
```bash
# Ensure no bypass variables
unset SPEC_KITTY_TEMPLATE_ROOT
unset SPEC_KITTY_REPO

# Verify
env | grep SPEC_KITTY  # Should return nothing

# Re-run distribution tests
pytest -m distribution
```

## Success Criteria Validation

After running tests, verify success criteria from spec.md:

- **SC-001**: 100% of distribution tests pass without SPEC_KITTY_TEMPLATE_ROOT
- **SC-002**: 100% of orchestrator state transitions validated
- **SC-003**: 100% of VCS code paths tested in isolation
- **SC-004**: Zero data loss scenarios pass
- **SC-005**: All 9 agent invokers pass invocation tests
- **SC-006**: 100% of edge cases have test cases
- **SC-007**: Functional <10min, distribution <45min
- **SC-008**: Coverage >85% for changed modules
- **SC-009**: 100% of migrations execute successfully
- **SC-010**: Backward compatibility for v0.11.0, v0.11.1, v0.11.2
- **SC-011**: At least 3 real bugs discovered
- **SC-012**: Zero false negatives in preflight validation

## Next Steps

1. Review test output for failures or skips
2. If bugs found, document in `findings/{version}/YYYY-MM-DD_NN_description.md`
3. If coverage below 85%, identify untested code paths
4. If tests pass, validate against success criteria above
5. Report bugs to spec-kitty implementation team via findings/ directory

## Additional Resources

- [Specification](spec.md) - Feature requirements and success criteria
- [Implementation Plan](plan.md) - Technical architecture and design
- [Data Model](data-model.md) - Test entities and fixtures
- [Fixture Protocols](contracts/fixtures.py) - Fixture interfaces
- [Marker Definitions](contracts/markers.py) - pytest markers and usage
- [Constitution](../../.kittify/memory/constitution.md) - Testing philosophy and standards
