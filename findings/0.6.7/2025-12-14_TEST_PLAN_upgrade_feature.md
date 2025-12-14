# Test Plan: spec-kitty Upgrade Feature

**Date:** 2025-12-14
**Version:** 0.7.0
**Feature:** `spec-kitty upgrade` command system
**Status:** 📋 Planning Complete
**Estimated Tests:** 97 tests across 11 test files

---

## Executive Summary

This document outlines the comprehensive testing strategy for the new `spec-kitty upgrade` command that will migrate projects from any historical version (v0.1.x+) to the current version. The upgrade system includes version metadata tracking, migration registry, and automatic worktree upgrades.

### Key Features Being Tested

1. **Version Detection** - Heuristic-based detection when metadata missing
2. **Migration Registry** - Ordered execution of breaking-change migrations
3. **Metadata Tracking** - `.kittify/metadata.yaml` for version history
4. **Worktree Auto-Upgrade** - Automatic upgrade of all worktrees
5. **CLI Integration** - Full `spec-kitty upgrade` command with options

---

## Test Strategy

### Hybrid Testing Approach

**Static Fixtures:**
- Key historical versions (v0.1.x, v0.4.7, v0.6.4, v0.6.6) as committed directories
- Provides visual inspection and reproducibility
- Documents what each version looked like

**Programmatic Generation:**
- Edge cases (conflicts, partial states, corrupted metadata)
- Worktree scenarios
- More flexible for complex test setups

**Test Levels:**
- **Unit Tests** - Individual migration classes, metadata, detector, registry
- **Integration Tests** - Full CLI command with migrations
- **End-to-End Tests** - Complete upgrade paths with worktrees

---

## Historical Versions Under Test

| Version | Key Characteristics | Migration Needed | Test Priority |
|---------|---------------------|------------------|---------------|
| **v0.1.x** | Uses `.specify/`, `/specs/` | Directory rename | High |
| **v0.4.7** | Missing git protection | Add .gitignore + hooks | High |
| **v0.6.4** | Uses `commands/` not `command-templates/` | Rename commands dirs | **Critical** |
| **v0.6.6** | Current structure, no metadata | Add metadata only | Medium |

**Why v0.6.4 is Critical:** Users like `~/Code/agentfunc` are on this version experiencing doubled slash commands in Claude Code due to both `commands/` and `command-templates/` being discovered.

---

## Test File Structure

```
tests/test_upgrade/
├── conftest.py                             # Shared fixtures (8 fixtures)
├── fixtures/                               # Committed historical states
│   ├── v0_1_x_project/                     # .specify/ directory
│   ├── v0_4_7_project/                     # Missing git protection
│   ├── v0_6_4_project/                     # Old commands/ structure
│   ├── v0_6_6_project/                     # Current structure, no metadata
│   └── broken_mission_project/             # "Unknown mission" in dashboard
├── test_metadata.py                        # 8 tests
├── test_detector.py                        # 11 tests
├── test_migrations/
│   ├── test_base.py                        # 3 tests
│   ├── test_m_0_2_0_specify_to_kittify.py  # 6 tests
│   ├── test_m_0_4_8_gitignore_agents.py    # 5 tests
│   ├── test_m_0_5_0_encoding_hooks.py      # 5 tests
│   ├── test_m_0_6_5_commands_rename.py     # 8 tests
│   └── test_m_0_6_6_mission_repair.py      # 6 tests
├── test_registry.py                        # 6 tests
├── test_runner.py                          # 7 tests
├── test_integration_cli.py                 # 15 tests
├── test_worktree_upgrade.py                # 8 tests
└── test_edge_cases.py                      # 10 tests
```

**Total:** 97 tests

---

## Test Categories

### 1. Metadata Tests (8 tests)

**File:** `test_metadata.py`

#### TestMetadataIO (4 tests)
- `test_create_new_metadata()` - Create with version, timestamps, platform info
- `test_save_and_load_metadata()` - Round-trip `.kittify/metadata.yaml`
- `test_load_missing_metadata()` - Returns `None` when file doesn't exist
- `test_load_malformed_metadata()` - Handles corrupted YAML gracefully

#### TestMigrationTracking (4 tests)
- `test_has_migration()` - Check if specific migration applied
- `test_record_migration()` - Record successful migration
- `test_record_failed_migration()` - Track failed attempts
- `test_migration_chronology()` - Migrations recorded in order

