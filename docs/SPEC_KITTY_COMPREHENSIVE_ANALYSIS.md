# Spec Kitty Architecture and Functional Testing Guide

**Spec-Kitty Version Analyzed:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (commit ed3f461)
**Analysis Date:** 2025-11-13
**Code Location:** `/Users/robert/Code/spec-kitty/` at the commit above
**Validity Note:** This analysis is accurate for the specified commit. Check git history for this repo if analyzing a different version.

## Executive Summary

This document provides a comprehensive analysis of the spec-kitty codebase for understanding how to create functional tests. It covers:

1. **Test Structure**: Complete testing framework and patterns
2. **Init Workflow**: Detailed orchestration of project initialization
3. **Template System**: How templates are rendered for different agents
4. **Agent Interaction**: How agents receive and process commands
5. **State Management**: Persistence, missions, and work packages
6. **Dashboard**: Real-time project tracking and coordination
7. **Functional Testing Opportunities**: Concrete test scenarios with agent simulation

---

## 1. Test Framework and Structure

### Framework: pytest

- **Config File**: `pytest.ini` with pythonpath `. src`
- **Test Discovery**: `tests/` directory, all `test_*.py` files
- **Execution**: `pytest` command with verbose output

### Test Organization (27 test files)

```
tests/
├── conftest.py                    # Shared fixtures (temp_repo, feature_repo, merge_repo)
├── utils.py                        # Helper functions (run, run_tasks_cli, write_wp)
├── integration/
│   └── test_init_flow.py          # Full init workflow tests (7 tests)
├── specify_cli/test_cli/
│   ├── test_init_command.py       # Init-specific tests (3 tests)
│   ├── test_commands.py            # CLI commands (10+ tests)
│   └── test_ui.py                 # UI tests
├── specify_cli/test_core/
│   ├── test_config.py
│   ├── test_git_ops.py
│   ├── test_project_resolver.py
│   ├── test_tool_checker.py
│   └── test_utils.py
└── test_template/
    ├── test_renderer.py            # Template rendering (3 tests)
    ├── test_asset_generator.py    # Asset generation (2 tests)
    ├── test_manager.py
    └── test_github_client.py
```

### Key Fixtures

**temp_repo**: Minimal git repository
- Creates in tmp_path
- Initializes with git config
- Base for other fixtures

**feature_repo**: Full feature structure
- Creates `kitty-specs/001-demo-feature/`
- Adds spec.md, plan.md, tasks.md, etc.
- Commits to git
- Returns tmp_path as repo root

**merge_repo**: Feature branch workflow
- Creates main branch with README.md
- Creates 002-feature branch
- Sets up `.worktrees/002-feature` git worktree
- Returns (repo, worktree_dir, feature_slug)

---

## 2. Init Command Workflow (566 lines in init.py)

### High-Level Stages

```
init(project_name, --ai, --script, --mission, ...)
├─ Validate inputs (project name, --here flag)
├─ Check git availability
├─ Select AI assistants (multi-select: copilot, claude, gemini, cursor, qwen, etc.)
├─ Check agent tool requirements (skip with --ignore-agent-tools)
├─ Select script type (sh vs ps; auto-detect)
├─ Select mission (software-dev vs research)
├─ Detect template mode (local → package → remote)
├─ Create StepTracker for progress display
├─ For each agent:
│  ├─ Fetch/download templates
│  ├─ Generate agent-specific command files
│  └─ Track progress
├─ Activate mission (symlink + load config)
├─ Ensure scripts executable (chmod +x)
├─ Initialize git repo (optional)
├─ Start dashboard
└─ Display next steps
```

### Configuration Options

**Agents** (12 choices):
- copilot, claude, gemini, cursor, qwen, opencode, codex, windsurf, kilocode, auggie, roo, q

**Script Types**:
- sh (POSIX Shell) - default on Unix
- ps (PowerShell) - default on Windows

**Missions**:
- software-dev (default)
- research

**Template Modes**:
1. Local: from `spec-kitty` git checkout
2. Package: from installed `specify_cli` package
3. Remote: from GitHub releases

### Dependency Injection Pattern (for testability)

```python
# Module-level variables
_console: Console | None = None
_show_banner: Callable[[], None] | None = None
_activate_mission: Callable[[Path, str, str, Console], str] | None = None
_ensure_executable_scripts: Callable[[Path, StepTracker | None], None] | None = None

# Used in tests via register_init_command()
def register_init_command(app, console=None, show_banner=None, ...):
    # Sets module variables for injection
```

