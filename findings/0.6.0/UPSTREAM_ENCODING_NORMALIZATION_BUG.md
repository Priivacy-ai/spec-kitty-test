# Encoding Normalization Regression - Spec-Kitty

**Report Date**: 2025-11-16
**Affected Version**: spec-kitty-cli v0.5.3 (commit 1113b38)
**Reporter**: LLM Test Agent via spec-kitty-test suite
**Severity**: Medium (breaks encoding cleanup workflow)

---

## Summary

The `normalize_feature_encoding()` function in `scripts/tasks/acceptance_support.py` is **not actually normalizing** Windows-1252 characters to their ASCII/UTF-8 equivalents. It re-encodes without character mapping, leaving problematic bytes that cause `UnicodeDecodeError` when reading as UTF-8.

**Impact**: Users with Windows-1252 encoded files (smart quotes, em dashes, math symbols) cannot clean them automatically. The normalization function completes without errors but leaves files in an invalid state.

---

## Test Failures

**4 out of 5 normalization tests failing:**

```
FAILED test_normalize_fixes_windows1252
FAILED test_converts_smart_quotes_to_straight
FAILED test_handles_mathematical_symbols
FAILED test_returns_list_of_fixed_files
PASSED test_preserves_valid_utf8_content ✓
```

---

## Root Cause

**Current Implementation** (`acceptance_support.py:288-334`):

```python
def normalize_feature_encoding(repo_root: Path, feature: str) -> List[Path]:
    # ... (setup code)

    for path in candidates:
        data = path.read_bytes()
        try:
            data.decode("utf-8")
            continue  # Already valid UTF-8
        except UnicodeDecodeError:
            pass

        # Try to decode with Windows encodings
        text: Optional[str] = None
        for encoding in ("cp1252", "latin-1"):
            try:
                text = data.decode(encoding)  # ❌ PROBLEM: Decodes but doesn't normalize
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            text = data.decode("utf-8", errors="replace")

        path.write_text(text, encoding="utf-8")  # ❌ Writes cp1252 chars as UTF-8
        rewritten.append(path)

    return rewritten
```