**Dependencies:** YAML library, filesystem access

---

### 2. Version Detection Tests (11 tests)

**File:** `test_detector.py`

#### TestDetectionWithMetadata (2 tests)
- `test_detect_from_metadata_file()` - Read from `metadata.yaml`
- `test_metadata_takes_precedence()` - Metadata overrides heuristics

#### TestDetectionHeuristics (7 tests)
- `test_detect_v0_1_x_from_specify_dir()` - `.specify/` → v0.1.x
- `test_detect_v0_4_7_missing_gitignore()` - No agent dirs → v0.4.7
- `test_detect_v0_6_4_from_commands_dir()` - `.kittify/templates/commands/` → v0.6.4
- `test_detect_v0_6_5_from_command_templates()` - `command-templates/` → v0.6.5+
- `test_detect_broken_mission_system()` - Dashboard shows "Unknown mission" → needs mission repair
- `test_detect_unknown_version()` - Ambiguous state returns "unknown"
- `test_multiple_heuristics_agree()` - Consistent signals = confident

#### TestDetectionEdgeCases (2 tests)
- `test_detect_mixed_old_new_structure()` - Both `commands/` and `command-templates/`
- `test_detect_fresh_install()` - Current version with all features

**Key Heuristics Table:**

| File/Directory Exists | Detected Version |
|----------------------|------------------|
| `.specify/` | v0.1.x |
| `.kittify/templates/commands/` | v0.6.4 |
| `.kittify/*/command-templates/` | v0.6.5+ |
| `.gitignore` missing agent dirs | < v0.4.8 |
| No pre-commit hooks | < v0.5.0 |
| Dashboard shows "Unknown mission" | Broken mission system |
| `metadata.yaml` exists | Read from file |

---

### 3. Migration Unit Tests (33 tests)

#### test_m_0_2_0_specify_to_kittify.py (6 tests)

**Migration:** `.specify/` → `.kittify/`, `/specs/` → `/kitty-specs/`

**TestSpecifyToKittifyMigration:**
- `test_detect_old_specify_structure()` - Detects `.specify/` directory
- `test_rename_specify_to_kittify()` - Directory rename works
- `test_rename_specs_to_kitty_specs()` - Spec directory renamed
- `test_update_symlinks_if_exist()` - Fixes symlink targets post-rename
- `test_migration_idempotent()` - Safe to run twice
- `test_preserves_user_content()` - Constitution intact

#### test_m_0_4_8_gitignore_agents.py (5 tests)

**Migration:** Add all 12 agent directories to `.gitignore`

**TestGitignoreAgentsMigration:**
- `test_detect_missing_agent_dirs()` - Detects incomplete `.gitignore`
- `test_add_all_12_agent_directories()` - Adds agents + `.github/copilot/`
- `test_preserve_existing_gitignore()` - Appends, doesn't overwrite
- `test_handles_no_gitignore()` - Creates if missing
- `test_already_has_agents_skips()` - Idempotent

#### test_m_0_5_0_encoding_hooks.py (5 tests)

**Migration:** Install pre-commit hook for encoding validation

**TestEncodingHooksMigration:**
- `test_detect_missing_precommit_hook()` - Detects no hook
- `test_install_precommit_hook()` - Installs `pre-commit-agent-check`
- `test_hook_is_executable()` - Sets correct permissions (Unix)
- `test_preserves_existing_hooks()` - Doesn't overwrite others
- `test_updates_old_hook_version()` - Replaces outdated script

#### test_m_0_6_5_commands_rename.py (8 tests)

**Migration:** `commands/` → `command-templates/` (Most Critical)

**TestCommandsRenameMigration:**
- `test_detect_old_commands_directories()` - Finds `commands/` in missions
- `test_rename_mission_commands()` - Renames to `command-templates/`
- `test_handles_both_old_and_new()` - Merges if both exist (new wins)
- `test_preserves_custom_commands()` - User commands kept
- `test_updates_rendered_commands()` - Re-renders `.claude/commands/`
- `test_removes_template_pollution()` - Deletes `.kittify/templates/` in user projects
- `test_migration_handles_worktrees()` - Upgrades worktrees too
- `test_dry_run_preview()` - Shows changes without applying

