"""Agent configuration and detection fixtures for agentic E2E testing.

This module provides:
- AgentConfig: Dataclass for agent configuration
- AgentRegistry: Loads and validates agent configurations from YAML
- Agent detection: Checks if agents are installed and authenticated
- Skip decorators: Graceful skip for unavailable agents

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import functools
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, TypeVar

import pytest
import yaml

from .container_fixtures import ResourceLimits

if TYPE_CHECKING:
    from ..invoker.discovery import AgentDiscovery
    from ..agents.base import BaseAgentConfig


class InvocationPattern(Enum):
    """Agent invocation pattern for prompt input.

    Per research.md E007: Agent invocation patterns from Feature 020
    """

    STDIN = "stdin"  # Prompt via stdin
    ARGUMENT = "argument"  # Prompt as CLI argument
    FILE = "file"  # Prompt from file path


@dataclass
class AgentConfig:
    """Configuration for a single AI coding agent.

    Loaded from agents.yaml and validated on construction.

    Attributes:
        agent_id: Unique identifier (e.g., "claude-code", "github-copilot")
        enabled: Whether the agent is enabled for testing
        command: CLI command to invoke the agent
        invocation_pattern: How prompts are passed to the agent
        headless_flag: Flag to run in headless/non-interactive mode
        json_output_flag: Flag to enable JSON output
        timeout_seconds: Default timeout for agent commands
        credentials_secret: Name of the credentials file in secrets/
        requires_timeout_wrapper: Whether agent needs external timeout wrapper
        resource_limits: CPU, memory, and disk constraints
        invocation_config: Optional link to BaseAgentConfig for invoker integration
    """

    agent_id: str
    enabled: bool
    command: str
    invocation_pattern: InvocationPattern
    headless_flag: str
    json_output_flag: str
    timeout_seconds: int
    credentials_secret: str
    requires_timeout_wrapper: bool
    resource_limits: ResourceLimits
    invocation_config: Optional["BaseAgentConfig"] = field(default=None)

    @property
    def is_available(self) -> bool:
        """Check if agent is installed, has credentials, and is authenticated.

        Returns:
            True if agent can be used for testing
        """
        return (
            self._check_installed()
            and self._check_credentials()
            and self._check_authenticated()
        )

    @property
    def is_installed(self) -> bool:
        """Check only if agent CLI is installed."""
        return self._check_installed()

    @property
    def has_credentials(self) -> bool:
        """Check only if credentials file exists."""
        return self._check_credentials()

    def _check_installed(self) -> bool:
        """Check if agent CLI is installed and in PATH.

        Returns:
            True if the agent's command is executable
        """
        cmd = self.command.split()[0]
        return shutil.which(cmd) is not None

    def _check_credentials(self) -> bool:
        """Check if credentials file exists.

        Returns:
            True if the credentials file exists and is non-empty
        """
        secrets_dir = Path(__file__).parent.parent / "config" / "secrets"
        creds_file = secrets_dir / f"{self.credentials_secret}.txt"

        if not creds_file.exists():
            return False

        # Check if file has content (not just placeholder)
        content = creds_file.read_text().strip()
        return bool(content) and content != "placeholder"

    def _check_authenticated(self) -> bool:
        """Verify agent is authenticated by running a minimal command.

        Each agent has its own authentication check method.

        Returns:
            True if agent is properly authenticated
        """
        try:
            if self.agent_id == "claude-code":
                result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "github-copilot":
                result = subprocess.run(
                    ["copilot", "auth", "status"],
                    capture_output=True,
                    timeout=10,
                )
                return "Logged in" in result.stdout.decode()

            elif self.agent_id == "github-codex":
                result = subprocess.run(
                    ["codex", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "google-gemini":
                result = subprocess.run(
                    ["gemini", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "cursor":
                result = subprocess.run(
                    ["cursor", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "qwen-code":
                result = subprocess.run(
                    ["qwen", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "opencode":
                result = subprocess.run(
                    ["opencode", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "kilocode":
                result = subprocess.run(
                    ["kilocode", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            elif self.agent_id == "augment-code":
                result = subprocess.run(
                    ["auggie", "--version"],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0

            # Unknown agent - fall back to installed check only
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_availability_reason(self) -> str:
        """Get human-readable reason why agent is unavailable.

        Returns:
            Empty string if available, otherwise reason for unavailability
        """
        if not self._check_installed():
            return f"CLI command '{self.command.split()[0]}' not found in PATH"
        if not self._check_credentials():
            return f"Credentials file '{self.credentials_secret}.txt' missing or empty"
        if not self._check_authenticated():
            return "Authentication check failed"
        return ""


class AgentRegistry:
    """Registry of available agents loaded from configuration.

    Loads agent configurations from agents.yaml and provides
    methods to query available agents.

    Attributes:
        config_path: Path to agents.yaml configuration file
        discovery: Optional AgentDiscovery for runtime agent detection
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        discovery: Optional["AgentDiscovery"] = None,
    ):
        """Initialize registry from configuration file.

        Args:
            config_path: Path to agents.yaml (defaults to config/agents.yaml)
            discovery: Optional AgentDiscovery for runtime detection
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "agents.yaml"

        self._config_path = config_path
        self._agents: Dict[str, AgentConfig] = {}
        self._defaults: Dict = {}
        self._discovery = discovery
        self._load_config()

    def _load_config(self):
        """Load agent configuration from YAML file."""
        with open(self._config_path) as f:
            data = yaml.safe_load(f)

        self._defaults = data.get("defaults", {})
        defaults = self._defaults
        default_limits = defaults.get("resource_limits", {})

        for agent_id, config in data.get("agents", {}).items():
            limits_data = config.get("resource_limits", default_limits)

            self._agents[agent_id] = AgentConfig(
                agent_id=agent_id,
                enabled=config.get("enabled", True),
                command=config["command"],
                invocation_pattern=InvocationPattern(config["invocation_pattern"]),
                headless_flag=config.get("headless_flag", ""),
                json_output_flag=config.get("json_output_flag", ""),
                timeout_seconds=config.get(
                    "timeout_seconds", defaults.get("timeout_seconds", 300)
                ),
                credentials_secret=config["credentials_secret"],
                requires_timeout_wrapper=config.get(
                    "requires_timeout_wrapper",
                    defaults.get("requires_timeout_wrapper", False),
                ),
                resource_limits=ResourceLimits(
                    cpu_cores=limits_data.get("cpu_cores", 2.0),
                    memory_mb=limits_data.get("memory_mb", 4096),
                    disk_mb=limits_data.get("disk_mb", 10240),
                ),
            )

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get specific agent config by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentConfig if found, None otherwise
        """
        return self._agents.get(agent_id)

    def get_all_agents(self) -> List[AgentConfig]:
        """Return list of all configured agents."""
        return list(self._agents.values())

    def get_enabled_agents(self) -> List[AgentConfig]:
        """Return list of enabled agents (may not be installed)."""
        return [agent for agent in self._agents.values() if agent.enabled]

    def get_available_agents(self) -> List[AgentConfig]:
        """Return list of agents that are installed, enabled, and authenticated.

        Returns:
            List of AgentConfig for all available agents
        """
        return [
            agent
            for agent in self._agents.values()
            if agent.enabled and agent.is_available
        ]

    def get_installed_agents(self) -> List[AgentConfig]:
        """Return list of agents that are installed (enabled or not)."""
        return [agent for agent in self._agents.values() if agent.is_installed]

    def set_discovery(self, discovery: "AgentDiscovery") -> None:
        """Set the AgentDiscovery instance for runtime detection.

        Args:
            discovery: AgentDiscovery instance to use
        """
        self._discovery = discovery

    def refresh_availability(self) -> None:
        """Refresh agent availability from discovery.

        Uses the AgentDiscovery to update availability status
        and link invocation configs for all registered agents.
        """
        if self._discovery is None:
            return

        for discovered in self._discovery.discover_all(use_cache=False):
            if discovered.agent_id in self._agents:
                agent = self._agents[discovered.agent_id]
                # Update enabled based on discovery availability
                # Note: We use object.__setattr__ because dataclass may be frozen
                # in some configurations
                agent.enabled = discovered.is_available
                agent.invocation_config = discovered.config

    def get_invocation_configs(self) -> List["BaseAgentConfig"]:
        """Return list of BaseAgentConfig for available agents.

        Returns:
            List of invocation configs for agents that have them
        """
        return [
            agent.invocation_config
            for agent in self._agents.values()
            if agent.invocation_config is not None
        ]


