# Spec-Kitty Test Suite

Comprehensive testing framework for [Spec-Kitty](https://github.com/Priivacy-ai/spec-kitty), a CLI tool for spec-driven development.

[![Tests](https://img.shields.io/badge/tests-323-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

## Purpose

This repository provides extensive functional testing for Spec-Kitty, helping to:

- ✅ Verify CLI commands work correctly across versions
- ✅ Catch regressions before they reach users
- ✅ Document bugs with reproducible test cases
- ✅ Validate UX for both humans and LLM agents
- ✅ Test real-world workflows end-to-end

**By testing spec-kitty directly, we identify issues, document findings, and make it better for everyone.**

## Quick Start

```bash
# 1. Clone this repository
git clone https://github.com/YOUR_ORG/spec-kitty-test.git
cd spec-kitty-test

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate

# 3. Install spec-kitty (choose one):
# Option A: From PyPI (stable release)
pip install spec-kitty-cli

# Option B: From source (development version)
git clone https://github.com/Priivacy-ai/spec-kitty.git ../spec-kitty
pip install -e ../spec-kitty

# 4. Install test dependencies
pip install -r requirements.txt

# 5. Install Playwright browsers (for UI tests)
playwright install chromium

# 6. Configure environment
export SPEC_KITTY_REPO=../spec-kitty  # or path to your spec-kitty clone
export SPEC_KITTY_TEMPLATE_ROOT=../spec-kitty

# 7. Run tests
pytest tests/functional/ -v
```

## Test Coverage

**323 tests** across 28 test modules covering:

### Core Functionality (✅ Passing)
- **Agent Workflows** (11 tests) - Command discovery and execution
- **Multi-Agent Init** (43 tests) - All 12 supported AI agents
- **Template Rendering** (10 tests) - Variable substitution per agent
- **Worktree Management** (15 tests) - Isolated feature development
- **Task Approval** (17 tests) - Reviewer attribution system

### Dashboard & State (✅ Mostly Passing)
- **Dashboard Lifecycle** (14 tests) - Server startup and shutdown
- **Dashboard State** (11 tests) - Feature and artifact detection
- **Dashboard Server** (9 tests) - HTTP server functionality
- **Dashboard sys.path** (4 tests) - Import priority in complex environments

### Real-Time Updates (⚠️ Known Issues)
- **File Modification Detection** (15 tests) - Live UI updates (bugs confirmed)
- **Live Updates** (16 tests) - Constitution/spec/plan changes (bugs confirmed)

### Quality & Validation (✅ Passing)
- **Encoding Issues** (32 tests) - UTF-8 validation and fixing
- **Error Handling** (7 tests) - Graceful failure modes
- **Diagnostics** (12 tests) - System health checking
- **Version Compatibility** (9 tests) - Cross-version testing

### Template System (✅ Passing)
- **Variable Substitution** (9 tests) - Template rendering
- **Slash Command Paths** (12 tests) - Command file locations
- **Readability** (8 tests) - Human and agent UX

## Repository Structure

```
spec-kitty-test/
├── tests/
│   ├── functional/              # 28 test modules, 323 tests
│   │   ├── test_task_approval.py
│   │   ├── test_dashboard_*.py
│   │   ├── test_template_*.py
│   │   └── ...
│   └── conftest.py              # Shared fixtures and Playwright config
│
├── findings/                    # Bug reports and observations
│   ├── 0.5.1/                   # Findings for spec-kitty v0.5.1
│   ├── 0.5.3/                   # Findings for spec-kitty v0.5.3
│   │   ├── 2025-11-15_01_dashboard_artifact_tracking.md
│   │   ├── 2025-11-15_02_dashboard_modification_detection.md
│   │   └── ...
│   └── TEMPLATE.md              # Finding template
│
├── docs/
│   └── test-reports/            # Test execution reports
│       ├── DASHBOARD_BUG_SUMMARY.md
│       ├── TASK_APPROVAL_TESTS.md
│       └── ...
│
├── venv/                        # Python virtual environment
└── README.md                    # This file
```

## Running Tests

### All Tests

```bash
source venv/bin/activate
pytest tests/functional/ -v
```

### By Category

```bash
# Dashboard tests
pytest tests/functional/test_dashboard_*.py -v

# Task approval tests
pytest tests/functional/test_task_approval.py -v

# Template rendering tests
pytest tests/functional/test_template_*.py -v

# Quick smoke test (fast tests only)
pytest tests/functional/test_verify_setup.py -v
```

### Specific Bug Reproduction

```bash
# Dashboard modification detection bug
pytest tests/functional/test_dashboard_modification_api.py -v -s

# Task reviewer attribution
pytest tests/functional/test_task_approval.py::TestReviewerIdentityPreservation -v

# Template variable substitution
pytest tests/functional/test_template_variable_substitution.py -v
```

## Key Features

### 🎭 Playwright Integration

Real browser automation tests for dashboard UI:

```bash
# Run with visible browser (debugging)
pytest tests/functional/test_dashboard_file_modifications.py --headed

# Run with slow motion
pytest tests/functional/test_dashboard_file_modifications.py --headed --slowmo 1000
```

### 🔄 Version Compatibility

Tests work across multiple spec-kitty versions:

```python
from test_helpers import get_diagnostics_command

# Automatically adapts to available commands
diag_cmd, version = get_diagnostics_command()
# Returns: ['spec-kitty', 'verify-setup', '--diagnostics'] for v0.5.3+
# Or:      ['spec-kitty', 'diagnostics'] for older versions
```

### 📋 Structured Findings

All bugs documented using consistent template in `findings/`:

- Organized by version (0.5.1/, 0.5.3/)
- Dated findings (YYYY-MM-DD_NN_description.md)
- Includes reproduction steps and fix recommendations
- Links to test coverage

### 🐛 Bug Reproduction

Tests reproduce real user-reported bugs:

```python
# Example: Dashboard modification detection
spec.write_text("# Placeholder\n")          # Agent creates initial
api_state_1 = get_dashboard_api()           # Dashboard shows it

spec.write_text("# Actual Spec\n[10KB]")    # Agent updates
api_state_2 = get_dashboard_api()           # Dashboard SHOULD update

assert api_state_1 != api_state_2  # ✗ FAILS - bug confirmed!
```

## Current Findings

### High Priority

**Dashboard Modification Detection** ([Finding 02](findings/0.5.3/2025-11-15_02_dashboard_modification_detection.md))
- Dashboard doesn't detect when existing files are modified
- Users must manually refresh to see changes
- 15 tests reproduce and confirm the bug
- **Root cause**: Scanner only checks file existence, not mtime/size

### Medium Priority

**Constitution.md Not Tracked** ([Finding 01](findings/0.5.3/2025-11-15_01_dashboard_artifact_tracking.md))
- Scanner doesn't check for constitution.md
- Cannot show constitution in dashboard
- Frontend has constitution UI but backend doesn't provide data

### Low Priority

**Misleading Path Metadata** ([Finding 03](findings/0.5.3/2025-11-15_03_template_path_metadata.md))
- Command files show source template path, not actual file path
- Causes confusion about which file is being read
- Not a functional bug, just UX issue

## Configuration

### Environment Variables

```bash
# Where spec-kitty repository is located
export SPEC_KITTY_REPO=/path/to/spec-kitty

# Template root for spec-kitty init commands
export SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty
```

### Test Configuration

Edit `tests/conftest.py` to customize:
- Playwright browser settings (headless/headed)
- Test timeouts
- Fixture scope

## Contributing

### Running Tests Locally

1. Fork this repository
2. Set up environment (see Quick Start)
3. Run tests: `pytest tests/functional/ -v`
4. All tests should pass (except known failing tests for documented bugs)

### Adding New Tests

1. Create test file in `tests/functional/`
2. Follow existing patterns (see `test_helpers.py` for utilities)
3. Use descriptive test names: `test_<what>_<expected_behavior>`
4. Add docstrings explaining what the test covers
5. Run locally to verify

### Reporting Findings

1. Copy `findings/TEMPLATE.md`
2. Name: `findings/<version>/YYYY-MM-DD_NN_descriptive-name.md`
3. Fill in all sections
4. Include reproduction steps
5. Link to related test coverage
6. Submit PR

## Test Statistics

```
Total Tests: 323
Test Files: 28
Test Coverage:
  - Dashboard: 61 tests
  - Tasks/Workflow: 45 tests
  - Templates: 30 tests
  - Encoding: 32 tests
  - Agent Support: 43 tests
  - Other: 112 tests

Execution Time: ~60 seconds (full suite)
```

## Dependencies

- **Python**: 3.11+
- **pytest**: 8.4+
- **playwright**: 1.56+ (for UI tests)
- **spec-kitty-cli**: 0.5.1+ (tested package)

See `requirements.txt` for complete list.

## Documentation

### For Test Users

- [Quick Start Guide](docs/QUICK_START.md) - Get running in 5 minutes
- [Test Reports](docs/test-reports/) - Detailed test execution results
- [Findings](findings/) - Bug reports and UX observations

### For Test Developers

- [Testing Setup Summary](docs/TESTING_SETUP_SUMMARY.md) - Architecture overview
- [Comprehensive Analysis](docs/SPEC_KITTY_COMPREHENSIVE_ANALYSIS.md) - Deep dive
- [Test Helpers](tests/functional/test_helpers.py) - Reusable utilities

## Spec-Kitty Project Links

- **Main Repository**: [github.com/Priivacy-ai/spec-kitty](https://github.com/Priivacy-ai/spec-kitty)
- **Documentation**: [Spec-Kitty Docs](https://github.com/Priivacy-ai/spec-kitty#readme)
- **Issues**: [Report Bugs](https://github.com/Priivacy-ai/spec-kitty/issues)

## Recent Test Additions (2025-11-15)

### Dashboard Update Testing
- **57 new tests** for real-time dashboard updates
- **Playwright integration** for browser automation
- **3 critical bugs confirmed** with reproducible tests

### Task Approval System
- **17 new tests** for reviewer attribution
- **Prevents audit trail corruption**
- **Validates multi-agent workflows**

### Version Compatibility
- **29 tests updated** to support PyPI and development versions
- **Automatic command detection** (v0.5.2 vs v0.5.3+)
- **Cross-version validation**

See [Test Summary](docs/test-reports/TEST_SUMMARY_2025-11-15.md) for details.

## Known Issues

### Tests Expected to Fail

The following tests **intentionally fail** to document bugs:

1. **Dashboard Modification Tests** (15 tests)
   - Reproduce file modification detection bug
   - Will pass once scanner adds mtime tracking
   - See: [Finding 02](findings/0.5.3/2025-11-15_02_dashboard_modification_detection.md)

2. **Dashboard Live Updates** (some tests)
   - Reproduce constitution.md tracking bug
   - Will pass once constitution is added to scanner
   - See: [Finding 01](findings/0.5.3/2025-11-15_01_dashboard_artifact_tracking.md)

These are **documented bugs with test coverage**, not test failures.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Spec-Kitty Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install spec-kitty-cli
          pip install -r requirements.txt
          playwright install chromium

      - name: Run tests
        run: |
          source venv/bin/activate
          pytest tests/functional/ -v --tb=short
```

## Development Workflow

### Testing Against Development Version

```bash
# 1. Clone spec-kitty for development
git clone https://github.com/Priivacy-ai/spec-kitty.git ../spec-kitty

# 2. Install in editable mode
pip install -e ../spec-kitty

# 3. Make changes to spec-kitty
cd ../spec-kitty
# ... edit code ...

# 4. Test changes
cd ../spec-kitty-test
pytest tests/functional/test_dashboard_*.py -v

# 5. Document findings
cp findings/TEMPLATE.md findings/0.5.3/2025-MM-DD_NN_description.md
# ... fill in findings ...
```

### Creating a Finding

1. Encounter a bug or UX issue
2. Create reproducible test (or document manual steps)
3. Copy `findings/TEMPLATE.md` to appropriate version directory
4. Fill in all sections:
   - Summary
   - Root cause analysis
   - Impact assessment
   - Reproduction steps
   - Suggested fixes
5. Submit PR with finding + test coverage

## Test Philosophy

This test suite validates that **spec-kitty bridges humans and machines**:

- **For Humans**: Clear instructions, readable output, helpful errors
- **For LLM Agents**: Parseable prompts, clear expectations, actionable feedback
- **For System**: Reliable orchestration, accurate state tracking, proper attribution

Every test verifies that this bridge works reliably.

## Example Test Output

### Successful Test

```bash
$ pytest tests/functional/test_task_approval.py::TestBasicApprovalFlow::test_approve_moves_task_to_done -v

PASSED [100%]

✓ Task moved from for_review → done
✓ Reviewer attribution recorded
✓ Activity log updated
✓ Git operations completed
```

### Bug Reproduction

```bash
$ pytest tests/functional/test_dashboard_modification_api.py::test_api_detects_spec_modification -v -s

FAILED: Dashboard did not detect spec.md modification after 15s.

Timeline:
1. Created spec.md (36 bytes) ✓
2. Modified spec.md (469 bytes) ✓
3. API polled for 15s ✓
4. API response: UNCHANGED ✗

🐛 BUG CONFIRMED: Backend doesn't track file modifications
```

This output becomes a finding with fix recommendations.

## Performance

**Full Suite**: ~60 seconds
- Unit-style tests: < 1s each
- Integration tests: 1-3s each
- Playwright tests: 5-10s each

**Parallel Execution**: Supported via pytest-xdist (optional)

```bash
# Install parallel runner
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/functional/ -n 4 -v
```

## Troubleshooting

### Tests Fail to Import spec-kitty

```bash
# Verify spec-kitty is installed
pip show spec-kitty-cli

# Verify SPEC_KITTY_REPO points to correct location
echo $SPEC_KITTY_REPO
ls $SPEC_KITTY_REPO/src/specify_cli/
```

### Playwright Tests Fail

```bash
# Reinstall browsers
playwright install chromium

# Run with headed mode to see what's happening
pytest tests/functional/test_dashboard_file_modifications.py --headed
```

### Permission Errors

```bash
# Ensure test directories are writable
chmod -R u+w tests/

# Clean pytest cache
rm -rf .pytest_cache
```

## License

MIT License - same as [Spec-Kitty](https://github.com/Priivacy-ai/spec-kitty)

## Related Projects

- **Spec-Kitty**: [github.com/Priivacy-ai/spec-kitty](https://github.com/Priivacy-ai/spec-kitty) - The main CLI tool
- **Spec Kit**: Original GitHub project that inspired Spec-Kitty

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for any new functionality
4. Ensure all tests pass (except known failing tests)
5. Document findings for any bugs discovered
6. Submit pull request

## Contact

- **Issues**: [github.com/YOUR_ORG/spec-kitty-test/issues](https://github.com/YOUR_ORG/spec-kitty-test/issues)
- **Spec-Kitty Issues**: [github.com/Priivacy-ai/spec-kitty/issues](https://github.com/Priivacy-ai/spec-kitty/issues)

---

**Status**: ✅ Active Development
**Last Updated**: 2025-11-15
**Spec-Kitty Versions Tested**: 0.5.1 (PyPI), 0.5.2 (PyPI), 0.5.3-pre (development)
