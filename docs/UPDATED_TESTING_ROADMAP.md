# Updated Testing Roadmap - Spec-Kitty Test Framework

**Date:** 2025-11-13
**Status:** Categories 1-4 Complete (79/~110 tests, 72%)
**Based on:** spec-kitty commit c02c2ad (2025-11-13)

## Executive Summary

After implementing Categories 1-4 and analyzing critical gaps, this roadmap expands our testing strategy to cover:

1. **Artifact Rendering** - CSV, YAML, TOML, JSON, MD inline display
2. **Script Execution** - Validate all 11 command scripts actually work
3. **Diagnostics System** - API and CLI validation in multiple scenarios
4. **Worktree Management** - Feature isolation and workflow patterns

---

## Critical Findings from Analysis

### 1. Artifact Rendering System

**Location:** `src/specify_cli/dashboard/handlers/features.py`

**Discovery:**
- Dashboard serves research artifacts via `/api/features/{feature_id}/research` endpoint
- Supports inline viewing of: `.csv`, `.md`, `.json`, `.xlsx`, `.xls`
- Icon mapping: 📊 csv, 📝 md, 📋 json, 📈 xlsx/xls, 📄 default
- Artifacts served from `research/` subdirectory within feature
- Text content served as `text/plain` with UTF-8 encoding
- Error recovery for non-UTF-8 files

**Test Requirements:**
```python
# Need to test:
1. CSV files render correctly (proper parsing)
2. YAML/TOML files display as structured data
3. JSON files are prettified
4. Markdown files render with syntax highlighting
5. Large files don't crash the system
6. Non-UTF-8 files trigger error recovery
7. Artifact list includes all supported types
8. Security: Path traversal attempts blocked
```

### 2. Script Execution System

**Location:** `.kittify/scripts/bash/` and command templates

**Commands with Script Invocations (11 total):**
1. `specify.md` → `create-new-feature.sh`
2. `plan.md` → `setup-plan.sh`
3. `research.md` → (mission-specific research scripts)
4. `tasks.md` → `refresh-kittify-tasks.sh`
5. `implement.md` → `move-task-to-doing.sh`
6. `review.md` → `mark-task-status.sh`
7. `accept.md` → `accept-feature.sh`
8. `merge.md` → `merge-feature.sh`
9. `analyze.md` → (analysis scripts)
10. `clarify.md` → (clarification scripts)
11. `checklist.md` → (checklist generation scripts)

**Script Types:**
- **Bash scripts:** `.kittify/scripts/bash/*.sh`
- **PowerShell scripts:** `.kittify/scripts/powershell/*.ps1`
- **Common utilities:** `common.sh` (shared functions)

**Test Requirements:**
```python
# For EACH command:
1. Script file exists at referenced path
2. Script has execute permissions
3. Script accepts expected arguments (--json flag, etc.)
4. Script produces valid JSON output (when applicable)
5. Script handles missing dependencies gracefully
6. Script works in both repo root and worktree contexts
7. Script error messages are clear and actionable
8. Script exit codes are correct (0 = success)
```

### 3. Diagnostics System

**Location:** `src/specify_cli/dashboard/diagnostics.py`

**Capabilities:**
- File integrity checking (via FileManifest)
- Worktree status detection (via WorktreeStatus)
- Git branch detection
- Feature state analysis
- Mission verification
- Observation generation (unusual states)

**Test Scenarios:**
```python
# Scenario 1: Fresh init (no features)
- All core files present
- No worktrees
- On main branch
- Mission activated
- No observations

# Scenario 2: Single feature in development
- Feature branch exists
- Worktree created
- Artifacts in worktree only
- Not yet merged
- Current feature detected

# Scenario 3: Multiple features (mixed states)
- Some features merged
- Some in development
- Some worktrees deleted but branches remain
- Observations flag inconsistencies

# Scenario 4: Error states
- Missing core files
- Corrupted mission config
- Orphaned worktrees
- Branch/worktree mismatches

# Scenario 5: From worktree context
- diagnostics run from within .worktrees/feature-name/
- Current feature correctly detected
- Paths resolved relative to repo root

# Scenario 6: CLI vs API
- spec-kitty diagnostics (CLI) output
- /api/diagnostics (dashboard) JSON response
- Both return equivalent data
```

