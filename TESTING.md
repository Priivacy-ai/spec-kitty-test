# Testing Philosophy for Spec-Kitty Test Suite

**Last Updated:** 2026-01-06
**Status:** ✅ Active - Required Reading for All Contributors

## Why This Document Exists

In late 2025, a **catastrophic bug affecting 100% of PyPI users** shipped through **8+ releases** despite **323 passing tests**. This document ensures it never happens again.

---

## The Failure: What Happened

### The Bug
- `pyproject.toml` bundled wrong templates (`/templates/` instead of `/.kittify/templates/`)
- ALL PyPI users got broken templates with bash script references
- Scripts didn't exist (removed in v0.10.0)
- Every `spec-kitty init` created unusable projects

### Why 323 Tests Missed It

**Every test did this:**
```python
def test_something(spec_kitty_repo_root):
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)  # ← THE BYPASS
    subprocess.run(['spec-kitty', 'init'], env=env)
```

**This created parallel universes:**

```
UNIVERSE A: Tests                    UNIVERSE B: Reality
├─ Local repo templates              ├─ Packaged templates
├─ Python CLI commands ✅            ├─ Bash scripts ❌
├─ All tests pass                    ├─ All users fail
└─ False confidence                  └─ GitHub issues flood in
```

### The Impact
- **Development workflow:** 95% coverage ✅
- **User workflow:** 0% coverage ❌
- **Package distribution:** Not tested ❌
- **Result:** Production disaster

**Full analysis:** `findings/0.10.8/COMPREHENSIVE_TESTING_FAILURE_SUMMARY.md`

---

## The Solution: Dual Testing Strategy

### Two Test Categories

| Category | Purpose | Speed | Override | Tests |
|----------|---------|-------|----------|-------|
| **Functional** | Development workflow | Fast | Yes | 323 |
| **Distribution** | User workflow | Slow | **NO** | 44+ |

### When to Use Each

#### Functional Tests (`tests/functional/`)
**Use for:** Code correctness, feature functionality, rapid iteration

```python
def test_feature_works(spec_kitty_repo_root):
    """Fast test against local repository."""
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    subprocess.run(['spec-kitty', 'some-command'], env=env)
    # Test passes quickly using local templates
```

**Advantages:**
- ✅ Fast execution (~1s per test)
- ✅ No build/install overhead
- ✅ Immediate feedback during development

**Limitations:**
- ❌ Doesn't test package distribution
- ❌ Doesn't catch pyproject.toml bugs
- ❌ Doesn't simulate user experience

#### Distribution Tests (`tests/distribution/`)
**Use for:** Package correctness, user experience, release validation

```python
def test_package_works():
    """Test actual user experience - NO overrides."""
    env = os.environ.copy()

    # CRITICAL: Remove development bypasses
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
    env.pop('SPEC_KITTY_REPO', None)

    subprocess.run(['spec-kitty', 'init', 'test'], env=env)
    # Test uses actual installed package
```

**Advantages:**
- ✅ Tests real user experience
- ✅ Catches package configuration bugs
- ✅ Validates pyproject.toml correctness
- ✅ Ensures package contents are correct

**Requirements:**
- Slower execution (~10s per test)
- May require package build/install
- Must run before releases

---

## Core Testing Principles

### Principle 1: Test What You Ship

**Bad:**
```python
def test_init(spec_kitty_repo_root):
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
    # Testing local repo, not shipped package
```

**Good:**
```python
def test_init():
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
    # Testing what users actually install
```

### Principle 2: No Hidden Assumptions

**Don't assume:**
- ❌ Package contents match repository
- ❌ pyproject.toml is configured correctly
- ❌ Templates are up to date
- ❌ Users have SPEC_KITTY_TEMPLATE_ROOT set

**Explicitly test:**
- ✅ What pyproject.toml bundles
- ✅ What users install from PyPI
- ✅ Fresh environment without overrides
- ✅ Package contents after build

### Principle 3: Development Convenience ≠ Production Correctness

Fast iteration helpers (like `SPEC_KITTY_TEMPLATE_ROOT`) are valuable for development.

But they **must not** be the only testing path.

**Always ask:**
- Would this test pass if I installed from PyPI?
- Am I testing the package or just the code?
- Should this have a distribution test variant?

---

## Test Categories in Detail

