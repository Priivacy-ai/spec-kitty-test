# Findings Report: Gemini Format Has Claude Variables

**Date:** 2025-11-13
**Session ID:** spec-kitty-testing-001
**Tested by:** Functional test `test_agent_specific_formats`
**Category:** Bug Report, Template Rendering
**Spec-Kitty Version:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6
**Analysis Date:** 2025-11-13
**Applies To:** spec-kitty at commit ed3f461 template rendering for Gemini agent

## Summary
Gemini agent command files (TOML format) contain `$ARGUMENTS` variable syntax intended for Claude/Codex (Markdown format), instead of using Gemini's `{{args}}` syntax.

## Observation
When running `spec-kitty init` with both `--ai=claude,gemini`, the generated Gemini TOML files contain `$ARGUMENTS` which is the wrong variable syntax for Gemini. Gemini expects `{{args}}` syntax.

Test failure:
```
AssertionError: Gemini should not use Claude's $ARGUMENTS
assert '$ARGUMENTS' not in gemini_content
```

## Impact
- **Severity:** Medium
- **Scope:** Affects Gemini agent users
- **Frequency:** Happens always when Gemini agent is selected

## Root Cause Analysis
The template rendering system may not be properly converting variable syntax when transforming Markdown templates to TOML format for Gemini. The format conversion (MD→TOML) is happening, but variable syntax substitution is incomplete.

Expected behavior:
- Claude/Codex: Markdown files with `$ARGUMENTS`
- Gemini: TOML files with `{{args}}`

Actual behavior:
- Claude/Codex: Markdown files with `$ARGUMENTS` ✓
- Gemini: TOML files with `$ARGUMENTS` ✗ (should be `{{args}}`)

## User/Agent Journey
1. User runs: `spec-kitty init project --ai=claude,gemini`
2. System creates `.claude/commands/*.md` with `$ARGUMENTS` (correct)
3. System creates `.gemini/commands/*.toml` with `$ARGUMENTS` (incorrect)
4. Gemini agent reads TOML file expecting `{{args}}`
5. Gemini agent is confused by `$ARGUMENTS` syntax

## What Could Have Helped
1. **Variable syntax mapping** in template renderer for format conversion
2. **Validation test** that checks agent-specific syntax per format
3. **Template rendering tests** that verify format-specific variable syntax

## Suggested Improvements
In `src/specify_cli/template/renderer.py` or `asset_generator.py`:
- When converting MD→TOML for Gemini, also convert variable syntax:
  - `$ARGUMENTS` → `{{args}}`
  - `$AGENT_SCRIPT` → appropriate Gemini equivalent
- Add validation step that checks variable syntax matches target format
- Document the variable syntax per agent in templates/AGENTS.md

## Related Files
- `src/specify_cli/template/renderer.py` - Template rendering
- `src/specify_cli/template/asset_generator.py` - Per-agent asset generation
- `templates/commands/*.md` - Source templates with variables
- `.gemini/commands/*.toml` - Generated Gemini commands (incorrect syntax)

## Example Output/Reproduction
```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate
export SPEC_KITTY_TEMPLATE_ROOT=/Users/robert/Code/spec-kitty

# Run init with Gemini
spec-kitty init test_gemini --ai=gemini --ignore-agent-tools <<< "y"

# Check generated file
cat test_gemini/.gemini/commands/spec-kitty.specify.toml | grep -i arguments
# Shows: $ARGUMENTS (wrong - should be {{args}})
```

## Test Case
```python
# From tests/functional/test_init_template_discovery.py::test_agent_specific_formats
gemini_content = gemini_specify.read_text()
assert '{{args}}' in gemini_content, "Gemini should use {{args}}"
assert '$ARGUMENTS' not in gemini_content, "Gemini should not use Claude's $ARGUMENTS"
```

---
**Notes:** This was discovered through automated testing. The template format conversion works (MD→TOML) but variable syntax conversion is incomplete. This affects Gemini agent's ability to correctly parse and use the commands.

**Status**: Reported via functional test on 2025-11-13
