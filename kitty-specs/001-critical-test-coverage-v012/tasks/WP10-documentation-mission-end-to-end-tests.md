---
work_package_id: "WP10"
subtasks:
  - "T092"
  - "T093"
  - "T094"
  - "T095"
  - "T096"
  - "T097"
  - "T098"
  - "T099"
  - "T100"
  - "T101"
  - "T102"
  - "T103"
  - "T104"
  - "T105"
  - "T106"
title: "Documentation Mission End-to-End Tests"
phase: "Phase 2 - Documentation Mission Track"
lane: "doing"
assignee: ""
agent: "Codex"
shell_pid: "57727"
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-14T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 – Documentation Mission End-to-End Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` in the frontmatter.
- **Report progress**: Update Activity Log explaining changes made.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work needs changes.]*

---

## Objectives & Success Criteria

**Primary Objective**: Implement test_documentation_mission_end_to_end.py (15 tests) validating full documentation workflow: initial mode, gap-filling mode, framework detection, Divio classification, state persistence.

**Success Criteria**:
- ✅ 15/15 end-to-end tests implemented in test_documentation_mission_end_to_end.py
- ✅ `pytest tests/functional/test_documentation_mission_end_to_end.py -xvs` shows 15/15 PASSED
- ✅ Tests validate complete workflow: specify → plan → tasks → implement → review
- ✅ Tests validate initial mode (stores state in meta.json)
- ✅ Tests validate gap-filling mode (gap analysis, classification, coverage matrix)
- ✅ Tests validate framework detection (Sphinx, MkDocs, Docusaurus, etc.)
- ✅ Tests validate state persistence across git operations
- ✅ Tests validate migration installs documentation mission

**Why Important**: End-to-end tests validate complete user workflows. While distribution tests (WP08-WP09) ensure packaging works, E2E tests ensure the feature actually works for users end-to-end.

---

## Context & Constraints

### Related Documents
- **Gap Analysis**: ~/Code/spec-kitty/src/specify_cli/gap_analysis.py
- **Doc State**: ~/Code/spec-kitty/src/specify_cli/doc_state.py
- **Migration**: ~/Code/spec-kitty/src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (FR-002: Documentation Mission Testing)

### Feature Capabilities
- **Initial mode**: Creates new documentation from scratch
- **Gap-filling mode**: Analyzes existing docs, identifies gaps using Divio framework
- **Framework detection**: Sphinx, MkDocs, Docusaurus, Jekyll, Hugo, plain markdown
- **Divio classification**: Tutorial, how-to, reference, explanation (via heuristics)
- **Coverage matrix**: project_areas × divio_types grid showing gaps
- **State persistence**: meta.json stores documentation_state field

---

## Subtasks & Detailed Guidance

### Initial Mode Tests (T092-T093)

### Subtask T092 – Test initial mode workflow (specify → plan → tasks phases)

**Purpose**: Validate basic documentation workflow from scratch.

**Steps**:

1. Create test in tests/functional/test_documentation_mission_end_to_end.py:

```python
class TestInitialMode:
    """Validate initial mode documentation workflow."""

    def test_initial_mode_workflow(
        self,
        tmp_path,
        init_spec_kitty_project
    ):
        """
        Test: Initial mode workflow (specify → plan → tasks phases)

        Why: Validates users can create documentation project from scratch
        following guided workflow phases.

        Reference: gap_analysis.py, doc_state.py (initial mode logic)
        Related: Documentation mission workflow
        """
        # Initialize spec-kitty project
        project = init_spec_kitty_project("docs-initial-test")

        # Create documentation feature
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'api-docs',
             '--mission=documentation'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, (
            f"Feature creation with documentation mission failed\n"
            f"Error: {result.stderr}"
        )

        # Verify feature created with documentation mission structure
        feature_dir = project / 'kitty-specs' / 'api-docs'
        assert feature_dir.exists(), f"Feature directory should exist: {feature_dir}"

        # Check for documentation-specific artifacts
        # (Exact structure depends on mission templates)
        spec_file = feature_dir / 'spec.md'
        assert spec_file.exists(), "spec.md should be created"

        # Run specify phase
        result = subprocess.run(
            ['spec-kitty', 'specify', 'api-docs'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed (or prompt for input)
        # (Validation depends on implementation)
```

**Files**:
- Create: `tests/functional/test_documentation_mission_end_to_end.py` (~40 lines)

**Parallel?**: No - Foundation test

**Reference**: gap_analysis.py, doc_state.py (initial mode)

---

### Subtask T093 – Test initial mode stores state in meta.json

**Purpose**: Validate documentation_state field persisted in meta.json.

**Steps**:

1. Create test:

```python
def test_initial_mode_stores_state(
    self,
    tmp_path,
    init_spec_kitty_project
):
    """
    Test: Initial mode stores state in meta.json (documentation_state field)

    Why: State persistence enables resuming work across sessions. meta.json
    must survive git operations.

    Reference: doc_state.py (state storage in meta.json)
    Related: State persistence, meta.json structure
    """
    project = init_spec_kitty_project("docs-state-test")

    # Create documentation feature
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'api-docs', '--mission=documentation'],
        cwd=project, capture_output=True, text=True, timeout=30, check=True
    )

    # Check meta.json exists and has documentation_state
    meta_json = project / 'kitty-specs' / 'api-docs' / 'meta.json'

    if not meta_json.exists():
        pytest.skip("meta.json not created (implementation may differ)")

    import json
    meta = json.loads(meta_json.read_text())

    # Validate documentation_state field exists
    assert 'documentation_state' in meta or 'doc_state' in meta, (
        f"meta.json should have documentation_state field\n"
        f"Meta: {meta}"
    )

    # Validate state structure
    doc_state = meta.get('documentation_state') or meta.get('doc_state')
    assert isinstance(doc_state, dict), "documentation_state should be dict"

    # Check for expected fields (depends on implementation)
    # e.g., iteration_mode, divio_types, generators, etc.
