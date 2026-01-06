## Critical Context: Testing Philosophy (2026-01-06)

**REQUIRED READING:** This test suite exists to prevent broken code from shipping to users.

### The Catastrophic Failure We Had (Issues #62, #63, #64)
A bug affecting **100% of PyPI users** shipped through **8+ releases** despite **323 passing tests**. Why?

**ALL existing tests did this:**
```python
env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)  # ← BYPASS
```

This created two universes:
- **Tests (✅):** Used local repo templates → Everything passed
- **Users (❌):** Used packaged templates → Everything failed

**Zero tests validated what PyPI users experience.**

### The New Testing Paradigm

**CRITICAL PRINCIPLE:**
> "Test what you ship, not just what you write."

**Two Test Categories:**

1. **Functional Tests** (`tests/functional/`) - Development workflow
   - Fast iteration
   - Uses `SPEC_KITTY_TEMPLATE_ROOT`
   - Tests code correctness

2. **Distribution Tests** (`tests/distribution/`) - User workflow ⭐ **NEW**
   - Real user experience
   - NO `SPEC_KITTY_TEMPLATE_ROOT`
   - Tests package correctness

### When Writing Tests

**For functional tests (existing behavior):**
```python
def test_something(spec_kitty_repo_root):
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
    # Fast local testing
```

**For distribution tests (CRITICAL):**
```python
def test_something():
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)  # NO BYPASS!
    # Test real user experience
```

**Always ask yourself:**
- Does this test validate what users experience?
- Should this also have a distribution test variant?
- Am I testing the package, or just the code?

### Key Files to Review Before Starting
1. `findings/0.10.8/COMPREHENSIVE_TESTING_FAILURE_SUMMARY.md` - The full story
2. `tests/distribution/README.md` - Distribution testing guide
3. `findings/0.10.8/2026-01-06_02_test_suite_systemic_failure_analysis.md` - Deep analysis

### When Reporting Bugs
Put your findings in ./findings and follow the organizational and naming conventions as well as ./findings/TEMPLATE.md

### Documentation
Don't write any other .md files in . (root directory has comprehensive docs already)