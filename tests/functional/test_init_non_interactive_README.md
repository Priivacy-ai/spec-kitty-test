# Non-Interactive Mode Tests for `spec-kitty init`

## Overview

This test suite validates the non-interactive operation of `spec-kitty init` for CI/automation environments. The tests document both the **desired behavior** (when features are implemented) and the **current limitations**.

## Gap Analysis Summary

### Current Interactive Points

The following aspects of `spec-kitty init` currently require user interaction:

1. **AI Selection** (if `--ai` not provided)
   - Location: `src/specify_cli/cli/commands/init.py:298-302`
   - Uses: `multi_select_with_arrows()`
   - Requires: `readchar.readkey()` for arrow navigation

2. **Agent Selection Strategy** ⚠️ ALWAYS PROMPTS
   - Location: `src/specify_cli/cli/commands/init.py:347-351`
   - Uses: `select_with_arrows()`
   - **Currently blocks non-interactive use even when `--ai` is provided**

3. **Preferred Implementer** (when strategy = "preferred")
   - Location: `src/specify_cli/cli/commands/init.py:361-365`
   - Uses: `select_with_arrows()`
   - Required for orchestrator agent selection

4. **Preferred Reviewer** (when strategy = "preferred")
   - Location: `src/specify_cli/cli/commands/init.py:372-376`
   - Uses: `select_with_arrows()`
   - Required for orchestrator review assignment

5. **Directory Confirmation** (when using `--here` with non-empty directory)
   - Location: `src/specify_cli/cli/commands/init.py:223`
   - Uses: `typer.confirm()`
   - Bypassed with `--force` flag

### Missing Features for Full Non-Interactive Operation

1. **No `--non-interactive` / `--yes` mode**
   - No global switch to force automatic resolution of all prompts
   - No fail-fast mode when interaction would be required

2. **No CLI args for selection strategy**
   - Missing: `--agent-strategy` with choices `preferred|random`

3. **No CLI args for preferred agents**
   - Missing: `--preferred-implementer <agent>`
   - Missing: `--preferred-reviewer <agent>`

4. **No environment-based override**
   - Missing: `SPEC_KITTY_NON_INTERACTIVE=1` env var

5. **No default policy for single-agent case**
   - When only one agent selected with `strategy=preferred`, should auto-assign
   - Currently still prompts even when choice is obvious

6. **No UI helper guards**
   - `select_with_arrows()` and `multi_select_with_arrows()` don't check for non-interactive mode
   - Would call `readchar.readkey()` in CI, causing hangs or errors

7. **No documentation**
   - CLI help doesn't document non-interactive usage
   - README lacks automation/CI examples

8. **No test coverage**
   - No tests ensuring non-interactive operation works
   - No tests ensuring clear errors when flags missing

## Test Coverage

### Test Classes

#### `TestNonInteractiveFlagsComplete`
Tests that init works without prompts when all required flags provided:
- ✅ Complete flag set enables non-interactive operation
- ✅ Random strategy doesn't require preferred flags
- ✅ Single agent auto-selects for both roles

#### `TestNonInteractiveMissingFlags`
Tests clear error messages when required flags missing:
- ✅ Missing `--agent-strategy` fails with helpful message
- ✅ Missing `--preferred-implementer` fails when strategy=preferred
- ✅ Missing `--preferred-reviewer` fails when strategy=preferred

#### `TestNonInteractiveHereFlag`
Tests `--here` flag behavior in non-interactive mode:
- ✅ Empty directory works without `--force`
- ✅ Non-empty directory requires `--force`
- ✅ `--force` bypasses confirmation in non-interactive mode

#### `TestEnvironmentVariableOverride`
Tests environment variable alternative to flag:
- ✅ `SPEC_KITTY_NON_INTERACTIVE=1` enables non-interactive mode
- ✅ Env var with missing flags still fails appropriately

#### `TestInvalidAgentPreferences`
Tests validation of agent preferences:
- ✅ Preferred implementer must be in selected agents
- ✅ Preferred reviewer must be in selected agents

#### `TestBackwardsCompatibility`
Ensures existing interactive behavior preserved:
- ✅ Without `--non-interactive`, prompts still work with stdin

#### `TestCurrentLimitations` (SKIPPED)
Documents current limitations preventing non-interactive use:
- ⚠️ Strategy selection always prompts even with `--ai`
- These tests are skipped until features implemented

## Implementation Plan

### Phase 1: Core Non-Interactive Support

1. **Add `--non-interactive` flag**
   ```python
   non_interactive: bool = typer.Option(
       False,
       "--non-interactive",
       "--yes",
       "--no-prompt",
       help="Run without interactive prompts (fail if required args missing)"
   )
   ```

2. **Add environment variable support**
   ```python
   non_interactive = non_interactive or os.getenv('SPEC_KITTY_NON_INTERACTIVE') == '1'
   ```

3. **Guard UI helpers**
   ```python
   def select_with_arrows(...):
       if os.getenv('SPEC_KITTY_NON_INTERACTIVE') == '1':
           raise RuntimeError(
               "Interactive selection required but running in non-interactive mode"
           )
       # existing code
   ```

### Phase 2: Strategy and Preference Flags

1. **Add `--agent-strategy` flag**
   ```python
   agent_strategy: str = typer.Option(
       None,
       "--agent-strategy",
       help="Agent selection strategy: preferred or random"
   )
   ```

