# Testing Quick Reference Card

**Keep this handy when writing tests for spec-kitty!**

---

## ⚠️ The Critical Lesson

**A bug affecting 100% of PyPI users shipped through 8+ releases with 323 passing tests.**

**Why?** All tests used `SPEC_KITTY_TEMPLATE_ROOT` which bypassed package distribution.

**Solution:** Dual testing strategy.

---

## Two Test Categories

### ✅ Functional Tests - Fast Iteration
```python
def test_feature(spec_kitty_repo_root):
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)
    # Tests code correctness
```
**Location:** `tests/functional/`
**Use for:** Feature development, code correctness

### ✅ Distribution Tests - Real Experience
```python
def test_feature():
    env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)  # NO BYPASS!
    # Tests user experience
```
**Location:** `tests/distribution/`
**Use for:** Package validation, user experience

---

## Quick Decision Tree

```
Writing a test?
│
├─ Testing code/features?
│  └─ Functional test (WITH override)
│
├─ Testing package/config?
│  └─ Distribution test (WITHOUT override)
│
└─ Both?
   └─ Write BOTH variants!
```

---

## The Golden Rule

> **"Test what you ship, not just what you write."**

Always ask:
- [ ] Does this test what users experience?
- [ ] Should this have a distribution variant?
- [ ] Am I testing the package or just code?

---

## Run Before Committing

```bash
# Quick check
pytest tests/distribution/test_pyproject_toml_validation.py -v

# Full distribution suite
pytest tests/distribution/ -v
```

---

## Key Files

- **Philosophy:** `TESTING.md`
- **Full story:** `findings/0.10.8/COMPREHENSIVE_TESTING_FAILURE_SUMMARY.md`
- **Guide:** `tests/distribution/README.md`
- **Project instructions:** `CLAUDE.md`

---

**Remember:** If ALL existing tests used overrides and missed the bug, your new test might too. When in doubt, write BOTH test variants!
