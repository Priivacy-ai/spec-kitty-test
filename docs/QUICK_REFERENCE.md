# Spec Kitty Quick Reference for Functional Testing

**Spec-Kitty Version:** ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (commit ed3f461)
**Analysis Date:** 2025-11-13
**Purpose:** Quick lookup tables and code patterns for testing spec-kitty

## Test Organization Summary

| Category | Location | Focus | Key Files |
|----------|----------|-------|-----------|
| **Unit Tests** | `tests/specify_cli/test_core/` | Config, git ops, project resolution | `test_config.py`, `test_git_ops.py` |
| **Template Tests** | `tests/test_template/` | Rendering, asset generation, formats | `test_renderer.py`, `test_asset_generator.py` |
| **CLI Tests** | `tests/specify_cli/test_cli/` | Command execution, UI | `test_init_command.py`, `test_commands.py` |
| **Integration Tests** | `tests/integration/` | Full workflows with GitignoreManager | `test_init_flow.py` |
| **Dashboard Tests** | `tests/test_dashboard/` | Server, scanner, diagnostics | `test_server.py`, `test_scanner.py` |

## Key Fixtures (conftest.py)

```python
@pytest.fixture
def temp_repo(tmp_path):
    # Git repo with config
    # Returns: tmp_path with .git initialized

@pytest.fixture
def feature_repo(temp_repo):
    # Full feature structure
    # Returns: repo with kitty-specs/001-demo-feature/

@pytest.fixture
def merge_repo(temp_repo):
    # Feature branch workflow
    # Returns: (repo, worktree_dir, feature_slug)
```

## Init Command Stages (Quick Lookup)

| Stage | Function | Input | Output | Abort Conditions |
|-------|----------|-------|--------|------------------|
| 1 | Validate inputs | project_name, --here | Verified paths | Dir exists, no name |
| 2 | Check git | --no-git flag | should_init_git bool | None |
| 3 | Select agents | --ai option | selected_agents list | None selected |
| 4 | Check tools | --ignore-agent-tools | None (or error) | Missing tools |
| 5 | Select script | --script option | selected_script str | Invalid type |
| 6 | Select mission | --mission option | selected_mission str | Invalid mission |
| 7 | Detect template | SPECIFY_TEMPLATE_REPO | template_mode str | None |
| 8 | Track progress | (automatic) | StepTracker object | None |
| 9 | Get templates | Mode-specific | commands_dir Path | Download/extract fail |
| 10 | Generate assets | For each agent | Agent command files | Script error |
| 11 | Activate mission | selected_mission | Mission symlink | Mission load fail |
| 12 | Chmod scripts | (automatic) | Executable scripts | None |
| 13 | Init git | --no-git flag | .git directory | Git unavailable |
| 14 | Start dashboard | (automatic) | Dashboard running | Port unavailable |
| 15 | Summary | (automatic) | Display output | None |

## Agent Command Structure

```
Template File (SOURCE):
  templates/commands/specify.md
    ├── Frontmatter (YAML):
    │   ├── description: "..."
    │   ├── scripts:
    │   │   ├── sh: ".kittify/scripts/bash/... {ARGS}"
    │   │   └── ps: ".kittify/scripts/powershell/... {ARGS}"
    │   └── agent_scripts: (optional)
    └── Body: Markdown with {SCRIPT}, __AGENT__, etc.

Generated (PER AGENT):
  .{agent}/{dir}/spec-kitty.{command}.{ext}
    ├── .claude/commands/spec-kitty.specify.md
    │   └── Variables: $ARGUMENTS, paths → .kittify/
    ├── .gemini/commands/spec-kitty.specify.toml
    │   └── Variables: {{args}}, TOML format
    └── .codex/prompts/spec_kitty.specify.md
        └── Variables: $ARGUMENTS, underscores
```

## Variables Substitution Reference

| Placeholder | Claude Value | Gemini Value | Other Agents |
|------------|--------------|--------------|--------------|
| `{SCRIPT}` | Shell command from `scripts.sh` | Shell command | Shell command |
| `{ARGS}` | `$ARGUMENTS` | `{{args}}` | `$ARGUMENTS` |
| `{AGENT_SCRIPT}` | From `agent_scripts.sh` | From `agent_scripts.sh` | From `agent_scripts.sh` |
| `__AGENT__` | `"claude"` | `"gemini"` | Agent key string |

## Path Rewriting Rules

```
Input Path              → Output Path
scripts/run.sh          → .kittify/scripts/run.sh
templates/commands/     → .kittify/templates/commands/
memory/context.json     → .kittify/memory/context.json
```

## Agent Directory Mapping

| Agent | Command Directory | File Extension | Default Ext | Arg Format |
|-------|------------------|----------------|-------------|-----------|
| claude | `.claude/commands` | `.md` | .md | `$ARGUMENTS` |
| gemini | `.gemini/commands` | `.toml` | .toml | `{{args}}` |
| copilot | `.github/prompts` | `.prompt.md` | .prompt.md | `$ARGUMENTS` |
| cursor | `.cursor/commands` | `.md` | .md | `$ARGUMENTS` |
| codex | `.codex/prompts` | `.md` | .md | `$ARGUMENTS` |
| qwen | `.qwen/commands` | `.toml` | .toml | `{{args}}` |
| opencode | `.opencode/command` | `.md` | .md | `$ARGUMENTS` |
| windsurf | `.windsurf/workflows` | `.md` | .md | `$ARGUMENTS` |
| kilocode | `.kilocode/workflows` | `.md` | .md | `$ARGUMENTS` |
| auggie | `.augment/commands` | `.md` | .md | `$ARGUMENTS` |
| roo | `.roo/commands` | `.md` | .md | `$ARGUMENTS` |
| q | `.amazonq/prompts` | `.md` | .md | `$ARGUMENTS` |

