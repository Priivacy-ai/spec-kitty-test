# PyPI Release 0.12.0 Test Results

**Date:** 2026-01-24
**Session ID:** pypi-0.12.0-release-test
**Tested by:** Claude Opus 4.5 (adversarial testing)
**Category:** Bug Report (Multiple Issues)
**Spec-Kitty Version:** 0.12.0
**Analysis Date:** 2026-01-24
**Applies To:** spec-kitty-cli 0.12.0 (https://pypi.org/project/spec-kitty-cli/)

## Summary

Testing of spec-kitty-cli 0.12.0 from PyPI reveals **4 critical bugs** that were present in 0.11.3 remain unfixed. The test results are nearly identical: 986 passed, 405 failed, 174 errors, 450 skipped.

## Test Results Overview

| Metric | 0.11.3 | 0.12.0 | Change |
|--------|--------|--------|--------|
| Passed | 985 | 986 | +1 |
| Failed | 406 | 405 | -1 |
| Errors | 174 | 174 | 0 |
| Skipped | 450 | 450 | 0 |
| Total | 2048 | 2048 | 0 |

## Critical Bugs Still Present

### Bug #1: Mission.__init__() String Type Error (CRITICAL)

**Location:** `specify_cli/mission.py:173`

**Error:**
```
AttributeError: 'str' object has no attribute 'resolve'
```

**Impact:**
- Severity: **Critical**
- All mission loading fails when string arguments are passed
- Breaks `Mission('software-dev')`, `Mission('research')`, `Mission('documentation')`
- 16 distribution tests fail directly due to this

**Reproduction:**
```python
from specify_cli.mission import Mission
m = Mission('software-dev')  # FAILS
m = Mission(Path('software-dev'))  # Works
```

**Root Cause:** Line 173 assumes `mission_path` is already a Path object:
```python
self.path = mission_path.resolve()  # Fails if mission_path is str
```

**Fix Required:** Add type coercion at the start of `__init__`:
```python
if isinstance(mission_path, str):
    mission_path = Path(mission_path)
```

---

### Bug #2: VCS get_vcs() String Type Error (HIGH)

**Location:** `specify_cli/core/vcs/`

**Error:**
```
AttributeError: 'str' object has no attribute 'resolve'
```

**Impact:**
- Severity: **High**
- VCS operations fail when string paths are passed
- Affects any code that uses `get_vcs(str_path)`

**Reproduction:**
```python
from pathlib import Path
from specify_cli.core.vcs import get_vcs

get_vcs(Path.cwd())  # Works - returns GitVCS
get_vcs(str(Path.cwd()))  # FAILS - AttributeError
```

**Root Cause:** Same pattern as Bug #1 - assumes Path objects, not strings.

---

### Bug #3: spec-kitty init Requires TTY (HIGH)

**Location:** `specify_cli/cli/commands/init.py:347` and `specify_cli/cli/ui.py:89`

**Error:**
```
error: (19, 'Operation not supported by device')
termios.tcgetattr(fd) fails on non-TTY stdin
```

**Impact:**
- Severity: **High**
- 174 test errors (all tests using `spec_kitty_project` fixture)
- Blocks automated testing in CI environments
- Blocks scripted initialization workflows

**Reproduction:**
```bash
# In a non-TTY environment (subprocess, CI):
spec-kitty init --agent claude --here --force
# FAILS at agent strategy selection prompt
```

**Root Cause:** The `select_with_arrows()` function uses `readchar.readkey()` which requires a TTY. There's no `--non-interactive` or `--yes` flag to bypass interactive prompts.

**Fix Required:** Add non-interactive mode:
```bash
spec-kitty init --agent claude --here --force --non-interactive --strategy preferred
```

---

### Bug #4: Migration System Incomplete (MEDIUM)

**Impact:**
- Severity: **Medium**
- 90+ migration-related test errors
- Upgrade path from older versions may fail

**Affected Tests:**
- `test_m_0_10_0_python_cli.py` - All 15 tests ERROR
- `test_m_0_10_9_repair_templates.py` - All 4 tests ERROR
- `test_m_0_8_0_remove_active_mission.py` - All 4 tests ERROR

---

## Distribution Test Failures

All distribution tests that require `spec-kitty init` fail due to Bug #3:

```
tests/distribution/templates_migrations/test_fresh_install_workflow.py::test_fresh_install_init_workflow FAILED
tests/distribution/templates_migrations/test_mission_templates.py - 16 failures due to Bug #1
```

## Commands That Work

Despite the bugs, basic CLI commands work:

```bash
spec-kitty --version                    # ✓ Works
spec-kitty --help                       # ✓ Works
spec-kitty agent tasks status           # ✓ Works (in initialized projects)
spec-kitty agent workflow implement     # ✓ Works (in initialized projects)
```

## User/Agent Journey

1. User installs spec-kitty-cli 0.12.0 from PyPI
2. User tries to initialize a new project with `spec-kitty init`
3. Init fails in non-TTY environment (CI, subprocess) with termios error
4. User tries Python API: `Mission('software-dev')` fails with AttributeError
5. User cannot use spec-kitty in automated workflows

## What Could Have Helped

1. **Type annotations enforcement** - Using `mission_path: Path` instead of `Union[str, Path]` would have caught this at static analysis
2. **Non-TTY testing in CI** - Running tests in non-interactive mode would catch Bug #3
3. **Distribution test gate** - Requiring distribution tests to pass before release

## Suggested Improvements

### Immediate Fixes (0.12.1)

1. **Fix Mission.__init__()** - Add `Path(mission_path)` coercion
2. **Fix get_vcs()** - Add `Path(path)` coercion
3. **Add --non-interactive flag** to init command

### Process Improvements

1. **Gate releases on distribution tests** - Don't release if distribution tests fail
2. **Add non-TTY CI testing** - Test in environments without TTY
3. **Type checking in CI** - Run mypy/pyright to catch type errors

## Related Files

- `specify_cli/mission.py:173` - Mission.__init__ type error
- `specify_cli/core/vcs/` - VCS type errors
- `specify_cli/cli/commands/init.py:347` - TTY requirement
- `specify_cli/cli/ui.py:19,89` - readchar TTY dependency

## Example Output/Reproduction

### Bug #1 Reproduction
```
$ python3 -c "from specify_cli.mission import Mission; m = Mission('software-dev')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../specify_cli/mission.py", line 173, in __init__
    self.path = mission_path.resolve()
AttributeError: 'str' object has no attribute 'resolve'
```

### Bug #3 Reproduction
```
$ spec-kitty init --agent claude --here --force
... (prompts work in TTY)
error: (19, 'Operation not supported by device')
```

---

**Notes:** This release (0.12.0) has the same bugs as 0.11.3. The bugs affect all PyPI users who try to:
1. Use the Python API with string arguments
2. Run spec-kitty init in non-TTY environments (CI, automated scripts)

These bugs have now persisted through multiple releases since 0.10.8.
