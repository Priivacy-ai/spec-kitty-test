# Distribution Testing Suite

**Purpose:** Test the actual package that ships to users, not just development code.

## The Bug This Would Have Caught

This entire test category was **COMPLETELY MISSING** from the original test suite, which allowed a catastrophic bug to ship through 8+ releases affecting **100% of PyPI users**.

### The Bug:
- `pyproject.toml` line 72 bundled `/templates/` (outdated, bash/PowerShell refs)
- Should have bundled `/.kittify/templates/` (correct, Python CLI commands)
- ALL 12 AI agents got broken slash commands
- Every `spec-kitty init` created unusable projects

### Why Existing Tests Missed It:
**ALL 323 existing tests used this pattern:**
```python
env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
```

This bypassed the package's bundled templates, creating a parallel universe where:
- **Tests:** Used `/.kittify/templates/` (correct) → Passed ✅
- **Users:** Got `/templates/` (broken) → Failed ❌

**Zero tests** validated what PyPI users actually experience.

## Test Philosophy

### Old Approach (Broken):
```python
# All existing tests do this:
def test_init(spec_kitty_repo_root):
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)  # ← BYPASS
    subprocess.run(['spec-kitty', 'init'], env=env)
    # ✅ Passes because using local repo templates
```

### New Approach (Correct):
```python
# Distribution tests do this:
def test_init():
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)  # ← NO BYPASS
    subprocess.run(['spec-kitty', 'init'], env=env)
    # ✅ or ❌ Tests actual user experience
```

## Test Categories

### 1. Package Configuration Validation
**File:** `test_pyproject_toml_validation.py`

Tests that would have caught the bug:
- ✅ `test_package_data_points_to_kittify_templates()` - **THE ROOT CAUSE TEST**
- ✅ `test_bundled_templates_use_python_cli_not_scripts()`
- ✅ `test_no_bash_script_references_in_bundled_templates()`
- ✅ `test_no_powershell_script_references_in_bundled_templates()`
- ✅ `test_no_template_directory_divergence()`

### 2. User Experience Simulation
**File:** `test_user_experience_simulation.py`

Tests without development overrides:
- ✅ `test_init_succeeds_without_template_root_override()` - Key test
- ✅ `test_command_templates_have_correct_content_without_overrides()` - **Would catch Issues #62, #63, #64**
- ✅ `test_worktree_command_has_no_script_references_without_overrides()` - Issue #62
- ✅ `test_specify_command_has_no_ps1_references_without_overrides()` - Issue #63
- ✅ `test_all_agents_get_correct_templates_without_overrides()` - Issue #64

## Running Distribution Tests

### Quick Test (Recommended for CI/CD):
```bash
# Test pyproject.toml configuration
pytest tests/distribution/test_pyproject_toml_validation.py -v

# Test user experience without development overrides
pytest tests/distribution/test_user_experience_simulation.py -v
```

### Full Distribution Test Suite:
```bash
# Run all distribution tests
pytest tests/distribution/ -v
```

### Expected Results:

**If pyproject.toml is CORRECT (.kittify/templates bundled):**
```
tests/distribution/test_pyproject_toml_validation.py::...  PASSED ✅
tests/distribution/test_user_experience_simulation.py::... PASSED ✅
```

**If pyproject.toml is WRONG (/templates bundled):**
```
tests/distribution/test_pyproject_toml_validation.py::test_package_data_points_to_kittify_templates FAILED ❌
  CRITICAL BUG: pyproject.toml points to wrong template directory!

tests/distribution/test_user_experience_simulation.py::test_command_templates_have_correct_content_without_overrides FAILED ❌
  🐛 BUG CONFIRMED: Command templates contain script references!
  This is exactly Issues #62, #63, #64!
```

## Integration with CI/CD

### Recommended GitHub Actions Workflow:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  # Existing tests (development workflow)
  test-development:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e ../spec-kitty  # Editable install
      - name: Run functional tests
        run: pytest tests/functional/ -v

  # NEW: Distribution tests (user workflow)
  test-distribution:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Install spec-kitty (NON-editable)
        run: pip install spec-kitty-cli  # From PyPI or built wheel
      - name: Run distribution tests
        run: pytest tests/distribution/ -v
        env:
          # Explicitly unset development overrides
          SPEC_KITTY_TEMPLATE_ROOT: ''
          SPEC_KITTY_REPO: ''

  # Both must pass before merge
  merge-gate:
    needs: [test-development, test-distribution]
    runs-on: ubuntu-latest
    steps:
      - run: echo "All tests passed!"
