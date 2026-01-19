---
work_package_id: WP01
title: 'Foundation: Directory Structure and Configuration Schemas'
lane: "doing"
dependencies: []
subtasks:
- T001
- T008
- T012
phase: Phase 1 - Infrastructure
assignee: ''
agent: "claude-opus"
shell_pid: "15522"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Foundation: Directory Structure and Configuration Schemas

## Objective

Create the foundational directory structure for the agentic testing framework under `tests/agentic/` and define the YAML configuration schemas for agents and test paths. This work package establishes the scaffolding that all subsequent work packages depend on.

## Context

This is the first work package in a 10-WP feature implementing an end-to-end testing framework for spec-kitty's multi-agent orchestrator. The framework tests up to 9 AI coding agents through containerized, adversarial testing workflows.

**User Stories Addressed**: All (foundational)
**Functional Requirements**: FR-012, FR-015 (agents.yaml), FR-007/008/009 (paths.yaml)

## Subtasks

### T001: Create tests/agentic/ directory structure

Create the complete directory structure as defined in the plan:

```
tests/agentic/
├── __init__.py
├── conftest.py                    # pytest fixtures (stub)
│
├── config/
│   ├── __init__.py
│   ├── agents.yaml                # Agent configurations
│   ├── paths.yaml                 # Test path definitions
│   └── secrets/                   # Git-ignored credentials
│       └── .gitkeep
│
├── containers/
│   └── .gitkeep                   # Dockerfile.base added in WP02
│
├── fixtures/
│   ├── __init__.py
│   └── .gitkeep                   # Fixture modules added in WP03
│
├── paths/
│   ├── __init__.py
│   └── .gitkeep                   # Path classes added in WP04
│
├── faults/
│   ├── __init__.py
│   └── .gitkeep                   # Fault injectors added in WP08
│
├── tests/
│   ├── __init__.py
│   └── .gitkeep                   # Test files added in WP09/WP10
│
└── results/                       # Git-ignored test outputs
    └── .gitkeep
```

**Acceptance Criteria**:
- All directories exist with proper `__init__.py` files
- `tests/agentic/config/secrets/` is git-ignored
- `tests/agentic/results/` is git-ignored
- Add entry to root `.gitignore` for these paths
- `conftest.py` exists with a docstring explaining its purpose

### T008: Create agents.yaml schema with all 9 agents

Create `tests/agentic/config/agents.yaml` with configuration for all 9 CLI-capable agents per data-model.md schema:

```yaml
# Agent configuration for E2E testing
version: "1.0"

agents:
  claude-code:
    enabled: true
    command: "claude"
    invocation_pattern: "stdin"
    timeout_seconds: 600
    credentials_secret: "claude_api_key"
    requires_timeout_wrapper: false
    resource_limits:
      cpu_cores: 2.0
      memory_mb: 4096
      disk_mb: 10240

  github-codex:
    enabled: true
    command: "codex exec"
    invocation_pattern: "stdin"
    timeout_seconds: 300
    credentials_secret: "github_token"
    requires_timeout_wrapper: false
    resource_limits:
      cpu_cores: 2.0
      memory_mb: 4096
      disk_mb: 10240

  # ... remaining 7 agents per research.md E007
```

**Required Agents** (per FR-012 and research.md E007):
1. `claude-code` - command: `claude`, stdin, `-p`, `--output-format json`
2. `github-codex` - command: `codex exec`, stdin/arg, `--json`
3. `github-copilot` - command: `copilot`, arg, `-p`, `--silent`
4. `google-gemini` - command: `gemini`, stdin, `-p`, `--output-format json`
5. `qwen-code` - command: `qwen`, stdin, `-p`, `--output-format json`
6. `opencode` - command: `opencode run`, stdin/`-f`, `--format json`
7. `kilocode` - command: `kilocode`, arg, `-a`, `-j`
8. `augment-code` - command: `auggie`, arg, `--acp`
9. `cursor` - command: `cursor agent`, arg, `-p`, `--output-format json`, **requires_timeout_wrapper: true**

