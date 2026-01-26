# Non-Interactive Mode Test Implementation

## Summary

I've implemented a comprehensive test suite (15 tests) to validate the non-interactive functionality for `spec-kitty init`. These tests use a **Test-Driven Development (TDD)** approach, documenting the desired behavior before implementation.

## Files Created

1. **`tests/functional/test_init_non_interactive.py`** (15 tests, ~450 lines)
   - Complete test suite covering all non-interactive scenarios
   - Currently most tests will fail (expected) - they document desired behavior
   - 1 test explicitly skipped to document current limitation

2. **`tests/functional/test_init_non_interactive_README.md`** (comprehensive docs)
   - Gap analysis summary
   - Implementation plan with code examples
   - Usage examples
   - Validation checklist

## Test Coverage (15 tests)

### ✅ Complete Non-Interactive Operation (3 tests)
- `test_init_with_all_flags_no_interaction` - All flags provided, no prompts
- `test_init_with_random_strategy_no_preferred_flags` - Random strategy doesn't need preferred flags
- `test_init_single_agent_auto_selects_for_both_roles` - Single agent auto-assignment

### ❌ Missing Flags Error Handling (3 tests)
- `test_init_noninteractive_without_agent_strategy_fails` - Clear error when strategy missing
- `test_init_noninteractive_preferred_without_implementer_fails` - Error when implementer missing
- `test_init_noninteractive_preferred_without_reviewer_fails` - Error when reviewer missing

### 📁 --here Flag Behavior (3 tests)
- `test_here_with_empty_dir_no_force_needed` - Empty dir works without --force
- `test_here_with_nonempty_dir_requires_force_in_noninteractive` - Non-empty requires --force
- `test_here_with_nonempty_dir_succeeds_with_force` - --force bypasses confirmation

### 🔧 Environment Variable Override (2 tests)
- `test_env_var_enables_noninteractive_mode` - SPEC_KITTY_NON_INTERACTIVE=1 works
- `test_env_var_with_missing_flags_fails_appropriately` - Env var + missing flags = clear error

### ⚠️ Validation (2 tests)
- `test_preferred_implementer_not_in_selected_agents_fails` - Implementer must be valid
- `test_preferred_reviewer_not_in_selected_agents_fails` - Reviewer must be valid

### ⏮️ Backwards Compatibility (1 test)
- `test_init_without_noninteractive_flag_still_prompts` - Interactive mode preserved

### 📋 Current Limitations (1 test, SKIPPED)
- `test_current_implementation_requires_stdin_for_strategy` - Documents current gap

## New Flags Required (Not Yet Implemented)

These are the flags the tests expect:

```bash
spec-kitty init myproject \
    --ai=claude,codex \
    --agent-strategy=preferred \        # NEW FLAG
    --preferred-implementer=claude \    # NEW FLAG
    --preferred-reviewer=codex \        # NEW FLAG
    --non-interactive                   # NEW FLAG
```

Or with environment variable:
```bash
export SPEC_KITTY_NON_INTERACTIVE=1    # NEW ENV VAR
spec-kitty init myproject --ai=claude --agent-strategy=preferred ...
```

## Current Status

### What Works Now
- `--ai` flag for agent selection
- `--force` flag for bypassing --here confirmation
- Interactive mode with stdin input

### What's Missing (Why Tests Fail)
1. ❌ No `--non-interactive` flag
2. ❌ No `--agent-strategy` flag (always prompts)
3. ❌ No `--preferred-implementer` flag (always prompts when strategy=preferred)
4. ❌ No `--preferred-reviewer` flag (always prompts when strategy=preferred)
5. ❌ No `SPEC_KITTY_NON_INTERACTIVE` env var
6. ❌ UI helpers don't check for non-interactive mode (would hang in CI)

### Critical Gap
**Lines 347-351 in `init.py`** always call `select_with_arrows()` for strategy selection, even when `--ai` is provided. This blocks non-interactive use entirely.

```python
# Current code ALWAYS prompts (blocking issue)
selected_strategy = select_with_arrows(
    strategy_choices,
    "How should agents be selected for tasks?",
    default_key="preferred",
)
```

## Running the Tests

### Run all non-interactive tests
```bash
pytest tests/functional/test_init_non_interactive.py -v
```

### Expected Results

**Now (before implementation)**:
- Most tests will **FAIL** (expected - features don't exist)
- 1 test **SKIPPED** (explicitly documenting current limitation)

**After implementation**:
- All tests should **PASS**
- Remove `@pytest.mark.skip` from `TestCurrentLimitations`

## Implementation Priority

Based on the gap analysis, implement in this order:

1. **Phase 1: Basic Non-Interactive Support**
   - Add `--non-interactive` flag
   - Add `SPEC_KITTY_NON_INTERACTIVE` env var
   - Guard UI helpers to fail-fast in non-interactive mode

2. **Phase 2: Strategy and Preference Flags**
   - Add `--agent-strategy` flag
   - Add `--preferred-implementer` flag
   - Add `--preferred-reviewer` flag
   - Add conditional logic (if non_interactive, require flags, else prompt)

3. **Phase 3: Auto-Select Defaults**
   - Single agent case: auto-select for both roles
   - Validation: ensure preferred agents are in selected list

4. **Phase 4: Documentation**
   - Update CLI help with non-interactive examples
   - Add CI/automation examples to README

## Validation

Before considering implementation complete, all 15 tests should pass:

```bash
pytest tests/functional/test_init_non_interactive.py -v
# Expected: 15 passed
```

## Key Design Decisions Needed

1. **Fail-fast vs Auto-select for multi-agent preferred strategy**
   - Option A: Require explicit `--preferred-implementer/reviewer` (recommended for CI)
   - Option B: Auto-select first agent as implementer, second as reviewer

   **Recommendation**: Option A (fail-fast) for deterministic tests

2. **Error message format**
   ```
   Error: --agent-strategy required in non-interactive mode.
   Choose from: preferred, random

   Use --agent-strategy=preferred or set SPEC_KITTY_NON_INTERACTIVE=0
   ```

3. **Backwards compatibility**
   - Keep all interactive prompts when `--non-interactive` not set
   - Tests verify this in `TestBackwardsCompatibility`

## Benefits of This Test Suite

1. **Documents desired API** - Tests show exactly how flags should work
2. **Prevents regressions** - Once implemented, tests ensure functionality preserved
3. **Guides implementation** - Test names and assertions provide implementation roadmap
4. **CI-ready** - All tests use `stdin=subprocess.DEVNULL` to simulate CI environment
5. **Comprehensive coverage** - 15 tests cover happy paths, error cases, edge cases
6. **Backwards compatible** - Explicitly tests that interactive mode still works

## Next Steps

1. Review test suite and README
2. Confirm design decisions (fail-fast policy, error messages)
3. Implement features in spec-kitty repo following the plan
4. Run tests to verify implementation
5. Remove `@pytest.mark.skip` from `TestCurrentLimitations` as features complete
6. Update docs with non-interactive examples

## Related Files

- **Test suite**: `tests/functional/test_init_non_interactive.py`
- **Documentation**: `tests/functional/test_init_non_interactive_README.md`
- **Summary**: This file
- **Implementation target**: `../spec-kitty/src/specify_cli/cli/commands/init.py`
- **UI helpers**: `../spec-kitty/src/specify_cli/cli/ui.py`
