# Findings Report: Encoding Errors Crash Dashboard Server

**Date:** 2025-11-13
**Session ID:** encoding-findings-2025-11-13
**Tested by:** Robert (based on Battleship project encoding issues)
**Category:** Bug Report - Critical
**Spec-Kitty Version:** 8fb628b91042f6777bf80fda76715df8577349d8 (commit 8fb628b)
**Analysis Date:** 2025-11-13
**Applies To:** 0.4.13 and likely earlier versions

## Summary

LLM-generated markdown files containing Windows-1252 smart quotes or other non-UTF-8 characters cause the spec-kitty dashboard acceptance server to crash with `ArtifactEncodingError`, rendering a completely blank dashboard page to users. The strict UTF-8 decoding in `_read_text_strict()` has no fallback mechanism, making a single encoding error in any markdown file fatal to the entire dashboard.

## Observation

When LLMs generate markdown files (spec.md, research.md, data-model.md, etc.) that contain Windows-1252 encoded characters—most commonly smart quotes (' ' " "), mathematical symbols (± ×), or other non-ASCII characters—the dashboard server crashes during the `collect_feature_summary()` phase.

**Specific characters that trigger the crash:**
- RIGHT SINGLE QUOTE (0x92): `'`
- LEFT SINGLE QUOTE (0x91): `'`
- LEFT DOUBLE QUOTE (0x93): `"`
- RIGHT DOUBLE QUOTE (0x94): `"`
- PLUS-MINUS SIGN (0xB1): `±`
- MULTIPLICATION SIGN (0xD7): `×`

**Observed behavior:**
1. User runs dashboard command (from Claude Code slash command or CLI)
2. Dashboard server starts and attempts to parse markdown artifacts
3. Server encounters Windows-1252 byte in a markdown file
4. `_read_text_strict()` raises `UnicodeDecodeError`
5. This becomes `ArtifactEncodingError` and aborts `collect_feature_summary()`
6. Dashboard renders completely blank page
7. No user-visible error message explaining what went wrong

## Impact

- **Severity:** Critical
- **Scope:** All users, but especially LLM agents who frequently copy content with smart quotes from specifications or external sources
- **Frequency:** High - happens whenever LLM writes smart quotes or certain mathematical symbols to markdown files

**User journey impact:**
- Complete loss of dashboard functionality (blank page)
- No actionable error message
- Requires manual investigation to discover encoding issue
- Blocks all feature tracking and progress monitoring

## Root Cause Analysis

The issue stems from a strict UTF-8 reading policy without fallback or graceful degradation:

**File:** `/Users/robert/Code/spec-kitty/scripts/tasks/acceptance_support.py`

**Function:** `_read_text_strict()` (lines 247-251)
```python
def _read_text_strict(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactEncodingError(path, exc) from exc
```

**How it propagates:**
1. `collect_feature_summary()` calls `_read_file()`
2. `_read_file()` calls `_read_text_strict()`
3. `_read_text_strict()` raises `ArtifactEncodingError`
4. Exception bubbles up and crashes the dashboard summary generation
5. Dashboard frontend receives no data, renders blank page

**Why LLMs create this problem:**
- LLMs often copy text from user prompts or external sources that contain smart quotes
- Many text editors and IDEs default to smart quotes
- LLMs trained on web content may reproduce smart quotes from training data
- The characters look correct visually, so LLMs don't recognize them as problematic

**Existing mitigation:**
- `normalize_feature_encoding()` function exists (lines 288-329) but is NOT called automatically
- `validate_encoding.py` script exists but requires manual invocation
- `--normalize-encoding` flag available on some commands but not discoverable

## User/Agent Journey

**Scenario 1: LLM writes spec with smart quotes**
1. LLM agent creates feature using `create-new-feature.sh`
2. LLM writes specification containing smart quotes (e.g., "user's profile")
3. User attempts to view dashboard
4. Dashboard shows blank page
5. User confused, no error message visible
6. User must debug manually or ask LLM for help

**Scenario 2: Copy-paste from external document**
1. User provides specification to LLM that contains smart quotes
2. LLM copies specification text into data-model.md
3. Dashboard becomes unusable
4. User doesn't understand connection between spec content and dashboard crash

**Scenario 3: Mathematical documentation**
1. LLM documents API that uses ± or × symbols
2. LLM writes these as Windows-1252 characters instead of Unicode escapes
3. Dashboard crashes silently
4. Error is non-obvious because symbols look correct in editor

## What Could Have Helped

**Missing error visibility:**
- Dashboard frontend should show encoding errors, not blank page
- Error message should specify which file and byte position has problem
- Error message should suggest the fix: `spec-kitty validate-encoding --fix`

**Missing proactive validation:**
- No pre-commit hook to catch encoding issues
- No automatic encoding validation when files are written
- No warning when LLM writes potentially problematic characters

**Missing graceful degradation:**
- Could attempt cp1252/latin-1 decode and display with warning
- Could show partial dashboard with problematic files marked
- Could auto-repair on dashboard start and log the fix

