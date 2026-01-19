---
work_package_id: WP03
title: 'Core Fixtures: Container and Agent Lifecycle'
lane: "doing"
dependencies: []
subtasks:
- T006
- T022
- T023
- T009
- T010
phase: Phase 2 - Fixtures
assignee: ''
agent: "claude-opus"
shell_pid: "30118"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Core Fixtures: Container and Agent Lifecycle

## Objective

Implement the pytest fixtures for container lifecycle management and agent configuration loading. This includes timeout enforcement, agent detection (installed + authenticated), and graceful skip logic for unavailable agents.

## Context

**Depends On**: WP01 (config files), WP02 (Docker infrastructure)
**User Stories Addressed**: US4 (Container Isolation), US8 (Modular Agent Config)
**Functional Requirements**: FR-001, FR-005, FR-013, FR-014, FR-015

This work package creates the fixture layer that abstracts container management and agent configuration from test code. Uses testcontainers-python 4.14.0 per research.md E002.

## Subtasks

### T006: Implement container timeout enforcement

Add timeout handling to container operations per FR-005:

```python
# tests/agentic/fixtures/container_fixtures.py

import signal
from contextlib import contextmanager
from typing import Optional

class ContainerTimeoutError(Exception):
    """Raised when container execution exceeds timeout."""
    pass

@contextmanager
def container_timeout(seconds: int, container_id: str):
    """Context manager for container timeout enforcement.

    Uses SIGALRM on Unix systems. Falls back to threading on Windows.
    """
    def timeout_handler(signum, frame):
        raise ContainerTimeoutError(
            f"Container {container_id} exceeded {seconds}s timeout"
        )

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

**Acceptance Criteria**:
- Timeout raises ContainerTimeoutError
- Container is terminated when timeout fires
- Timeout value configurable per agent
- Works with pytest-timeout integration

### T022: Create container_fixtures.py with TestContainer management

Create `tests/agentic/fixtures/container_fixtures.py`:

```python
"""Container lifecycle management fixtures."""

import pytest
from dataclasses import dataclass
from typing import Optional, Dict, Any
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

@dataclass
class ResourceLimits:
    """Container resource constraints."""
    cpu_cores: float = 2.0
    memory_mb: int = 4096
    disk_mb: int = 10240

@dataclass
class TestContainer:
    """Wrapper for test container with metadata."""
    container_id: str
    agent_id: str
    container: DockerContainer
    resource_limits: ResourceLimits
    worktree_path: str

    def exec_command(self, cmd: str, timeout: int = 300) -> tuple[int, str, str]:
        """Execute command in container with timeout."""
        ...

class AgentContainerFactory:
    """Factory for creating agent-specific containers."""

    def __init__(self, image: str = "spec-kitty-agent:latest"):
        self.image = image
        self._network = None

    def create_container(
        self,
        agent_id: str,
        worktree_path: str,
        resource_limits: Optional[ResourceLimits] = None,
        secrets: Optional[Dict[str, str]] = None
    ) -> TestContainer:
        """Create isolated container for agent execution."""
        limits = resource_limits or ResourceLimits()

        container = (
            DockerContainer(self.image)
            .with_network(self._get_internal_network())
            .with_volume_mapping(worktree_path, "/workspace", "rw")
            .with_env("AGENT_ID", agent_id)
        )

        # Apply resource limits
        container.with_kwargs(
            cpu_period=100000,
            cpu_quota=int(limits.cpu_cores * 100000),
            mem_limit=f"{limits.memory_mb}m"
        )

        # Mount secrets
        if secrets:
            for name, path in secrets.items():
                container.with_volume_mapping(path, f"/run/secrets/{name}", "ro")

        container.start()

        return TestContainer(
            container_id=container.get_container_id(),
            agent_id=agent_id,
            container=container,
            resource_limits=limits,
            worktree_path=worktree_path
        )

@pytest.fixture(scope="session")
def container_factory():
    """Session-scoped factory for creating test containers."""
    factory = AgentContainerFactory()
    yield factory
    # Cleanup happens automatically via testcontainers

@pytest.fixture(scope="function")
def test_container(container_factory, agent_config, tmp_worktree):
    """Function-scoped container for a single test."""
    container = container_factory.create_container(
        agent_id=agent_config.agent_id,
        worktree_path=tmp_worktree,
        resource_limits=agent_config.resource_limits
    )
    yield container
    container.container.stop()
```

**Acceptance Criteria**:
- Session-scoped factory for expensive image operations
- Function-scoped containers for test isolation
- Resource limits applied via Docker kwargs
- Automatic cleanup on test completion
- Worktree mounted as only writable path

### T023: Create agent_fixtures.py for agent config loading

Create `tests/agentic/fixtures/agent_fixtures.py`:

```python
"""Agent configuration and detection fixtures."""

import pytest
import yaml
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class InvocationPattern(Enum):
    STDIN = "stdin"
    ARGUMENT = "argument"
    FILE = "file"

@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    agent_id: str
    enabled: bool
    command: str
    invocation_pattern: InvocationPattern
    timeout_seconds: int
    credentials_secret: str
    requires_timeout_wrapper: bool
    resource_limits: 'ResourceLimits'

    @property
    def is_available(self) -> bool:
        """Check if agent is installed and credentials exist."""
        return self._check_installed() and self._check_credentials()

    def _check_installed(self) -> bool:
        """Check if agent CLI is installed."""
        cmd = self.command.split()[0]
        return shutil.which(cmd) is not None

    def _check_credentials(self) -> bool:
        """Check if credentials file exists."""
        secrets_dir = Path(__file__).parent.parent / "config" / "secrets"
        return (secrets_dir / f"{self.credentials_secret}.txt").exists()

