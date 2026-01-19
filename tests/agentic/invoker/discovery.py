"""
Agent discovery system for runtime detection of available agents.

Provides:
- AvailabilityResult: Result of checking agent availability
- DiscoveredAgent: An agent discovered on the host
- AgentDiscovery: Main discovery engine
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..agents.base import BaseAgentConfig


@dataclass
class AvailabilityResult:
    """Result of checking agent availability."""

    installed: bool
    authenticated: bool
    version: Optional[str]
    error: Optional[str] = None

    @property
    def available(self) -> bool:
        """Agent is available if installed AND authenticated."""
        return self.installed and self.authenticated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "installed": self.installed,
            "authenticated": self.authenticated,
            "version": self.version,
            "error": self.error,
            "available": self.available,
        }


@dataclass
class DiscoveredAgent:
    """An agent discovered on the host."""

    agent_id: str
    config: "BaseAgentConfig"
    version: Optional[str]
    authenticated: bool
    unavailable_reason: Optional[str] = None

    @property
    def is_available(self) -> bool:
        """Check if agent can be used."""
        return self.authenticated and self.unavailable_reason is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "authenticated": self.authenticated,
            "unavailable_reason": self.unavailable_reason,
            "is_available": self.is_available,
        }


class AgentDiscovery:
    """
    Discovers available agents at runtime.

    Provides methods to check which AI coding agents are installed
    and authenticated on the current machine, with caching support
    for performance.
    """

    def __init__(
        self,
        agent_configs: Optional[List["BaseAgentConfig"]] = None,
    ):
        """
        Initialize with list of agent configurations to check.

        Args:
            agent_configs: List of agent configs to probe. If None, uses
                          an empty list (configs can be added via register_config).
        """
        self._configs: List["BaseAgentConfig"] = list(agent_configs or [])
        self._cache: Dict[str, DiscoveredAgent] = {}
        self._cache_valid = False

    def check_availability(
        self,
        agent_config: "BaseAgentConfig",
    ) -> AvailabilityResult:
        """
        Check if a specific agent is available.

        Runs:
        1. agent_config.check_installed() - verify CLI exists
        2. agent_config.check_authenticated() - verify credentials

        Args:
            agent_config: The agent configuration to check

        Returns:
            AvailabilityResult with detailed status
        """
        # Check installation
        installed, install_info = agent_config.check_installed()
        if not installed:
            return AvailabilityResult(
                installed=False,
                authenticated=False,
                version=None,
                error=install_info or "CLI not found in PATH",
            )

        # Version might be in install_info
        version = install_info if installed else None

        # Check authentication
        authenticated, auth_error = agent_config.check_authenticated()
        return AvailabilityResult(
            installed=True,
            authenticated=authenticated,
            version=version,
            error=auth_error if not authenticated else None,
        )

    def discover_one(self, agent_id: str) -> Optional[DiscoveredAgent]:
        """
        Discover a specific agent by ID.

        Args:
            agent_id: The agent identifier to find

        Returns:
            DiscoveredAgent if found, None if no config registered
        """
        config = next(
            (c for c in self._configs if c.agent_id == agent_id),
            None,
        )
        if config is None:
            return None

        result = self.check_availability(config)
        return DiscoveredAgent(
            agent_id=agent_id,
            config=config,
            version=result.version,
            authenticated=result.authenticated,
            unavailable_reason=result.error if not result.available else None,
        )

    def discover_all(self, use_cache: bool = True) -> List[DiscoveredAgent]:
        """
        Discover all registered agents.

        Args:
            use_cache: If True, return cached results if available

        Returns:
            List of DiscoveredAgent for all registered configs
        """
        if use_cache and self._cache_valid:
            return list(self._cache.values())

        self._cache.clear()
        for config in self._configs:
            result = self.check_availability(config)
            discovered = DiscoveredAgent(
                agent_id=config.agent_id,
                config=config,
                version=result.version,
                authenticated=result.authenticated,
                unavailable_reason=result.error if not result.available else None,
            )
            self._cache[config.agent_id] = discovered

        self._cache_valid = True
        return list(self._cache.values())

    def get_available(self) -> List[DiscoveredAgent]:
        """Return only agents that are available for use."""
        return [a for a in self.discover_all() if a.is_available]

    def get_unavailable(self) -> List[DiscoveredAgent]:
        """Return agents that are not available, with reasons."""
        return [a for a in self.discover_all() if not a.is_available]

    def invalidate_cache(self) -> None:
        """Force re-discovery on next call."""
        self._cache_valid = False
        self._cache.clear()

    def register_config(self, config: "BaseAgentConfig") -> None:
        """
        Add an agent config to the discovery list.

        Args:
            config: The agent configuration to add
        """
        self._configs.append(config)
        self._cache_valid = False

    def unregister_config(self, agent_id: str) -> bool:
        """
        Remove an agent config from the discovery list.

        Args:
            agent_id: ID of the agent to remove

        Returns:
            True if removed, False if not found
        """
        for i, config in enumerate(self._configs):
            if config.agent_id == agent_id:
                del self._configs[i]
                self._cache_valid = False
                return True
        return False

    @property
    def registered_agents(self) -> List[str]:
        """List of registered agent IDs."""
        return [c.agent_id for c in self._configs]

    def get_config(self, agent_id: str) -> Optional["BaseAgentConfig"]:
        """
        Get the configuration for a specific agent.

        Args:
            agent_id: The agent identifier

        Returns:
            BaseAgentConfig if found, None otherwise
        """
        return next(
            (c for c in self._configs if c.agent_id == agent_id),
            None,
        )