class DynamicAgentRegistry(AgentRegistry):
    """Agent registry that supports runtime configuration updates.

    Extends AgentRegistry with methods to add, remove, and update agents
    at runtime. This is useful for testing scenarios where agent
    configuration needs to change during test execution.

    T011: Support dynamic agent configuration loading
    """

    def add_agent(self, agent_config: AgentConfig) -> None:
        """Add a new agent at runtime.

        Args:
            agent_config: Configuration for the new agent
        """
        self._agents[agent_config.agent_id] = agent_config

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from registry.

        Args:
            agent_id: ID of the agent to remove

        Returns:
            True if agent was removed, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def update_agent(self, agent_id: str, **kwargs) -> bool:
        """Update agent configuration.

        Updates only the specified fields, leaving others unchanged.

        Args:
            agent_id: ID of the agent to update
            **kwargs: Fields to update (e.g., timeout_seconds=600)

        Returns:
            True if agent was updated, False if not found
        """
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]
        for key, value in kwargs.items():
            if hasattr(agent, key):
                # Handle special cases for nested objects
                if key == "resource_limits" and isinstance(value, dict):
                    current_limits = agent.resource_limits
                    new_limits = ResourceLimits(
                        cpu_cores=value.get("cpu_cores", current_limits.cpu_cores),
                        memory_mb=value.get("memory_mb", current_limits.memory_mb),
                        disk_mb=value.get("disk_mb", current_limits.disk_mb),
                    )
                    object.__setattr__(agent, key, new_limits)
                elif key == "invocation_pattern" and isinstance(value, str):
                    object.__setattr__(agent, key, InvocationPattern(value))
                else:
                    object.__setattr__(agent, key, value)
        return True

    def reload_config(self) -> None:
        """Reload configuration from YAML file.

        Clears all current agents and reloads from the original config file.
        """
        self._agents.clear()
        self._load_config()

    def create_agent_from_dict(self, agent_id: str, config: Dict) -> AgentConfig:
        """Create an AgentConfig from a dictionary.

        Useful for creating agents from test data.

        Args:
            agent_id: ID for the new agent
            config: Configuration dictionary

        Returns:
            New AgentConfig instance
        """
        defaults = self._defaults
        default_limits = defaults.get("resource_limits", {})
        limits_data = config.get("resource_limits", default_limits)

        return AgentConfig(
            agent_id=agent_id,
            enabled=config.get("enabled", True),
            command=config.get("command", "echo"),
            invocation_pattern=InvocationPattern(
                config.get("invocation_pattern", "stdin")
            ),
            headless_flag=config.get("headless_flag", ""),
            json_output_flag=config.get("json_output_flag", ""),
            timeout_seconds=config.get(
                "timeout_seconds", defaults.get("timeout_seconds", 300)
            ),
            credentials_secret=config.get("credentials_secret", "none"),
            requires_timeout_wrapper=config.get(
                "requires_timeout_wrapper",
                defaults.get("requires_timeout_wrapper", False),
            ),
            resource_limits=ResourceLimits(
                cpu_cores=limits_data.get("cpu_cores", 2.0),
                memory_mb=limits_data.get("memory_mb", 4096),
                disk_mb=limits_data.get("disk_mb", 10240),
            ),
        )