```

**Files**:
- Update: `tests/functional/test_documentation_mission_end_to_end.py` (~35 lines)

**Parallel?**: Yes [P]

---

### Gap-Filling Mode Tests (T094-T099)

### Subtask T094 – Test gap-filling mode runs gap analysis automatically

**Purpose**: Validate gap analysis runs when existing docs detected.

**Steps**:

1. Create test:

```python
class TestGapFillingMode:
    """Validate gap-filling mode and gap analysis."""

    def test_gap_analysis_runs_automatically(
        self,
        tmp_path,
        init_spec_kitty_project
    ):
        """
        Test: Gap-filling mode runs gap analysis automatically

        Why: When docs/ directory exists, system should analyze existing docs
        and identify gaps rather than starting from scratch.

        Reference: gap_analysis.py (analyze_documentation_gaps function)
        Related: Existing documentation analysis
        """
        project = init_spec_kitty_project("docs-gap-test")

        # Create existing docs directory with some files
        docs_dir = project / 'docs'
        docs_dir.mkdir()

        (docs_dir / 'README.md').write_text("# API Documentation")
        (docs_dir / 'tutorial.md').write_text("# Getting Started Tutorial")

        # Create documentation feature (should detect existing docs)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'api-docs', '--mission=documentation'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0

        # Verify gap analysis artifacts created
        gap_analysis_file = project / 'kitty-specs' / 'api-docs' / 'gap-analysis.md'

        # May or may not exist depending on when gap analysis runs
        # Test validates it CAN run (via command if not automatic)

        # Run gap analysis explicitly if needed
        result = subprocess.run(
            ['spec-kitty', 'analyze-gaps', 'api-docs'],  # or similar command
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Validation depends on whether command exists
```

**Files**:
- Update: `tests/functional/test_documentation_mission_end_to_end.py` (~35 lines)

**Parallel?**: Yes [P]

---

### Subtasks T095-T099: Gap Analysis Features

**T095**: test_classification_by_divio_type (tutorial, how-to, reference, explanation)
**T096**: test_framework_detection (Sphinx via conf.py, MkDocs via mkdocs.yml, etc.)
**T097**: test_divio_classification_heuristics (keywords, file names, structure)
**T098**: test_coverage_matrix_generation (project_areas × divio_types grid)
**T099**: test_gap_prioritization (HIGH/MEDIUM/LOW based on missing types)

Pattern: Create projects with different doc structures, run gap analysis, validate detection/classification.

---

### State Persistence Tests (T100-T102)

### Subtask T100 – Test state persistence across git commit/checkout

**Purpose**: Validate meta.json survives git operations.

**Steps**:

1. Create test:

```python
class TestStatePersistence:
    """Validate state persistence across git operations."""

    def test_state_survives_git_operations(
        self,
        tmp_path,
        init_spec_kitty_project
    ):
        """
        Test: State persistence across git commit/checkout

        Why: Users must be able to commit work, switch branches, return without
        losing documentation state.

        Reference: doc_state.py (meta.json persistence)
        Related: Git integration, state recovery
        """
        project = init_spec_kitty_project("docs-persist-test")

        # Create docs feature
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'api-docs', '--mission=documentation'],
            cwd=project, capture_output=True, text=True, timeout=30, check=True
        )

        # Verify meta.json exists
        meta_json = project / 'kitty-specs' / 'api-docs' / 'meta.json'
        if not meta_json.exists():
            pytest.skip("meta.json not used")

        # Commit to git
        subprocess.run(['git', 'add', '.'], cwd=project, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add docs feature'], cwd=project, check=True)

        # Create new branch and switch
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=project, check=True)

        # Verify meta.json still exists and has state
        assert meta_json.exists(), "meta.json should survive branch switch"

        import json
        meta = json.loads(meta_json.read_text())
        assert 'documentation_state' in meta or 'doc_state' in meta, (
            "State should persist across git operations"
        )