### 4. Worktree Management

**Location:** `src/specify_cli/manifest.py` (WorktreeStatus class)

**Key Concepts:**
```
Repository Structure:
project-root/
├── .kittify/               # Core infrastructure
├── .worktrees/             # Feature worktrees
│   ├── 001-feature-a/      # Isolated worktree for feature
│   │   ├── .git           # Git worktree link
│   │   ├── .kittify/      # Symlink to main
│   │   └── kitty-specs/   # Feature-specific artifacts
│   │       └── 001-feature-a/
│   │           ├── spec.md
│   │           ├── plan.md
│   │           └── tasks/
│   └── 002-feature-b/
├── kitty-specs/            # Features in main branch
│   └── 000-baseline/       # Merged features
└── .git/                   # Main repository
```

**Worktree Lifecycle:**
1. `/spec-kitty.specify` → Creates branch + worktree + spec
2. Agent works in `.worktrees/feature-name/`
3. All artifacts live in worktree until merged
4. `/spec-kitty.merge` → Merges to main, cleans up worktree
5. Artifacts move from `.worktrees/*/kitty-specs/` to `kitty-specs/`

**Test Requirements:**
```python
# Worktree Creation
1. spec-kitty specify creates worktree at correct path
2. .kittify/ symlinked (not copied)
3. Git branch created and checked out in worktree
4. Feature directory created in worktree's kitty-specs/

# Worktree Isolation
5. Multiple worktrees don't interfere
6. Scripts executed in worktree context work correctly
7. Dashboard detects current worktree context
8. Paths in commands resolve correctly from worktree

# Worktree Detection
9. Agent can determine if running in worktree
10. Dashboard shows active worktree in UI
11. Diagnostics correctly identify worktree features

# Worktree Cleanup
12. Merge removes worktree (configurable)
13. Orphaned worktrees detected and reported
14. Branch cleanup happens (or preserved with --keep-branch)
```

---

## Revised Test Category Structure

### ✅ Category 1: Initialization Workflows (51 tests) - COMPLETE
- Template discovery mechanisms
- Multi-agent initialization
- All 12 agents validated
- Variable substitution
- Format conversion

### ✅ Category 2: Agent Workflow Execution (11 tests) - COMPLETE
- Command discovery and readability
- Workflow order correctness
- Path references
- Multi-agent isolation
- Content quality

### ✅ Category 3: Template Rendering (10 tests) - COMPLETE
- Variable substitution ($ARGUMENTS, {SCRIPT}, etc.)
- Format conversion (MD→TOML, .prompt.md)
- Path rewriting to .kittify/

### ✅ Category 4: Dashboard & State (7 tests) - COMPLETE
- State detection after init
- Artifact detection
- Workflow status transitions
- Kanban lane structure

---

### 🆕 Category 5: Artifact Rendering & Display (10 tests) - NEW

**Test Class:** `TestArtifactRendering`

#### 5.1 Research Artifact Discovery (3 tests)
```python
def test_research_artifacts_discovered(temp_project_dir, spec_kitty_repo_root):
    """Test: All artifact types in research/ directory are discovered"""
    # Create feature with research/ artifacts
    # Verify API returns complete artifact list

def test_artifact_icon_mapping(temp_project_dir, spec_kitty_repo_root):
    """Test: Icons correctly assigned based on file extension"""
    # csv → 📊, md → 📝, json → 📋, xlsx → 📈, default → 📄

def test_nested_research_artifacts(temp_project_dir, spec_kitty_repo_root):
    """Test: Artifacts in subdirectories are discovered recursively"""
    # research/phase1/data.csv should be found
```