**Acceptance Criteria**:
- All 9 agents defined with complete configuration
- Default resource limits defined
- Network configuration defined with `internal: true`
- YAML validates against data-model.md schema
- Comments explain each agent's special requirements (e.g., Cursor timeout wrapper)

### T012: Create paths.yaml schema for test path definitions

Create `tests/agentic/config/paths.yaml` defining the 3 test paths:

```yaml
# Test path definitions
version: "1.0"

paths:
  single-agent:
    description: "Single agent performs both implementation and review"
    agent_slots:
      - slot_id: "implementer"
        role: "implementation"
        required: true
        fallback_allowed: false
      - slot_id: "reviewer"
        role: "review"
        required: true
        fallback_allowed: false
        same_as: "implementer"  # Same agent fills both slots
    max_iterations: 5
    timeout_seconds: 1800

  cross-review:
    description: "Different agents for implementation vs review"
    agent_slots:
      - slot_id: "implementer"
        role: "implementation"
        required: true
        fallback_allowed: true
      - slot_id: "reviewer"
        role: "review"
        required: true
        fallback_allowed: true
        different_from: "implementer"  # Must be different agent
    max_iterations: 3
    timeout_seconds: 2400

  parallel-three:
    description: "Three agents working on independent WPs in parallel"
    agent_slots:
      - slot_id: "worker_1"
        role: "implementation"
        required: true
        fallback_allowed: true
      - slot_id: "worker_2"
        role: "implementation"
        required: false
        fallback_allowed: true
      - slot_id: "worker_3"
        role: "implementation"
        required: false
        fallback_allowed: true
    max_iterations: 3
    timeout_seconds: 3600

defaults:
  max_iterations: 3
  timeout_seconds: 1800
```

**Acceptance Criteria**:
- All 3 test paths defined per FR-007, FR-008, FR-009
- Agent slot constraints captured (same_as, different_from)
- Reasonable timeout and iteration limits
- Defaults section for shared configuration

## Technical Notes

- Use PyYAML for parsing (already in test dependencies)
- Consider adding JSON Schema validation in WP03
- Paths reference agents by `agent_id` from agents.yaml
- The `same_as` and `different_from` constraints are enforced at runtime by the fixture layer

## Files to Create

1. `tests/agentic/__init__.py`
2. `tests/agentic/conftest.py` (stub)
3. `tests/agentic/config/__init__.py`
4. `tests/agentic/config/agents.yaml`
5. `tests/agentic/config/paths.yaml`
6. `tests/agentic/config/secrets/.gitkeep`
7. `tests/agentic/containers/.gitkeep`
8. `tests/agentic/fixtures/__init__.py`
9. `tests/agentic/paths/__init__.py`
10. `tests/agentic/faults/__init__.py`
11. `tests/agentic/tests/__init__.py`
12. `tests/agentic/results/.gitkeep`

## Verification

```bash
# Verify directory structure
find tests/agentic -type f -name "*.py" -o -name "*.yaml"

# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('tests/agentic/config/agents.yaml'))"
python -c "import yaml; yaml.safe_load(open('tests/agentic/config/paths.yaml'))"

# Verify gitignore
git status tests/agentic/config/secrets/
git status tests/agentic/results/
```

## Definition of Done

- [ ] All directories created with proper structure
- [ ] All __init__.py files present
- [ ] agents.yaml complete with all 9 agents
- [ ] paths.yaml complete with all 3 test paths
- [ ] secrets/ and results/ directories git-ignored
- [ ] YAML files parse without errors
- [ ] conftest.py stub exists with docstring

## Activity Log

- 2026-01-19T10:04:17Z – claude-opus – shell_pid=15522 – lane=doing – Started implementation via workflow command