### Agent Tool Requirements

Some agents require local tools:
- claude → claude-code CLI
- gemini → gemini-cli
- qwen → qwen-code
- etc.

Checked unless `--ignore-agent-tools` flag passed.

---

## 3. Template System

### Template Locations

**Source Templates**: `templates/commands/*.md`
- 13 command templates: specify, plan, research, tasks, implement, review, accept, etc.
- Frontmatter with scripts (sh + ps variants)
- Placeholder variables: {SCRIPT}, {ARGS}, {AGENT_SCRIPT}, __AGENT__

**Generated Files**: `.{agent}/commands/spec-kitty.{command}.{ext}`
- Claude: `.claude/commands/spec-kitty.*.md`
- Gemini: `.gemini/commands/spec-kitty.*.toml`
- Copilot: `.github/prompts/spec-kitty.*.prompt.md`
- etc.

### Template Rendering Pipeline

```
Template File
    ↓
parse_frontmatter() → (metadata, body, raw_frontmatter)
    ↓
_resolve_variables(metadata) → {"{SCRIPT}": "...", "{ARGS}": "..."}
    ↓
_apply_variables(body, replacements) → substituted body
    ↓
rewrite_paths(rendered) → .kittify/ paths
    ↓
Output File
```

### Agent Configuration

```python
AGENT_COMMAND_CONFIG = {
    "claude":    {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "gemini":    {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"},
    "copilot":   {"dir": ".github/prompts", "ext": "prompt.md", "arg_format": "$ARGUMENTS"},
    "cursor":    {"dir": ".cursor/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "qwen":      {"dir": ".qwen/commands", "ext": "toml", "arg_format": "{{args}}"},
    "opencode":  {"dir": ".opencode/command", "ext": "md", "arg_format": "$ARGUMENTS"},
    "windsurf":  {"dir": ".windsurf/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "codex":     {"dir": ".codex/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
    "kilocode":  {"dir": ".kilocode/workflows", "ext": "md", "arg_format": "$ARGUMENTS"},
    "auggie":    {"dir": ".augment/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "roo":       {"dir": ".roo/commands", "ext": "md", "arg_format": "$ARGUMENTS"},
    "q":         {"dir": ".amazonq/prompts", "ext": "md", "arg_format": "$ARGUMENTS"},
}
```

### Path Rewriting Rules

Default transformations applied to all templates:
- `scripts/` → `.kittify/scripts/`
- `templates/` → `.kittify/templates/`
- `memory/` → `.kittify/memory/`

---

## 4. Agent Interaction

### How Agents Discover Commands

Each agent has a directory containing spec-kitty commands:

**Discovery Methods**:
- Claude Code: Looks in `.claude/commands/` for `*.md` files
- Gemini: Looks in `.gemini/commands/` for `*.toml` files
- Copilot: Looks in `.github/prompts/` for `*.prompt.md` files

### Command Invocation

Agents invoke commands via slash commands:
- `/spec-kitty.specify` or `/specify`
- `/spec-kitty.plan` or `/plan`
- etc.

### Available Commands (13 total)

1. **specify** - Create/update feature specification
2. **plan** - Design technical architecture
3. **research** - Conduct mission-specific research
4. **tasks** - Break into work packages (kanban)
5. **implement** - Execute implementation
6. **review** - Code review and quality checks
7. **accept** - Validate feature completeness
8. **clarify** - Ask structured questions (optional)
9. **analyze** - Cross-artifact consistency (optional)
10. **checklist** - Generate quality checklists (optional)
11. **constitution** - Establish project principles
12. **dashboard** - Open real-time dashboard
13. **merge** - Merge feature into main

### Command Content Structure

Each command file contains:

```markdown
---
description: [Human-readable description]
scripts:
  sh: [Shell command with {ARGS}]
  ps: [PowerShell command with {ARGS}]
---

[Rendered markdown body with:
- Instructions for the agent
- Discovery questions
- Artifact requirements
- Variable substitutions applied
- Paths rewritten to .kittify/
```

### Variable Substitution Example

**Template**:
```markdown
---
scripts:
  sh: ./scripts/run.sh "{ARGS}"
---
Run {SCRIPT} with arguments {ARGS} for agent __AGENT__.
```

