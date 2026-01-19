"""
Claude Code CLI configuration for agent invocation.

Provides configuration for invoking Claude Code via the `claude` CLI.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import BaseAgentConfig, PromptMethod
from ..invoker.invocation_result import ParsedAgentResponse


@dataclass
class ClaudeCodeConfig:
    """Configuration for Claude Code CLI."""

    # Allow override via environment or explicit setting
    _cli_override: Optional[str] = field(default=None)

    @property
    def agent_id(self) -> str:
        return "claude-code"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    @property
    def cli_command(self) -> List[str]:
        cmd = self._cli_override or os.environ.get("CLAUDE_CLI", "claude")
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
        """
        Build Claude Code CLI command.

        Claude accepts:
        - --print for non-interactive output
        - --cwd for working directory
        - Prompt via stdin
        """
        cmd = self.cli_command + [
            "--print",
            "--cwd",
            worktree_path,
        ]
        return cmd

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if claude CLI is installed."""
        try:
            result = subprocess.run(
                self.cli_command + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Extract version from output
                version = result.stdout.strip().split()[-1] if result.stdout else "unknown"
                return True, version
            return False, None
        except FileNotFoundError:
            return False, None
        except subprocess.TimeoutExpired:
            return False, None

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        """Check if ANTHROPIC_API_KEY is set or claude is authenticated."""
        # Check for API key in environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            return True, None

        # Claude Code may have its own authentication
        # Try running a minimal command to check
        try:
            result = subprocess.run(
                self.cli_command + ["--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # If --help works, assume authentication is handled by the CLI
            if result.returncode == 0:
                return True, None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False, "ANTHROPIC_API_KEY environment variable not set"

    def parse_output(
        self,
        stdout: str,
        stderr: str,
    ) -> ParsedAgentResponse:
        """
        Parse Claude Code output.

        Claude typically outputs:
        - File changes with paths
        - Git commits with hashes
        - Review decisions (approve/reject)
        """
        files_created: List[str] = []
        files_modified: List[str] = []
        commits_made: List[str] = []
        approval: Optional[bool] = None
        review_comments: List[str] = []
        requested_changes: List[str] = []

        # Parse for file operations
        for line in stdout.split("\n"):
            line_lower = line.lower()
            if "created" in line_lower and "/" in line:
                # Extract path after "created"
                parts = line.split()
                for i, part in enumerate(parts):
                    if "created" in part.lower() and i + 1 < len(parts):
                        files_created.append(parts[i + 1])
            elif "modified" in line_lower or "updated" in line_lower:
                parts = line.split()
                for part in parts:
                    if "/" in part or "." in part:
                        files_modified.append(part)

        # Parse for git commits
        commit_pattern = r"[a-f0-9]{7,40}"
        for match in re.finditer(commit_pattern, stdout):
            commits_made.append(match.group())

        # Parse for review decisions
        stdout_lower = stdout.lower()
        if "approved" in stdout_lower or "lgtm" in stdout_lower:
            approval = True
        elif "rejected" in stdout_lower or "changes requested" in stdout_lower:
            approval = False

        return ParsedAgentResponse(
            files_created=files_created,
            files_modified=files_modified,
            commits_made=commits_made[:10],  # Limit to 10
            approval=approval,
            review_comments=review_comments,
            requested_changes=requested_changes,
            raw_output=stdout,
            thinking=None,
        )
