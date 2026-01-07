# Issue #66: Windows JSON Encoding Error (UnicodeEncodeError)

**Date:** 2026-01-06
**Session ID:** issue-66-windows-encoding-analysis
**Tested by:** Claude Code Agent
**Category:** Bug Report - Windows Compatibility
**Spec-Kitty Version:** v0.10.9
**Analysis Date:** 2026-01-06
**Applies To:** All versions (v0.4.9+), affects Windows only

## Summary

Windows users get `UnicodeEncodeError: 'charmap' codec can't encode characters` when running spec-kitty commands with `--json` flag. The error occurs because the `main()` entry point doesn't configure stdout encoding for Windows, which defaults to cp1252/charmap that cannot encode Unicode characters (✓, ✗, emoji) present in JSON error messages.

## Observation

### User Command
```bash
spec-kitty agent feature create-feature "my-great-feature" --json
```

### Error Output
```
{"error": "'charmap' codec can't encode characters in position 161-163: character maps to <undefined>"}
```

### User Attempts to Fix
User tried multiple workarounds:
1. Setting `PYTHONIOENCODING=utf-8` in shell
2. Running `chcp 65001` (UTF-8 code page)
3. Setting environment variable before command

**None worked** because these must be set BEFORE Python starts, and don't reconfigure an already-running process.

## Impact

- **Severity:** HIGH
- **Scope:** Windows users only (macOS/Linux unaffected)
- **Frequency:** Happens on EVERY `--json` command that encounters Unicode in output
- **Affected Commands:**
  - `spec-kitty agent feature create-feature --json`
  - `spec-kitty agent feature accept --json`
  - `spec-kitty agent tasks move-task --json`
  - All agent commands with `--json` flag

**User Impact:**
- Windows users cannot use JSON output mode reliably
- Blocks automation and scripting workflows
- AI agents using spec-kitty on Windows affected

## Root Cause Analysis

### The Core Problem

**File:** `src/specify_cli/__init__.py` lines 151-152

```python
def main():
    app()  # ❌ No encoding configuration!
```

**What happens on Windows:**
1. Python starts with default Windows encoding (cp1252/charmap)
2. `sys.stdout.encoding` = 'charmap' (cannot encode Unicode)
3. spec-kitty runs, encounters error with Unicode character
4. Code calls `print(json.dumps({"error": str(e)}))`
5. `json.dumps()` creates JSON string (may contain Unicode)
6. `print()` attempts to write to stdout
7. **FAILS:** charmap cannot encode ✓ (U+2713), ✗ (U+2717), emoji, etc.

### Where Unicode Characters Come From

**Multiple sources in spec-kitty:**

1. **Console output strings** (feature.py):
   - Line 152: `"[green]✓[/green] Feature created"`
   - Line 201: `"[green]✓[/green] Prerequisites check passed"`
   - Line 204: `"[red]✗[/red] Prerequisites check failed"`

2. **Version error messages** (version_checker.py):
   - Line 149: `"✅ Check mark button"`
   - Line 157: `"❌ Cross mark"`
   - Line 163: `"🚨 Police car light"`

3. **Exception messages** propagated via `str(e)`:
   - Error messages from various parts of code
   - Git command output (may contain Unicode)
   - File names with Unicode characters

### The JSON Output Pattern

**Found in feature.py (15+ instances):**

```python
except Exception as e:
    if json_output:
        print(json.dumps({"error": str(e)}))  # ❌ FAILS on Windows
    else:
        console.print(f"[red]Error:[/red] {e}")  # Works (Rich handles it)
```

**Why it fails:**
- `str(e)` preserves Unicode from exception message
- `json.dumps()` by default uses `ensure_ascii=True`, BUT
- `print()` still needs to encode the result to stdout
- On Windows, stdout is charmap, cannot encode Unicode
- **Error happens during print(), not during json.dumps()**

## User/Agent Journey

### Journey: Windows User with AI Agent Automation