**Generated for Claude** (sh):
```markdown
---
description: [description]
---
Run ./scripts/run.sh "$ARGUMENTS" with arguments $ARGUMENTS for agent claude.
```

**Generated for Gemini** (sh + TOML):
```toml
description = "[description]"

[command]
prompt = """
Run ./scripts/run.sh "{{args}}" with arguments {{args}} for agent gemini.
"""
```

---

## 5. State Management

### .kittify Directory

```
.kittify/
├── active-mission → missions/software-dev/        [Symlink]
├── AGENTS.md                                       [Agent docs]
├── memory/                                         [Persistent memory]
├── missions/
│  ├── software-dev/
│  │  ├── mission.yaml                             [Mission config]
│  │  ├── commands/                                [Command templates]
│  │  ├── constitution/                            [Project rules]
│  │  └── templates/                               [Mission templates]
│  └── research/                                   [Alternative mission]
├── scripts/
│  ├── bash/                                       [Shell scripts]
│  ├── tasks/                                      [Task CLI scripts]
│  └── validate_encoding.py
└── templates/
   ├── commands/                                   [Template sources]
   └── [Agent-specific templates]
```

### Mission System

**Mission Class** (mission.py):
```python
class Mission:
    def __init__(self, mission_path: Path):
        self.path = mission_path
        self.config = self._load_config()  # from mission.yaml
    
    @property
    def name(self) -> str: ...
    @property
    def templates_dir(self) -> Path: ...
    @property
    def commands_dir(self) -> Path: ...
    @property
    def constitution_dir(self) -> Path: ...
```

**Mission Configuration** (mission.yaml):

```yaml
name: "Software Dev Kitty"
description: "Build high-quality software with structured workflows"
version: "1.0.0"
domain: "software"

workflow:
  phases:
    - name: "research"
    - name: "design"
    - name: "implement"
    - name: "test"
    - name: "review"

artifacts:
  required: [spec.md, plan.md, tasks.md]
  optional: [data-model.md, research.md, contracts/]

paths:
  workspace: "src/"
  tests: "tests/"
  deliverables: "contracts/"

validation:
  checks: [git_clean, all_tests_pass, kanban_complete]
  custom_validators: true

mcp_tools:
  required: [filesystem, git]
  recommended: [code-search, test-runner]

commands:
  specify:
    prompt: "Define user scenarios and acceptance criteria"
  plan:
    prompt: "Design technical architecture"
  # ... etc
```

### Work Packages

**Structure**: `kitty-specs/{feature-slug}/tasks/{lane}/{WP-ID}.md`

**Example File**: `kitty-specs/001-demo-feature/tasks/planned/WP01.md`

```yaml
---
work_package_id: "WP01"
lane: "planned"            # State: planned, doing, review, done
agent: "system"            # Agent handling it
assignee: "Owner"
shell_pid: "1234"
---

## Description

[Task description]

## Activity Log

- 2025-01-01T00:00:00Z – system – shell_pid=1234 – lane=planned – Created
- 2025-01-01T01:00:00Z – claude – shell_pid=5678 – lane=doing – Started
```

### Feature Structure

```
kitty-specs/001-demo-feature/
├── spec.md                    # User stories and requirements
├── plan.md                    # Technical plan
├── tasks.md                   # Kanban task list
├── quickstart.md              # Quick reference
├── data-model.md              # Data structures
├── research.md                # Research findings
├── tasks/
│  ├── planned/                # Planned work
│  │  ├── WP01.md
│  │  └── WP02.md
│  ├── doing/                  # In progress
│  ├── review/                 # Under review
│  └── done/                   # Completed
└── research/                  # Research artifacts
   └── evidence-log.csv        # Evidence tracker
```

---

## 6. Dashboard

### Dashboard Module

```
src/specify_cli/dashboard/
├── __init__.py           # Main entry: ensure_dashboard_running()
├── server.py             # HTTP server
├── scanner.py            # File system monitoring
├── lifecycle.py          # Process management
├── diagnostics.py        # Health checks
├── handlers/             # HTTP handlers
├── static/               # Frontend assets
└── templates/            # HTML templates
```

### Dashboard Lifecycle

**Starting**:
```python
dashboard_url, port, started = ensure_dashboard_running(project_path)
```

Returns:
- `dashboard_url`: "http://localhost"
- `port`: 3000-5000 range
- `started`: True if newly started, False if reconnected

