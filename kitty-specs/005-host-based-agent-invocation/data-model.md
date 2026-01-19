# Data Model: Host-Based Agent Invocation

**Feature**: 005-host-based-agent-invocation
**Date**: 2026-01-19
**Purpose**: Define entities for the agent invocation layer

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Invocation Layer                               │
│                                                                         │
│  ┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐  │
│  │  AgentInvoker   │────▶│  AgentProcess   │────▶│InvocationResult  │  │
│  │  (Controller)   │     │  (Running Proc) │     │   (Outcome)      │  │
│  └────────┬────────┘     └─────────────────┘     └──────────────────┘  │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐     ┌─────────────────┐                           │
│  │WorktreeManager  │     │ AgentDiscovery  │                           │
│  │  (Isolation)    │     │  (Detection)    │                           │
│  └─────────────────┘     └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Configurations                             │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ ClaudeCode  │  │  Copilot    │  │   Gemini    │  │  OpenCode   │   │
│  │   Config    │  │   Config    │  │   Config    │  │   Config    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │   Codex     │                                                        │
│  │   Config    │                                                        │
│  └─────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Entities

### 1. InvocationResult

Immutable result from a single agent invocation.

```python
@dataclass(frozen=True)
class InvocationResult:
    """Result from invoking an agent."""

    # Process output
    stdout: str
    stderr: str
    exit_code: int

    # Timing
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    # Parsed outcome
    outcome: InvocationOutcome  # Enum: SUCCESS, FAILURE, TIMEOUT, CRASH, PARSE_ERROR
    parsed_response: Optional[ParsedAgentResponse]

    # Context
    agent_id: str
    prompt_hash: str  # SHA256 of prompt for deduplication
    worktree_path: str

    # Error details
    error_message: Optional[str] = None
    timeout_exceeded: bool = False
    killed: bool = False
```

**InvocationOutcome Enum:**
```python
class InvocationOutcome(Enum):
    SUCCESS = "success"           # Agent completed, output parseable
    FAILURE = "failure"           # Agent completed with error exit code
    TIMEOUT = "timeout"           # Agent exceeded timeout, killed
    CRASH = "crash"               # Agent process crashed
    PARSE_ERROR = "parse_error"   # Completed but output unparseable
```

**ParsedAgentResponse:**
```python
@dataclass
class ParsedAgentResponse:
    """Parsed response from agent output."""

    # For implementation tasks
    files_created: List[str]
    files_modified: List[str]
    commits_made: List[str]

    # For review tasks
    approval: Optional[bool]  # True=approved, False=rejected, None=unclear
    review_comments: List[str]
    requested_changes: List[str]

    # Raw sections
    raw_output: str
    thinking: Optional[str]  # If agent exposes reasoning
```

### 2. AgentProcess

Wrapper around a running subprocess with lifecycle management.

```python
class AgentProcess:
    """Represents a running agent subprocess."""

    def __init__(
        self,
        agent_id: str,
        process: subprocess.Popen,
        timeout_seconds: float,
        worktree_path: str,
    ):
        self.agent_id = agent_id
        self._process = process
        self._timeout = timeout_seconds
        self._worktree = worktree_path
        self._started_at = datetime.utcnow()
        self._stdout_buffer: List[str] = []
        self._stderr_buffer: List[str] = []

    # Properties
    @property
    def pid(self) -> int: ...
    @property
    def is_running(self) -> bool: ...
    @property
    def elapsed_seconds(self) -> float: ...

    # Lifecycle
    def wait(self, timeout: Optional[float] = None) -> InvocationResult: ...
    def kill(self, signal: int = signal.SIGTERM, grace_period: float = 5.0) -> None: ...
    def force_kill(self) -> None: ...  # SIGKILL

    # Output
    def get_stdout(self) -> str: ...
    def get_stderr(self) -> str: ...
    def stream_output(self) -> Iterator[Tuple[str, str]]: ...  # (stream_name, line)
```

### 3. AgentInvoker

Main controller for starting agent processes.

```python
class AgentInvoker:
    """Starts and manages agent invocations."""

    def __init__(
        self,
        worktree_manager: WorktreeManager,
        default_timeout: float = 1800.0,  # 30 minutes
        cleanup_on_exit: bool = True,
    ):
        self._worktree_manager = worktree_manager
        self._default_timeout = default_timeout
        self._cleanup_on_exit = cleanup_on_exit
        self._active_processes: Dict[str, AgentProcess] = {}

        if cleanup_on_exit:
            atexit.register(self._cleanup_all)

    # Core API
    def invoke(
        self,
        agent_config: AgentConfig,
        prompt: str,
        worktree: Optional[str] = None,  # Auto-creates if None
        timeout: Optional[float] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> InvocationResult: ...

    def invoke_async(
        self,
        agent_config: AgentConfig,
        prompt: str,
        worktree: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> AgentProcess: ...

    # Management
    def get_active_processes(self) -> List[AgentProcess]: ...
    def kill_all(self) -> None: ...

    # Constraints (FR-011, FR-012)
    def invoke_with_constraint(
        self,
        constraint: AgentConstraint,
        available_agents: List[AgentConfig],
        **invoke_kwargs,
    ) -> Tuple[AgentConfig, InvocationResult]: ...
```

**AgentConstraint:**
```python
class AgentConstraint(Enum):
    SAME_AS = "same_as"           # Use same agent (single-agent path)
    DIFFERENT_FROM = "different_from"  # Use different agent (cross-review)
    ANY = "any"                   # Any available agent
```

### 4. WorktreeManager

Manages isolated git worktrees for test runs.