#### 5.2 Artifact Content Serving (4 tests)
```python
def test_csv_file_served_correctly(temp_project_dir, spec_kitty_repo_root):
    """Test: CSV files served as text/plain with correct content"""
    # Create CSV, verify API serves it correctly

def test_json_file_content_valid(temp_project_dir, spec_kitty_repo_root):
    """Test: JSON files served with valid UTF-8 encoding"""

def test_yaml_file_readable(temp_project_dir, spec_kitty_repo_root):
    """Test: YAML files served as plain text"""

def test_markdown_artifact_content(temp_project_dir, spec_kitty_repo_root):
    """Test: Markdown artifacts served correctly"""
```

#### 5.3 Error Handling (3 tests)
```python
def test_non_utf8_file_error_recovery(temp_project_dir, spec_kitty_repo_root):
    """Test: Non-UTF-8 files trigger error message + recovery"""
    # Create file with latin-1 encoding
    # Verify error message present + file readable with errors='replace'

def test_path_traversal_blocked(temp_project_dir, spec_kitty_repo_root):
    """Test: Path traversal attacks blocked by API"""
    # Attempt to access ../../sensitive-file
    # Verify 404 response

def test_large_artifact_handling(temp_project_dir, spec_kitty_repo_root):
    """Test: Large files (>10MB) handled gracefully"""
    # Create large CSV
    # Verify doesn't crash, reasonable response time
```

---

### 🆕 Category 6: Script Execution Validation (15 tests) - EXPANDED

**Test Class:** `TestScriptExecution`

#### 6.1 Script Existence & Permissions (3 tests)
```python
def test_all_referenced_scripts_exist(temp_project_dir, spec_kitty_repo_root):
    """Test: Every script referenced in commands exists"""
    # Parse all command templates
    # Extract {SCRIPT} references
    # Verify .kittify/scripts/bash/*.sh exist

def test_bash_scripts_executable(temp_project_dir, spec_kitty_repo_root):
    """Test: All bash scripts have execute permissions"""

def test_powershell_scripts_exist(temp_project_dir, spec_kitty_repo_root):
    """Test: PowerShell equivalents exist for all bash scripts"""
```

#### 6.2 Core Script Functionality (6 tests)
```python
def test_create_new_feature_script(temp_project_dir, spec_kitty_repo_root):
    """Test: create-new-feature.sh produces valid JSON output"""
    # Run script with test feature description
    # Verify JSON output with BRANCH_NAME, SPEC_FILE, FEATURE_NUM
    # Verify feature directory created

def test_setup_plan_script(temp_project_dir, spec_kitty_repo_root):
    """Test: setup-plan.sh initializes plan structure"""
    # Create feature first
    # Run setup-plan.sh
    # Verify plan.md created with correct template

def test_refresh_tasks_script(temp_project_dir, spec_kitty_repo_root):
    """Test: refresh-kittify-tasks.sh generates work packages"""
    # Create feature with tasks.md
    # Run refresh script
    # Verify tasks/planned/ directory populated

def test_move_task_to_doing_script(temp_project_dir, spec_kitty_repo_root):
    """Test: move-task-to-doing.sh moves work packages correctly"""
    # Create task in planned/
    # Run script with WP01 identifier
    # Verify moved to doing/

def test_mark_task_status_script(temp_project_dir, spec_kitty_repo_root):
    """Test: mark-task-status.sh updates task frontmatter"""
    # Create task
    # Run script to mark complete
    # Verify frontmatter updated

def test_accept_feature_script(temp_project_dir, spec_kitty_repo_root):
    """Test: accept-feature.sh validates feature completeness"""
    # Create complete feature
    # Run acceptance script
    # Verify exit code 0 and validation report
```

#### 6.3 Script Error Handling (3 tests)
```python
def test_script_missing_args_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts provide clear error when args missing"""
    # Run create-new-feature.sh without arguments
    # Verify helpful error message (not cryptic bash error)

def test_script_invalid_json_flag(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts handle malformed --json arguments"""

def test_script_git_not_available_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts detect missing git dependency"""
    # Mock git not in PATH
    # Verify clear error message
```