**Scanning**:
- Monitors `.kittify/` for config changes
- Scans `kitty-specs/` for feature/WP changes
- Detects state transitions (planned → doing → review → done)
- Watches `.git/` for branch info

**Data Flow**:
```
File System Changes
    ↓
Scanner.scan() → Features, WorkPackages
    ↓
Dashboard State Update
    ↓
HTTP/WebSocket to Frontend
    ↓
Browser UI Update (Real-time)
```

### Dashboard API Endpoints

- `GET /` - Dashboard UI
- `GET /api/features` - List features and work packages
- `GET /api/feature/{slug}` - Feature details
- `GET /api/dashboard-status` - Health/ready status
- `POST /api/task/{wp_id}/move` - Update WP lane
- `WebSocket /ws` - Real-time updates

### Available Data After Each Stage

**After init**:
```json
{
  "project": {
    "name": "demo",
    "activeMission": "software-dev",
    "agentsFeatured": ["claude", "gemini"]
  },
  "features": [],
  "configuration": {
    "mission": "software-dev"
  }
}
```

**After first feature creation**:
```json
{
  "features": [
    {
      "slug": "001-demo-feature",
      "title": "Demo Feature",
      "workPackages": {
        "planned": ["WP01"],
        "doing": [],
        "review": [],
        "done": []
      },
      "artifacts": {
        "spec": "spec.md",
        "plan": "plan.md"
      }
    }
  ]
}
```

---

## 7. Functional Testing Scenarios

### Scenario 1: Complete Init Workflow

```python
def test_init_to_project_ready(tmp_path):
    """Test: Init completes → Project structure valid → Dashboard runs"""
    
    # Run init
    result = run_init_command(
        project_path=tmp_path / "test-proj",
        ai="claude",
        script="sh",
        mission="software-dev",
        no_git=True
    )
    
    assert result.exit_code == 0
    assert "Project ready" in result.output
    
    # Verify project structure
    project = tmp_path / "test-proj"
    assert (project / ".claude/commands").exists()
    assert (project / ".kittify/active-mission").is_symlink()
    assert (project / ".kittify/missions/software-dev/mission.yaml").exists()
    
    # Verify commands exist
    commands = list((project / ".claude/commands").glob("spec-kitty.*.md"))
    assert len(commands) >= 13  # All commands
    
    # Verify dashboard starts
    dashboard_url, port, started = ensure_dashboard_running(project)
    assert dashboard_url is not None
    assert 3000 <= port <= 5000
    
    # Verify API response
    features_resp = requests.get(f"{dashboard_url}:{port}/api/features")
    assert features_resp.status_code == 200
    assert features_resp.json() == []
```

### Scenario 2: Multi-Agent Command Generation

```python
def test_multi_agent_init_generates_all_commands(tmp_path):
    """Test: Init with 3 agents → Each has correct command files"""
    
    project = tmp_path / "multi-agent"
    
    # Init with multiple agents
    result = run_init_command(
        project_path=project,
        ai="claude,gemini,codex",
        script="sh",
        mission="software-dev",
        no_git=True
    )
    
    assert result.exit_code == 0
    
    # Verify Claude commands (Markdown)
    claude_cmds = list((project / ".claude/commands").glob("spec-kitty.*.md"))
    assert len(claude_cmds) >= 13
    
    claude_specify = (project / ".claude/commands/spec-kitty.specify.md").read_text()
    assert "$ARGUMENTS" in claude_specify  # Claude variable placeholder
    assert "{SCRIPT}" not in claude_specify  # Variables resolved
    assert ".kittify/scripts" in claude_specify  # Paths rewritten
    
    # Verify Gemini commands (TOML)
    gemini_cmds = list((project / ".gemini/commands").glob("spec-kitty.*.toml"))
    assert len(gemini_cmds) >= 13
    
    gemini_specify = (project / ".gemini/commands/spec-kitty.specify.toml").read_text()
    assert '[command]' in gemini_specify  # TOML format
    assert 'prompt = """' in gemini_specify  # Body as prompt
    assert "{{args}}" in gemini_specify  # Gemini variable placeholder
    
    # Verify Codex commands (Markdown, underscores)
    codex_cmds = list((project / ".codex/prompts").glob("spec-kitty.*.md"))
    assert len(codex_cmds) >= 13
```