### 1. Functional Tests (Existing)

**Location:** `tests/functional/`
**Count:** 323 tests
**Purpose:** Rapid development iteration

**Examples:**
- Template rendering tests
- Command execution tests
- Feature functionality tests
- Agent workflow tests

**Fixture Pattern:**
```python
@pytest.fixture
def spec_kitty_repo_root():
    """Returns path to local spec-kitty repository."""
    return Path(__file__).parent.parent.parent / "spec-kitty"
```

**Usage:** Continue using for fast feedback during development

### 2. Distribution Tests (NEW - Critical)

**Location:** `tests/distribution/`
**Count:** 18+ tests
**Purpose:** Validate shipped package

**Key Tests:**

#### A. Package Configuration
```python
# tests/distribution/test_pyproject_toml_validation.py
def test_package_data_points_to_kittify_templates():
    """Validates pyproject.toml line 72 - ROOT CAUSE of Issue #62-64"""
    # Checks that correct directory is bundled
```

#### B. User Experience Simulation
```python
# tests/distribution/test_user_experience_simulation.py
def test_command_templates_have_correct_content_without_overrides():
    """Tests WITHOUT SPEC_KITTY_TEMPLATE_ROOT"""
    # Would have caught Issues #62, #63, #64
```

#### C. Package Bundling
```python
# tests/test_package_bundling.py
def test_sdist_bundles_kittify_templates():
    """Validates what actually gets shipped to PyPI"""
    # Builds package, inspects contents
```

**Usage:** Run before every release, periodically in CI/CD

### 3. Issue-Specific Tests

**Location:** `tests/functional/test_issue_*.py`
**Purpose:** Reproduce and prevent specific bugs

**Example:**
```python
# tests/functional/test_issue_62_63_64_template_bundling.py
# 18 tests covering the template bundling catastrophe
```

**When to create:** When a bug is discovered, write comprehensive tests that:
1. Reproduce the bug
2. Validate the fix
3. Prevent regression

---

## Writing New Tests

### Decision Tree

```
Need to write a test?
│
├─ Testing code correctness / features?
│  └─ Write functional test (with SPEC_KITTY_TEMPLATE_ROOT)
│
├─ Testing package distribution / config?
│  └─ Write distribution test (WITHOUT overrides)
│
└─ Testing specific bug fix?
   └─ Write issue-specific test (both variants if needed)
```

### Functional Test Template

```python
# tests/functional/test_my_feature.py
import pytest
from pathlib import Path

class TestMyFeature:
    """Test my new feature functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_feature_works(self, temp_project_dir, spec_kitty_repo_root):
        """Test feature with development setup."""
        import os, subprocess

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'my-command'],
            cwd=temp_project_dir,
            env=env,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        # Fast feedback during development
```

### Distribution Test Template

```python
# tests/distribution/test_my_feature.py
import pytest
from pathlib import Path

class TestMyFeatureDistribution:
    """Test feature from user perspective."""

    @pytest.fixture
    def clean_environment(self):
        """Environment without development overrides."""
        import os
        env = os.environ.copy()

        # CRITICAL: Remove bypasses
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)

        return env

    def test_feature_works_for_users(self, temp_project_dir, clean_environment):
        """Test feature as PyPI user would experience it."""
        import subprocess

        result = subprocess.run(
            ['spec-kitty', 'my-command'],
            cwd=temp_project_dir,
            env=clean_environment,  # NO OVERRIDES!
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        # Validates actual user experience
```

---

## Running Tests

### Quick Checks (During Development)

```bash
# Run functional tests (fast)
pytest tests/functional/ -v

# Run specific test file
pytest tests/functional/test_my_feature.py -v
```

### Pre-Commit Validation

```bash
# Run all tests including distribution
pytest tests/ -v

# Or run distribution tests specifically
pytest tests/distribution/ -v
pytest tests/test_package_bundling.py -v
```

### Pre-Release Validation (Required)

```bash
# 1. Validate pyproject.toml
pytest tests/distribution/test_pyproject_toml_validation.py -v

# 2. Test user experience
pytest tests/distribution/test_user_experience_simulation.py -v

# 3. Validate package bundling
pytest tests/test_package_bundling.py -v

# All distribution tests must pass before release!
```

---

## CI/CD Integration

### Recommended GitHub Actions

