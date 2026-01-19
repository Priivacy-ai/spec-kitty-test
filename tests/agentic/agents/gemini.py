"""
Google Gemini CLI configuration for agent invocation.

Provides configuration for invoking Google Gemini via CLI.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import BaseAgentConfig, PromptMethod
from ..invoker.invocation_result import ParsedAgentResponse


@dataclass
class GeminiConfig:
    """Configuration for Google Gemini CLI."""

    # CLI name may vary - allow override
    _cli_override: Optional[str] = field(default=None)

    @property
    def agent_id(self) -> str:
        return "google-gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini"

    @property
    def cli_command(self) -> List[str]:
        # Try common CLI names
        cmd = self._cli_override or os.environ.get("GEMINI_CLI", "gemini")
        return [cmd]

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.STDIN  # Assume stdin for now

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        """Build Gemini CLI command."""
        cmd = self.cli_command.copy()
        # Add working directory if supported
        return cmd

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if Gemini CLI is installed."""
        # Try multiple possible CLI names
        cli_names = ["gemini", "google-ai", "genai"]

        if self._cli_override:
            cli_names = [self._cli_override]
        elif os.environ.get("GEMINI_CLI"):
            cli_names = [os.environ["GEMINI_CLI"]]

        for cli in cli_names:
            try:
                result = subprocess.run(
                    [cli, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version = result.stdout.strip() or "unknown"
                    return True, version
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                continue

        return False, None

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        """Check for Google API key."""
        # Check common env vars
        for var in ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"]:
            if os.environ.get(var):
                return True, None

        # Check for gcloud auth (alternative)
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "auth",
                    "list",
                    "--filter=status:ACTIVE",
                    "--format=value(account)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True, None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return (
            False,
            "No Google API key found. Set GOOGLE_API_KEY or authenticate with gcloud",
        )

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> ParsedAgentResponse:
        """Parse Gemini output."""
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
