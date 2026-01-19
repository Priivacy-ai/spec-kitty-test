# Research: Existing Agentic Testing Infrastructure

**Feature**: 005-host-based-agent-invocation
**Date**: 2026-01-19
**Purpose**: Document what code exists from Feature 004 and what needs to be built

## Executive Summary

Feature 004 created **comprehensive scaffolding** for agentic E2E testing - approximately 5000+ lines of well-designed code. However, 100% of agent workflow tests are **SKIPPED** because the critical **agent invocation layer** is missing.

**The gap is not architecture - it's integration with real CLI tools.**

## Inventory of Existing Code

### Test Paths (COMPLETE - KEEP AS-IS)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `paths/base_path.py` | ~150 | Abstract base path with `execute()` | Complete |
| `paths/single_agent.py` | ~100 | US1: One agent implements + reviews | Complete |
| `paths/cross_review.py` | ~100 | US2: Agent A implements, B reviews | Complete |
| `paths/parallel_three.py` | ~100 | US3: Three agents, three WPs, parallel | Complete |

**Analysis**: Path implementations are sound. They define workflow orchestration but delegate actual agent execution to an invoker (which doesn't exist yet).

### Fixtures (COMPLETE - KEEP AS-IS)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `fixtures/agent_fixtures.py` | ~300 | AgentConfig, AgentRegistry, DynamicAgentRegistry | Complete |
| `fixtures/workflow_fixtures.py` | ~400 | TestRun, WorkPackage, WorkflowManager | Complete |
| `fixtures/container_fixtures.py` | ~200 | Docker container management | Complete (not used) |
| `fixtures/observability.py` | ~935 | Logging, git capture, metrics, post-mortem | Complete |

**Analysis**: All fixture code is production-quality. The observability module is particularly thorough with `AgentOutputLogger`, `GitStateCapture`, `WPTransitionLogger`, `ContainerMetricsCollector`, and `PostMortemExporter`.

### Fault Injection (COMPLETE - KEEP AS-IS)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `faults/process_faults.py` | ~400 | Base classes, ProcessFaultInjector | Complete |
| `faults/file_faults.py` | ~1093 | FileFaultInjector, PermissionFaultInjector, GitFaultInjector | Complete |
| `faults/auth_faults.py` | ~803 | AuthFaultInjector, MultiCredentialFaultInjector | Complete |
| `faults/resource_faults.py` | ~841 | ResourceFaultInjector, DiskQuotaInjector | Complete |

**Analysis**: Fault injection is fully implemented with backup/restore capabilities. These will be valuable for adversarial testing once the invoker exists.

### Test Files (SCAFFOLDING - NEEDS INVOKER)

| File | Tests | Skip Status | Why Skipped |
|------|-------|-------------|-------------|
| `tests/test_single_agent.py` | ~15 | 100% skipped | "Agent claude-code not available" |
| `tests/test_cross_review.py` | ~10 | 100% skipped | "No agents available for testing" |
| `tests/test_parallel.py` | ~10 | 100% skipped | "Fewer than 3 agents available" |
| `tests/test_fault_injection.py` | ~20 | 100% skipped | Depends on agent invocation |
| `tests/test_distribution.py` | 5 | Passes | Tests config/structure, not agents |
| `tests/test_agent_config.py` | 9 | Passes | Tests config/structure, not agents |

**Analysis**: Tests are well-written but blocked by missing invoker. Once the invoker exists, these tests should transition from SKIPPED to PASSED/FAILED.

## The Missing Layer: Agent Invocation

### What Needs to Be Built

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING (Feature 004)                       │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │   Paths   │  │  Fixtures  │  │   Faults   │  │   Tests    │ │
│  │  (Done)   │  │   (Done)   │  │   (Done)   │  │ (Skipped)  │ │
│  └─────┬─────┘  └──────┬─────┘  └─────┬──────┘  └──────┬─────┘ │
└────────┼───────────────┼──────────────┼────────────────┼───────┘
         │               │              │                │
         └───────────────┴──────────────┴────────────────┘
                                  │
                                  ▼
         ┌────────────────────────────────────────────────────────┐
         │              MISSING (Feature 005)                     │
         │                                                        │
         │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │
         │  │   Agent     │  │   Agent     │  │   Worktree    │  │
         │  │  Invoker    │  │  Discovery  │  │   Manager     │  │
         │  └──────┬──────┘  └──────┬──────┘  └───────┬───────┘  │
         │         │                │                 │          │
         │         └────────────────┴─────────────────┘          │
         │                          │                             │
         │                          ▼                             │
         │  ┌─────────────────────────────────────────────────┐  │
         │  │            Agent-Specific Configs               │  │
         │  │  claude_code.py  copilot.py  gemini.py  etc.    │  │
         │  └─────────────────────────────────────────────────┘  │
         └────────────────────────────────────────────────────────┘
                                  │
                                  ▼
         ┌────────────────────────────────────────────────────────┐
         │                    REAL AGENTS                         │
         │  ┌──────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────┐ │
         │  │Claude│  │Copilot │  │ Gemini │  │OpenCode│  │Codex│ │
         │  │ Code │  │   CLI  │  │  CLI   │  │  CLI   │  │ CLI│ │
         │  └──────┘  └────────┘  └────────┘  └────────┘  └────┘ │
         └────────────────────────────────────────────────────────┘
```

### Component Responsibilities

1. **AgentInvoker**: Starts subprocess, passes prompt, captures output, enforces timeout
2. **AgentProcess**: Wraps `subprocess.Popen`, provides `wait()`, `kill()`, `get_output()`
3. **InvocationResult**: Immutable result with stdout, stderr, exit_code, duration, parsed_outcome
4. **WorktreeManager**: Creates isolated git worktrees for each test run
5. **Agent Discovery**: Detects installed agents via CLI version checks
6. **Agent Configs**: Per-agent invocation patterns (how to pass prompts, parse output)

## Available Agents on Host

| Agent | CLI Command | Auth Location | Detection |
|-------|-------------|---------------|-----------|
| Claude Code | `claude` | `$ANTHROPIC_API_KEY` | `claude --version` |
| GitHub Copilot | `gh copilot` | `~/.zshrc` | `gh copilot --version` |
| Google Gemini | TBD | `~/.zshrc` | TBD |
| OpenCode | `opencode` | TBD | `opencode --version` |
| OpenAI Codex | TBD | TBD | TBD |

## Key Integration Points

### 1. Path → Invoker

```python
# Current (Feature 004) - abstract
class SingleAgentPath(BasePath):
    def execute(self, agent: AgentConfig) -> PathResult:
        # Calls self._invoke_agent() which doesn't exist
        pass

# After Feature 005
class SingleAgentPath(BasePath):
    def __init__(self, invoker: AgentInvoker):
        self.invoker = invoker

    def execute(self, agent: AgentConfig) -> PathResult:
        result = self.invoker.invoke(
            agent=agent,
            prompt=self._build_prompt(),
            worktree=self.worktree,
            timeout=self.timeout
        )
        return self._process_result(result)
```

### 2. Fixture → Discovery

```python
# Current (Feature 004) - hardcoded
@pytest.fixture
def available_agents(agent_registry):
    return agent_registry.get_available()  # Always empty

# After Feature 005
@pytest.fixture
def available_agents(agent_discovery):
    return agent_discovery.discover_all()  # Runtime detection
```

### 3. Test → Real Execution

```python
# Current (Feature 004) - skipped
def test_single_agent_workflow(available_agents, single_agent_path):
    if len(available_agents) < 1:
        pytest.skip("No agents available")  # Always skips
    # Never reaches here

# After Feature 005
def test_single_agent_workflow(available_agents, single_agent_path, agent_invoker):
    if len(available_agents) < 1:
        pytest.skip("No agents available")

    agent = available_agents[0]
    result = single_agent_path.execute(agent)  # Actually runs!
    assert result.status == "completed"
```

## Recommendations

### DO NOT DELETE

All existing code (paths, fixtures, faults, tests) is well-designed and should be preserved. The scaffolding represents significant investment and will become functional once the invoker layer exists.

### BUILD (Feature 005)

1. `tests/agentic/invoker/` - New package for invocation infrastructure
2. `tests/agentic/agents/` - New package for agent-specific configs
3. Integration code to wire invoker into existing fixtures

### TEST VALIDATION

After Feature 005, the same test command should produce:
- **Before**: `104 tests collected, 100 skipped, 4 passed`
- **After**: `104 tests collected, X passed, Y failed, Z skipped` (where skipped only for genuinely unavailable agents)