2. **Add preferred agent flags**
   ```python
   preferred_implementer: str = typer.Option(
       None,
       "--preferred-implementer",
       help="Preferred agent for implementation (must be in --ai list)"
   )
   preferred_reviewer: str = typer.Option(
       None,
       "--preferred-reviewer",
       help="Preferred agent for review (must be in --ai list)"
   )
   ```

3. **Conditional logic**
   ```python
   if non_interactive:
       if not agent_strategy:
           console.print("[red]Error:[/red] --agent-strategy required in non-interactive mode")
           raise typer.Exit(1)

       if agent_strategy == "preferred":
           if not preferred_implementer:
               console.print("[red]Error:[/red] --preferred-implementer required")
               raise typer.Exit(1)
           # ... similar for reviewer
   else:
       # existing interactive flow
   ```

### Phase 3: Auto-Select Defaults

1. **Single agent case**
   ```python
   if non_interactive and agent_strategy == "preferred":
       if len(selected_agents) == 1:
           # Auto-select the only agent for both roles
           preferred_implementer = preferred_implementer or selected_agents[0]
           preferred_reviewer = preferred_reviewer or selected_agents[0]
   ```

2. **Multi-agent defaults** (choose one policy):
   - **Option A (fail-fast)**: Require explicit flags, fail if missing
   - **Option B (auto-select)**: Use first agent as implementer, second as reviewer
   - **Recommendation**: Option A (fail-fast) for deterministic tests

### Phase 4: Documentation and Help

1. **Update CLI help**
   ```python
   INIT_COMMAND_DOC = """
   Initialize a new Spec Kitty project.

   ## Non-Interactive Mode (for CI/automation):

       spec-kitty init myproject \\
           --ai=claude,codex \\
           --agent-strategy=preferred \\
           --preferred-implementer=claude \\
           --preferred-reviewer=codex \\
           --non-interactive

   Or use environment variable:
       export SPEC_KITTY_NON_INTERACTIVE=1
   """
   ```

2. **Update README** with CI examples

## Running the Tests

### Run all non-interactive tests
```bash
pytest tests/functional/test_init_non_interactive.py -v
```

### Run specific test class
```bash
pytest tests/functional/test_init_non_interactive.py::TestNonInteractiveFlagsComplete -v
```

### Run without skipped tests
```bash
pytest tests/functional/test_init_non_interactive.py -v -k "not CurrentLimitations"
```

### Expected Results

**Before Implementation**: Most tests will FAIL or be SKIPPED
- Tests in `TestCurrentLimitations` are explicitly skipped
- Other tests expect features that don't exist yet
- Tests document the desired behavior

**After Implementation**: All tests should PASS
- Remove `@pytest.mark.skip` from `TestCurrentLimitations`
- All non-interactive scenarios work
- Clear errors when flags missing
- Backwards compatibility preserved

## Example Usage (Once Implemented)

### Minimal non-interactive (single agent)
```bash
spec-kitty init myproject \
    --ai=claude \
    --agent-strategy=preferred \
    --preferred-implementer=claude \
    --preferred-reviewer=claude \
    --non-interactive
```

### Multi-agent with random strategy
```bash
spec-kitty init myproject \
    --ai=claude,codex,gemini \
    --agent-strategy=random \
    --non-interactive
```

### Initialize in current directory
```bash
spec-kitty init --here \
    --ai=claude \
    --agent-strategy=preferred \
    --preferred-implementer=claude \
    --preferred-reviewer=claude \
    --force \
    --non-interactive
```

### Using environment variable
```bash
export SPEC_KITTY_NON_INTERACTIVE=1
spec-kitty init myproject \
    --ai=claude \
    --agent-strategy=preferred \
    --preferred-implementer=claude \
    --preferred-reviewer=claude
```

## Validation Checklist

Before marking implementation complete, verify:

- [ ] All tests in `test_init_non_interactive.py` pass
- [ ] `--non-interactive` flag works
- [ ] `SPEC_KITTY_NON_INTERACTIVE=1` env var works
- [ ] `--agent-strategy` flag works (preferred/random)
- [ ] `--preferred-implementer` flag works
- [ ] `--preferred-reviewer` flag works
- [ ] Single agent auto-selects for both roles
- [ ] Missing flags fail with clear error messages
- [ ] `--force` works with `--here` in non-interactive mode
- [ ] Invalid agent preferences are rejected
- [ ] Interactive mode still works (backwards compatibility)
- [ ] CLI help documents non-interactive mode
- [ ] README has CI/automation examples
- [ ] No `readchar.readkey()` called in non-interactive mode
- [ ] Tests run in CI without stdin available

## Related Files

- Test suite: `tests/functional/test_init_non_interactive.py`
- Implementation: `../spec-kitty/src/specify_cli/cli/commands/init.py`
- UI helpers: `../spec-kitty/src/specify_cli/cli/ui.py`
- Agent config: `../spec-kitty/src/specify_cli/orchestrator/agent_config.py`

## Notes

- These tests use **test-driven development (TDD)** approach
- Tests are written BEFORE implementation
- Tests document the desired behavior and API
- Most tests currently fail/skip - this is expected
- Remove `@pytest.mark.skip` as features are implemented
- Keep backwards compatibility - interactive mode must still work