### Scenario 3: Mission Activation and Configuration

```python
def test_mission_activation(tmp_path):
    """Test: Mission selected → Symlink created → Config loaded"""
    
    project = tmp_path / "mission-test"
    
    result = run_init_command(
        project_path=project,
        ai="claude",
        mission="software-dev",
        script="sh",
        no_git=True
    )
    
    assert result.exit_code == 0
    
    # Verify symlink
    active_mission = project / ".kittify/active-mission"
    assert active_mission.is_symlink()
    assert active_mission.resolve().name == "software-dev"
    
    # Verify mission.yaml loaded
    mission_yaml = active_mission / "mission.yaml"
    assert mission_yaml.exists()
    
    config = yaml.safe_load(mission_yaml.read_text())
    assert config["name"] == "Software Dev Kitty"
    assert config["domain"] == "software"
    assert "specify" in config["commands"]
    
    # Verify commands available in mission
    commands = list(active_mission.glob("commands/spec-kitty.*.md"))
    assert len(commands) >= 13
```

### Scenario 4: Feature Creation and Dashboard State

```python
def test_feature_creation_updates_dashboard(tmp_path, feature_repo):
    """Test: Create feature → Dashboard detects → API returns updated state"""
    
    # Start dashboard
    dashboard_url, port, started = ensure_dashboard_running(feature_repo)
    
    # Initially no features
    resp = requests.get(f"{dashboard_url}:{port}/api/features")
    assert resp.json() == []
    
    # Create feature directory
    feature = feature_repo / "kitty-specs/001-demo-feature"
    feature.mkdir(parents=True, exist_ok=True)
    (feature / "spec.md").write_text("# Spec")
    (feature / "plan.md").write_text("# Plan")
    (feature / "tasks.md").write_text("# Tasks")
    
    # Wait for scanner
    import time
    time.sleep(1)
    
    # Dashboard should detect feature
    resp = requests.get(f"{dashboard_url}:{port}/api/features")
    features = resp.json()
    
    assert len(features) == 1
    assert features[0]["slug"] == "001-demo-feature"
    assert "spec" in features[0]["artifacts"]
```

### Scenario 5: Work Package State Transitions

```python
def test_work_package_lane_transitions(tmp_path, feature_repo):
    """Test: Create WP → Move through lanes → Dashboard tracks states"""
    
    feature_slug = "001-demo-feature"
    feature_path = feature_repo / f"kitty-specs/{feature_slug}"
    feature_path.mkdir(parents=True, exist_ok=True)
    
    # Create initial WP in "planned"
    write_wp(feature_repo, feature_slug, "planned", "WP01", agent="system")
    
    # Verify initial state
    from specify_cli.dashboard.scanner import ProjectScanner
    scanner = ProjectScanner(feature_repo)
    features = scanner.scan()
    
    assert len(features) == 1
    assert "WP01" in features[0].work_packages["planned"]
    assert features[0].work_packages["doing"] == []
    
    # Move WP to "doing"
    wp_planned = feature_path / "tasks/planned/WP01.md"
    content = wp_planned.read_text()
    content = content.replace("lane: \"planned\"", "lane: \"doing\"")
    
    wp_doing = feature_path / "tasks/doing/WP01.md"
    wp_doing.parent.mkdir(parents=True, exist_ok=True)
    wp_doing.write_text(content)
    wp_planned.unlink()
    
    # Verify state change detected
    features = scanner.scan()
    assert "WP01" not in features[0].work_packages["planned"]
    assert "WP01" in features[0].work_packages["doing"]
```

### Scenario 6: Template Mode Detection

```python
def test_init_template_modes(tmp_path, monkeypatch):
    """Test: Init detects and uses correct template mode (local/package/remote)"""
    
    # Mode 1: Local (if spec-kitty source available)
    # This would set SPEC_KITTY_ROOT or find .git/modules
    # Expected output: "Using local templates from"
    
    # Mode 2: Package (default)
    result = run_init_command(
        project_path=tmp_path / "pkg-init",
        ai="claude",
        debug=True,
        no_git=True
    )
    
    # In debug mode, should print template source
    assert "templates" in result.output.lower()
    
    # Mode 3: Remote (if SPECIFY_TEMPLATE_REPO env var set)
    monkeypatch.setenv("SPECIFY_TEMPLATE_REPO", "owner/repo")
    
    result = run_init_command(
        project_path=tmp_path / "remote-init",
        ai="claude",
        debug=True,
        no_git=True
    )
    
    # Should attempt remote download
    # (may fail without actual GitHub access)
```