## Mission Configuration Structure

```yaml
software-dev:
  name: "Software Dev Kitty"
  domain: "software"
  artifacts:
    required: [spec.md, plan.md, tasks.md]
  validation:
    checks: [git_clean, all_tests_pass, kanban_complete]
  commands: [specify, plan, tasks, implement, review, accept, ...]

research:
  name: "Deep Research Kitty"
  domain: "research"
  artifacts:
    required: [research.md, evidence.md]
  commands: [research, analyze, ...]
```

## Work Package States (Lanes)

```
planned  →  doing  →  review  →  done
 (WP01)     (WP02)    (WP03)     (WP04)

File Structure:
  kitty-specs/{feature}/tasks/{lane}/{WP-ID}.md
    
Example:
  kitty-specs/001-demo-feature/tasks/planned/WP01.md
```

## Test File Template

```python
# tests/test_something.py
from pathlib import Path
import pytest
from specify_cli.module import Function

def test_function_behavior(tmp_path: Path):
    """Test: Given X, when Y happens, then Z is true"""
    
    # Setup
    project = tmp_path / "test-project"
    project.mkdir()
    
    # Exercise
    result = Function(input_value)
    
    # Verify
    assert result == expected
    assert (project / "expected/file").exists()

@pytest.mark.parametrize("input,expected", [
    ("a", "result_a"),
    ("b", "result_b"),
])
def test_multiple_inputs(input, expected):
    assert compute(input) == expected
```

## Common Test Assertions

```python
# File existence
assert (project_path / ".claude/commands/spec-kitty.specify.md").exists()

# Content checks
content = path.read_text()
assert "$ARGUMENTS" in content  # Variable substituted
assert "{SCRIPT}" not in content  # Variable resolved
assert ".kittify/" in content    # Paths rewritten

# Directory structure
agents_dirs = [
    project_path / ".claude/commands",
    project_path / ".gemini/commands",
]
for d in agents_dirs:
    assert d.exists()
    assert len(list(d.glob("*.md"))) >= 13

# State verification
from specify_cli.dashboard.scanner import ProjectScanner
scanner = ProjectScanner(project_path)
features = scanner.scan()
assert len(features) == 1
assert features[0].slug == "001-demo-feature"
```

## CLI Testing Pattern

```python
from typer.testing import CliRunner
from specify_cli import app

runner = CliRunner()
result = runner.invoke(app, [
    "init", "project-name",
    "--ai", "claude",
    "--script", "sh",
    "--mission", "software-dev",
    "--no-git"
])

assert result.exit_code == 0
assert "Project ready" in result.stdout
```

## Monkeypatch Common Injections

```python
def test_with_mocks(monkeypatch):
    # Mock local repo detection
    monkeypatch.setattr(
        "specify_cli.cli.commands.init.get_local_repo_root",
        lambda: Path("/fake/repo")
    )
    
    # Mock dashboard
    monkeypatch.setattr(
        "specify_cli.cli.commands.init.ensure_dashboard_running",
        lambda p: ("http://localhost", 3000, True)
    )
    
    # Mock git check
    monkeypatch.setattr(
        "specify_cli.cli.commands.init.check_tool",
        lambda *args, **kwargs: True
    )
```

## Common Errors and Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError: commands_dir` | Templates not copied | Verify template_mode detection |
| `yaml.YAMLError` | mission.yaml malformed | Validate mission.yaml syntax |
| `PermissionError` | Script chmod failed | Check file permissions |
| `subprocess.CalledProcessError` | Git command failed | Check git availability |
| `Port already in use` | Dashboard conflict | Kill existing dashboard or use different port |
| `{PLACEHOLDER} in output` | Variable not substituted | Check script_type matches |

## Source Code Map for Testing

```
src/specify_cli/
├── cli/
│   └── commands/
│       ├── init.py              [TEST: integration test for full flow]
│       └── init_help.py          [TEST: help text validation]
├── core/
│   ├── config.py                [TEST: agent choices, mission choices, configs]
│   ├── tool_checker.py          [TEST: tool detection logic]
│   ├── git_ops.py               [TEST: git repository operations]
│   └── project_resolver.py      [TEST: finding project root]
├── template/
│   ├── renderer.py              [TEST: variable substitution, path rewriting]
│   ├── asset_generator.py       [TEST: command file generation per agent]
│   └── manager.py               [TEST: template loading and caching]
├── dashboard/
│   ├── scanner.py               [TEST: feature/WP detection]
│   ├── server.py                [TEST: HTTP server startup]
│   └── lifecycle.py             [TEST: process management]
├── mission.py                   [TEST: mission loading and config]
└── gitignore_manager.py         [TEST: gitignore protection]
```

## Execution Command Reference

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_template/test_renderer.py

# Run specific test
pytest tests/test_template/test_renderer.py::test_parse_frontmatter

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src

# Run integration tests only
pytest tests/integration/

# Run with specific marker
pytest -m integration
```

## Environment Variables for Testing

```bash
# Template repository (for remote mode testing)
export SPECIFY_TEMPLATE_REPO="owner/repo"

# GitHub token (for API access)
export GH_TOKEN="token"

# Skip TLS verification (testing only!)
export SKIP_TLS=true
```

## Dashboard API Quick Reference

```
GET http://localhost:3000/api/features
  Response: [{ slug, title, workPackages, artifacts }, ...]

POST http://localhost:3000/api/task/{wp_id}/move
  Payload: { "lane": "doing" }

WebSocket ws://localhost:3000/ws
  Real-time updates on project changes
```

---

**Total Coverage**: 27 test files, 100+ individual tests
**Primary Framework**: pytest with rich fixtures
**Integration Level**: Unit through end-to-end workflows