```yaml
name: Comprehensive Testing

on: [push, pull_request]

jobs:
  # Fast feedback - functional tests
  test-development:
    runs-on: ubuntu-latest
    steps:
      - name: Run functional tests
        run: pytest tests/functional/ -v
        # Uses SPEC_KITTY_TEMPLATE_ROOT

  # Reality check - distribution tests
  test-distribution:
    runs-on: ubuntu-latest
    steps:
      - name: Run distribution tests
        run: pytest tests/distribution/ -v
        env:
          SPEC_KITTY_TEMPLATE_ROOT: ''  # Explicitly unset

  # Package validation
  test-package:
    runs-on: ubuntu-latest
    steps:
      - name: Validate package bundling
        run: pytest tests/test_package_bundling.py -v

  # BOTH must pass
  merge-gate:
    needs: [test-development, test-distribution, test-package]
    runs-on: ubuntu-latest
    steps:
      - run: echo "✅ All tests passed - safe to merge"
```

---

## Common Pitfalls

### ❌ Pitfall 1: Only Testing Development Path

```python
def test_init(spec_kitty_repo_root):
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
    # This passes even if package is broken!
```

**Fix:** Add distribution test variant:
```python
def test_init_from_package():
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
    # Tests actual user experience
```

### ❌ Pitfall 2: Assuming Package Matches Repository

```python
def test_templates_correct(spec_kitty_repo_root):
    templates = spec_kitty_repo_root / '.kittify' / 'templates'
    # Tests local repo, not what's bundled!
```

**Fix:** Test what gets bundled:
```python
def test_bundled_templates_correct():
    subprocess.run(['python', '-m', 'build'])
    # Validate dist/*.whl contents
```

### ❌ Pitfall 3: Not Validating Configuration

```python
def test_features():
    # Tests features but not pyproject.toml config
```

**Fix:** Add configuration tests:
```python
def test_pyproject_bundles_correct_files():
    # Validate [tool.setuptools.package-data]
```

---

## Success Metrics

### Before Distribution Tests
- ❌ 0 tests validated pyproject.toml
- ❌ 0 tests without SPEC_KITTY_TEMPLATE_ROOT
- ❌ 0 tests of package contents
- ❌ Bug shipped through 8+ releases

### After Distribution Tests
- ✅ 10+ tests validate pyproject.toml
- ✅ 15+ tests without overrides
- ✅ 8+ tests validate package bundling
- ✅ **Bug would be caught immediately**

---

## Key Files Reference

### Must-Read Documentation
1. **This file** - Testing philosophy overview
2. `findings/0.10.8/COMPREHENSIVE_TESTING_FAILURE_SUMMARY.md` - Full story
3. `tests/distribution/README.md` - Distribution testing guide
4. `findings/0.10.8/2026-01-06_02_test_suite_systemic_failure_analysis.md` - Deep analysis

### Test Locations
- `tests/functional/` - Development workflow tests (323)
- `tests/distribution/` - User workflow tests (18+)
- `tests/test_package_bundling.py` - Package validation (8)
- `tests/functional/test_issue_*.py` - Bug reproduction/prevention

### Example Tests to Study
- `tests/distribution/test_user_experience_simulation.py` - No overrides pattern
- `tests/distribution/test_pyproject_toml_validation.py` - Config validation
- `tests/test_package_bundling.py` - Package inspection
- `tests/functional/test_issue_62_63_64_template_bundling.py` - Comprehensive coverage

---

## The Bottom Line

> **"Test what you ship, not just what you write."**

### What Went Wrong
- All tests used development shortcuts
- Created parallel universe where tests passed but users failed
- 323 tests gave false confidence

### What's Different Now
- Dual testing strategy (development + distribution)
- Explicit testing of package distribution
- No hidden assumptions about package contents

### Your Responsibility
When writing tests, always ask:
1. **Does this test what users experience?**
2. **Should this have a distribution test variant?**
3. **Am I testing the package or just the code?**

If uncertain, err on the side of caution: **write both test variants**.

---

**Remember:** The bug that affected 100% of users was **invisible to 323 passing tests**. Distribution tests ensure it never happens again.

---

**Document Status:** ✅ Living Document - Update as testing evolves
**Last Major Revision:** 2026-01-06
**Next Review:** After any major testing changes