# Type variable for decorator return type preservation
F = TypeVar("F", bound=Callable)


def _is_agent_available(agent_id: str) -> bool:
    """Check if a specific agent is available.

    Used by skip decorators to check availability at test collection time.
    """
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    registry = AgentRegistry(config_path)
    agent = registry.get_agent(agent_id)
    return agent is not None and agent.is_available


def skip_if_agent_unavailable(agent_id: str) -> Callable[[F], F]:
    """Decorator to skip test if specified agent is unavailable.

    Usage:
        @skip_if_agent_unavailable("claude-code")
        def test_claude_workflow():
            ...

    Args:
        agent_id: ID of the agent to check

    Returns:
        Decorator function that wraps the test
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        @pytest.mark.skipif(
            not _is_agent_available(agent_id),
            reason=f"Agent '{agent_id}' not available",
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_agents(*agent_ids: str) -> Callable[[F], F]:
    """Decorator to skip test if ANY of the specified agents are unavailable.

    Useful for tests that require multiple agents (e.g., cross-review tests).

    Usage:
        @require_agents("claude-code", "github-copilot")
        def test_cross_review():
            ...

    Args:
        agent_ids: IDs of all required agents

    Returns:
        Decorator function that wraps the test
    """
    def decorator(func: F) -> F:
        unavailable = [
            agent_id for agent_id in agent_ids if not _is_agent_available(agent_id)
        ]

        @functools.wraps(func)
        @pytest.mark.skipif(
            bool(unavailable),
            reason=f"Required agents not available: {', '.join(unavailable)}",
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# === Pytest Fixtures ===


@pytest.fixture(scope="session")
def agent_registry() -> AgentRegistry:
    """Session-scoped agent registry.

    Loads configuration once per test session for efficiency.

    Returns:
        AgentRegistry instance
    """
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    return AgentRegistry(config_path)


@pytest.fixture(scope="session")
def available_agents(agent_registry: AgentRegistry) -> List[AgentConfig]:
    """List of agents available for testing.

    Skips the entire test session if no agents are available.

    Args:
        agent_registry: The agent registry fixture

    Returns:
        List of available AgentConfig instances
    """
    agents = agent_registry.get_available_agents()
    if not agents:
        pytest.skip("No agents available for testing")
    return agents


@pytest.fixture
def require_agent(agent_registry: AgentRegistry) -> Callable[[str], AgentConfig]:
    """Fixture that provides a function to require a specific agent.

    Skips the test if the required agent is unavailable.

    Usage:
        def test_something(require_agent):
            claude = require_agent("claude-code")
            # test using claude config...

    Returns:
        Function that takes agent_id and returns AgentConfig or skips
    """
    def _require(agent_id: str) -> AgentConfig:
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            pytest.skip(f"Agent '{agent_id}' not configured")
        if not agent.enabled:
            pytest.skip(f"Agent '{agent_id}' is disabled")
        if not agent.is_available:
            reason = agent.get_availability_reason()
            pytest.skip(f"Agent '{agent_id}' not available: {reason}")
        return agent

    return _require


@pytest.fixture
def agent_config(request, agent_registry: AgentRegistry) -> AgentConfig:
    """Get agent configuration for parameterized tests.

    Expects the test to be parameterized with agent_id.

    Usage:
        @pytest.mark.parametrize("agent_id", ["claude-code", "github-copilot"])
        def test_agent_workflow(agent_config):
            # agent_config is the AgentConfig for the parameterized agent_id

    Returns:
        AgentConfig for the parameterized agent
    """
    agent_id = request.param if hasattr(request, "param") else request.node.name

    agent = agent_registry.get_agent(agent_id)
    if not agent:
        pytest.skip(f"Agent '{agent_id}' not configured")
    if not agent.is_available:
        reason = agent.get_availability_reason()
        pytest.skip(f"Agent '{agent_id}' not available: {reason}")

    return agent