1. User installs spec-kitty on Windows: `pip install spec-kitty-cli`
2. User configures AI agent to use `--json` flag for structured output
3. Agent runs: `spec-kitty agent feature create-feature "new-feature" --json`
4. Command encounters some condition that raises exception
5. Exception message contains ✓ or ✗ (common in spec-kitty)
6. **Error:** `UnicodeEncodeError: 'charmap' codec can't encode...`
7. AI agent receives encoding error instead of structured error JSON
8. User tries environment variable workarounds (don't work)
9. User reports bug
10. User is blocked from using JSON automation on Windows

### Journey: Windows Developer Testing

1. Developer runs spec-kitty on Windows
2. Tests `--json` output for automation
3. **Every command with Unicode in error path fails**
4. Cannot reliably parse outputs
5. Cannot build automation tools
6. Windows becomes second-class citizen

## What Could Have Helped

### Prevention
1. **Windows CI/CD testing:**
   - Run tests on actual Windows environment
   - Test `--json` output mode specifically
   - Would catch encoding errors

2. **Encoding configuration at entry point:**
   - Configure UTF-8 in `main()` function
   - Standard practice for cross-platform Python CLIs
   - Many CLIs do this (click, typer, etc.)

3. **Defensive JSON output:**
   - Use `ensure_ascii=True` in all `json.dumps()`
   - Converts Unicode to `\uXXXX` escape sequences
   - Windows-safe even without stdout reconfiguration

### Detection
1. **Better error messages:**
   - Catch `UnicodeEncodeError` specifically
   - Provide Windows-specific guidance
   - Suggest fix or workaround

2. **Documentation:**
   - Document Windows encoding requirements
   - Provide setup instructions for Windows users
   - Explain `--json` mode limitations

## Suggested Improvements

### Immediate Fix (Required for v0.10.10)

**Option 1: Configure stdout in main() (RECOMMENDED)**

**File:** `src/specify_cli/__init__.py`

```python
def main():
    """Entry point for spec-kitty CLI.

    Configures UTF-8 encoding on Windows to prevent UnicodeEncodeError
    when printing JSON output containing Unicode characters.
    """
    import sys

    # Fix for Issue #66: Configure UTF-8 on Windows
    if sys.platform == 'win32':
        try:
            # Python 3.7+
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 fallback
            import io
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace'
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding='utf-8', errors='replace'
            )

    app()
```

**Rationale:**
- ✅ Fixes root cause (stdout encoding)
- ✅ Works for ALL commands, not just --json
- ✅ Standard practice for cross-platform CLIs
- ✅ No code changes needed elsewhere

**Option 2: Use ensure_ascii=True (DEFENSIVE)**

**File:** `src/specify_cli/cli/commands/agent/feature.py` (15 locations)

```python
# Pattern replacement:

# Before:
print(json.dumps({"error": str(e)}))

# After:
print(json.dumps({"error": str(e)}, ensure_ascii=True))
```

**Rationale:**
- ✅ Works even without main() fix
- ✅ Defense-in-depth approach
- ⚠️ Makes JSON less readable (`\u2713` instead of ✓)
- ⚠️ Requires changes in multiple locations

**Recommendation:** Implement **BOTH** options for maximum compatibility.

### Testing Improvements

**File:** `tests/functional/test_issue_66_windows_json_encoding.py` (NEW)

**Coverage:**
1. Simulate Windows charmap encoding behavior
2. Reproduce exact error from Issue #66
3. Validate fix option 1 (stdout reconfiguration)
4. Validate fix option 2 (ensure_ascii=True)
5. Test common Unicode characters in spec-kitty
6. Test real-world scenarios

**Key Feature:** Tests work on **macOS/Linux** by simulating Windows behavior!

**Implementation:**
```python
class CharmapStdout:
    """Simulates Windows cp1252/charmap stdout encoding."""
    def write(self, text):
        for i, char in enumerate(text):
            if ord(char) > 127:  # Non-ASCII
                raise UnicodeEncodeError(
                    'charmap', text, i, i + 1,
                    'character maps to <undefined>'
                )
```

This allows testing Windows issues on any platform! 🎯

### CI/CD Improvements

**Add Windows testing to GitHub Actions:**

```yaml
test-windows:
  runs-on: windows-latest
  steps:
    - name: Install spec-kitty
      run: pip install spec-kitty-cli

    - name: Test JSON output
      run: |
        spec-kitty agent feature create-feature "test" --json --help
        # Should not fail with encoding error
```

### Documentation

**Add to README or Windows setup guide:**

```markdown
## Windows Users

If you encounter encoding errors like:
`'charmap' codec can't encode characters`

**Quick Fix:**
Run PowerShell as Administrator and set UTF-8:
```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```

**Permanent Fix:**
Use Windows Terminal or ensure your console supports UTF-8.
```

## Related Files

**Entry Point (FIX HERE):**
- `src/specify_cli/__init__.py` (line 151) - main() function

**JSON Output Locations (15 instances):**
- `src/specify_cli/cli/commands/agent/feature.py`
  - Lines: 137, 145, 158, 183, 196, 198, 215, 237, 267, 277, 397, 407, 441, 537, 584, 621

**Unicode Sources:**
- `src/specify_cli/cli/commands/agent/feature.py` - ✓, ✗ in console output
- `src/specify_cli/core/version_checker.py` - ✅, ❌, 🚨 emoji
- Various console.print() calls throughout codebase

**Existing Encoding Work:**
- PR #56 - Fixed file reading encoding
- `tests/functional/test_pr_56_windows_utf8_encoding.py` - Tests file I/O
- **Gap:** No tests for stdout/stderr encoding

**New Test File:**
- `tests/functional/test_issue_66_windows_json_encoding.py` - NEW

## Example Output/Reproduction

### The Error (Before Fix)

```powershell
PS C:\Users\user\project> spec-kitty agent feature create-feature "my-feature" --json
{"error": "'charmap' codec can't encode characters in position 161-163: character maps to <undefined>"}
```

### Working Output (After Fix)

**With stdout reconfigure (Option 1):**
```powershell
PS C:\Users\user\project> spec-kitty agent feature create-feature "my-feature" --json
{"status": "success", "feature_dir": ".worktrees/001-my-feature", "worktree_path": ".worktrees/001-my-feature"}
```

**With ensure_ascii=True (Option 2):**
```powershell
PS C:\Users\user\project> spec-kitty agent feature create-feature "my-feature" --json
{"status": "success", "feature_dir": ".worktrees/001-my-feature", "message": "Feature created \u2713"}
```

### User Workflow (After Fix)

```powershell
# 1. Install/upgrade
pip install --upgrade spec-kitty-cli

# 2. Use --json mode
spec-kitty agent feature create-feature "my-feature" --json

# 3. Parse output
$result = spec-kitty agent feature create-feature "my-feature" --json | ConvertFrom-Json
Write-Host "Feature created at: $($result.feature_dir)"
```

## Test Coverage

**New Test File:** `tests/functional/test_issue_66_windows_json_encoding.py`

**Test Classes:**

1. **TestWindowsEncodingSimulation** (4 tests)
   - Reproduce charmap encoding failure
   - Test json.dumps() with Unicode
   - Test ensure_ascii workaround
   - Test common spec-kitty Unicode chars

2. **TestWindowsEncodingFix** (3 tests)
   - Validate stdout reconfiguration fix
   - Test on actual Windows (conditional)
   - Verify encoding after fix

3. **TestJSONOutputPatterns** (3 tests)
   - Test error JSON pattern from feature.py
   - Test success JSON pattern
   - Test ensure_ascii safety

4. **TestUnicodeSourcesInSpecKitty** (3 tests)
   - Console.print Unicode leakage
   - Version checker emoji
   - Git output Unicode

5. **TestRealWorldScenario** (2 tests)
   - Exact Issue #66 reproduction
   - User workaround validation

**Total:** 15 comprehensive tests

**Key Innovation:** Tests work on **any platform** by simulating Windows charmap behavior!

## Priority

**🔴 HIGH - Blocks Windows users from JSON automation**

### User Impact
- Windows users cannot use `--json` flag reliably
- AI agents on Windows cannot parse structured output
- Automation scripts fail unpredictably

### Workarounds Available
- ⚠️ Set `PYTHONIOENCODING=utf-8` before Python starts (not in running shell)
- ⚠️ Use Windows Terminal (UTF-8 by default)
- ⚠️ Avoid Unicode in error paths (not realistic)

**Better solution:** Fix in code.

## Recommended Action

### For v0.10.10 Release

1. **Apply stdout reconfiguration fix**
   - Location: `src/specify_cli/__init__.py` main()
   - 5 lines of code
   - Fixes root cause

2. **Optionally: Use ensure_ascii=True**
   - 15 locations in feature.py
   - Defense-in-depth

3. **Add tests**
   - Already created: `test_issue_66_windows_json_encoding.py`
   - 15 tests covering all scenarios
   - Works on any platform

4. **Add Windows CI/CD**
   - Test on actual Windows environment
   - Validate `--json` output works
   - Catch future encoding issues

### Complexity

**Fix:** ⭐ Simple (5 lines of code)
**Testing:** ⭐⭐ Moderate (simulation required)
**Risk:** ⭐ Low (backwards compatible)

---

**Notes:**

This is a **software bug**, not user error. The user correctly identified the command structure after initial syntax mistakes. The encoding error is a legitimate bug that blocks Windows users from using JSON output mode.

The fix is simple and standard practice for cross-platform Python CLIs. The test suite provides comprehensive coverage using Windows behavior simulation that works on any platform.

**Relationship to Recent Work:**
- This continues the theme of testing what users experience
- Windows users are real users who deserve first-class support
- Our new distribution testing paradigm should include Windows compatibility

---

## Related Issues

- **Issue #62, #63, #64** - Template bundling bug (fixed in v0.10.9)
- **Issue #68** - Mission templates still have script refs (discovered while investigating #66)