#### 6.4 Script Context Awareness (3 tests)
```python
def test_script_runs_from_repo_root(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts work when executed from repo root"""
    # cd to project root
    # Run script
    # Verify success

def test_script_runs_from_worktree(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts work when executed from worktree context"""
    # Create worktree
    # cd to .worktrees/feature/
    # Run script
    # Verify resolves paths correctly

def test_script_detects_feature_context(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts auto-detect current feature when in worktree"""
    # In worktree, run review script without feature arg
    # Verify detects feature from context
```

---

### 🆕 Category 7: Diagnostics System (12 tests) - NEW

**Test Class:** `TestDiagnostics`

#### 7.1 Basic Diagnostics (3 tests)
```python
def test_diagnostics_fresh_init(temp_project_dir, spec_kitty_repo_root):
    """Test: Diagnostics show healthy state after fresh init"""
    # Run diagnostics
    # Verify: file_integrity all present, no issues, on main branch

def test_diagnostics_detect_git_branch(temp_project_dir, spec_kitty_repo_root):
    """Test: Current git branch correctly detected"""
    # Create branch, checkout
    # Run diagnostics
    # Verify git_branch field correct

def test_diagnostics_detect_active_mission(temp_project_dir, spec_kitty_repo_root):
    """Test: Active mission reported correctly"""
    # Verify active_mission = 'software-dev' (default)
```

#### 7.2 Feature State Detection (3 tests)
```python
def test_diagnostics_detect_single_feature(temp_project_dir, spec_kitty_repo_root):
    """Test: Feature in development correctly identified"""
    # Create feature
    # Run diagnostics
    # Verify all_features list includes feature
    # Verify state = 'in_development'

def test_diagnostics_current_feature_detection(temp_project_dir, spec_kitty_repo_root):
    """Test: Current feature detected from worktree context"""
    # Create feature with worktree
    # Run diagnostics from worktree directory
    # Verify current_feature detected correctly

def test_diagnostics_multiple_features_mixed_states(temp_project_dir, spec_kitty_repo_root):
    """Test: Multiple features with different states tracked"""
    # Create 3 features: one merged, one in dev, one with artifacts only
    # Run diagnostics
    # Verify each state correct
```

#### 7.3 Error Detection (3 tests)
```python
def test_diagnostics_detect_missing_files(temp_project_dir, spec_kitty_repo_root):
    """Test: Missing mission files flagged in diagnostics"""
    # Delete a command file
    # Run diagnostics
    # Verify missing_files list includes it
    # Verify observation about file integrity

def test_diagnostics_detect_orphaned_worktree(temp_project_dir, spec_kitty_repo_root):
    """Test: Worktree without matching branch flagged"""
    # Create worktree, delete branch
    # Run diagnostics
    # Verify observation about inconsistent state

def test_diagnostics_unusual_states_observed(temp_project_dir, spec_kitty_repo_root):
    """Test: Unusual states generate observations"""
    # Be in worktree but on main branch (unusual)
    # Run diagnostics
    # Verify observation present
```

#### 7.4 API vs CLI Consistency (3 tests)
```python
def test_diagnostics_api_endpoint(temp_project_dir, spec_kitty_repo_root):
    """Test: /api/diagnostics returns valid JSON"""
    # Start dashboard (or use scanner directly)
    # Call diagnostics API
    # Verify JSON structure matches expected schema

def test_diagnostics_cli_command(temp_project_dir, spec_kitty_repo_root):
    """Test: spec-kitty diagnostics CLI command works"""
    # Run: spec-kitty diagnostics (if command exists)
    # Verify output human-readable
    # Verify exit code 0 on healthy state

def test_diagnostics_api_cli_equivalence(temp_project_dir, spec_kitty_repo_root):
    """Test: API and CLI return equivalent data"""
    # Run both
    # Parse CLI output to JSON equivalent
    # Verify same project_path, git_branch, features, etc.
```

---