```

**Files**:
- Update: `tests/functional/test_documentation_mission_end_to_end.py` (~35 lines)

**Parallel?**: Yes [P]

---

### Subtasks T101-T102: Resource Access

**T101**: test_divio_templates_accessible_during_workflow (templates load during implement)
**T102**: test_generators_configured_correctly (JSDoc, Sphinx, rustdoc configs created)

---

### Migration Tests (T103-T104)

### Subtask T103 – Test migration installs documentation mission

**Purpose**: Validate migration script installs mission to .kittify/missions/.

**Steps**:

1. Create test:

```python
class TestMigration:
    """Validate migration to documentation mission."""

    def test_migration_installs_mission(
        self,
        tmp_path,
        init_spec_kitty_project
    ):
        """
        Test: Migration installs documentation mission to .kittify/missions/

        Why: Upgrade from v0.11.0 to v0.12.0 requires migration to install
        documentation mission into project.

        Reference: upgrade/migrations/m_0_12_0_documentation_mission.py
        Related: Upgrade path, migration system
        """
        project = init_spec_kitty_project("docs-migrate-test")

        # Run migration (if migration system exists)
        result = subprocess.run(
            ['spec-kitty', 'upgrade', 'apply'],  # or similar command
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # May or may not have upgrade command
        if result.returncode != 0 and 'not found' in result.stderr:
            pytest.skip("Upgrade system not implemented")

        # Verify documentation mission installed
        mission_dir = project / '.kittify' / 'missions' / 'documentation'

        # May be in different location depending on implementation
        # Check for mission presence
```

**Files**:
- Update: `tests/functional/test_documentation_mission_end_to_end.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Subtask T104 – Test migration idempotent

**Purpose**: Validate migration safe to run multiple times.

---

### Validation Tests (T105-T106)

### Subtask T105 – Test backward compatibility

**Purpose**: Validate old features without documentation_state handled gracefully.

**Steps**:

1. Create test:

```python
class TestValidation:
    """Validate input validation and backward compatibility."""

    def test_backward_compatibility(
        self,
        tmp_path,
        init_spec_kitty_project
    ):
        """
        Test: Backward compatibility (features without documentation_state work)

        Why: v0.11.0 features don't have documentation_state field. System must
        handle gracefully without breaking.

        Reference: doc_state.py (handle missing state)
        Related: Backward compatibility, graceful degradation
        """
        project = init_spec_kitty_project("docs-compat-test")

        # Create regular feature (not documentation mission)
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'regular-feature', '--json'],
            cwd=project, capture_output=True, text=True, timeout=30, check=True
        )

        # Try running documentation commands on regular feature (should handle gracefully)
        result = subprocess.run(
            ['spec-kitty', 'analyze-gaps', 'regular-feature'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should either skip (not doc mission) or handle gracefully (not crash)
        # Exact behavior depends on implementation
```

**Files**:
- Update: `tests/functional/test_documentation_mission_end_to_end.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Subtask T106 – Test state validation

**Purpose**: Validate invalid state rejected with clear errors.

---

## Test Strategy

**Test File**: `tests/functional/test_documentation_mission_end_to_end.py`

**Test Classes**:
- `TestInitialMode` (T092-T093): 2 tests
- `TestGapFillingMode` (T094-T099): 6 tests
- `TestStatePersistence` (T100-T102): 3 tests
- `TestMigration` (T103-T104): 2 tests
- `TestValidation` (T105-T106): 2 tests

**Execution**:
```bash
pytest tests/functional/test_documentation_mission_end_to_end.py -xvs
```

---

## Risks & Mitigations

**Risk 1: Workflow breaks at any phase**
- **Likelihood**: MEDIUM
- **Impact**: HIGH (feature unusable)
- **Mitigation**: Tests catch phase transitions. Fix workflow logic.

**Risk 2: State persistence fails**
- **Likelihood**: LOW
- **Impact**: HIGH (users lose progress)
- **Mitigation**: Validate meta.json survives git operations.

---

## Definition of Done Checklist

- [ ] test_documentation_mission_end_to_end.py created with 5 test classes
- [ ] All 15 tests implemented (T092-T106)
- [ ] Tests validate complete workflow (specify → plan → tasks)
- [ ] Tests validate gap-filling mode (analysis, classification)
- [ ] Tests validate state persistence (meta.json survives git)
- [ ] Tests executed: 15/15 PASSED

---

## Review Guidance

**For Reviewer**:

1. **Validate workflow coverage**:
   - Tests cover initial mode and gap-filling mode
   - Tests validate state persistence

2. **Run tests**:
   ```bash
   pytest tests/functional/test_documentation_mission_end_to_end.py -xvs
   ```

**Key Questions**:
- Do tests validate complete user workflows?
- Would tests catch workflow phase bugs?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T12:23:40Z – Codex – shell_pid=57727 – lane=doing – Started implementation via workflow command
