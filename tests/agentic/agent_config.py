"""User-configurable agent selection for agentic E2E testing.

This module provides the ability for users to configure which AI coding agents
to use for implementation and review tasks. Preferences can be stored in
`.kittify/config.yaml` and overridden via CLI flags.

Supports two selection strategies:
1. "preferred" - User specifies preferred implementer and reviewer agents
2. "random" - Randomly selects from available agents

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .agents.base import BaseAgentConfig


# Selection strategy constants
STRATEGY_PREFERRED = "preferred"
STRATEGY_RANDOM = "random"
VALID_STRATEGIES = [STRATEGY_PREFERRED, STRATEGY_RANDOM]


@dataclass
class AgentConfig:
    """User-configured agent selection preferences.

    Stores available agents and selection preferences for both
    implementation and review tasks.

    Attributes:
        available_agents: List of agent IDs that are installed and authenticated
        selection_strategy: "preferred" or "random"
        preferred_implementer: Agent ID for implementation (when strategy="preferred")
        preferred_reviewer: Agent ID for review (when strategy="preferred")
    """

    available_agents: List[str] = field(default_factory=list)
    selection_strategy: str = STRATEGY_PREFERRED
    preferred_implementer: Optional[str] = None
    preferred_reviewer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to YAML-serializable dictionary."""
        return {
            "available_agents": self.available_agents,
            "selection_strategy": self.selection_strategy,
            "preferred_implementer": self.preferred_implementer,
            "preferred_reviewer": self.preferred_reviewer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dictionary (e.g., loaded from YAML)."""
        return cls(
            available_agents=data.get("available_agents", []),
            selection_strategy=data.get("selection_strategy", STRATEGY_PREFERRED),
            preferred_implementer=data.get("preferred_implementer"),
            preferred_reviewer=data.get("preferred_reviewer"),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if self.selection_strategy not in VALID_STRATEGIES:
            errors.append(
                f"Invalid selection_strategy '{self.selection_strategy}'. "
                f"Must be one of: {VALID_STRATEGIES}"
            )

        if self.selection_strategy == STRATEGY_PREFERRED:
            if self.preferred_implementer and self.preferred_implementer not in self.available_agents:
                errors.append(
                    f"Preferred implementer '{self.preferred_implementer}' "
                    f"not in available_agents: {self.available_agents}"
                )
            if self.preferred_reviewer and self.preferred_reviewer not in self.available_agents:
                errors.append(
                    f"Preferred reviewer '{self.preferred_reviewer}' "
                    f"not in available_agents: {self.available_agents}"
                )

        return errors


class AgentSelectionConfig:
    """Manages agent selection based on user configuration.

    Provides methods to select implementer and reviewer agents
    based on the configured selection strategy.

    Attributes:
        config: AgentConfig with user preferences
        agent_configs: Dictionary mapping agent_id to BaseAgentConfig
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_configs: Optional[Dict[str, "BaseAgentConfig"]] = None,
    ):
        """Initialize selection config.

        Args:
            config: AgentConfig with user preferences
            agent_configs: Optional mapping of agent_id to config objects
        """
        self.config = config
        self.agent_configs = agent_configs or {}

    def select_implementer(
        self,
        override: Optional[str] = None,
    ) -> Optional[str]:
        """Select agent for implementation task.

        Args:
            override: CLI override (takes precedence if provided)

        Returns:
            Agent ID or None if no agents available
        """
        # CLI override takes precedence
        if override:
            if override in self.config.available_agents:
                return override
            raise ValueError(
                f"Override agent '{override}' not in available agents: "
                f"{self.config.available_agents}"
            )

        if not self.config.available_agents:
            return None

        if self.config.selection_strategy == STRATEGY_PREFERRED:
            # Use preferred or fall back to first available
            if self.config.preferred_implementer:
                return self.config.preferred_implementer
            return self.config.available_agents[0]

        elif self.config.selection_strategy == STRATEGY_RANDOM:
            return random.choice(self.config.available_agents)

        # Default fallback
        return self.config.available_agents[0] if self.config.available_agents else None

    def select_reviewer(
        self,
        override: Optional[str] = None,
        different_from: Optional[str] = None,
    ) -> Optional[str]:
        """Select agent for review task.

        Args:
            override: CLI override (takes precedence if provided)
            different_from: Agent ID that reviewer must be different from
                           (for DIFFERENT_FROM constraint in cross-review)

        Returns:
            Agent ID or None if no agents available
        """
        # CLI override takes precedence
        if override:
            if override in self.config.available_agents:
                if different_from and override == different_from:
                    raise ValueError(
                        f"Override reviewer '{override}' cannot be same as "
                        f"implementer '{different_from}' with DIFFERENT_FROM constraint"
                    )
                return override
            raise ValueError(
                f"Override agent '{override}' not in available agents: "
                f"{self.config.available_agents}"
            )

        if not self.config.available_agents:
            return None

        # Filter out the different_from agent if specified
        candidates = self.config.available_agents
        if different_from:
            candidates = [a for a in candidates if a != different_from]
            if not candidates:
                # Only one agent available and it's the one we can't use
                return None

        if self.config.selection_strategy == STRATEGY_PREFERRED:
            # Use preferred if it's valid
            if self.config.preferred_reviewer:
                if self.config.preferred_reviewer in candidates:
                    return self.config.preferred_reviewer
                # Preferred not available, fall through to first candidate
            return candidates[0] if candidates else None

        elif self.config.selection_strategy == STRATEGY_RANDOM:
            return random.choice(candidates) if candidates else None

        # Default fallback
        return candidates[0] if candidates else None

    def get_agent_config(self, agent_id: str) -> Optional["BaseAgentConfig"]:
        """Get BaseAgentConfig for an agent ID.

        Args:
            agent_id: The agent ID to look up

        Returns:
            BaseAgentConfig or None if not found
        """
        return self.agent_configs.get(agent_id)