### 🆕 Category 8: Worktree Management (15 tests) - NEW

**Test Class:** `TestWorktreeManagement`

#### 8.1 Worktree Creation (4 tests)
```python
def test_worktree_created_for_new_feature(temp_project_dir, spec_kitty_repo_root):
    """Test: Worktree created at .worktrees/{feature}/ when feature specified"""
    # Run specify command with feature description
    # Verify .worktrees/001-feature/ exists
    # Verify git worktree list includes it

def test_worktree_has_kittify_symlink(temp_project_dir, spec_kitty_repo_root):
    """Test: .kittify/ in worktree is symlink to main repo"""
    # Create feature with worktree
    # Verify .worktrees/feature/.kittify is symlink
    # Verify resolves to main .kittify/

def test_worktree_feature_directory_structure(temp_project_dir, spec_kitty_repo_root):
    """Test: Feature artifacts created in worktree's kitty-specs/"""
    # Create feature
    # Verify .worktrees/001-feature/kitty-specs/001-feature/ exists
    # Verify spec.md present

def test_worktree_git_branch_checkout(temp_project_dir, spec_kitty_repo_root):
    """Test: Worktree checked out to feature branch"""
    # Create feature
    # cd to worktree
    # Run git branch --show-current
    # Verify on feature/001-feature branch
```

#### 8.2 Worktree Isolation (4 tests)
```python
def test_multiple_worktrees_isolated(temp_project_dir, spec_kitty_repo_root):
    """Test: Multiple worktrees don't interfere with each other"""
    # Create 2 features with worktrees
    # Verify each has own kitty-specs/ directory
    # Modify file in one, verify other unchanged

def test_worktree_script_execution(temp_project_dir, spec_kitty_repo_root):
    """Test: Scripts executed from worktree work correctly"""
    # Create feature with worktree
    # cd to worktree
    # Run plan script
    # Verify plan.md created in worktree's feature dir

def test_worktree_path_resolution(temp_project_dir, spec_kitty_repo_root):
    """Test: Paths in commands resolve correctly from worktree"""
    # In worktree, run implement command
    # Verify references to .kittify/scripts/ resolve
    # Verify tasks/doing/ paths correct

def test_worktree_dashboard_detection(temp_project_dir, spec_kitty_repo_root):
    """Test: Dashboard detects when running from worktree"""
    # Create feature with worktree
    # Run diagnostics from worktree
    # Verify in_worktree = true
    # Verify current_feature detected
```

#### 8.3 Worktree Detection & Status (4 tests)
```python
def test_worktree_status_in_development(temp_project_dir, spec_kitty_repo_root):
    """Test: Feature with worktree shows 'in_development' state"""
    # Create feature with worktree
    # Run diagnostics
    # Verify state = 'in_development'

def test_worktree_exists_field_accurate(temp_project_dir, spec_kitty_repo_root):
    """Test: worktree_exists field in diagnostics accurate"""
    # Create feature with worktree
    # Verify worktree_exists = true
    # Delete worktree manually
    # Re-run diagnostics
    # Verify worktree_exists = false

def test_dashboard_shows_active_worktree(temp_project_dir, spec_kitty_repo_root):
    """Test: Dashboard UI displays current worktree"""
    # Create feature, enter worktree
    # Call /api/features/list
    # Verify active_worktree field set

def test_worktree_path_displayed_correctly(temp_project_dir, spec_kitty_repo_root):
    """Test: Worktree paths shown with ~ for home directory"""
    # Create worktree
    # Check diagnostics
    # Verify path uses ~/... format for readability
```

#### 8.4 Worktree Cleanup (3 tests)
```python
def test_merge_removes_worktree_by_default(temp_project_dir, spec_kitty_repo_root):
    """Test: Merging feature removes worktree"""
    # Create feature with worktree
    # Run merge script (simulate)
    # Verify .worktrees/feature/ removed

def test_merge_keeps_worktree_with_flag(temp_project_dir, spec_kitty_repo_root):
    """Test: --keep-branch flag preserves worktree"""
    # Create feature with worktree
    # Run merge with --keep-branch
    # Verify worktree still exists

def test_orphaned_worktree_detected(temp_project_dir, spec_kitty_repo_root):
    """Test: Worktree without matching branch flagged as orphaned"""
    # Create worktree
    # Delete branch externally (git branch -D)
    # Run diagnostics
    # Verify observation about orphaned worktree
```

