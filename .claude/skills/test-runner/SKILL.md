---
name: test-runner
description: Run and validate spec-kitty tests. Use when running tests, checking test results, validating pass rates, debugging test failures, or preparing for release. Knows about functional vs distribution tests, environment issues, and test philosophy.
---

# Spec-Kitty Test Runner

This skill helps you run and interpret tests for the spec-kitty-test project.

## Critical Context: Testing Philosophy

**REQUIRED READING**: This test suite exists to prevent broken code from shipping to users.

### The Two Universes Problem (Issues #62-64)

A bug affecting **100% of PyPI users** shipped through **8+ releases** despite **323 passing tests** because all tests used:

```python
env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)  # BYPASS!
```

This created:
- **Tests**: Used local repo templates → Everything passed
- **Users**: Used packaged templates → Everything failed

**Principle**: "Test what you ship, not just what you write."

## Test Categories

### 1. Functional Tests (`tests/functional/`)
- **Purpose**: Fast development iteration, test code correctness
- **Environment**: Uses `SPEC_KITTY_TEMPLATE_ROOT` bypass
- **Speed**: Fast
- **When to use**: During development, quick validation

### 2. Distribution Tests (`tests/distribution/`)
- **Purpose**: Validate real user experience
- **Environment**: NO bypass - tests actual packaged templates
- **Speed**: Slower (creates clean environments)
- **When to use**: Before release, after packaging changes

## Before Running Tests

### Reinstall spec-kitty from source
Always reinstall before testing to get latest changes:

```bash
pip install -e ~/Code/spec-kitty --quiet
```

### Check for environment issues
Common problems on macOS:
- `python` not found → macOS uses `python3`, not `python`
- `fixture 'page' not found` → Install pytest-playwright: `pip install pytest-playwright && playwright install`

## Key Test Files

| File | Tests | Category |
|------|-------|----------|
| `tests/functional/test_sparse_checkout_infrastructure.py` | 46 | Sparse-checkout |
| `tests/distribution/test_doc_generators_distribution.py` | 15 | Doc generators |
| `tests/distribution/test_documentation_mission_distribution.py` | 20 | Doc mission |
| `tests/functional/test_documentation_mission_end_to_end.py` | 15 | Doc mission E2E |
| `tests/functional/test_dependency_warning_propagation.py` | 10 | Template validation |

## Running Tests

### Quick validation (new tests only - 96 tests)
```bash
# Sparse-checkout tests (46)
pytest tests/functional/test_sparse_checkout_infrastructure.py -v

# Documentation tests (50)
pytest tests/distribution/test_doc_generators_distribution.py \
       tests/distribution/test_documentation_mission_distribution.py \
       tests/functional/test_documentation_mission_end_to_end.py -v
```

### Full regression suite (parallel)
```bash
pytest tests/ -v --tb=line -n auto 2>&1 | tee regression_results.txt
```

### Specific test categories
```bash
# Distribution tests only (real user experience)
pytest tests/distribution/ -v

# Functional tests only (fast iteration)
pytest tests/functional/ -v
```

## Success Criteria

| Metric | Target | Notes |
|--------|--------|-------|
| New tests (96) | 100% pass | Zero tolerance |
| Overall pass rate | ≥95% | Some expected failures OK |
| Execution time | <15 minutes | Use `-n auto` for parallelization |
| Critical bugs | 0 | All must be fixed |

## Interpreting Results

### Expected failure categories
These are NOT bugs - tests need updates for v0.12.0 behavior:
- Command syntax changes (`spec-kitty agent workflow` vs old syntax)
- Template structure changes (central package vs .kittify/)
- Worktree management changes (sparse-checkout behavior)

### Environment errors (not failures)
- `FileNotFoundError: 'python'` → Use `sys.executable` in tests
- `fixture 'page' not found` → pytest-playwright not installed
- `fixture 'spec_kitty_repo_root' not found` → Worktree context issue

### Real failures to investigate
- Any failure in `tests/distribution/` (user experience tests)
- Any failure in new 96 tests (sparse-checkout + documentation)
- Unexpected assertion errors in core functionality

## Findings Documentation

When you find bugs or issues, document them in:
- `findings/test-infrastructure/` directory
- Follow template in `findings/TEMPLATE.md`
- Use naming: `YYYY-MM-DD_##_short_description.md`

Key findings files:
- `v0.12.0-bugs-found.md` - All bugs found and fixed
- `v0.12.0-regression-analysis.md` - Full test analysis
- `v0.12.0-known-failures.md` - Expected failures documentation

## Quick Diagnosis Commands

```bash
# Count test results
grep -c "PASSED\|FAILED\|SKIPPED\|ERROR" regression_results.txt

# List all failures
grep "FAILED" regression_results.txt

# Check specific test file
pytest tests/functional/test_sparse_checkout_infrastructure.py -v --tb=short

# Run single test with full output
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestWorktreeCreation::test_kitty_specs_excluded_from_worktree -v -s
```

## Troubleshooting

### Tests pass locally but fail in CI
- Check if using `SPEC_KITTY_TEMPLATE_ROOT` bypass
- Verify packaged templates with distribution tests

### Slow test execution (>15 min)
- Use parallel execution: `pytest -n auto`
- Check for tests creating unnecessary fixtures

### Flaky tests
- Check for race conditions in multi-agent tests
- Verify deterministic behavior (no real parallelism in tests)

### Missing templates in tests
- Reinstall spec-kitty: `pip install -e ~/Code/spec-kitty`
- Check `pyproject.toml` artifacts configuration