def get_config_path(project_root: Optional[Path] = None) -> Path:
    """Get path to .kittify/config.yaml.

    Args:
        project_root: Project root directory (defaults to current directory)

    Returns:
        Path to config file
    """
    root = project_root or Path.cwd()
    return root / ".kittify" / "config.yaml"


def load_agent_config(
    project_root: Optional[Path] = None,
) -> Optional[AgentConfig]:
    """Load agent configuration from .kittify/config.yaml.

    Args:
        project_root: Project root directory (defaults to current directory)

    Returns:
        AgentConfig or None if file doesn't exist
    """
    config_path = get_config_path(project_root)

    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        # Agent config is under 'agent_selection' key
        agent_data = data.get("agent_selection", {})
        if not agent_data:
            return None

        return AgentConfig.from_dict(agent_data)
    except Exception:
        return None


def save_agent_config(
    config: AgentConfig,
    project_root: Optional[Path] = None,
) -> Path:
    """Save agent configuration to .kittify/config.yaml.

    Args:
        config: AgentConfig to save
        project_root: Project root directory (defaults to current directory)

    Returns:
        Path to saved config file
    """
    config_path = get_config_path(project_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config to preserve other settings
    existing = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                existing = yaml.safe_load(f) or {}
        except Exception:
            existing = {}

    # Update agent_selection section
    existing["agent_selection"] = config.to_dict()

    with open(config_path, "w") as f:
        yaml.safe_dump(existing, f, default_flow_style=False, sort_keys=False)

    return config_path


def create_agent_selection_config(
    available_agent_configs: List["BaseAgentConfig"],
    project_root: Optional[Path] = None,
) -> AgentSelectionConfig:
    """Create AgentSelectionConfig from available agent configs.

    Loads user preferences from .kittify/config.yaml if they exist,
    otherwise uses defaults.

    Args:
        available_agent_configs: List of available BaseAgentConfig objects
        project_root: Project root directory (defaults to current directory)

    Returns:
        AgentSelectionConfig ready for use
    """
    # Build agent_id -> config mapping
    agent_configs_map = {cfg.agent_id: cfg for cfg in available_agent_configs}
    available_agent_ids = list(agent_configs_map.keys())

    # Load user config
    user_config = load_agent_config(project_root)

    if user_config:
        # Update available_agents to reflect what's actually available
        user_config.available_agents = available_agent_ids
    else:
        # Create default config
        user_config = AgentConfig(
            available_agents=available_agent_ids,
            selection_strategy=STRATEGY_PREFERRED,
            preferred_implementer=available_agent_ids[0] if available_agent_ids else None,
            preferred_reviewer=available_agent_ids[0] if available_agent_ids else None,
        )

    return AgentSelectionConfig(
        config=user_config,
        agent_configs=agent_configs_map,
    )


# =============================================================================
# T020: Init Flow Helpers (for spec-kitty init integration)
# =============================================================================


def prompt_agent_selection(
    available_agents: List[str],
    prompt_func: Optional[callable] = None,
) -> AgentConfig:
    """Interactive prompt for agent selection configuration.

    This function is designed to be called during `spec-kitty init` to
    gather user preferences for agent selection.

    Args:
        available_agents: List of available agent IDs
        prompt_func: Optional custom prompt function (for testing)
                    Default uses input() for interactive prompts

    Returns:
        AgentConfig with user preferences

    Raises:
        ValueError: If no agents available
    """
    if not available_agents:
        raise ValueError("No agents available. Please install at least one agent.")

    # Default to input() for interactive prompts
    if prompt_func is None:
        prompt_func = input

    print("\n=== Agent Selection Configuration ===\n")
    print("Available agents:")
    for i, agent_id in enumerate(available_agents, 1):
        print(f"  {i}. {agent_id}")
    print()

    # Prompt for selection strategy
    print("Selection strategy:")
    print("  1. Preferred - Always use specific agents")
    print("  2. Random - Randomly select from available agents")
    print()

    strategy_choice = prompt_func("Enter choice (1 or 2) [1]: ").strip() or "1"
    selection_strategy = STRATEGY_PREFERRED if strategy_choice == "1" else STRATEGY_RANDOM

    preferred_implementer = None
    preferred_reviewer = None

    if selection_strategy == STRATEGY_PREFERRED:
        # Prompt for preferred implementer
        print("\nSelect preferred implementation agent:")
        for i, agent_id in enumerate(available_agents, 1):
            print(f"  {i}. {agent_id}")

        impl_choice = prompt_func(f"Enter number [1]: ").strip() or "1"
        try:
            impl_idx = int(impl_choice) - 1
            if 0 <= impl_idx < len(available_agents):
                preferred_implementer = available_agents[impl_idx]
            else:
                preferred_implementer = available_agents[0]
        except ValueError:
            preferred_implementer = available_agents[0]

        # Prompt for preferred reviewer
        print("\nSelect preferred review agent:")
        for i, agent_id in enumerate(available_agents, 1):
            marker = " (same as implementer)" if agent_id == preferred_implementer else ""
            print(f"  {i}. {agent_id}{marker}")

        review_choice = prompt_func(f"Enter number [1]: ").strip() or "1"
        try:
            review_idx = int(review_choice) - 1
            if 0 <= review_idx < len(available_agents):
                preferred_reviewer = available_agents[review_idx]
            else:
                preferred_reviewer = available_agents[0]
        except ValueError:
            preferred_reviewer = available_agents[0]

    print(f"\nConfiguration:")
    print(f"  Strategy: {selection_strategy}")
    if selection_strategy == STRATEGY_PREFERRED:
        print(f"  Implementer: {preferred_implementer}")
        print(f"  Reviewer: {preferred_reviewer}")
    print()

    return AgentConfig(
        available_agents=available_agents,
        selection_strategy=selection_strategy,
        preferred_implementer=preferred_implementer,
        preferred_reviewer=preferred_reviewer,
    )


def init_agent_config(
    available_agent_configs: List["BaseAgentConfig"],
    project_root: Optional[Path] = None,
    prompt_func: Optional[callable] = None,
    non_interactive: bool = False,
) -> AgentConfig:
    """Initialize agent configuration during spec-kitty init.

    This is the main entry point for the init flow. It:
    1. Gets available agents from discovery
    2. Prompts user for preferences (or uses defaults in non-interactive mode)
    3. Saves config to .kittify/config.yaml

    Args:
        available_agent_configs: List of available BaseAgentConfig objects
        project_root: Project root directory (defaults to current directory)
        prompt_func: Optional custom prompt function (for testing)
        non_interactive: If True, use defaults without prompting

    Returns:
        The saved AgentConfig
    """
    available_agent_ids = [cfg.agent_id for cfg in available_agent_configs]

    if non_interactive or not available_agent_ids:
        # Use defaults
        config = AgentConfig(
            available_agents=available_agent_ids,
            selection_strategy=STRATEGY_PREFERRED,
            preferred_implementer=available_agent_ids[0] if available_agent_ids else None,
            preferred_reviewer=available_agent_ids[0] if available_agent_ids else None,
        )
    else:
        # Interactive prompts
        config = prompt_agent_selection(available_agent_ids, prompt_func)

    # Save to config file
    save_agent_config(config, project_root)

    return config


# =============================================================================
# T021: Orchestrator Integration Helpers
# =============================================================================


def select_agent_from_user_config(
    available_agent_configs: List["BaseAgentConfig"],
    project_root: Optional[Path] = None,
    override: Optional[str] = None,
) -> Optional["BaseAgentConfig"]:
    """Select implementation agent using user config.

    This is the main function for orchestrator integration.
    Reads from .kittify/config.yaml and respects user preferences.

    Args:
        available_agent_configs: List of available BaseAgentConfig objects
        project_root: Project root directory (defaults to current directory)
        override: CLI override (--impl-agent flag)

    Returns:
        Selected BaseAgentConfig or None if no agents available
    """
    selection_config = create_agent_selection_config(
        available_agent_configs,
        project_root,
    )

    agent_id = selection_config.select_implementer(override=override)
    if agent_id:
        return selection_config.get_agent_config(agent_id)
    return None


def select_review_agent_from_user_config(
    available_agent_configs: List["BaseAgentConfig"],
    implementer_id: Optional[str] = None,
    different_from_implementer: bool = False,
    project_root: Optional[Path] = None,
    override: Optional[str] = None,
) -> Optional["BaseAgentConfig"]:
    """Select review agent using user config.

    This is the main function for orchestrator integration.
    Reads from .kittify/config.yaml and respects user preferences.

    Args:
        available_agent_configs: List of available BaseAgentConfig objects
        implementer_id: ID of implementation agent (for DIFFERENT_FROM constraint)
        different_from_implementer: If True, reviewer must be different from implementer
        project_root: Project root directory (defaults to current directory)
        override: CLI override (--review-agent flag)

    Returns:
        Selected BaseAgentConfig or None if no agents available
    """
    selection_config = create_agent_selection_config(
        available_agent_configs,
        project_root,
    )

    different_from = implementer_id if different_from_implementer else None
    agent_id = selection_config.select_reviewer(
        override=override,
        different_from=different_from,
    )
    if agent_id:
        return selection_config.get_agent_config(agent_id)
    return None