---

### 🔄 Category 9: Human & Agent Interaction (8 tests) - REVISED

**Test Class:** `TestReadabilityAndClarity`

#### 9.1 Command Readability (3 tests)
```python
def test_commands_are_valid_markdown(temp_project_dir, spec_kitty_repo_root):
    """Test: All generated commands are valid Markdown"""
    # Parse each command file
    # Verify valid frontmatter YAML
    # Verify body is parseable Markdown

def test_commands_have_clear_goals(temp_project_dir, spec_kitty_repo_root):
    """Test: Commands include clear descriptions of what they do"""
    # Check each command has 'description:' in frontmatter
    # Verify description is non-empty and informative

def test_command_instructions_unambiguous(temp_project_dir, spec_kitty_repo_root):
    """Test: Command text provides clear, unambiguous instructions"""
    # Look for vague language like "maybe", "probably"
    # Verify commands have numbered steps or clear flow
```

#### 9.2 Agent Discovery (2 tests)
```python
def test_commands_discoverable_by_agent(temp_project_dir, spec_kitty_repo_root):
    """Test: Command naming follows conventions for agent discovery"""
    # Verify all start with spec-kitty prefix
    # Verify extension correct per agent (.md, .toml, .prompt.md)

def test_command_descriptions_informative(temp_project_dir, spec_kitty_repo_root):
    """Test: Descriptions help agents understand when to use command"""
    # Check description field not generic
    # Verify includes key verbs (create, update, verify, merge, etc.)
```

#### 9.3 Path Correctness (3 tests)
```python
def test_referenced_paths_exist_or_will_be_created(temp_project_dir, spec_kitty_repo_root):
    """Test: All paths referenced in commands are valid"""
    # Parse commands for path references
    # Verify .kittify/ paths exist
    # Verify templates/ paths will be created by scripts

def test_no_broken_template_links(temp_project_dir, spec_kitty_repo_root):
    """Test: Template paths in commands resolve correctly"""
    # Find references to templates/
    # Verify files exist in .kittify/templates/

def test_relative_paths_work_from_worktree(temp_project_dir, spec_kitty_repo_root):
    """Test: Relative paths in commands work from worktree context"""
    # Create worktree
    # Parse command referencing tasks/planned/
    # Verify path would resolve correctly from worktree
```

---

### 🔄 Category 10: Error Handling (10 tests) - EXPANDED

**Test Class:** `TestErrorHandling`

#### 10.1 Template Discovery Failures (3 tests)
```python
def test_clear_error_when_template_root_not_set(temp_project_dir):
    """Test: Helpful error when SPEC_KITTY_TEMPLATE_ROOT unset"""
    # Run init without env var
    # Verify error message explains all 3 solutions

def test_helpful_suggestions_for_template_errors(temp_project_dir):
    """Test: Error includes remediation steps"""
    # Verify mentions: pip install, --template-root flag, env var

def test_path_validation_messages_clear(temp_project_dir):
    """Test: Path validation errors are understandable"""
    # Provide invalid template path
    # Verify error mentions which path failed and why
```

#### 10.2 Init Edge Cases (4 tests)
```python
def test_existing_project_warning(temp_project_dir, spec_kitty_repo_root):
    """Test: Warning when initializing in non-empty directory"""
    # Create project, add files
    # Run init --here
    # Verify warning shown about merge/overwrite

def test_invalid_agent_name_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Clear error for unsupported agent name"""
    # Run init with --ai=invalid_agent
    # Verify error lists valid options

def test_missing_git_dependency_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Detects when git not available"""
    # Mock git not in PATH
    # Run init
    # Verify error message explains git required

def test_permission_denied_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Clear error when filesystem permissions insufficient"""
    # Create read-only directory
    # Attempt init
    # Verify error message helpful
```

