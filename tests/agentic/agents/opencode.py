"""
OpenCode CLI configuration for agent invocation.

Provides configuration for invoking OpenCode via the `opencode` CLI.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import BaseAgentConfig, PromptMethod
from ..invoker.invocation_result import ParsedAgentResponse


@dataclass
class OpenCodeConfig:
    """Configuration for OpenCode CLI."""

    _cli_override: Optional[str] = field(default=None)

    @property
    def agent_id(self) -> str:
        return "opencode"

    @property
    def display_name(self) -> str:
        return "OpenCode"

    @property
    def cli_command(self) -> List[str]:
        cmd = self._cli_override or os.environ.get("OPENCODE_CLI", "opencode")
        return [cmd]

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.STDIN  # Assume stdin

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        """Build OpenCode CLI command."""
        cmd = self.cli_command.copy()
        # Add working directory if supported
        if worktree_path:
            cmd.extend(["--cwd", worktree_path])
        return cmd

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if opencode CLI is installed."""
        try:
            result = subprocess.run(
                self.cli_command + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip() or "unknown"
                return True, version

            # Try --help if --version fails
            result = subprocess.run(
                self.cli_command + ["--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, "unknown"

            return False, None
        except FileNotFoundError:
            return False, None
        except subprocess.TimeoutExpired:
            return False, None

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        """Check for OpenCode authentication."""
        # Check common env vars
        for var in ["OPENCODE_API_KEY", "OPENCODE_TOKEN"]:
            if os.environ.get(var):
                return True, None

        # Check for config file
        config_paths = [
            os.path.expanduser("~/.opencode/config"),
            os.path.expanduser("~/.config/opencode/config"),
        ]
        for path in config_paths:
            if os.path.exists(path):
                return True, None

        # OpenCode might not require auth for some operations
        # Mark as available but warn
        return True, "No explicit auth found, may work without credentials"

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> ParsedAgentResponse:
        """Parse OpenCode output."""
        files_created: List[str] = []
        files_modified: List[str] = []
        commits_made: List[str] = []

        # Basic parsing - look for common patterns
        for line in stdout.split("\n"):
            line_lower = line.lower()
            if "created" in line_lower:
                # Try to extract file path
                parts = line.split()
                for part in parts:
                    if "/" in part or part.endswith((".py", ".js", ".ts", ".md")):
                        files_created.append(part)
            elif "modified" in line_lower or "updated" in line_lower:
                parts = line.split()
                for part in parts:
                    if "/" in part or part.endswith((".py", ".js", ".ts", ".md")):
                        files_modified.append(part)

        return ParsedAgentResponse(
            files_created=files_created,
            files_modified=files_modified,
            commits_made=commits_made,
            approval=None,
            review_comments=[],
            requested_changes=[],
            raw_output=stdout,
            thinking=None,
        )
