"""
Base agent configuration protocol and related enums.

Defines the contract that all agent configurations must implement,
plus enums for prompt delivery methods and agent selection constraints.
"""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Protocol, Tuple

if TYPE_CHECKING:
    from ..invoker.invocation_result import ParsedAgentResponse


class PromptMethod(Enum):
    """Method for delivering prompt to an agent."""

    STDIN = "stdin"  # Pipe prompt to stdin
    FILE = "file"  # Write to file, pass path as arg
    ARGUMENT = "argument"  # Pass prompt as CLI argument


class AgentConstraint(Enum):
    """Constraint for agent selection in multi-agent workflows."""

    SAME_AS = "same_as"  # Use same agent (single-agent path)
    DIFFERENT_FROM = "different_from"  # Use different agent (cross-review)
    ANY = "any"  # Any available agent


class BaseAgentConfig(Protocol):
    """
    Protocol defining the contract for agent configurations.

    All agent implementations (Claude, Copilot, Gemini, etc.) must
    implement this protocol to be usable by the AgentInvoker.
    """

    @property
    def agent_id(self) -> str:
        """Unique identifier for this agent (e.g., 'claude', 'copilot')."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for display (e.g., 'Claude Code')."""
        ...

    @property
    def cli_command(self) -> List[str]:
        """Base CLI command to invoke the agent (e.g., ['claude', 'code'])."""
        ...

    @property
    def prompt_method(self) -> PromptMethod:
        """How to deliver the prompt to this agent."""
        ...

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        """
        Build the full command to invoke the agent.

        Args:
            prompt: The prompt text to send
            worktree_path: Path to the git worktree
            prompt_file: Path to prompt file (for FILE method)

        Returns:
            Complete command as list of strings
        """
        ...

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if the agent CLI is installed.

        Returns:
            Tuple of (is_installed, error_message_if_not)
        """
        ...

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        """
        Check if the agent is authenticated/configured.

        Returns:
            Tuple of (is_authenticated, error_message_if_not)
        """
        ...

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> "ParsedAgentResponse":
        """
        Parse agent output into structured response.

        Args:
            stdout: Captured stdout from agent
            stderr: Captured stderr from agent

        Returns:
            ParsedAgentResponse with extracted information
        """
        ...
