"""
GitHub Copilot CLI configuration for agent invocation.

Provides configuration for invoking GitHub Copilot via the `gh copilot` CLI.
"""

import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .base import BaseAgentConfig, PromptMethod
from ..invoker.invocation_result import ParsedAgentResponse


@dataclass
class CopilotConfig:
    """Configuration for GitHub Copilot CLI."""

    @property
    def agent_id(self) -> str:
        return "github-copilot"

    @property
    def display_name(self) -> str:
        return "GitHub Copilot"

    @property
    def cli_command(self) -> List[str]:
        return ["gh", "copilot"]

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.ARGUMENT  # Copilot uses CLI argument

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        """
        Build Copilot CLI command.

        gh copilot suggest -t shell "prompt"
        or gh copilot explain "prompt"
        """
        # For code generation - prompt is passed via ARGUMENT method
        cmd = ["gh", "copilot", "suggest", "-t", "code", prompt]
        return cmd

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if gh copilot is installed."""
        try:
            # Check gh CLI first
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return False, None

            # Check copilot extension
            result = subprocess.run(
                ["gh", "copilot", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "copilot"
            return False, None
        except FileNotFoundError:
            return False, None
        except subprocess.TimeoutExpired:
            return False, None

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        """Check if gh is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, None
            return False, "Not authenticated with gh. Run: gh auth login"
        except FileNotFoundError:
            return False, "gh CLI not found"
        except subprocess.TimeoutExpired:
            return False, "Auth check timed out"

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> ParsedAgentResponse:
        """Parse Copilot output."""
        # Copilot outputs code suggestions
        return ParsedAgentResponse(
            files_created=[],
            files_modified=[],
            commits_made=[],
            approval=None,
            review_comments=[],
            requested_changes=[],
            raw_output=stdout,
            thinking=None,
        )
