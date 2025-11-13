# Findings Report: Template Discovery During Init

**Date:** 2025-11-13
**Session ID:** spec-kitty-init-001
**Tested by:** Claude Code (via Robert)
**Category:** UX Improvement, Documentation, Onboarding
**Spec-Kitty Version:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6
**Analysis Date:** 2025-11-13
**Applies To:** spec-kitty at commit ed3f461 and potentially earlier versions with similar template discovery behavior

## Summary
The `spec-kitty init` command fails with an unclear error when templates cannot be found, requiring users to understand environment variables and package structure to debug the issue.

## Observation
Attempted to run `spec-kitty init . --ai=claude,codex` in a clean test directory after installing spec-kitty via `pip install -e ../spec-kitty`. The command failed with:

```
Initialization failed: Command templates directory not found at
/Users/robert/Code/spec-kitty-test/test_init/.kittify/templates/commands
```

The error message is confusing because:
1. It references a path that doesn't exist yet (target init path)
2. It doesn't explain WHY the templates weren't found
3. It doesn't suggest solutions (environment variables, local checkout, etc.)
4. It doesn't indicate that there are fallback mechanisms for template discovery

## Impact
- **Severity:** High (blocks initialization completely)
- **Scope:** First-time users, developers working with editable installs, anyone not using packaged templates
- **Frequency:** Happens reliably when templates are not discoverable through default mechanisms

## Root Cause Analysis
The spec-kitty CLI has a three-tier template discovery system (as documented in the code):
1. **Local repository checkout** - if `SPEC_KITTY_TEMPLATE_ROOT` env var is set
2. **Packaged templates** - from `importlib.resources` (bundled with wheel)
3. **Remote GitHub repo** - if `SPECIFY_TEMPLATE_REPO` env var is set

When installed via `pip install -e ../spec-kitty` in development mode, the templates are found via importlib.resources during wheel building. However, if there's any issue with the resource discovery or if running from a location where the templates aren't discoverable, the system fails hard with minimal guidance.

## User/Agent Journey
1. Installed spec-kitty via editable install: `pip install -e ../spec-kitty`
2. Attempted initialization: `spec-kitty init . --ai=claude,codex`
3. Received cryptic error about missing templates directory
4. Had to investigate the source code to understand:
   - That there's an environment variable `SPEC_KITTY_TEMPLATE_ROOT`
   - That templates are discovered in a specific order
   - That the error message was misleading about *where* the search failed
5. Successfully ran: `SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty spec-kitty init test_init --ai=claude,codex`

## What Could Have Helped
1. **Better error messages** - The error should say something like:
   ```
   Templates could not be found in:
   - Packaged resources (bundled with CLI)
   - Environment variable SPEC_KITTY_TEMPLATE_ROOT (not set)
   - Remote repository (disabled or unavailable)

   To fix this, either:
   - Reinstall spec-kitty from a built package: pip install spec-kitty-cli
   - Set SPEC_KITTY_TEMPLATE_ROOT=/path/to/spec-kitty/repo
   - Set SPECIFY_TEMPLATE_REPO=owner/repo and ensure network access
   ```

2. **Clearer documentation** - README or help text should explain:
   - The template discovery mechanism
   - How to use spec-kitty in development/editable mode
   - What environment variables are available
   - Common issues and how to resolve them

3. **Fallback guidance** - When init fails, suggest the next steps

4. **Help command** - `spec-kitty init --help` could mention template environment variables

## Suggested Improvements
1. **Enhanced error messaging** in `src/specify_cli/cli/commands/init.py`:
   - Catch template discovery failures earlier
   - Provide detailed debugging information showing which paths were checked
   - Suggest concrete remediation steps

2. **Documentation additions**:
   - Add a "Development Setup" section to README
   - Create a troubleshooting guide for common init failures
   - Document all available environment variables (SPEC_KITTY_TEMPLATE_ROOT, SPECIFY_TEMPLATE_REPO, etc.)

3. **CLI improvements**:
   - Add `--template-root` flag to override template location without env vars
   - Add `spec-kitty doctor` command to diagnose setup issues
   - Show discovered paths in verbose mode (`-v` or `--verbose`)

4. **User guidance**:
   - Modify help text: `spec-kitty init --help` should mention template locations
   - Add a "Quick Start" section that works for both packaged and development installs

## Related Files
- `src/specify_cli/cli/commands/init.py` - Init command implementation
- `src/specify_cli/template/manager.py` - Template discovery logic
- `src/specify_cli/template/renderer.py` - Template rendering
- `pyproject.toml` - Package configuration and template bundling
- `README.md` - Documentation

## Example Output/Reproduction
```bash
# This fails with unclear error:
pip install -e ../spec-kitty
spec-kitty init test_project --ai=claude,codex

# This works but requires special knowledge:
SPEC_KITTY_TEMPLATE_ROOT=../spec-kitty spec-kitty init test_project --ai=claude,codex
```

---
**Notes:**
This is a classic case where the tool works fine once you understand its architecture, but doesn't help new users (human or LLM) understand that architecture when things go wrong. The three-tier discovery system is actually elegant and flexible, but its existence and mechanics are invisible to users until they hit an edge case. Better communication about this flexibility would make the tool much more approachable.

The user had to read source code to understand the issue—the CLI should be self-documenting enough to guide users to the solution without code inspection.
