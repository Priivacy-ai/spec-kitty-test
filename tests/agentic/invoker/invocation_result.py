"""
Invocation result data structures for agent subprocess invocations.

This module defines:
- InvocationOutcome: Enum representing the outcome of an agent invocation
- ParsedAgentResponse: Structured data extracted from agent output
- InvocationResult: Immutable result of a completed agent invocation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InvocationOutcome(Enum):
    """Outcome of an agent invocation."""

    SUCCESS = "success"  # Agent completed, output parseable
    FAILURE = "failure"  # Agent completed with error exit code
    TIMEOUT = "timeout"  # Agent exceeded timeout, was killed
    CRASH = "crash"  # Agent process crashed unexpectedly
    PARSE_ERROR = "parse_error"  # Completed but output couldn't be parsed


@dataclass
class ParsedAgentResponse:
    """
    Structured data extracted from agent output.

    Contains information about files modified, commits made,
    and review decisions (for review tasks).
    """

    # For implementation tasks
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    commits_made: List[str] = field(default_factory=list)

    # For review tasks
    approval: Optional[bool] = None  # True=approved, False=rejected, None=unclear
    review_comments: List[str] = field(default_factory=list)
    requested_changes: List[str] = field(default_factory=list)

    # Raw sections
    raw_output: str = ""
    thinking: Optional[str] = None  # If agent exposes reasoning

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "commits_made": self.commits_made,
            "approval": self.approval,
            "review_comments": self.review_comments,
            "requested_changes": self.requested_changes,
            "raw_output": self.raw_output,
            "thinking": self.thinking,
        }

    @classmethod
    def from_raw(cls, stdout: str, stderr: str) -> "ParsedAgentResponse":
        """
        Create a minimal instance from raw output.

        This is a fallback when proper parsing isn't possible.
        The raw_output will contain the combined stdout/stderr.
        """
        combined = stdout
        if stderr:
            combined = f"{stdout}\n\n[STDERR]\n{stderr}" if stdout else stderr
        return cls(raw_output=combined)


@dataclass(frozen=True)
class InvocationResult:
    """
    Immutable result of a completed agent invocation.

    This dataclass captures the complete result of an agent invocation
    including output, timing, and parsed outcome. It is frozen to ensure
    immutability across async boundaries.
    """

    stdout: str
    stderr: str
    exit_code: int
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    outcome: InvocationOutcome
    parsed_response: Optional[ParsedAgentResponse]
    agent_id: str
    prompt_hash: str  # SHA256 of prompt for deduplication
    worktree_path: str
    error_message: Optional[str] = None
    timeout_exceeded: bool = False
    killed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat() + "Z",
            "completed_at": self.completed_at.isoformat() + "Z",
            "duration_seconds": self.duration_seconds,
            "outcome": self.outcome.value,
            "parsed_response": (
                self.parsed_response.to_dict() if self.parsed_response else None
            ),
            "agent_id": self.agent_id,
            "prompt_hash": self.prompt_hash,
            "worktree_path": self.worktree_path,
            "error_message": self.error_message,
            "timeout_exceeded": self.timeout_exceeded,
            "killed": self.killed,
        }