**Why This is Critical:** Fixes the agentfunc doubled-commands issue where Claude Code discovers commands from both old and new locations.

#### test_m_0_6_6_mission_repair.py (6 tests)

**Migration:** Fix broken mission system that shows "Unknown mission"

**TestMissionRepairMigration:**
- `test_detect_broken_mission_system()` - Dashboard shows "Unknown mission"
- `test_repair_missing_mission_metadata()` - Recreate mission metadata files
- `test_repair_corrupted_mission_config()` - Fix malformed mission.yaml
- `test_detect_via_dashboard_query()` - Query dashboard API for mission status
- `test_preserves_working_missions()` - Doesn't touch functional missions
- `test_idempotent_repair()` - Safe to run multiple times

**Why This is Critical:** "Most people's mission system is broken" from buggy versions. Dashboard showing "Mission: Unknown mission" indicates corrupted/missing mission metadata that needs repair.

**Detection Method:**
1. Start dashboard server
2. Query mission status API
3. If returns "Unknown mission" → broken mission system
4. Inspect `.kittify/missions/` for missing metadata
5. Recreate/repair mission.yaml files

#### test_base.py (3 tests)

**TestBaseMigration:**
- `test_migration_has_required_fields()` - ID, description, target_version
- `test_detect_method_required()` - Abstract method enforced
- `test_apply_method_required()` - Abstract method enforced

---

### 4. Registry Tests (6 tests)

**File:** `test_registry.py`

**TestMigrationRegistry:**
- `test_register_migration()` - Decorator registers class
- `test_get_all_migrations()` - Returns all registered
- `test_get_applicable_migrations()` - Filters by version range
- `test_migration_ordering()` - Chronological order
- `test_duplicate_id_error()` - Raises on duplicate IDs
- `test_missing_target_version()` - Validates metadata

**Example:**
```python
@MigrationRegistry.register
class Migration_0_6_5_CommandsRename(BaseMigration):
    migration_id = "0.6.5_commands_rename"
    target_version = "0.6.5"
    ...
```

---

### 5. Runner Tests (7 tests)

**File:** `test_runner.py`

**TestMigrationRunner:**
- `test_plan_upgrade_path()` - Identifies needed migrations (v0.4.7 → v0.6.7)
- `test_run_single_migration()` - Executes one migration
- `test_run_migration_chain()` - Executes multiple in order
- `test_skip_already_applied()` - Doesn't re-run recorded migrations
- `test_stop_on_failure()` - Halts chain if one fails
- `test_rollback_on_error()` - Documents limitation (no rollback)
- `test_metadata_updated_after_each()` - Records each immediately

**Orchestration Logic:**
1. Detect current version
2. Get applicable migrations (current → target)
3. Filter out already-applied migrations
4. Execute in order, recording each
5. Stop on first failure

---

### 6. CLI Integration Tests (15 tests)

**File:** `test_integration_cli.py`

#### TestUpgradeCommandBasic (5 tests)
- `test_upgrade_no_changes_needed()` - Current version → no-op
- `test_upgrade_single_migration()` - v0.6.4 → v0.6.5
- `test_upgrade_full_path()` - v0.1.x → current (4 migrations)
- `test_upgrade_output_format()` - Shows migration plan table
- `test_upgrade_creates_metadata()` - Adds `metadata.yaml` if missing

#### TestUpgradeCommandOptions (5 tests)
- `test_dry_run_no_changes()` - `--dry-run` shows plan only
- `test_force_skips_confirmation()` - `--force` auto-confirms
- `test_target_version()` - `--target 0.6.5` stops early
- `test_json_output()` - `--json` machine-readable
- `test_verbose_logging()` - `-v` shows detailed progress

#### TestUpgradeCommandEdgeCases (5 tests)
- `test_upgrade_with_uncommitted_changes()` - Warning behavior
- `test_upgrade_not_git_repo()` - Clear error message
- `test_upgrade_not_kittify_project()` - Detects missing `.kittify/`
- `test_upgrade_corrupted_metadata()` - Falls back to heuristics
- `test_upgrade_from_worktree()` - Error: must run from main repo