```

## What These Tests Validate

### ✅ Package Configuration
- pyproject.toml points to correct template directory
- Bundled directory exists and has content
- No outdated bash/PowerShell references in bundled templates

### ✅ User Experience
- Init works without SPEC_KITTY_TEMPLATE_ROOT
- Commands use Python CLI, not bash/PowerShell scripts
- All AI agents get correct templates
- No divergence between development and production

### ✅ Regression Prevention
- Template directory consistency
- No script references in any template
- Development/production parity

## Key Differences from Existing Tests

| Aspect | Existing Tests (functional/) | Distribution Tests (distribution/) |
|--------|------------------------------|-----------------------------------|
| **Environment** | `SPEC_KITTY_TEMPLATE_ROOT` set | `SPEC_KITTY_TEMPLATE_ROOT` unset |
| **Template Source** | Local repo `/.kittify/templates/` | Package bundled templates |
| **Tests** | Development workflow | User workflow |
| **Coverage** | "Does code work?" | "Does package work?" |
| **Bug Visibility** | Missed the bug ❌ | Would catch it ✅ |

## Test Failures and What They Mean

### `test_package_data_points_to_kittify_templates` FAILS
**Meaning:** pyproject.toml is misconfigured
**Fix:** Change line 72 to bundle `.kittify/templates`

### `test_command_templates_have_correct_content_without_overrides` FAILS
**Meaning:** PyPI users are getting broken templates
**Fix:** Fix pyproject.toml AND verify bundled templates

### `test_no_template_directory_divergence` FAILS
**Meaning:** Multiple template sources are out of sync
**Fix:** Sync `/templates/` with `/.kittify/templates/` OR remove `/templates/`

## Why This Matters

### Impact of Missing These Tests:
- **Releases affected:** v0.10.0 through v0.10.8 (8+ releases)
- **Users affected:** 100% of PyPI installations
- **Commands broken:** All 12+ slash commands for all 12 AI agents
- **User experience:** Complete failure - tool appears broken
- **Reputation damage:** "spec-kitty doesn't work" for new users

### Cost of the Bug:
- Existing tests: 323 tests, all passing ✅
- Real users: 100% failure rate ❌
- Discovery: Users reported it (not tests)
- Time to detect: Multiple releases

### Value of These Tests:
- ✅ Would have detected bug before first release
- ✅ Would have blocked PR with misconfigured pyproject.toml
- ✅ Would have prevented 8+ broken releases
- ✅ Would have saved user trust and developer time

## Related Documentation

- **Finding:** `findings/0.10.8/2026-01-06_01_wrong_template_bundling_issues_62_63_64.md`
  - Details the bug and user impact

- **Test Suite Analysis:** `findings/0.10.8/2026-01-06_02_test_suite_systemic_failure_analysis.md`
  - Deep dive into why existing tests failed to catch it
  - Comprehensive analysis of the testing blind spot

- **GitHub Issues:** #62, #63, #64
  - User reports of the bug

## Lessons Learned

### The Blind Spot:
**Tests validated development workflow, not user workflow.**

All tests used `SPEC_KITTY_TEMPLATE_ROOT` which:
- ✅ Helpful for rapid development iteration
- ✅ Tests local code changes quickly
- ❌ Hides package configuration bugs
- ❌ Creates parallel universe (tests pass, users fail)

### The Fix:
**Test what you ship, not just what you write.**

Distribution tests validate:
- ✅ Package builds correctly
- ✅ Package contains correct files
- ✅ Package works for users (not just developers)
- ✅ Configuration (pyproject.toml) is correct

### The Principle:
> **"Development convenience should not create production invisibility."**

Fast iteration in development is good.
But we must also test the production artifact.

---

**Status:** ✅ Tests Created (2026-01-06)
**Coverage:** Package configuration, user experience, regression prevention
**Next Steps:** Add to CI/CD pipeline, run on every PR