**Documentation gaps:**
- `validate_encoding.py` script exists but not documented in user guides
- `--normalize-encoding` flag not mentioned in common workflows
- No explanation of why UTF-8 is required or how to fix issues

**LLM agent instructions:**
- No explicit warning in agent prompts about smart quotes
- No instruction to use straight quotes and ASCII symbols
- `.kittify/AGENTS.md` exists but may not be consistently referenced

## Suggested Improvements

### 1. Immediate: Better Error Reporting
- Dashboard should catch `ArtifactEncodingError` and display it
- Error message should include:
  - Which file has the problem
  - Byte position and problematic byte (0x92, etc.)
  - Command to fix: `spec-kitty validate-encoding --fix <dir>`
  - Link to documentation

### 2. Short-term: Automatic Repair
- Add `--auto-repair-encoding` flag to dashboard command
- Dashboard could call `normalize_feature_encoding()` on startup
- Log which files were repaired so users are aware

### 3. Medium-term: Proactive Prevention
- Add encoding validation to file write operations
- Provide git pre-commit hook that runs `validate_encoding.py`
- Add encoding check to `spec-kitty verify-setup`
- Warn when potentially problematic characters detected

### 4. Long-term: LLM Agent Guardrails
- Update all agent templates to explicitly forbid smart quotes
- Show examples of forbidden characters
- Instruct LLMs to use ASCII alternatives:
  - `'` instead of ' '
  - `"` instead of " "
  - `+/-` instead of ±
  - `x` or `*` instead of ×
- Make `.kittify/AGENTS.md` more prominent in agent context

### 5. Fallback Decoding Strategy
- Attempt cp1252/latin-1 decode if UTF-8 fails
- Display content with warning banner: "This file has encoding issues"
- Provide "Fix encoding" button in dashboard UI
- Keep dashboard functional even with encoding problems

### 6. Testing Infrastructure
- Add encoding tests to verify dashboard handles invalid UTF-8 gracefully
- Test that `normalize_feature_encoding()` correctly fixes common issues
- Test that `validate_encoding.py` detects all problematic characters
- Test that error messages are actionable

## Related Files

**Core encoding logic:**
- `/Users/robert/Code/spec-kitty/scripts/tasks/acceptance_support.py` - Lines 247-251 (`_read_text_strict`)
- `/Users/robert/Code/spec-kitty/scripts/tasks/acceptance_support.py` - Lines 288-329 (`normalize_feature_encoding`)
- `/Users/robert/Code/spec-kitty/scripts/validate_encoding.py` - Validation and repair utility

**Error definitions:**
- `/Users/robert/Code/spec-kitty/scripts/tasks/acceptance_support.py` - Lines 29-45 (`AcceptanceError`, `ArtifactEncodingError`)

**Existing tests:**
- `/Users/robert/Code/spec-kitty/tests/test_acceptance_support.py` - May need encoding test coverage

**Agent instructions:**
- `.kittify/AGENTS.md` - Should warn about encoding issues

## Example Output/Reproduction

**To reproduce:**

```bash
# 1. Create a test project
cd /tmp
spec-kitty init test_encoding --ai=claude --ignore-agent-tools <<< "y"
cd test_encoding

# 2. Create feature with encoding issue
.kittify/scripts/bash/create-new-feature.sh --feature-name "TestEncoding" "Test encoding issue"

# 3. Write Windows-1252 characters to markdown file
cd .worktrees/001-test-encoding
echo "User's profile" > kitty-specs/001-test-encoding/spec.md  # smart quotes

# 4. Try to view dashboard
cd /tmp/test_encoding
spec-kitty dashboard
# Result: Blank dashboard page, no error message
```

**Validation script detection:**

```bash
# Run encoding validator
cd /tmp/test_encoding/.worktrees/001-test-encoding
python3 /Users/robert/Code/spec-kitty/scripts/validate_encoding.py kitty-specs/001-test-encoding

# Output shows:
# ❌ spec.md
#    Error: Position 5: invalid start byte (byte 0x92)
```

**Manual byte inspection:**

```bash
# Check file encoding
file -I spec.md
# Output: application/octet-stream; charset=binary

# Find problematic bytes
python3 << 'EOF'
import sys
with open('spec.md', 'rb') as f:
    data = f.read()
    for i, byte in enumerate(data):
        if byte >= 0x80 and byte <= 0x9F:
            print(f"Line ?, Position {i}: byte 0x{byte:02x}")
EOF
```

---

**Notes:**

This finding is based on real encoding issues encountered in the Battleship project, where `data-model.md` and `research.md` contained Windows-1252 characters that crashed the dashboard. The issue is widespread because:

1. LLMs frequently generate smart quotes from training data
2. Users copy specifications containing smart quotes
3. The dashboard provides no feedback about encoding errors
4. The fix exists but requires manual discovery and invocation

The combination of strict UTF-8 enforcement + no error visibility + no automatic repair makes this a critical usability issue for both human users and LLM agents.