class AgentRegistry:
    """Registry of available agents loaded from config."""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._agents: Dict[str, AgentConfig] = {}
        self._load_config()

    def _load_config(self):
        """Load agent configuration from YAML."""
        with open(self._config_path) as f:
            data = yaml.safe_load(f)

        defaults = data.get('defaults', {})

        for agent_id, config in data.get('agents', {}).items():
            limits_data = config.get('resource_limits', defaults.get('resource_limits', {}))

            self._agents[agent_id] = AgentConfig(
                agent_id=agent_id,
                enabled=config.get('enabled', True),
                command=config['command'],
                invocation_pattern=InvocationPattern(config['invocation_pattern']),
                timeout_seconds=config.get('timeout_seconds', defaults.get('timeout_seconds', 300)),
                credentials_secret=config['credentials_secret'],
                requires_timeout_wrapper=config.get('requires_timeout_wrapper', False),
                resource_limits=ResourceLimits(
                    cpu_cores=limits_data.get('cpu_cores', 2.0),
                    memory_mb=limits_data.get('memory_mb', 4096),
                    disk_mb=limits_data.get('disk_mb', 10240)
                )
            )

    def get_available_agents(self) -> List[AgentConfig]:
        """Return list of agents that are installed and enabled."""
        return [
            agent for agent in self._agents.values()
            if agent.enabled and agent.is_available
        ]

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get specific agent config by ID."""
        return self._agents.get(agent_id)

@pytest.fixture(scope="session")
def agent_registry():
    """Session-scoped agent registry."""
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    return AgentRegistry(config_path)

@pytest.fixture(scope="session")
def available_agents(agent_registry):
    """List of agents available for testing."""
    agents = agent_registry.get_available_agents()
    if not agents:
        pytest.skip("No agents available for testing")
    return agents
```

**Acceptance Criteria**:
- Loads configuration from agents.yaml
- Detects installed agents via `shutil.which()`
- Checks for credentials files
- Session-scoped for efficiency
- Skips tests when no agents available

### T009: Implement agent detection (installed + authenticated)

Extend agent detection with authentication verification:

```python
# In agent_fixtures.py

def _check_authenticated(self) -> bool:
    """Verify agent is authenticated by running a minimal command."""
    try:
        # Agent-specific auth checks
        if self.agent_id == "claude-code":
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        elif self.agent_id == "github-copilot":
            result = subprocess.run(
                ["copilot", "auth", "status"],
                capture_output=True,
                timeout=10
            )
            return "Logged in" in result.stdout.decode()
        # ... other agents
        return True  # Default to installed check only
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

**Acceptance Criteria**:
- Verifies installation AND authentication
- Agent-specific authentication checks
- Timeout on auth check commands
- Handles command failures gracefully

### T010: Implement graceful skip for unavailable agents

Add skip markers for unavailable agents:

```python
# In agent_fixtures.py

def skip_if_agent_unavailable(agent_id: str):
    """Pytest marker to skip test if agent unavailable."""
    def decorator(func):
        @pytest.mark.skipif(
            not _is_agent_available(agent_id),
            reason=f"Agent {agent_id} not available"
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

@pytest.fixture
def require_agent(agent_registry):
    """Fixture that skips test if required agent unavailable."""
    def _require(agent_id: str) -> AgentConfig:
        agent = agent_registry.get_agent(agent_id)
        if not agent or not agent.is_available:
            pytest.skip(f"Agent {agent_id} not available")
        return agent
    return _require

# Usage in tests:
# @skip_if_agent_unavailable("claude-code")
# def test_claude_workflow():
#     ...
```

**Acceptance Criteria**:
- Tests skip cleanly when agent unavailable
- Skip message identifies the missing agent
- Works with parameterized tests
- Does not fail the test suite

## Technical Notes

- Use testcontainers-python 4.14.0 per research.md
- Session scope for expensive operations (registry, factory)
- Function scope for isolation (individual containers)
- Import ResourceLimits from container_fixtures in agent_fixtures

## Files to Create/Modify

1. `tests/agentic/fixtures/__init__.py` (update exports)
2. `tests/agentic/fixtures/container_fixtures.py` (create)
3. `tests/agentic/fixtures/agent_fixtures.py` (create)
4. `tests/agentic/conftest.py` (import and expose fixtures)

## Verification

```bash
# Run fixture tests
pytest tests/agentic/ -v --collect-only

# Test agent detection
python -c "
from tests.agentic.fixtures.agent_fixtures import AgentRegistry
from pathlib import Path
registry = AgentRegistry(Path('tests/agentic/config/agents.yaml'))
print(f'Available agents: {[a.agent_id for a in registry.get_available_agents()]}')
"

# Test container creation (requires Docker)
pytest tests/agentic/fixtures/ -v -k "container"
```

## Definition of Done

- [ ] container_fixtures.py with TestContainer class
- [ ] AgentContainerFactory with resource limits
- [ ] agent_fixtures.py with AgentRegistry
- [ ] Agent detection (installed + authenticated)
- [ ] Graceful skip for unavailable agents
- [ ] Timeout enforcement implemented
- [ ] All fixtures exposed in conftest.py
- [ ] Unit tests for fixture logic pass

## Activity Log

- 2026-01-19T10:19:59Z – claude-opus – shell_pid=30118 – lane=doing – Started implementation via workflow command