#### 10.3 State Validation (3 tests)
```python
def test_invalid_feature_directory_structure_error(temp_project_dir, spec_kitty_repo_root):
    """Test: Scanner handles malformed feature directories"""
    # Create kitty-specs/invalid-name/ (no number prefix)
    # Run scanner
    # Verify doesn't crash, skips invalid directories

def test_malformed_frontmatter_handling(temp_project_dir, spec_kitty_repo_root):
    """Test: Commands with invalid YAML frontmatter handled gracefully"""
    # Create work package with bad YAML
    # Run scanner
    # Verify error logged, file skipped, doesn't crash

def test_corrupted_meta_json_handling(temp_project_dir, spec_kitty_repo_root):
    """Test: Invalid meta.json doesn't break feature detection"""
    # Create feature with corrupted meta.json
    # Run scanner
    # Verify feature still detected, uses directory name fallback
```

---

## Summary: Revised Test Coverage

| Category | Tests | Status | Priority |
|----------|-------|--------|----------|
| 1. Initialization Workflows | 51 | ✅ Complete | - |
| 2. Agent Workflow Execution | 11 | ✅ Complete | - |
| 3. Template Rendering | 10 | ✅ Complete | - |
| 4. Dashboard & State | 7 | ✅ Complete | - |
| 5. Artifact Rendering & Display | 10 | ⏳ Next | **HIGH** |
| 6. Script Execution Validation | 15 | ⏳ Pending | **CRITICAL** |
| 7. Diagnostics System | 12 | ⏳ Pending | **HIGH** |
| 8. Worktree Management | 15 | ⏳ Pending | **CRITICAL** |
| 9. Human & Agent Interaction | 8 | ⏳ Pending | MEDIUM |
| 10. Error Handling | 10 | ⏳ Pending | MEDIUM |
| **TOTAL** | **149** | **79 done (53%)** | |

**Key Changes from Original Plan:**
- **Original estimate:** ~98 tests
- **Revised estimate:** ~149 tests (+51 tests, +52% scope)
- **Critical additions:**
  - Script execution validation (15 tests)
  - Worktree management (15 tests)
  - Diagnostics system (12 tests)
  - Artifact rendering (10 tests)

---

## Implementation Strategy

### Phase 1: Critical Infrastructure (Categories 6 & 8)
**Priority:** CRITICAL
**Why:** These test core functionality that agents depend on

```bash
# Week 1-2
1. Category 6: Script Execution (15 tests)
   - Ensures all 11 command scripts actually work
   - Validates JSON output formats
   - Tests both bash and PowerShell

2. Category 8: Worktree Management (15 tests)
   - Core to multi-feature development workflow
   - Tests isolation and path resolution
   - Validates cleanup and detection
```

### Phase 2: User-Facing Features (Categories 5 & 7)
**Priority:** HIGH
**Why:** Directly impact user experience and debugging

```bash
# Week 3
3. Category 5: Artifact Rendering (10 tests)
   - CSV, JSON, YAML inline display
   - Security (path traversal)
   - Error handling for large files

4. Category 7: Diagnostics (12 tests)
   - CLI and API validation
   - Multiple scenarios (fresh init, worktrees, errors)
   - Consistency between interfaces
```

### Phase 3: Quality & Polish (Categories 9 & 10)
**Priority:** MEDIUM
**Why:** Important but can be addressed after core functionality validated

```bash
# Week 4
5. Category 9: Readability & Clarity (8 tests)
   - Markdown validity
   - Agent discoverability
   - Path correctness

6. Category 10: Error Handling (10 tests)
   - Edge cases
   - Clear error messages
   - Graceful degradation
```

---

## Testing Patterns for New Categories

