# Contributing to Spec-Kitty Test Suite

Thank you for your interest in improving the spec-kitty testing framework! This guide will help you contribute effectively.

## Quick Start for Contributors

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/spec-kitty-test.git
cd spec-kitty-test

# 2. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Clone spec-kitty (for testing against source)
git clone https://github.com/Priivacy-ai/spec-kitty.git ../spec-kitty
pip install -e ../spec-kitty

# 4. Install Playwright
playwright install chromium

# 5. Configure environment
export SPEC_KITTY_REPO=../spec-kitty
export SPEC_KITTY_TEMPLATE_ROOT=../spec-kitty

# 6. Run tests to verify setup
pytest tests/functional/test_verify_setup.py -v
```

## Types of Contributions

### 1. Adding New Tests

**When to add tests:**
- You found a bug in spec-kitty
- You want to verify a feature works correctly
- You're testing a new spec-kitty feature
- You want to prevent regression of a fix

**Steps:**
1. Create test file in `tests/functional/`
2. Follow naming convention: `test_<feature_area>.py`
3. Add comprehensive docstring explaining what's tested
4. Use existing fixtures from `conftest.py`
5. Run locally: `pytest tests/functional/test_your_new_test.py -v`
6. Ensure tests are clear and well-documented

**Example:**

```python
"""
Feature X Tests

Tests the spec-kitty feature X to ensure it works correctly.

Test Coverage:
1. Basic Functionality (3 tests)
   - Feature does A
   - Feature does B
   - Feature handles errors
"""

import pytest

class TestFeatureX:
    """Test feature X basic functionality."""

    def test_feature_does_a(self, spec_kitty_repo_root):
        """Test: Feature successfully performs action A"""
        # Arrange
        # Act
        # Assert
```

### 2. Documenting Findings

**When to create findings:**
- You discovered a bug in spec-kitty
- You found a UX issue
- You identified a confusing error message
- You want to suggest an improvement

**Steps:**
1. Determine spec-kitty version: `spec-kitty --version`
2. Copy `findings/TEMPLATE.md`
3. Name: `findings/<version>/YYYY-MM-DD_NN_description.md`
4. Fill in ALL sections (don't skip any)
5. Include reproduction steps
6. Link to related test coverage (if exists)
7. Submit PR

**Naming convention:**
- `YYYY-MM-DD` - ISO date format
- `NN` - Sequential number (01, 02, 03...)
- `description` - Hyphen-separated brief description

**Example:** `findings/0.5.3/2025-11-15_01_dashboard_artifact_tracking.md`

### 3. Improving Documentation

**What to document:**
- Test execution guides
- Setup troubleshooting
- Test patterns and best practices
- Findings summaries

**Where:**
- Quick guides: `docs/`
- Test reports: `docs/test-reports/`
- Findings: `findings/<version>/`

### 4. Fixing Bugs in Tests

**Common issues:**
- Tests failing due to spec-kitty version changes
- Broken fixtures
- Outdated assertions
- Missing dependencies

**Steps:**
1. Identify failing test
2. Determine if it's a test bug or spec-kitty bug
3. Fix the test OR document the spec-kitty bug
4. Ensure fix doesn't break other tests
5. Submit PR with clear explanation

## Code Style

### Python Code

- Follow PEP 8
- Use type hints where helpful
- Add docstrings to all test classes and functions
- Keep tests focused (one thing per test)
- Use descriptive assertion messages

### Test Organization

**File structure:**
```python
"""Module docstring explaining what's tested."""

import statements

@pytest.fixture
def fixture_name():
    """Fixture docstring."""
    # Setup
    yield value
    # Teardown

class TestFeatureArea:
    """Test class docstring."""

    def test_specific_behavior(self, fixture):
        """Test: Specific behavior description"""
        # Test implementation
```

**Naming:**
- Test files: `test_<feature>.py`
- Test classes: `Test<FeatureArea>`
- Test methods: `test_<what>_<expected_behavior>`

## Test Guidelines

### Good Tests

✅ Clear purpose stated in docstring
✅ Single responsibility (tests one thing)
✅ Reproducible (deterministic results)
✅ Fast (< 5 seconds if possible)
✅ Independent (doesn't rely on test order)
✅ Helpful failure messages

### Bad Tests

✗ No docstring or unclear purpose
✗ Tests multiple unrelated things
✗ Flaky (sometimes passes, sometimes fails)
✗ Slow (> 30 seconds)
✗ Depends on other tests running first
✗ Generic assertions with no context

## Playwright Test Guidelines

### When to Use Playwright

Use Playwright for tests that need to verify:
- **Browser UI** rendering and updates
- **Real-time** updates in dashboard
- **User interactions** with web interface
- **JavaScript behavior** in the frontend

**Don't use for:**
- Backend API testing (use urllib/requests)
- CLI command testing (use subprocess)
- File system testing (use pathlib)

### Playwright Best Practices

```python
def test_ui_feature(page, dashboard_with_feature):
    """Test: UI shows feature correctly"""
    url = dashboard_with_feature['url']

    # Load page and wait for stability
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector('body', timeout=5000)

    # Interact with page
    page.click('button.submit')

    # Verify behavior
    assert page.locator('.success-message').is_visible()

    # For debugging: take screenshot
    # page.screenshot(path='debug.png')
```

## Version Compatibility

When adding tests that might behave differently across versions:

```python
from test_helpers import get_diagnostics_command, check_command_exists

def test_feature(self):
    # Use version-aware helper
    cmd, version = get_diagnostics_command()

    # Adapt assertions based on version
    if version == 'v0.5.2':
        assert 'old behavior' in output
    else:
        assert 'new behavior' in output
```

## Commit Message Format

Follow conventional commits:

```
<type>: <description>

<body>

<footer>
```

**Types:**
- `test:` - Adding or modifying tests
- `docs:` - Documentation changes
- `fix:` - Fixing a test bug
- `feat:` - New test feature/capability
- `chore:` - Maintenance tasks

**Example:**

```
test: Add dashboard modification detection tests

Created 15 Playwright tests to reproduce user-reported bug where
dashboard doesn't show file modifications without manual refresh.

Tests confirm the bug exists and will validate the fix once
scanner.py is updated to track file modification times.

Closes #42
```

## Pull Request Process

1. **Create issue first** (for significant changes)
2. **Fork and branch** from main
3. **Make changes** with clear commits
4. **Run tests locally** - ensure they pass (or fail as expected)
5. **Update documentation** if needed
6. **Submit PR** with:
   - Clear title and description
   - Link to related issue
   - Test results showing what changed
   - Any new findings documented

## Review Criteria

PRs will be reviewed for:

- ✅ Tests are clear and well-documented
- ✅ Tests follow existing patterns
- ✅ Findings follow TEMPLATE.md format
- ✅ Documentation is accurate and helpful
- ✅ No sensitive information committed
- ✅ All tests run successfully (or fail as expected for bug reproduction)

## Questions?

- **Test Framework**: Open an issue in this repository
- **Spec-Kitty Bugs**: Report in [spec-kitty repository](https://github.com/Priivacy-ai/spec-kitty/issues)
- **General Questions**: Start a discussion

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to make spec-kitty better!

---

Thank you for contributing! 🎉
