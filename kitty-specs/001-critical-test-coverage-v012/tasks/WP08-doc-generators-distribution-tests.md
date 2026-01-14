---
work_package_id: "WP08"
subtasks:
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
  - "T067"
  - "T068"
  - "T069"
  - "T070"
  - "T071"
title: "Doc Generators Distribution Tests"
phase: "Phase 2 - Documentation Mission Track (Risk-First)"
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

# Work Package Prompt: WP08 – Doc Generators Distribution Tests

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

**Primary Objective**: Implement test_doc_generators_distribution.py (15 tests) validating JSDoc, Sphinx, and rustdoc generators load from pip package without SPEC_KITTY_TEMPLATE_ROOT.

**Success Criteria**:
- ✅ 15/15 distribution tests implemented in test_doc_generators_distribution.py
- ✅ `pytest tests/distribution/test_doc_generators_distribution.py -xvs` shows 15/15 PASSED
- ✅ ALL tests use clean_environment fixture (explicitly remove SPEC_KITTY_TEMPLATE_ROOT)
- ✅ Tests validate generators accessible via importlib (from package, not local repo)
- ✅ Tests would catch Issues #62-64 pattern (local works, package fails)
- ✅ Each test has clear docstring explaining distribution testing rationale
- ✅ All assertions include "DO NOT SHIP" warnings if packaging broken

**Why Risk-First**: This is THE test that would have caught Issues #62-64. If templates not bundled in package, generators fail for 100% of PyPI users despite local tests passing. Distribution testing is critical - we MUST validate what users experience.

---

## Context & Constraints

### Related Documents
- **Implementation Reference**: ~/Code/spec-kitty/src/specify_cli/doc_generators.py (JSDocGenerator, SphinxGenerator, RustdocGenerator classes)
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (FR-002, FR-003: Distribution testing requirements)
- **Issues #62-64**: All 323 tests passed locally (used SPEC_KITTY_TEMPLATE_ROOT), 100% PyPI users failed (templates not in package)

### Implementation Code Behavior
- **JSDocGenerator**: Detects JavaScript/TypeScript (package.json, .js/.ts files), creates jsdoc.json config
- **SphinxGenerator**: Detects Python (setup.py, pyproject.toml, .py files), creates conf.py config
- **RustdocGenerator**: Detects Rust (Cargo.toml, .rs files), creates rustdoc-config.md instructions
- **Template loading**: Should use importlib.resources to load from package, not read from local repo

### Critical Distribution Testing Requirement
- **MUST NOT set SPEC_KITTY_TEMPLATE_ROOT**: This env var bypasses package, uses local repo templates
- **MUST use clean_environment fixture**: Explicitly removes all SPEC_KITTY_* env vars
- **MUST test from package**: Simulates exact PyPI user experience
- **MUST fail if templates missing**: Tests should LOUDLY fail with "DO NOT SHIP v0.12.0" if packaging broken

---

## Subtasks & Detailed Guidance

Due to the size of this work package (15 subtasks with ~480 lines estimated), I'll provide comprehensive guidance for representative tests, with patterns to follow for remaining tests.

### Generator-Specific Tests (T057-T065)

### Subtask T057 – Test JSDoc generator detects JavaScript/TypeScript projects

**Purpose**: Validate JSDoc generator's project detection logic works when loaded from pip package.

**Steps**:

1. Create test in tests/distribution/test_doc_generators_distribution.py:

```python
class TestJSDocGenerator:
    """Validate JSDoc generator loads from pip package and detects projects correctly."""

    @pytest.fixture
    def clean_environment(self):
        """
        Clean environment simulating PyPI user (NO development overrides).

        CRITICAL: This fixture is the difference between catching Issues #62-64
        and shipping broken packages. ALL distribution tests must use this.
        """
        env = os.environ.copy()
        env.pop('SPEC_KITTY_TEMPLATE_ROOT', None)
        env.pop('SPEC_KITTY_REPO', None)
        # Remove all SPEC_KITTY_* vars except API key
        to_remove = [k for k in env.keys()
                     if k.startswith('SPEC_KITTY_') and k not in ['SPEC_KITTY_API_KEY']]
        for key in to_remove:
            env.pop(key, None)
        return env

    def test_jsdoc_detects_javascript_projects(
        self,
        tmp_path,
        clean_environment
    ):
        """
        Test: JSDoc generator detects JavaScript/TypeScript projects from package

        Why: This test would catch Issues #62-64 pattern. If JSDoc generator
        tries to load templates from local repo (via SPEC_KITTY_TEMPLATE_ROOT),
        it fails for PyPI users who don't have that env var or local repo.

        Reference: doc_generators.py (JSDocGenerator.detect method)
        Related: Package distribution validation, template packaging
        """
        # 1. Create JavaScript project structure
        project_dir = tmp_path / "js-project"
        project_dir.mkdir()

        # Create package.json (JavaScript indicator)
        package_json = project_dir / "package.json"
        package_json.write_text('{"name": "test-project", "version": "1.0.0"}')

        # Create .js files
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.js").write_text("console.log('test');")

        # 2. Import JSDocGenerator (should work from package, not local)
        try:
            from specify_cli.doc_generators import JSDocGenerator
        except ImportError as e:
            pytest.fail(
                f"CRITICAL: Cannot import JSDocGenerator from installed package\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0 - packaging broken\n"
                f"This is the EXACT failure pattern from Issues #62-64"
            )

        # 3. Instantiate generator (should not require SPEC_KITTY_TEMPLATE_ROOT)
        try:
            generator = JSDocGenerator(project_dir)
        except Exception as e:
            pytest.fail(
                f"CRITICAL: JSDocGenerator instantiation failed without SPEC_KITTY_TEMPLATE_ROOT\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0\n"
                f"PyPI users will experience 100% failure (no env var set)"
            )

        # 4. Validate detection works
        detected = generator.detect()

        assert detected is True, (
            f"JSDoc generator should detect JavaScript project\n"
            f"Project: {project_dir}\n"
            f"Files: package.json, src/index.js\n"
            f"If detection fails, logic broken or requires local repo - BUG"
        )

        # 5. Validate detection logic (via actual files)
        # Should find package.json
        assert package_json.exists(), "Setup: package.json should exist"

        # Detection should work without SPEC_KITTY_TEMPLATE_ROOT
        assert 'SPEC_KITTY_TEMPLATE_ROOT' not in os.environ, (
            f"Test setup error: SPEC_KITTY_TEMPLATE_ROOT should not be set\n"
            f"This test MUST simulate PyPI user environment"
        )
```

**Files**:
- Create: `tests/distribution/test_doc_generators_distribution.py` (new file, ~60 lines for first test)

**Parallel?**: Yes [P] with T058-T071 (different generators/aspects)

**Reference**: doc_generators.py (JSDocGenerator.detect method)

---

### Subtask T058 – Test JSDoc configuration template accessible from pip package

**Purpose**: Validate JSDoc template loads from packaged files, not local repo.

**Steps**:

1. Create test:

```python
def test_jsdoc_template_accessible_from_package(
    self,
    tmp_path,
    clean_environment
):
    """
    Test: JSDoc configuration template accessible from pip package

    Why: THIS IS THE BUG that caused Issues #62-64. Templates must be
    bundled in pip package and loadable via importlib.resources.
    If templates missing from package, this test MUST fail loudly.

    Reference: doc_generators.py (JSDocGenerator template loading)
    Related: pyproject.toml package-data configuration
    """
    from specify_cli.doc_generators import JSDocGenerator

    project_dir = tmp_path / "js-project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text('{"name": "test"}')

    generator = JSDocGenerator(project_dir)

    # Attempt to load template
    try:
        template_content = generator.get_config_template()
        # OR if method different: template_content = generator._load_template()
    except FileNotFoundError as e:
        pytest.fail(
            f"CRITICAL: JSDoc template not found in pip package\n"
            f"Error: {e}\n"
            f"DO NOT SHIP v0.12.0 - this is Issues #62-64 repeat\n"
            f"Fix: Update pyproject.toml [tool.setuptools.package-data]\n"
            f"Add: 'specify_cli': ['templates/**/*', 'missions/**/*']"
        )
    except Exception as e:
        pytest.fail(
            f"CRITICAL: JSDoc template loading failed\n"
            f"Error: {e}\n"
            f"Template should load via importlib.resources from package"
        )

    # Validate template content non-empty
    assert template_content, "Template should have content"
    assert len(template_content) > 10, "Template should not be placeholder"

    # Validate template is actual JSDoc config (not just any file)
    # Check for JSDoc-specific content
    assert 'jsdoc' in template_content.lower() or 'plugins' in template_content.lower(), (
        f"Template should be JSDoc configuration\n"
        f"Content preview: {template_content[:200]}"
    )
```

**Files**:
- Update: `tests/distribution/test_doc_generators_distribution.py` (~35 lines)

**Parallel?**: Yes [P]

**Reference**: doc_generators.py (template loading via importlib.resources)

---

### Subtask T059 – Test JSDoc creates valid jsdoc.json configuration

**Purpose**: Validate generated JSDoc config is valid and usable.

**Steps**:

1. Create test:

```python
def test_jsdoc_creates_valid_config(
    self,
    tmp_path,
    clean_environment
):
    """
    Test: JSDoc creates valid jsdoc.json configuration from package

    Why: Not only must template load from package, but generated config must
    be valid and usable. Validates end-to-end generator functionality.

    Reference: doc_generators.py (JSDocGenerator.generate_config)
    Related: JSDoc configuration format
    """
    from specify_cli.doc_generators import JSDocGenerator

    project_dir = tmp_path / "js-project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text('{"name": "test"}')
    (project_dir / "src").mkdir()
    (project_dir / "src" / "index.js").write_text("// code")

    generator = JSDocGenerator(project_dir)

    # Generate configuration
    try:
        config_path = generator.generate_config()
        # OR: generator.generate() if method name different
    except Exception as e:
        pytest.fail(
            f"Config generation failed\n"
            f"Error: {e}\n"
            f"Generator should work without SPEC_KITTY_TEMPLATE_ROOT"
        )

    # Validate config file created
    assert config_path.exists(), f"Config file should be created: {config_path}"

    # Validate config is valid JSON
    import json
    try:
        config_data = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        pytest.fail(f"Generated config is not valid JSON: {e}")

    # Validate config has expected JSDoc fields
    # (specific fields depend on template structure)
    assert isinstance(config_data, dict), "Config should be JSON object"
```

**Files**:
- Update: `tests/distribution/test_doc_generators_distribution.py` (~35 lines)

**Parallel?**: Yes [P]

---

### Subtasks T060-T062: Sphinx Generator Tests (Same Pattern)

Follow same pattern as T057-T059 for SphinxGenerator:

**T060**: `test_sphinx_detects_python_projects` - Look for setup.py, pyproject.toml, .py files
**T061**: `test_sphinx_template_accessible_from_package` - Validate conf.py template loads
**T062**: `test_sphinx_creates_valid_conf_py` - Validate generated conf.py is valid Python

**Key differences**:
- Detection: setup.py, pyproject.toml, src/**/*.py
- Template: conf.py (Python file, not JSON)
- Validation: Try to import/exec conf.py to validate Python syntax

---

### Subtasks T063-T065: Rustdoc Generator Tests (Same Pattern)

**T063**: `test_rustdoc_detects_rust_projects` - Look for Cargo.toml, .rs files
**T064**: `test_rustdoc_template_accessible_from_package` - Validate rustdoc-config.md loads
**T065**: `test_rustdoc_creates_config_instructions` - Validate generated markdown instructions

---

### Integration Tests (T066-T071)

### Subtask T066 – Test all generators accessible via importlib

**Purpose**: Validate all 3 generators can be imported from package.

**Steps**:

1. Create test:

```python
class TestGeneratorIntegration:
    """Validate generator integration and package accessibility."""

    @pytest.fixture
    def clean_environment(self):
        # Same as above
        ...

    def test_all_generators_importable_from_package(
        self,
        clean_environment
    ):
        """
        Test: All generators accessible via importlib (no SPEC_KITTY_TEMPLATE_ROOT)

        Why: Validates all generators properly packaged and importable by PyPI users.

        Reference: doc_generators.py (all generator classes)
        Related: Package __init__.py exports
        """
        # Try importing all generators
        try:
            from specify_cli.doc_generators import (
                JSDocGenerator,
                SphinxGenerator,
                RustdocGenerator
            )
        except ImportError as e:
            pytest.fail(
                f"CRITICAL: Cannot import generators from package\n"
                f"Error: {e}\n"
                f"DO NOT SHIP v0.12.0"
            )

        # Validate all are classes (not None or placeholder)
        assert JSDocGenerator is not None
        assert SphinxGenerator is not None
        assert RustdocGenerator is not None

        # Validate they are actual classes (not modules)
        import inspect
        assert inspect.isclass(JSDocGenerator), "JSDocGenerator should be a class"
        assert inspect.isclass(SphinxGenerator), "SphinxGenerator should be a class"
        assert inspect.isclass(RustdocGenerator), "RustdocGenerator should be a class"
```

**Files**:
- Update: `tests/distribution/test_doc_generators_distribution.py` (~30 lines)

**Parallel?**: Yes [P]

---

### Subtask T067 – Test generator detection works without development env vars

**Purpose**: Validate detection logic doesn't rely on SPEC_KITTY_* environment variables.

(Test similar to T066 but focuses on detection methods, ensure no env var dependencies)

---

### Subtask T068 – Test generator configs use relative paths

**Purpose**: Validate generated configs don't leak local repo paths.