### Scenario 7: Gitignore Protection

```python
def test_init_protects_agent_directories(tmp_path):
    """Test: Init creates .gitignore protecting all agent directories"""
    
    project = tmp_path / "gitignore-test"
    
    result = run_init_command(
        project_path=project,
        ai="claude,gemini,codex",
        script="sh",
        no_git=False
    )
    
    # Verify .gitignore exists
    gitignore = project / ".gitignore"
    assert gitignore.exists()
    
    content = gitignore.read_text()
    
    # All agent directories protected
    expected = [
        ".claude/", ".codex/", ".opencode/", ".windsurf/",
        ".gemini/", ".cursor/", ".qwen/", ".kilocode/",
        ".augment/", ".roo/", ".amazonq/"
    ]
    
    for entry in expected:
        assert entry in content
        # No duplicates
        assert content.count(entry) == 1
    
    # Marker present
    assert "Added by Spec Kitty CLI" in content
```

### Scenario 8: Git Repository Initialization

```python
def test_init_creates_git_repo(tmp_path):
    """Test: Init with git available → Repository initialized"""
    
    project = tmp_path / "git-test"
    
    result = run_init_command(
        project_path=project,
        ai="claude",
        script="sh",
        no_git=False
    )
    
    assert result.exit_code == 0
    
    # Git repo should exist
    assert (project / ".git").is_dir()
    
    # Verify initial commit
    import subprocess
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=project,
        capture_output=True,
        text=True
    )
    
    # Should have at least one commit
    assert result.returncode == 0
    assert result.stdout.strip() != ""
```

---

## 8. Test Utilities and Helpers

```python
def run_init_command(project_path, ai, script="sh", mission="software-dev", **kwargs):
    """Run init command and return result"""
    from typer.testing import CliRunner
    from specify_cli import app
    
    runner = CliRunner()
    args = [
        "init", str(project_path),
        "--ai", ai,
        "--script", script,
        "--mission", mission,
    ]
    
    if kwargs.get("no_git"):
        args.append("--no-git")
    if kwargs.get("debug"):
        args.append("--debug")
    
    return runner.invoke(app, args)

def read_work_package(path):
    """Parse work package from file"""
    from specify_cli.tasks_support import split_frontmatter
    
    content = path.read_text()
    front, body, padding = split_frontmatter(content)
    
    import yaml
    frontmatter = yaml.safe_load(front) or {}
    
    return {
        'id': frontmatter.get('work_package_id'),
        'lane': frontmatter.get('lane'),
        'agent': frontmatter.get('agent'),
        'body': body
    }

def verify_command_file(path, agent, expected_variables):
    """Verify command file has expected content"""
    content = path.read_text()
    
    # Check agent-specific things
    if agent == "claude":
        assert ".md" in path.name
        assert "$ARGUMENTS" in content
    elif agent == "gemini":
        assert ".toml" in path.name or "[command]" in content
        assert "{{args}}" in content
    elif agent == "codex":
        assert "_" in path.stem  # Underscores instead of dashes
    
    # Check common transformations
    assert ".kittify/" in content  # Paths rewritten
    assert "spec-kitty" in path.name  # Naming convention
```

---

## 9. Integration Points for Testing

1. **Template System** → `renderer.py`, `asset_generator.py`
2. **Mission System** → `mission.py`
3. **Dashboard** → `dashboard/scanner.py`, `dashboard/server.py`
4. **Init Command** → `cli/commands/init.py`
5. **Gitignore** → `gitignore_manager.py`
6. **Task Support** → `tasks_support.py`

---

## Summary

Spec Kitty's functional testing opportunities revolve around:

1. **Init Workflow**: Project creation, template selection, agent setup
2. **Template System**: Variable substitution, format conversion, path rewriting
3. **Mission Activation**: Configuration loading, command availability
4. **Work Package Management**: State tracking, lane transitions
5. **Dashboard Integration**: Real-time updates, feature detection
6. **Multi-Agent Scenarios**: Different agents with different configurations

The codebase is well-structured for testing with:
- Clear separation of concerns
- Dependency injection for mocking
- Comprehensive fixtures
- Well-defined interfaces between components