**CLI Options:**
```bash
spec-kitty upgrade              # Basic upgrade
spec-kitty upgrade --dry-run    # Preview only
spec-kitty upgrade --force      # Skip confirmation
spec-kitty upgrade --target 0.6.5   # Upgrade to specific version
spec-kitty upgrade --json       # Machine-readable output
spec-kitty upgrade -v           # Verbose
spec-kitty upgrade --no-worktrees   # Skip worktree upgrades
```

---

### 7. Worktree Upgrade Tests (8 tests)

**File:** `test_worktree_upgrade.py`

**TestWorktreeAutoUpgrade:**
- `test_discovers_all_worktrees()` - Finds all in `.worktrees/`
- `test_upgrades_each_worktree()` - Independent upgrade for each
- `test_worktree_metadata_separate()` - Each has own metadata
- `test_skip_worktrees_flag()` - `--no-worktrees` only upgrades main
- `test_worktree_upgrade_failure_continues()` - One failure doesn't stop others
- `test_worktree_symlink_preserved()` - Constitution symlink maintained
- `test_new_worktree_after_upgrade()` - New worktrees get current version
- `test_upgrade_output_shows_worktrees()` - CLI lists each worktree

**Worktree Upgrade Logic:**
1. Scan `.worktrees/` directory
2. For each worktree:
   - Detect version
   - Apply needed migrations
   - Record in worktree's own metadata