```python
def test_no_absolute_path_leakage_in_configs(
    self,
    tmp_path,
    clean_environment
):
    """
    Test: Generator configs use relative paths (no local repo references)

    Why: Generated configs should be portable. Must not include paths to
    local ~/Code/spec-kitty or SPEC_KITTY_TEMPLATE_ROOT.

    Reference: doc_generators.py (template rendering)
    Related: Path leakage prevention
    """
    from specify_cli.doc_generators import JSDocGenerator

    project_dir = tmp_path / "js-project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text('{"name": "test"}')

    generator = JSDocGenerator(project_dir)
    config_path = generator.generate_config()

    config_content = config_path.read_text()

    # Check for absolute path leakage
    forbidden_patterns = [
        '/Users/',  # macOS absolute paths
        '/home/',   # Linux absolute paths
        'C:\\',     # Windows absolute paths
        str(Path.home()),  # User home directory
        'spec-kitty',  # Local repo name
    ]

    for pattern in forbidden_patterns:
        assert pattern not in config_content, (
            f"Config contains absolute path: {pattern}\n"
            f"Config preview: {config_content[:500]}\n"
            f"Paths should be relative to project directory"
        )
```

---

### Subtask T069 – Test multi-language project detection

**Purpose**: Validate project with both JS and Python detected correctly.

---

### Subtask T070 – Test generator error handling

**Purpose**: Validate clear error messages when templates missing or corrupted.

---

### Subtask T071 – Test no template path leakage

**Purpose**: Validate templates don't include development paths in output.

---

## Test Strategy

**Test File**: `tests/distribution/test_doc_generators_distribution.py`

**Test Classes**:
- `TestJSDocGenerator` (T057-T059): 3 tests
- `TestSphinxGenerator` (T060-T062): 3 tests
- `TestRustdocGenerator` (T063-T065): 3 tests
- `TestGeneratorIntegration` (T066-T071): 6 tests

**Execution**:
```bash
pytest tests/distribution/test_doc_generators_distribution.py -xvs
```

**CRITICAL Distribution Testing Requirements**:
1. ALL tests MUST use clean_environment fixture
2. NO test should set SPEC_KITTY_TEMPLATE_ROOT
3. Tests MUST fail loudly if templates not in package
4. Failure messages MUST say "DO NOT SHIP v0.12.0"

---

## Risks & Mitigations

**Risk 1: Templates not bundled in package (Issues #62-64 repeat)**
- **Likelihood**: MEDIUM (common packaging mistake)
- **Impact**: CRITICAL (100% PyPI user failure)
- **Mitigation**: This is EXACTLY what tests catch. Tests MUST fail loudly. Fix pyproject.toml package-data.

**Risk 2: Tests accidentally use SPEC_KITTY_TEMPLATE_ROOT (false positive)**
- **Likelihood**: MEDIUM (easy mistake)
- **Impact**: CRITICAL (tests pass but package broken)
- **Mitigation**: clean_environment fixture explicitly removes var. Validate in tests.

**Risk 3: Generator code depends on local repo structure**
- **Likelihood**: LOW
- **Impact**: HIGH (generators fail for PyPI users)
- **Mitigation**: Tests import from package, not local code. Would fail if dependency exists.

---

## Definition of Done Checklist

- [ ] test_doc_generators_distribution.py created with 4 test classes
- [ ] All 15 tests implemented (T057-T071)
- [ ] ALL tests use clean_environment fixture
- [ ] Tests validated: NO SPEC_KITTY_TEMPLATE_ROOT set during execution
- [ ] Tests executed: `pytest tests/distribution/test_doc_generators_distribution.py -xvs`
- [ ] Test results: 15/15 PASSED
- [ ] If ANY test fails: Packaging bug documented, pyproject.toml fixed, re-run tests
- [ ] All tests have "DO NOT SHIP" warnings in failure messages
- [ ] Tests would catch Issues #62-64 pattern

---

## Review Guidance

**For Reviewer**:

1. **CRITICAL: Validate clean environment**:
   - ALL tests use clean_environment fixture
   - Fixture explicitly removes SPEC_KITTY_TEMPLATE_ROOT
   - No test sets SPEC_KITTY_* vars

2. **Validate test would catch packaging bugs**:
   - Tests import from specify_cli package (not local)
   - Tests load templates via importlib.resources
   - Failure messages say "DO NOT SHIP v0.12.0"

3. **Run tests**:
   ```bash
   # From spec-kitty-test repo
   pytest tests/distribution/test_doc_generators_distribution.py -xvs
   ```
   - Should see 15/15 PASSED
   - If failures: CRITICAL packaging bug, fix before shipping

**Key Questions**:
- Do ALL tests use clean_environment fixture?
- Would tests catch Issues #62-64 (templates missing from package)?
- Do failure messages clearly say "DO NOT SHIP"?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T12:12:06Z – Codex – shell_pid=57727 – lane=doing – Started implementation via workflow command
