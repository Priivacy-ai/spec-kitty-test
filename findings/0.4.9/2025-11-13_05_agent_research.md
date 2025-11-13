# Agent Research: Complete Agent Support Matrix

**Date:** 2025-11-13
**Session ID:** spec-kitty-agent-research-001
**Tested by:** Claude Code (research)
**Category:** Testing, Agent Compatibility, Documentation
**Spec-Kitty Version:** b2285ba427e3a39ee6397850899bf52452728d03
**Analysis Date:** 2025-11-13

## Summary

Research of all 12 agents supported by spec-kitty to create evidence-based tests that validate each agent's directory structure, file format, and variable syntax.

## Agent Support Matrix

From `src/specify_cli/core/config.py`:

| Agent | Full Name | Directory | Extension | Variable Format | Tool CLI | Documentation |
|-------|-----------|-----------|-----------|-----------------|----------|---------------|
| claude | Claude Code | `.claude/commands` | `.md` | `$ARGUMENTS` | `claude` | https://docs.anthropic.com/en/docs/claude-code/setup |
| copilot | GitHub Copilot | `.github/prompts` | `.prompt.md` | `$ARGUMENTS` | N/A | Built into GitHub/VS Code |
| gemini | Gemini CLI | `.gemini/commands` | `.toml` | `{{args}}` | `gemini` | https://github.com/google-gemini/gemini-cli |
| cursor | Cursor | `.cursor/commands` | `.md` | `$ARGUMENTS` | N/A | IDE-based |
| qwen | Qwen Code | `.qwen/commands` | `.toml` | `{{args}}` | `qwen` | https://github.com/QwenLM/qwen-code |
| opencode | opencode | `.opencode/command` | `.md` | `$ARGUMENTS` | `opencode` | https://opencode.ai |
| codex | Codex CLI | `.codex/prompts` | `.md` | `$ARGUMENTS` | `codex` | https://github.com/openai/codex |
| windsurf | Windsurf | `.windsurf/workflows` | `.md` | `$ARGUMENTS` | N/A | IDE-based |
| kilocode | Kilo Code | `.kilocode/workflows` | `.md` | `$ARGUMENTS` | N/A | IDE-based |
| auggie | Auggie CLI | `.augment/commands` | `.md` | `$ARGUMENTS` | `auggie` | https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli |
| roo | Roo Code | `.roo/commands` | `.md` | `$ARGUMENTS` | N/A | IDE-based |
| q | Amazon Q Developer CLI | `.amazonq/prompts` | `.md` | `$ARGUMENTS` | `q` | https://aws.amazon.com/developer/learning/q-developer-cli/ |

## Key Patterns Identified

### Pattern 1: Markdown Agents (9 agents)
**Format**: `.md` files with `$ARGUMENTS` variable syntax
- claude, copilot, cursor, opencode, codex, windsurf, kilocode, auggie, roo, q

### Pattern 2: TOML Agents (2 agents)
**Format**: `.toml` files with `{{args}}` variable syntax
- gemini, qwen

### Pattern 3: Special Format (1 agent)
**Format**: `.prompt.md` (Copilot-specific)
- copilot (GitHub Copilot uses special metadata format)

## Directory Naming Patterns

### Pattern A: `commands/` subdirectory (7 agents)
- `.claude/commands`
- `.gemini/commands`
- `.cursor/commands`
- `.qwen/commands`
- `.augment/commands`
- `.roo/commands`

### Pattern B: `prompts/` subdirectory (3 agents)
- `.github/prompts` (copilot)
- `.codex/prompts`
- `.amazonq/prompts`

### Pattern C: `workflows/` subdirectory (2 agents)
- `.windsurf/workflows`
- `.kilocode/workflows`

### Pattern D: `command/` singular (1 agent)
- `.opencode/command` (NOTE: singular, not plural!)

## Agent Availability for Testing