3. Continue on failure (don't block others)
4. Report status for each

---

### 8. Edge Case Tests (10 tests)

**File:** `test_edge_cases.py`

#### TestConflicts (3 tests)
- `test_both_specify_and_kittify_exist()` - Error: manual cleanup
- `test_both_commands_and_templates_exist()` - Merges (templates wins)
- `test_gitignore_has_conflicting_patterns()` - Preserves customizations

#### TestPartialStates (3 tests)
- `test_partial_migration_recovery()` - Resumes from last successful
- `test_migration_interrupted_midway()` - Metadata shows incomplete
- `test_rerun_failed_migration()` - Retry after fixing

#### TestRealWorldScenarios (4 tests)
- `test_agentfunc_doubled_commands()` - Replicates & fixes agentfunc issue
- `test_fresh_install_upgrade_noop()` - Fresh v0.6.7 → no-op
- `test_ancient_project_no_git()` - Partial functionality without git
- `test_windows_symlink_fallback()` - Copy on Windows

**agentfunc Test:** Most important real-world validation. Replicates the exact structure causing doubled commands and verifies upgrade fixes it.

---

## Test Fixtures

### Static Fixtures (Committed to Git)

#### fixtures/v0_1_x_project/

```
v0_1_x_project/
├── .specify/                    # OLD directory name
│   ├── memory/
│   │   └── constitution.md
│   └── missions/
│       └── research/
│           └── prompts/
├── specs/                       # OLD spec directory
│   └── 001-example/
└── .git/
```

**Purpose:** Tests fundamental directory rename migration (`.specify/` → `.kittify/`)

#### fixtures/v0_4_7_project/

```
v0_4_7_project/
├── .kittify/
│   ├── memory/
│   └── missions/
│       └── software-dev/
│           └── commands/         # Old name, but .kittify exists
├── .gitignore                   # Missing agent directories
└── .git/
```

**Purpose:** Tests git protection additions (.gitignore + pre-commit hooks)

#### fixtures/v0_6_4_project/

```
v0_6_4_project/
├── .kittify/
│   ├── templates/               # Template pollution!
│   │   └── commands/
│   └── missions/
│       └── software-dev/
│           └── commands/        # Old name
├── .gitignore                   # Complete
├── .git/
│   └── hooks/
│       └── pre-commit-agent-check
└── .claude/
    └── commands/
        ├── spec-kitty.specify.md
        ├── spec-kitty.implement.md
        └── ... (26 total - DOUBLED!)
```

**Purpose:** Tests commands rename migration - **CRITICAL for agentfunc fix**

#### fixtures/v0_6_6_project/

```
v0_6_6_project/
├── .kittify/
│   ├── missions/
│   │   └── software-dev/
│   │       └── command-templates/   # New name ✓
│   ├── memory/
│   └── scripts/
├── .gitignore                       # Complete
├── .claudeignore                    # Present
└── .git/
    └── hooks/
# NO metadata.yaml!                  # Only difference
```

**Purpose:** Tests metadata creation for already-upgraded projects

#### fixtures/broken_mission_project/

```
broken_mission_project/
├── .kittify/
│   ├── missions/
│   │   └── software-dev/
│   │       ├── command-templates/
│   │       └── mission.yaml          # CORRUPTED or MISSING
│   ├── memory/
│   └── scripts/
├── .gitignore
└── .git/
# Dashboard returns "Mission: Unknown mission"
```

**Purpose:** Tests mission system repair for projects where dashboard shows "Unknown mission" due to corrupted/missing mission metadata

**Broken State Characteristics:**
- Mission directory exists but `mission.yaml` corrupted or missing
- Dashboard API returns "Unknown mission"
- Affects "most people" according to user - very common issue
- Caused by buggy versions of mission system

---

### Programmatic Test Helpers

**In `conftest.py`:**

```python
@pytest.fixture
def create_project_with_worktrees(tmp_path):
    """Create test project with multiple worktrees."""
    def _create(version: str, num_worktrees: int = 2):
        # Copy fixture, add worktrees using create-new-feature.sh
        ...
    return _create

@pytest.fixture
def create_conflicting_state(tmp_path):
    """Create project with specific conflicts."""
    def _create(conflicts: List[str]):
        # conflicts = ['both_specify_and_kittify', 'both_commands_and_templates']
        ...
    return _create

@pytest.fixture
def inject_custom_content():
    """Add custom user content that should be preserved."""
    def _inject(project_path: Path, location: str, content: str):
        ...
    return _inject

@pytest.fixture
def corrupt_metadata(tmp_path):
    """Create malformed metadata for error handling tests."""
    def _corrupt(project_path: Path, corruption_type: str):
        # corruption_type = 'invalid_yaml', 'missing_version', 'bad_date'
        ...
    return _corrupt
```

---

## Validation Patterns

### Version Detection

```python
from specify_cli.upgrade.detector import VersionDetector

detected = VersionDetector.detect_version(project_path)
assert detected == "0.6.4", f"Expected v0.6.4, got {detected}"
```

### Migration Application

```python
from specify_cli.upgrade.migrations.m_0_6_5_commands_rename import CommandsRenameMigration

migration = CommandsRenameMigration()
result = migration.apply(project_path, dry_run=False)

assert result.success, f"Migration failed: {result.error}"
assert result.files_changed == 3
assert "Renamed commands/ → command-templates/" in result.changes
```

### Metadata Validation

```python
from specify_cli.upgrade.metadata import ProjectMetadata

metadata = ProjectMetadata.load(project_path / '.kittify')
assert metadata.version == "0.6.7"
assert metadata.has_migration("0.6.5_commands_rename")
assert len(metadata.applied_migrations) == 4
```

### CLI Output

```python
result = subprocess.run(
    ['spec-kitty', 'upgrade', '--dry-run'],
    cwd=project_path,
    capture_output=True,
    text=True
)

assert result.returncode == 0
assert "Migration Plan" in result.stdout
assert "0.6.5_commands_rename" in result.stdout
assert "commands/ → command-templates/" in result.stdout
```

### File Structure Post-Migration

```python
# v0.1.x → current
assert not (project_path / '.specify').exists(), ".specify/ should be renamed"
assert (project_path / '.kittify').exists(), ".kittify/ should exist"
assert (project_path / 'kitty-specs').exists(), "specs/ renamed"

# Commands renamed
missions = project_path / '.kittify/missions'
for mission in missions.iterdir():
    assert (mission / 'command-templates').exists()
    assert not (mission / 'commands').exists()

# Metadata created
assert (project_path / '.kittify/metadata.yaml').exists()
```

### Idempotency

```python
# Run twice
migration.apply(project_path)
metadata1 = ProjectMetadata.load(project_path / '.kittify')

migration.apply(project_path)
metadata2 = ProjectMetadata.load(project_path / '.kittify')

assert metadata1 == metadata2, "Second run should be no-op"
```

---

## Test Execution Strategy

### Phase 1: Unit Tests (Fast - ~10 seconds)

**Files:**
- `test_metadata.py` (8 tests)
- `test_detector.py` (10 tests)
- `test_base.py` (3 tests)
- `test_registry.py` (6 tests)

**Run:** On every commit

```bash
pytest tests/test_upgrade/test_metadata.py tests/test_upgrade/test_detector.py -v
```

### Phase 2: Migration Tests (Medium - ~20 seconds)

**Files:**
- `test_m_0_2_0_specify_to_kittify.py` (6 tests)
- `test_m_0_4_8_gitignore_agents.py` (5 tests)
- `test_m_0_5_0_encoding_hooks.py` (5 tests)
- `test_m_0_6_5_commands_rename.py` (8 tests)
- `test_runner.py` (7 tests)

**Run:** On pull requests

```bash
pytest tests/test_upgrade/test_migrations/ tests/test_upgrade/test_runner.py -v
```

### Phase 3: Integration Tests (Slow - ~40 seconds)

**Files:**
- `test_integration_cli.py` (15 tests)
- `test_worktree_upgrade.py` (8 tests)
- `test_edge_cases.py` (10 tests)

**Run:** Before release

```bash
pytest tests/test_upgrade/test_integration_cli.py tests/test_upgrade/test_worktree_upgrade.py tests/test_upgrade/test_edge_cases.py -v
```

### Full Suite

```bash
# All upgrade tests
export SPEC_KITTY_REPO=/Users/robert/Code/spec-kitty
pytest tests/test_upgrade/ -v

# With coverage
pytest tests/test_upgrade/ --cov=specify_cli.upgrade --cov-report=html

# Specific test
pytest tests/test_upgrade/test_migrations/test_m_0_6_5_commands_rename.py::TestCommandsRenameMigration::test_agentfunc_doubled_commands -v
```

---

## Success Criteria

### Must Pass (P0) - Blocking

- ✅ All 4 historical versions upgrade to current without errors
- ✅ Idempotency: Running upgrade twice is safe (no-op)
- ✅ Metadata correctly tracks applied migrations
- ✅ Worktrees upgraded automatically with main repo
- ✅ User content preserved (constitution, custom commands)
- ✅ **agentfunc doubled-commands issue fixed**
- ✅ Clean uninstall possible (remove `.kittify/metadata.yaml`)

### Should Pass (P1) - Important

- ✅ Dry-run shows accurate preview of changes
- ✅ JSON output is parseable and complete
- ✅ Edge cases handled gracefully (conflicts, partial states)
- ✅ Clear error messages with remediation steps
- ✅ Windows compatibility (symlink fallback to copy)
- ✅ Performance: < 5 seconds per migration

### Nice to Have (P2) - Optional

- ✅ Upgrade from unknown/corrupted state (best effort)
- ✅ Rollback guidance in error messages (git instructions)
- ✅ Progress bar for multi-migration upgrades
- ✅ `--check` flag to preview needed migrations without running
- ✅ `--list-migrations` to see all available migrations

---

## Test Coverage Matrix

| Version | v0.2.0 Rename | v0.4.8 Gitignore | v0.5.0 Hooks | v0.6.5 Commands | Total Migrations |
|---------|---------------|------------------|--------------|-----------------|------------------|
| v0.1.x  | ✅ | ✅ | ✅ | ✅ | 4 |
| v0.4.7  | - | ✅ | ✅ | ✅ | 3 |
| v0.6.4  | - | - | - | ✅ | 1 |
| v0.6.6  | - | - | - | - | 0 (metadata only) |
| v0.6.7  | - | - | - | - | 0 (no-op) |

**Upgrade Paths Tested:**
- v0.1.x → v0.6.7 (4 migrations)
- v0.4.7 → v0.6.7 (3 migrations)
- v0.6.4 → v0.6.7 (1 migration) **← Most common real-world scenario**
- v0.6.6 → v0.6.7 (metadata creation only)

---

## Critical Implementation Considerations

### For Test Writers

1. **Fixture Isolation** - Each test uses independent `tmp_path` directory
2. **Cleanup** - Always use `finally: shutil.rmtree(temp_dir, ignore_errors=True)`
3. **Timeouts** - Set 60s timeout for multi-migration upgrades
4. **Assertions** - Include actual vs expected in all failure messages
5. **Platform** - Use `if os.name != 'nt'` for Unix-specific tests (symlinks)

### For Migration Implementers

1. **Atomicity** - Each migration all-or-nothing (no partial states)
2. **Idempotency** - Must be safe to run multiple times
3. **Validation** - Use `can_apply()` to check preconditions before applying
4. **User Data** - Never delete user-created content (constitution, custom commands)
5. **Metadata** - Record migration immediately after success
6. **Worktrees** - Special handling for shared vs isolated content

### For CLI Developers

1. **Confirmation** - Require yes/no unless `--force`
2. **Progress** - Show current migration in verbose mode
3. **Errors** - Clear messages with remediation (e.g., "Run `git checkout` to rollback")
4. **JSON Mode** - Parseable output for automation/CI
5. **Exit Codes** - 0=success, 1=failure, 2=partial success (some worktrees failed)

---

## Test Development Timeline

| Day | Tasks | Tests | Status |
|-----|-------|-------|--------|
| **Day 1** | Create fixtures + metadata/detector tests | 20 | 📋 Planned |
| **Day 2** | Migration unit tests (all 5 migrations) | 30 | 📋 Planned |
| **Day 3** | Registry + runner tests | 13 | 📋 Planned |
| **Day 4** | CLI integration tests | 15 | 📋 Planned |
| **Day 5** | Worktree + edge case tests | 18 | 📋 Planned |
| **Day 6** | Documentation + bug fixes | - | 📋 Planned |

**Total Effort:** ~6 days for 97 tests

---

## Critical Files for Testing

| File Path | Purpose | Tests Dependency |
|-----------|---------|------------------|
| `src/specify_cli/upgrade/metadata.py` | Version tracking | All tests |
| `src/specify_cli/upgrade/detector.py` | Version detection | All integration tests |
| `src/specify_cli/upgrade/migrations/m_0_6_5_commands_rename.py` | Commands rename | **Critical for agentfunc** |
| `src/specify_cli/upgrade/migrations/m_0_6_6_mission_repair.py` | Mission system repair | **Critical - affects most users** |
| `src/specify_cli/upgrade/registry.py` | Migration ordering | Runner + integration |
| `src/specify_cli/upgrade/runner.py` | Orchestration | Integration tests |
| `tests/test_upgrade/conftest.py` | Shared fixtures | All test files |
| `tests/test_upgrade/fixtures/broken_mission_project/` | Broken mission state | Mission repair tests |
| `tests/test_upgrade/fixtures/` | Historical states | Migration + integration |

---

## Open Questions for Implementation

1. **Rollback Strategy:** Should failed migrations attempt automatic rollback, or just document how to use git?
   - **Recommendation:** No automatic rollback. Provide clear git instructions in error message.

2. **Uncommitted Changes:** Should upgrade block if there are uncommitted changes?
   - **Recommendation:** Warn but allow (users can use `--force` to skip warning).

3. **Windows Symlinks:** Should we attempt symlinks on Windows or always copy?
   - **Recommendation:** Try symlink, fall back to copy with warning.

4. **Partial Worktree Failure:** If 1 of 3 worktrees fails upgrade, what exit code?
   - **Recommendation:** Exit code 2 (partial success), list failed worktrees.

5. **Unknown Version Detection:** What if we can't detect version confidently?
   - **Recommendation:** Error with manual override: `spec-kitty upgrade --from-version 0.6.4`

---

## Related Documentation

- **Upgrade Implementation Plan:** `~/.claude/plans/cozy-tinkering-flask.md`
- **v0.6.0 Test Results:** `findings/0.6.0/2025-12-13_04_ALL_TESTS_PASSING.md`
- **Upgrade Path Analysis:** `findings/0.6.0/2025-12-13_02_upgrade_path_analysis.md`

---

## Next Steps

1. ✅ Create `findings/0.6.7/` directory
2. ✅ Write this test plan document
3. Create static fixture directories in `tests/test_upgrade/fixtures/`
4. Implement `tests/test_upgrade/conftest.py` with helpers
5. Begin with metadata + detector tests (foundation)
6. Progress through migrations (chronological order)
7. Add registry + runner tests
8. Finish with CLI integration tests
9. Add worktree + edge case tests
10. Document results in `2025-12-14_TEST_RESULTS_upgrade_feature.md`

---

**Status:** 📋 Test plan complete, ready for implementation
**Author:** Testing framework via Claude Code
**Version:** 1.0
**Last Updated:** 2025-12-14
