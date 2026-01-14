---
work_package_id: "WP09"
subtasks:
  - "T072"
  - "T073"
  - "T074"
  - "T075"
  - "T076"
  - "T077"
  - "T078"
  - "T079"
  - "T080"
  - "T081"
  - "T082"
  - "T083"
  - "T084"
  - "T085"
  - "T086"
  - "T087"
  - "T088"
  - "T089"
  - "T090"
  - "T091"
title: "Documentation Mission Distribution Tests"
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

# Work Package Prompt: WP09 – Documentation Mission Distribution Tests

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

**Primary Objective**: Implement test_documentation_mission_distribution.py (20 tests) validating documentation mission loads from pip package, all templates accessible, mission registry works.

**Success Criteria**:
- ✅ 20/20 distribution tests implemented in test_documentation_mission_distribution.py
- ✅ `pytest tests/distribution/test_documentation_mission_distribution.py -xvs` shows 20/20 PASSED
- ✅ ALL tests use clean_environment fixture (no SPEC_KITTY_TEMPLATE_ROOT)
- ✅ Tests validate mission.yaml loads from package via importlib
- ✅ Tests validate all 5 command templates accessible (specify, plan, tasks, implement, review)
- ✅ Tests validate 4 Divio templates accessible
- ✅ Tests validate mission registered and retrievable
- ✅ Tests would catch Issues #62-64 pattern (mission missing from package)

**Why Critical**: Documentation mission is a MAJOR v0.12.0 feature. If mission.yaml or templates not bundled in package, feature completely broken for PyPI users. This is the same failure pattern as Issues #62-64 - MUST validate distribution.

---

## Context & Constraints

