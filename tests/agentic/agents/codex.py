"""
OpenAI Codex CLI configuration for agent invocation.

Provides configuration for invoking OpenAI Codex via CLI.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import BaseAgentConfig, PromptMethod
from ..invoker.invocation_result import ParsedAgentResponse


@dataclass
class CodexConfig:
    """Configuration for OpenAI Codex CLI."""

    _cli_override: Optional[str] = field(default=None)

    @property
    def agent_id(self) -> str:
        return "openai-codex"

    @property
    def display_name(self) -> str:
        return "OpenAI Codex"

    @property
    def cli_command(self) -> List[str]:
        # Codex might be accessed via openai CLI or dedicated codex CLI
        cmd = self._cli_override or os.environ.get("CODEX_CLI", "codex")
        return [cmd]

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.STDIN

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        """Build Codex CLI command."""
        cmd = self.cli_command.copy()
        # Add working directory if supported
        return cmd

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if Codex CLI is installed."""
        # Try multiple possible CLI names
        cli_names = ["codex", "openai", "chatgpt"]

        if self._cli_override:
            cli_names = [self._cli_override]
        elif os.environ.get("CODEX_CLI"):
            cli_names = [os.environ["CODEX_CLI"]]

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
        """Check for OpenAI API key."""
        # Check env var
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            # Basic validation - accept any key
            return True, None

        # Check for config file
        config_paths = [
            os.path.expanduser("~/.openai/config"),
            os.path.expanduser("~/.config/openai/config"),
        ]
        for path in config_paths:
            if os.path.exists(path):
                return True, None

        return False, "OPENAI_API_KEY environment variable not set"

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> ParsedAgentResponse:
        """Parse Codex output."""
        files_created: List[str] = []
        files_modified: List[str] = []
        commits_made: List[str] = []

        # Codex output parsing - may vary by CLI version
        for line in stdout.split("\n"):
            line_lower = line.lower()
            if "created" in line_lower or "wrote" in line_lower:
                parts = line.split()
                for part in parts:
                    if "/" in part or "." in part:
                        files_created.append(part)
            elif "modified" in line_lower or "updated" in line_lower:
                parts = line.split()
                for part in parts:
                    if "/" in part or "." in part:
                        files_modified.append(part)

        # Look for commit hashes
        commit_pattern = r"\b[a-f0-9]{7,40}\b"
        for match in re.finditer(commit_pattern, stdout):
            commits_made.append(match.group())

        return ParsedAgentResponse(
            files_created=files_created,
            files_modified=files_modified,
            commits_made=commits_made[:10],
            approval=None,
            review_comments=[],
            requested_changes=[],
            raw_output=stdout,
            thinking=None,
        )