```python
class WorktreeManager:
    """Creates and manages isolated git worktrees."""

    def __init__(
        self,
        repo_path: str,
        worktree_base: Optional[str] = None,  # Default: /tmp/spec-kitty-worktrees
    ):
        self._repo_path = repo_path
        self._worktree_base = worktree_base or "/tmp/spec-kitty-worktrees"
        self._active_worktrees: Dict[str, WorktreeInfo] = {}

    # Creation
    def create(
        self,
        branch_name: Optional[str] = None,  # Auto-generates if None
        base_ref: str = "HEAD",
    ) -> WorktreeInfo: ...

    def create_for_test(
        self,
        test_id: str,
        feature_branch: str,
    ) -> WorktreeInfo: ...

    # Cleanup
    def remove(self, worktree_path: str) -> bool: ...
    def remove_all(self) -> int: ...  # Returns count removed

    # Query
    def list_active(self) -> List[WorktreeInfo]: ...
    def get_info(self, worktree_path: str) -> Optional[WorktreeInfo]: ...
```

**WorktreeInfo:**
```python
@dataclass
class WorktreeInfo:
    """Information about a git worktree."""

    path: str
    branch: str
    base_commit: str
    created_at: datetime
    test_id: Optional[str] = None
```

### 5. AgentDiscovery

Runtime detection of available agents.

```python
class AgentDiscovery:
    """Discovers available agents at runtime."""

    def __init__(self, agent_configs: List[Type[BaseAgentConfig]]):
        self._configs = agent_configs

    def discover_all(self) -> List[DiscoveredAgent]: ...

    def discover_one(self, agent_id: str) -> Optional[DiscoveredAgent]: ...

    def check_availability(
        self,
        agent_config: BaseAgentConfig,
    ) -> AvailabilityResult: ...
```

**DiscoveredAgent:**
```python
@dataclass
class DiscoveredAgent:
    """An agent discovered on the host."""

    agent_id: str
    config: BaseAgentConfig
    version: Optional[str]
    authenticated: bool
    unavailable_reason: Optional[str] = None

    @property
    def is_available(self) -> bool:
        return self.authenticated and self.unavailable_reason is None
```

**AvailabilityResult:**
```python
@dataclass
class AvailabilityResult:
    """Result of checking agent availability."""

    installed: bool
    authenticated: bool
    version: Optional[str]
    error: Optional[str]

    @property
    def available(self) -> bool:
        return self.installed and self.authenticated
```

## Agent Configuration Protocol

### BaseAgentConfig

Abstract base for all agent configurations.

```python
class BaseAgentConfig(Protocol):
    """Protocol for agent configurations."""

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def cli_command(self) -> List[str]: ...  # e.g., ["claude"] or ["gh", "copilot"]

    @property
    def prompt_method(self) -> PromptMethod: ...  # STDIN, FILE, ARGUMENT

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]: ...

    def check_installed(self) -> Tuple[bool, Optional[str]]: ...  # (installed, version)

    def check_authenticated(self) -> Tuple[bool, Optional[str]]: ...  # (authed, error)

    def parse_output(self, stdout: str, stderr: str) -> ParsedAgentResponse: ...
```

**PromptMethod:**
```python
class PromptMethod(Enum):
    STDIN = "stdin"       # Pipe prompt to stdin
    FILE = "file"         # Write to file, pass path as arg
    ARGUMENT = "argument" # Pass prompt as CLI argument
```

### Example: Claude Code Config

```python
class ClaudeCodeConfig(BaseAgentConfig):
    """Configuration for Claude Code CLI."""

    @property
    def agent_id(self) -> str:
        return "claude-code"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    @property
    def cli_command(self) -> List[str]:
        return ["claude"]

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.STDIN  # Claude accepts stdin

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        return [
            "claude",
            "--print",  # Print mode for non-interactive
            "--cwd", worktree_path,
        ]

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, None
        except FileNotFoundError:
            return False, None

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        # Claude uses ANTHROPIC_API_KEY
        if os.environ.get("ANTHROPIC_API_KEY"):
            return True, None
        return False, "ANTHROPIC_API_KEY not set"

    def parse_output(self, stdout: str, stderr: str) -> ParsedAgentResponse:
        # Parse Claude's output format
        # Look for commit hashes, file changes, approval signals
        ...
```

## Relationship to Existing Entities

### Integration with AgentRegistry (fixtures/agent_fixtures.py)

```python
# Existing AgentConfig becomes wrapper for BaseAgentConfig
@dataclass
class AgentConfig:
    agent_id: str
    available: bool
    capabilities: List[str]
    # NEW: Link to invocation config
    invocation_config: Optional[BaseAgentConfig] = None
```

### Integration with TestRun (fixtures/workflow_fixtures.py)

```python
# TestRun gains invocation_results
@dataclass
class TestRun:
    run_id: str
    path_id: str
    # ... existing fields ...

    # NEW: Track all invocations
    invocations: List[InvocationResult] = field(default_factory=list)
```

### Integration with Observability (fixtures/observability.py)

```python
# AgentOutputLogger captures InvocationResult
class AgentOutputLogger:
    def log_invocation(self, result: InvocationResult) -> None:
        """Log an invocation result."""
        # Uses existing capture_output() context manager
        ...
```

## Success Criteria Mapping

| SC | Entity | Field/Method |
|----|--------|--------------|
| SC-001 | InvocationResult | `outcome == SUCCESS` |
| SC-002 | AgentDiscovery | `discover_all()` accuracy |
| SC-003 | InvocationResult | `stdout`, `stderr` (no truncation) |
| SC-004 | AgentProcess | `kill()` within 5s of timeout |
| SC-005 | InvocationResult + Observability | timing, output, git state |
| SC-006 | AgentInvoker | `_active_processes` empty after cleanup |
| SC-007 | AgentInvoker | `invoke_with_constraint(DIFFERENT_FROM)` |