### CLI-Based Agents (Can be tested via npx/install)
1. ✅ **claude** - Available (we're using it!)
2. ⚠️ **gemini** - Available via npm: `npm install -g @google/gemini-cli`
3. ⚠️ **qwen** - Available via pip: `pip install qwen-code`
4. ⚠️ **codex** - OpenAI Codex (deprecated/limited access)
5. ⚠️ **auggie** - Available: https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli
6. ⚠️ **q** - Amazon Q CLI available via AWS CLI

### IDE-Based Agents (Cannot test CLI directly)
1. **copilot** - GitHub Copilot (VS Code/JetBrains integration)
2. **cursor** - Cursor IDE
3. **opencode** - opencode.ai platform
4. **windsurf** - Windsurf IDE
5. **kilocode** - Kilo Code IDE
6. **roo** - Roo Code IDE

## Testing Strategy

### Level 1: Directory Structure Tests (All 12 agents)
Test that `spec-kitty init --ai=<agent>` creates:
- Correct directory path
- Correct subdirectory name (`commands/`, `prompts/`, `workflows/`, `command/`)
- 13 command files with correct extension

### Level 2: File Format Tests (All 12 agents)
Test that generated files:
- Have correct file extension (`.md`, `.toml`, `.prompt.md`)
- Use correct variable syntax (`$ARGUMENTS` vs `{{args}}`)
- Are valid format (parseable Markdown or TOML)

### Level 3: Variable Syntax Tests (2 groups)
**Group A: Markdown with $ARGUMENTS** (9 agents)
- Verify `$ARGUMENTS` present in commands
- Verify NO `{{args}}` present
- Verify valid Markdown structure

**Group B: TOML with {{args}}** (2 agents)
- Verify `{{args}}` present in commands
- Verify NO `$ARGUMENTS` present
- Verify valid TOML structure

**Group C: Special Formats** (1 agent)
- copilot: Verify `.prompt.md` format with metadata

### Level 4: Integration Tests (CLI-based agents only)
For agents with available CLIs:
- Test if actual CLI can read generated files
- Test if file format matches CLI expectations
- Document any incompatibilities

## Proposed Test Matrix

```python
AGENT_TEST_MATRIX = {
    "claude": {
        "dir": ".claude/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": True,
        "test_cli": False,  # Already testing with this
    },
    "copilot": {
        "dir": ".github/prompts",
        "ext": "prompt.md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,
        "has_vscode_settings": True,  # Creates .vscode/settings.json
    },
    "gemini": {
        "dir": ".gemini/commands",
        "ext": "toml",
        "var_format": "{{args}}",
        "file_count": 13,
        "cli_available": True,
        "test_cli": True,
    },
    "cursor": {
        "dir": ".cursor/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,
    },
    "qwen": {
        "dir": ".qwen/commands",
        "ext": "toml",
        "var_format": "{{args}}",
        "file_count": 13,
        "cli_available": True,
        "test_cli": True,
    },
    "opencode": {
        "dir": ".opencode/command",  # NOTE: Singular!
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": True,
        "test_cli": False,  # Platform-based
    },
    "codex": {
        "dir": ".codex/prompts",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,  # Deprecated
    },
    "windsurf": {
        "dir": ".windsurf/workflows",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,
    },
    "kilocode": {
        "dir": ".kilocode/workflows",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,
    },
    "auggie": {
        "dir": ".augment/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": True,
        "test_cli": False,  # Requires auth
    },
    "roo": {
        "dir": ".roo/commands",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": False,
    },
    "q": {
        "dir": ".amazonq/prompts",
        "ext": "md",
        "var_format": "$ARGUMENTS",
        "file_count": 13,
        "cli_available": True,
        "test_cli": False,  # Requires AWS auth
    },
}
```

## Evidence-Based Test Approach

### Phase 1: Structure Validation (Can test all 12)
For each agent, run `spec-kitty init --ai=<agent>` and verify:
1. Directory created at correct path
2. Subdirectory has correct name
3. Exactly 13 files created
4. All files have correct extension
5. All files are non-empty and valid format

### Phase 2: Format Validation (Can test all 12)
For each agent, check one sample file:
1. Parse as Markdown or TOML (depending on extension)
2. Verify variable syntax matches expectation
3. Verify no cross-contamination (e.g., TOML variables in Markdown files)

### Phase 3: CLI Integration (Can test 2-3 agents)
For agents with available CLIs:
- **gemini**: Install and verify it can read the TOML files
- **qwen**: Install and verify it can read the TOML files

## Special Cases to Test

### 1. opencode directory anomaly
- Uses `.opencode/command` (singular) instead of `commands/` (plural)
- Must verify this singular form is intentional

### 2. copilot VS Code integration
- Creates `.vscode/settings.json` in addition to prompts
- Must verify this file is created and configured correctly

### 3. TOML format agents
- Only gemini and qwen use TOML
- Must verify format conversion works for both

## Recommended Next Steps

1. **Create comprehensive agent test** covering all 12 agents:
   - Structure validation (directory, extension, count)
   - Format validation (variable syntax, parseability)
   - Cross-contamination prevention

2. **Test with actual CLIs** (if available):
   - Install gemini CLI and validate TOML files
   - Document any incompatibilities

3. **Document findings**:
   - Any agents with special requirements
   - Any format inconsistencies found

---

**Status**: Research complete, ready for evidence-based testing
**Next**: Implement comprehensive agent validation test