**What happens:**
1. Read bytes: `b"It\x92s"` (It's with Windows-1252 right single quote)
2. Decode with cp1252: `"It's"` (the character is now Unicode U+2019 RIGHT SINGLE QUOTATION MARK)
3. Write as UTF-8: File contains UTF-8 encoding of U+2019 (bytes `\xe2\x80\x99`)
4. ❌ **File is NOT plain ASCII** - contains multi-byte UTF-8 sequences

**Expected behavior:**
1. Read bytes: `b"It\x92s"`
2. Decode with cp1252: `"It's"` (U+2019)
3. **Normalize U+2019 → U+0027** (straight apostrophe): `"It's"`
4. Write as UTF-8: File contains `It's` in plain ASCII
5. ✅ File is now plain UTF-8 compatible

---

## Reproduction

```python
# Test case that fails
from pathlib import Path
from scripts.tasks.acceptance_support import normalize_feature_encoding

# Create file with Windows-1252 smart quote
test_file = Path("spec.md")
test_file.write_bytes(b"It\x92s a test")  # 0x92 = right single quote in cp1252

# Try to normalize
normalize_feature_encoding(Path("."), "test-feature")

# Try to read as UTF-8
content = test_file.read_text(encoding='utf-8')  # ❌ UnicodeDecodeError!
# Error: 'utf-8' codec can't decode byte 0x92
```

**Expected**: Should read successfully as `"It's a test"` with ASCII apostrophe
**Actual**: Still contains 0x92 byte, fails UTF-8 decode

---

## Required Character Mappings

The function needs to **normalize** problematic characters to ASCII equivalents:

| Windows-1252 | Byte | Unicode | Should Convert To |
|--------------|------|---------|-------------------|
| Right single quote ' | 0x92 | U+2019 | `'` (U+0027) |
| Left single quote ' | 0x91 | U+2018 | `'` (U+0027) |
| Right double quote " | 0x94 | U+201D | `"` (U+0022) |
| Left double quote " | 0x93 | U+201C | `"` (U+0022) |
| Em dash — | 0x97 | U+2014 | `--` or `-` |
| En dash – | 0x96 | U+2013 | `-` |
| Plus-minus ± | 0xb1 | U+00B1 | `±` (keep as UTF-8) or `+/-` |
| Multiplication × | 0xd7 | U+00D7 | `×` (keep as UTF-8) or `*` |
| Ellipsis … | 0x85 | U+2026 | `...` |

---

## Suggested Fix

Add character normalization after decoding:

```python
def normalize_feature_encoding(repo_root: Path, feature: str) -> List[Path]:
    # Character mapping: Unicode → ASCII equivalent
    NORMALIZE_MAP = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201C': '"',  # Left double quote
        '\u201D': '"',  # Right double quote
        '\u2014': '--', # Em dash
        '\u2013': '-',  # En dash
        '\u2026': '...', # Ellipsis
        # Keep some UTF-8 chars that have no good ASCII equivalent
        # '\u00B1': '+/-',  # Plus-minus (optional)
        # '\u00D7': '*',    # Multiplication (optional)
    }

    # ... (setup code same as before)

    for path in candidates:
        data = path.read_bytes()
        try:
            data.decode("utf-8")
            continue
        except UnicodeDecodeError:
            pass

        text: Optional[str] = None
        for encoding in ("cp1252", "latin-1"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            text = data.decode("utf-8", errors="replace")

        # ✅ NEW: Normalize problematic characters to ASCII
        for unicode_char, ascii_replacement in NORMALIZE_MAP.items():
            text = text.replace(unicode_char, ascii_replacement)

        path.write_text(text, encoding="utf-8")
        rewritten.append(path)

    return rewritten
```

---

## Test Validation

After implementing the fix, these tests should pass:

```bash
pytest tests/functional/test_encoding_issues.py::TestNormalizationFunction -v

# Expected:
# test_normalize_fixes_windows1252 ✅ PASS
# test_converts_smart_quotes_to_straight ✅ PASS
# test_handles_mathematical_symbols ✅ PASS
# test_returns_list_of_fixed_files ✅ PASS
# test_preserves_valid_utf8_content ✅ PASS
```

---

## Affected Use Cases

**User Scenario**: Developer on Windows creates spec.md with smart quotes from Word/Outlook

```markdown
# Specification – Authentication System

## Requirements
- REQ-1: Support OAuth 2.0 "bearer tokens"
- REQ-2: Handle failures gracefully…
```

**Current behavior:**
1. User runs: `spec-kitty accept 001-auth --normalize-encoding`
2. Function decodes cp1252 → UTF-8 multi-byte sequences
3. ❌ File still contains multi-byte UTF-8 (not plain ASCII)
4. Some tools fail: `git grep`, regex patterns, CI validators
5. User confused: "I normalized but still have encoding errors!"

**Expected behavior:**
1. User runs: `spec-kitty accept 001-auth --normalize-encoding`
2. Function decodes cp1252 → normalizes to ASCII equivalents
3. ✅ File contains plain ASCII: `"bearer tokens"`, `...`
4. All tools work correctly
5. User happy: "Normalization fixed it!"

---

## Why This Matters

**Context from upstream fixes**:

You recently fixed two validation bugs (commits 9ff30e1, e5b48a2) with the pattern:

> "Overly strict validation forcing unnecessary user interaction"

This bug has the **opposite** problem:

> "Insufficient normalization leaving users with broken files"

**The pattern**:
- WP conflict bug: **Too strict** (blocked too much)
- Accept command bug: **Too strict** (asked too much)
- **Encoding bug: Too lenient** (normalized too little)

All three reflect **incorrect scope**:
- WP conflict: Should block same WP, not all WPs
- Accept command: Should ask when unknown, not when inferable
- **Encoding: Should normalize to ASCII, not just re-encode**

---

## Impact Assessment

**Severity**: Medium
- ✅ **Not a blocker**: Dashboard bugs (#1, #2) are fixed
- ✅ **Not a regression from 005**: Mission system unaffected
- ⚠️ **User experience gap**: Encoding normalization advertised but broken
- ⚠️ **Test coverage**: 4/5 tests failing indicates feature incomplete

**Priority**: Should fix before next release
- Feature is advertised: `--normalize-encoding` flag exists
- Tests exist and are well-written (they caught the bug!)
- Fix is straightforward: add character mapping

---

## Suggested Timeline

1. **Immediate**: Add character normalization map to `normalize_feature_encoding()`
2. **Verify**: Run encoding test suite (`pytest tests/functional/test_encoding_issues.py::TestNormalizationFunction`)
3. **Document**: Update help text to explain which characters are normalized
4. **Release**: Include in next patch release (v0.5.4)

---

## Related Files

- **Implementation**: `scripts/tasks/acceptance_support.py:288-334`
- **Tests**: `tests/functional/test_encoding_issues.py:620-780` (in spec-kitty-test repo)
- **Usage**: `.kittify/templates/commands/accept.md` (mentions normalization)

---

## Additional Context

**Why the tests exist**: These tests validate the encoding normalization feature that detects and fixes Windows-1252/Latin-1 encoded artifacts. The feature was implemented in commit 177f092 ("feat: Add encoding validation and plan validation guardrails").

**Test quality**: The tests are excellent - they create files with actual Windows-1252 bytes, call the normalization function, and verify the output is valid UTF-8. They caught this regression immediately.

**User expectation**: When a function is called `normalize_feature_encoding`, users expect it to normalize characters (smart quotes → straight quotes), not just re-encode bytes.

---

## Recommendation

**Priority**: Medium
**Effort**: Low (15 minutes to add character map)
**Risk**: Low (tests validate the fix)
**User Impact**: High (fixes advertised feature)

Please add character normalization to the `normalize_feature_encoding()` function so users can actually clean their Windows-encoded files.

---

**Test suite reference**: https://github.com/YOUR_ORG/spec-kitty-test
**Failing tests**: `tests/functional/test_encoding_issues.py::TestNormalizationFunction`