### Pattern 1: Script Execution Tests
```python
def test_script_produces_valid_output(temp_project_dir, spec_kitty_repo_root):
    """Template for testing script execution"""
    # 1. Setup project
    project_path = setup_test_project(temp_project_dir, spec_kitty_repo_root)

    # 2. Run script with arguments
    result = subprocess.run(
        [str(project_path / '.kittify/scripts/bash/script-name.sh'),
         '--json', 'test-arg'],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False  # Don't raise on non-zero exit
    )

    # 3. Validate exit code
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # 4. Validate JSON output
    output_data = json.loads(result.stdout)
    assert 'expected_field' in output_data

    # 5. Validate filesystem changes
    assert (project_path / 'expected-file.md').exists()
```

### Pattern 2: Diagnostics Tests
```python
def test_diagnostics_scenario(temp_project_dir, spec_kitty_repo_root):
    """Template for testing diagnostics"""
    # 1. Setup specific scenario
    project_path = setup_test_project(temp_project_dir, spec_kitty_repo_root)
    create_feature_with_worktree(project_path, "001-test-feature")

    # 2. Run diagnostics
    from specify_cli.dashboard import run_diagnostics
    diagnostics = run_diagnostics(project_path)

    # 3. Validate structure
    assert 'project_path' in diagnostics
    assert 'all_features' in diagnostics

    # 4. Validate specific scenario
    assert diagnostics['in_worktree'] == False  # Running from main
    assert len(diagnostics['all_features']) == 1
    assert diagnostics['all_features'][0]['state'] == 'in_development'
```

### Pattern 3: Worktree Tests
```python
def test_worktree_behavior(temp_project_dir, spec_kitty_repo_root):
    """Template for testing worktree management"""
    # 1. Setup
    project_path = setup_test_project(temp_project_dir, spec_kitty_repo_root)

    # 2. Create feature (which creates worktree)
    feature_name = "001-test-feature"
    create_feature_via_script(project_path, feature_name, "Test description")

    # 3. Verify worktree structure
    worktree_path = project_path / '.worktrees' / feature_name
    assert worktree_path.exists()
    assert (worktree_path / '.kittify').is_symlink()

    # 4. Verify git worktree
    result = subprocess.run(
        ['git', 'worktree', 'list'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    assert str(worktree_path) in result.stdout

    # 5. Test script execution from worktree
    result = subprocess.run(
        [str(project_path / '.kittify/scripts/bash/some-script.sh')],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

---

## Success Criteria

### Must-Have (Required for 1.0 release)
- ✅ Categories 1-4: Complete (79 tests)
- ⏳ Category 6: Script Execution (15 tests) - **Critical**
- ⏳ Category 8: Worktree Management (15 tests) - **Critical**
- **Total:** 109 tests minimum

### Should-Have (Required for production quality)
- ⏳ Category 5: Artifact Rendering (10 tests)
- ⏳ Category 7: Diagnostics (12 tests)
- **Total:** 131 tests

### Nice-to-Have (Polish)
- ⏳ Category 9: Readability (8 tests)
- ⏳ Category 10: Error Handling (10 tests)
- **Total:** 149 tests (complete coverage)

---

## Risk Assessment

### High Risk Areas (Need Testing ASAP)
1. **Script execution in worktree context** - Could break core workflow
2. **Worktree path resolution** - Agents might reference wrong paths
3. **Diagnostics in edge cases** - Users depend on this for debugging

### Medium Risk Areas
4. **Artifact rendering security** - Path traversal vulnerabilities
5. **Large file handling** - Could crash dashboard
6. **Non-UTF-8 files** - Encoding errors break display

### Low Risk Areas
7. **Command readability** - Mostly subjective, less likely to break
8. **Error message clarity** - Important but not workflow-blocking

---

## Next Steps

1. **Immediate:** Start Category 6 (Script Execution) - Most critical
2. **This week:** Complete Category 8 (Worktree Management)
3. **Next week:** Categories 5 & 7 (Artifacts + Diagnostics)
4. **Following week:** Categories 9 & 10 (Polish)

**Target:** 149/149 tests passing by end of month