### Related Documents
- **Mission Config**: ~/Code/spec-kitty/src/specify_cli/missions/documentation/mission.yaml
- **Command Templates**: ~/Code/spec-kitty/src/specify_cli/missions/documentation/command-templates/*.md
- **Divio Templates**: ~/Code/spec-kitty/src/specify_cli/missions/documentation/divio-templates/
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (FR-002: Documentation Mission Distribution Testing)

### Mission Structure
- **Mission file**: missions/documentation/mission.yaml (name, version, phases, artifacts, conventions)
- **Command templates**: 5 templates (specify.md, plan.md, tasks.md, implement.md, review.md)
- **Divio templates**: 4 templates (tutorial.md, howto.md, reference.md, explanation.md)
- **Workflow phases**: 6 phases (discover, audit, design, generate, validate, publish)

### Critical Requirements
- **NO SPEC_KITTY_TEMPLATE_ROOT**: Tests must simulate PyPI users
- **Package loading**: Via importlib.resources, not file system paths
- **Loud failures**: "DO NOT SHIP v0.12.0" if mission not in package

---

## Subtasks & Detailed Guidance

### Mission Loading Tests (T072-T078)

### Subtask T072 – Test documentation mission loads from pip package

**Purpose**: Validate mission can be loaded without SPEC_KITTY_TEMPLATE_ROOT.

**Steps**:

1. Create test in tests/distribution/test_documentation_mission_distribution.py:

```python
class TestMissionLoading:
    """Validate documentation mission loads from pip package."""

    @pytest.fixture
    def clean_environment(self):
        """Remove all development env vars to simulate PyPI user."""
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)
        to_remove = [k for k in env.keys()
                     if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
        for key in to_remove:
            env.pop(key, None)
        return env

    def test_documentation_mission_loads_from_package(
        self,
        clean_environment
    ):
        """
        Test: Documentation mission loads from pip package (no SPEC_KITTY_TEMPLATE_ROOT)

        Why: This would catch Issues #62-64 pattern. If mission files not bundled
        in package, PyPI users experience 100% failure while local tests pass.

        Reference: missions/documentation/mission.yaml
        Related: Package distribution, mission registry
        """
        # Validate clean environment
        assert 'SPEC_KITTY_TEMPLATE_ROOT' not in os.environ, (
            "Test setup error: Must simulate PyPI user environment"
        )

        # Try importing mission loader
        try:
            from specify_cli.missions import get_mission_by_name
        except ImportError as e:
            pytest.fail(
                f"CRITICAL: Cannot import mission loader from package\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0 - packaging broken"
            )

        # Try loading documentation mission
        try:
            mission = get_mission_by_name("documentation")
        except FileNotFoundError as e:
            pytest.fail(
                f"CRITICAL: Documentation mission not found in package\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0 - mission.yaml not bundled\n"
                f"Fix: Update pyproject.toml package-data"
            )
        except Exception as e:
            pytest.fail(
                f"CRITICAL: Documentation mission loading failed\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0"
            )

        # Validate mission object returned
        assert mission is not None, "Mission should be loaded"
        assert hasattr(mission, 'name'), "Mission should have name attribute"
```

**Files**:
- Create: `tests/distribution/test_documentation_mission_distribution.py` (~50 lines)

**Parallel?**: No - Foundation test

**Reference**: missions/documentation/mission.yaml, mission registry code

---

### Subtask T073 – Test mission.yaml accessible and parses correctly

**Purpose**: Validate mission.yaml file loads and parses as valid YAML.

**Steps**:

1. Create test:

```python
def test_mission_yaml_accessible_and_valid(
    self,
    clean_environment
):
    """
    Test: mission.yaml accessible and parses correctly

    Why: Mission file must be bundled in package and parseable. Invalid YAML
    or missing file breaks entire documentation mission.

    Reference: missions/documentation/mission.yaml
    Related: YAML validation, package-data
    """
    from specify_cli.missions import get_mission_by_name

    mission = get_mission_by_name("documentation")

    # Validate mission has expected structure (from parsed YAML)
    # Check for required top-level fields
    assert hasattr(mission, 'name') or 'name' in mission, "Mission should have name"
    assert hasattr(mission, 'version') or 'version' in mission, "Mission should have version"
    assert hasattr(mission, 'phases') or 'phases' in mission, "Mission should have phases"

    # If mission is dict (raw YAML), validate structure
    if isinstance(mission, dict):
        assert 'name' in mission, "YAML should have name field"
        assert 'version' in mission, "YAML should have version field"
        assert 'phases' in mission, "YAML should have phases field"
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~25 lines)

**Parallel?**: Yes [P]

---

### Subtask T074 – Test mission name "Documentation Kitty" version 1.0.0

**Purpose**: Validate mission metadata correct.

**Steps**:

1. Create test:

```python
def test_mission_metadata_correct(
    self,
    clean_environment
):
    """
    Test: Mission name "Documentation Kitty" version 1.0.0

    Why: Validates mission identity and version for registry lookup.

    Reference: missions/documentation/mission.yaml (name and version fields)
    """
    from specify_cli.missions import get_mission_by_name

    mission = get_mission_by_name("documentation")

    # Extract name and version (handling dict or object)
    if isinstance(mission, dict):
        name = mission.get('name')
        version = mission.get('version')
    else:
        name = getattr(mission, 'name', None)
        version = getattr(mission, 'version', None)

    assert name == "Documentation Kitty", (
        f"Expected mission name 'Documentation Kitty', got '{name}'"
    )

    assert version == "1.0.0", (
        f"Expected version '1.0.0', got '{version}'"
    )
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~20 lines)

**Parallel?**: Yes [P]

---

### Subtasks T075-T078: Mission Structure Validation

**T075**: Test 6 workflow phases in correct order (discover, audit, design, generate, validate, publish)
**T076**: Test required artifacts defined (spec.md, plan.md, tasks.md, gap-analysis.md)
**T077**: Test optional artifacts defined (divio-templates/, generator-configs/, audit-report.md, research.md, release.md)
**T078**: Test workspace conventions correct (workspace="docs/", deliverables="docs/output/", documentation="docs/")

Pattern: Extract from mission object/dict, validate values match spec.

---

### Command Template Tests (T079-T084)

### Subtask T079 – Test specify command template accessible and non-empty

**Purpose**: Validate specify.md template loads from package.

**Steps**:

1. Create test:

```python
class TestCommandTemplates:
    """Validate command templates load from pip package."""

    @pytest.fixture
    def clean_environment(self):
        # Same as above
        ...

    def test_specify_template_accessible(
        self,
        clean_environment
    ):
        """
        Test: specify command template accessible and non-empty

        Why: Command templates guide users through workflow. If missing from
        package, commands fail for PyPI users.

        Reference: missions/documentation/command-templates/specify.md
        """
        from specify_cli.missions import get_mission_by_name

        mission = get_mission_by_name("documentation")

        # Get specify template (method depends on implementation)
        try:
            specify_template = mission.get_template('specify')
            # OR: mission.templates['specify']
            # OR: mission.load_template('specify.md')
        except Exception as e:
            pytest.fail(
                f"CRITICAL: specify template not accessible\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0 - template not bundled"
            )

        # Validate template content
        assert specify_template, "Template should not be empty"
        assert len(specify_template) > 100, "Template should have substantial content"
        assert 'specify' in specify_template.lower() or 'documentation' in specify_template.lower(), (
            "Template should be relevant to documentation mission"
        )
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Subtasks T080-T083: Remaining Command Templates

**T080**: test_plan_template_accessible
**T081**: test_tasks_template_accessible
**T082**: test_implement_template_accessible
**T083**: test_review_template_accessible

Pattern: Same as T079, just different template name.

---

### Subtask T084 – Test all templates have expected structure

**Purpose**: Validate templates have frontmatter and sections.

**Steps**:

1. Create test:

```python
def test_templates_have_expected_structure(
    self,
    clean_environment
):
    """
    Test: All templates have expected structure (frontmatter, sections)

    Why: Templates must be valid markdown with YAML frontmatter. Malformed
    templates cause parsing errors for users.

    Reference: command-templates/*.md format
    """
    from specify_cli.missions import get_mission_by_name

    mission = get_mission_by_name("documentation")

    template_names = ['specify', 'plan', 'tasks', 'implement', 'review']

    for template_name in template_names:
        template = mission.get_template(template_name)

        # Check for YAML frontmatter (starts with ---)
        assert template.startswith('---'), (
            f"{template_name} template should start with YAML frontmatter\n"
            f"Content preview: {template[:100]}"
        )

        # Check for markdown headings (# or ##)
        assert '#' in template, f"{template_name} should have markdown headings"

        # Check for reasonable length (not just placeholder)
        assert len(template) > 200, (
            f"{template_name} template suspiciously short: {len(template)} chars"
        )
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Template Packaging Tests (T085-T086)

### Subtask T085 – Test templates load via importlib.resources

**Purpose**: Validate templates use package loading, not file paths.

**Steps**:

1. Create test:

```python
class TestTemplatePackaging:
    """Validate template packaging and loading mechanism."""

    @pytest.fixture
    def clean_environment(self):
        ...

    def test_templates_load_via_importlib(
        self,
        clean_environment
    ):
        """
        Test: Templates load via importlib.resources (from package, not local repo)

        Why: This is the CORRECT way to load packaged resources. Using file paths
        (like SPEC_KITTY_TEMPLATE_ROOT) breaks for PyPI users.

        Reference: Mission loading code (should use importlib.resources)
        """
        # This test is more about code review than runtime behavior
        # But we can validate templates load without file system access

        from specify_cli.missions import get_mission_by_name

        mission = get_mission_by_name("documentation")

        # Validate mission loaded (implies importlib worked)
        assert mission is not None

        # Validate can load template without SPEC_KITTY_TEMPLATE_ROOT
        template = mission.get_template('specify')
        assert template is not None
        assert len(template) > 0

        # If implementation exposes template source, validate it's from package
        # (This part depends on implementation details)
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~25 lines)

**Parallel?**: Yes [P]

---

### Subtask T086 – Test no template path leakage

**Purpose**: Validate templates don't reference local repo paths.

**Steps**:

1. Create test:

```python
def test_no_template_path_leakage(
    self,
    clean_environment
):
    """
    Test: No template path leakage (no references to local ~/Code/spec-kitty paths)

    Why: Templates should be portable. Must not include development paths.

    Reference: Template content validation
    """
    from specify_cli.missions import get_mission_by_name

    mission = get_mission_by_name("documentation")

    template_names = ['specify', 'plan', 'tasks', 'implement', 'review']

    for template_name in template_names:
        template = mission.get_template(template_name)

        # Check for path leakage
        forbidden_patterns = [
            '/Users/',
            '/home/',
            'C:\\',
            str(Path.home()),
            'spec-kitty',
            'SPEC_KITTY_TEMPLATE_ROOT',
        ]

        for pattern in forbidden_patterns:
            assert pattern not in template, (
                f"{template_name} template contains forbidden path: {pattern}\n"
                f"Templates should be portable, not reference local paths"
            )
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~25 lines)

**Parallel?**: Yes [P]

---

### Mission Registry Tests (T087-T091)

### Subtask T087 – Test mission registered in mission registry

**Purpose**: Validate mission appears in registry after installation.

**Steps**:

1. Create test:

```python
class TestMissionRegistry:
    """Validate mission registry and retrieval."""

    @pytest.fixture
    def clean_environment(self):
        ...

    def test_mission_registered_in_registry(
        self,
        clean_environment
    ):
        """
        Test: Mission registered in mission registry after installation

        Why: Mission registry enables `spec-kitty list-missions` and lookup.
        If not registered, mission invisible to users.

        Reference: Mission registry code
        """
        try:
            from specify_cli.missions import list_missions
        except ImportError:
            pytest.skip("list_missions not implemented")

        missions = list_missions()

        # Should be list or dict of missions
        assert missions is not None
        assert len(missions) > 0, "Registry should have at least documentation mission"

        # Find documentation mission
        if isinstance(missions, list):
            mission_names = [m.get('name') or m.name for m in missions]
        else:
            mission_names = list(missions.keys())

        assert 'documentation' in mission_names or 'Documentation Kitty' in mission_names, (
            f"Documentation mission not in registry\n"
            f"Registry: {mission_names}"
        )
```

**Files**:
- Update: `tests/distribution/test_documentation_mission_distribution.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Subtasks T088-T091: Remaining Registry Tests

**T088**: test_mission_metadata_correct (name, domain, version)
**T089**: test_get_mission_by_name_returns_valid_mission (retrieval works)
**T090**: test_mission_validation_passes_pydantic (if using Pydantic models)
**T091**: test_all_divio_templates_present (tutorial, howto, reference, explanation)

Pattern: Registry queries, metadata validation, Divio template loading.

---

## Test Strategy

**Test File**: `tests/distribution/test_documentation_mission_distribution.py`

**Test Classes**:
- `TestMissionLoading` (T072-T078): 7 tests - mission.yaml loading and structure
- `TestCommandTemplates` (T079-T084): 6 tests - command template accessibility
- `TestTemplatePackaging` (T085-T086): 2 tests - importlib loading and path leakage
- `TestMissionRegistry` (T087-T091): 5 tests - registry and Divio templates

**Execution**:
```bash
pytest tests/distribution/test_documentation_mission_distribution.py -xvs
```

**CRITICAL Requirements**:
- ALL tests use clean_environment
- NO SPEC_KITTY_TEMPLATE_ROOT
- Loud failures if mission not in package

---

## Risks & Mitigations

**Risk 1: Mission files not bundled in package**
- **Likelihood**: MEDIUM
- **Impact**: CRITICAL (feature completely broken for PyPI users)
- **Mitigation**: Tests catch this. Fix pyproject.toml package-data.

**Risk 2: Templates bundled but importlib loading broken**
- **Likelihood**: LOW
- **Impact**: CRITICAL
- **Mitigation**: Tests validate importlib.resources works.

---

## Definition of Done Checklist

- [ ] test_documentation_mission_distribution.py created with 4 test classes
- [ ] All 20 tests implemented (T072-T091)
- [ ] ALL tests use clean_environment fixture
- [ ] Tests executed: 20/20 PASSED
- [ ] Mission loading validated (from package)
- [ ] All templates validated (command + Divio)
- [ ] Registry validated (lookup works)

---

## Review Guidance

**For Reviewer**:

1. **Validate clean environment**:
   - ALL tests use clean_environment
   - No SPEC_KITTY_TEMPLATE_ROOT

2. **Run tests**:
   ```bash
   pytest tests/distribution/test_documentation_mission_distribution.py -xvs
   ```

**Key Questions**:
- Do tests simulate PyPI user environment?
- Would tests catch mission packaging bugs?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T12:18:00Z – Codex – shell_pid=57727 – lane=doing – Started implementation via workflow command
