"""
WorktreeManager: Git worktree isolation for test runs.

Provides creation, tracking, and cleanup of isolated git worktrees
for agent invocations to prevent cross-contamination between tests.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Metadata about a created git worktree."""

    path: str
    branch: str
    base_commit: str
    created_at: datetime
    test_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "path": self.path,
            "branch": self.branch,
            "base_commit": self.base_commit,
            "created_at": self.created_at.isoformat() + "Z",
            "test_id": self.test_id,
        }


class WorktreeManager:
    """
    Manage isolated git worktrees for test runs.

    Creates and tracks worktrees to provide isolation between
    concurrent agent invocations. Ensures cleanup on exit.
    """

    def __init__(
        self,
        repo_path: str,
        worktree_base: Optional[str] = None,
    ):
        """
        Initialize the WorktreeManager.

        Args:
            repo_path: Path to the main git repository
            worktree_base: Base directory for worktrees (default: /tmp/spec-kitty-worktrees)
        """
        self._repo_path = Path(repo_path).resolve()
        self._worktree_base = Path(
            worktree_base or "/tmp/spec-kitty-worktrees"
        ).resolve()
        self._active_worktrees: Dict[str, WorktreeInfo] = {}

        # Ensure base directory exists
        self._worktree_base.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        branch_name: Optional[str] = None,
        base_ref: str = "HEAD",
    ) -> WorktreeInfo:
        """
        Create a new git worktree.

        Args:
            branch_name: Name for the new branch (auto-generated if None)
            base_ref: Git ref to base the worktree on (default: HEAD)

        Returns:
            WorktreeInfo with details about the created worktree

        Raises:
            RuntimeError: If worktree creation fails
        """
        # Generate unique branch name if not provided
        if branch_name is None:
            branch_name = f"test-{uuid4().hex[:8]}"

        # Ensure branch name is valid
        branch_name = self._sanitize_branch_name(branch_name)

        # Create unique worktree path
        worktree_path = self._worktree_base / branch_name
        if worktree_path.exists():
            # Add suffix for uniqueness
            worktree_path = self._worktree_base / f"{branch_name}-{uuid4().hex[:4]}"

        # Get base commit hash
        base_commit = self._get_commit_hash(base_ref)

        # Create the worktree
        cmd = [
            "git",
            "-C",
            str(self._repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "-b",
            branch_name,
            base_ref,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(f"Created worktree: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to create worktree: {e.stderr}"
            ) from e

        # Create info object
        info = WorktreeInfo(
            path=str(worktree_path),
            branch=branch_name,
            base_commit=base_commit,
            created_at=datetime.now(timezone.utc),
        )

        # Track it
        self._active_worktrees[str(worktree_path)] = info

        logger.info(f"Created worktree at {worktree_path} on branch {branch_name}")
        return info

    def create_for_test(
        self,
        test_id: str,
        feature_branch: str,
    ) -> WorktreeInfo:
        """
        Create a worktree specifically for a test run.

        Args:
            test_id: Unique identifier for the test
            feature_branch: Branch to base the worktree on

        Returns:
            WorktreeInfo with test_id populated
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        branch_name = f"test-{test_id}-{timestamp}"

        info = self.create(branch_name=branch_name, base_ref=feature_branch)

        # Update with test_id
        info_with_test = WorktreeInfo(
            path=info.path,
            branch=info.branch,
            base_commit=info.base_commit,
            created_at=info.created_at,
            test_id=test_id,
        )
        self._active_worktrees[info.path] = info_with_test

        return info_with_test

    def remove(self, worktree_path: str) -> bool:
        """
        Remove a worktree.

        Args:
            worktree_path: Path to the worktree to remove

        Returns:
            True if removal succeeded, False otherwise
        """
        worktree_path = str(Path(worktree_path).resolve())

        cmd = [
            "git",
            "-C",
            str(self._repo_path),
            "worktree",
            "remove",
            worktree_path,
            "--force",
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Removed worktree at {worktree_path}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to remove worktree {worktree_path}: {e.stderr}")
            return False

        # Remove from tracking
        self._active_worktrees.pop(worktree_path, None)
        return True

    def remove_all(self) -> int:
        """
        Remove all active worktrees.

        Returns:
            Number of worktrees successfully removed
        """
        count = 0
        # Copy keys to avoid modification during iteration
        for path in list(self._active_worktrees.keys()):
            if self.remove(path):
                count += 1
        return count

    def list_active(self) -> List[WorktreeInfo]:
        """
        List all active worktrees managed by this instance.

        Returns:
            List of WorktreeInfo for all active worktrees
        """
        return list(self._active_worktrees.values())

    def get_info(self, worktree_path: str) -> Optional[WorktreeInfo]:
        """
        Get info for a specific worktree.

        Args:
            worktree_path: Path to the worktree

        Returns:
            WorktreeInfo if found, None otherwise
        """
        worktree_path = str(Path(worktree_path).resolve())
        return self._active_worktrees.get(worktree_path)

    def _get_commit_hash(self, ref: str) -> str:
        """Get the commit hash for a git ref."""
        cmd = [
            "git",
            "-C",
            str(self._repo_path),
            "rev-parse",
            ref,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ref  # Return ref as-is if resolution fails

    def _sanitize_branch_name(self, name: str) -> str:
        """Ensure branch name is valid for git."""
        # Replace invalid characters
        sanitized = name.replace(" ", "-").replace(":", "-").replace("~", "-")
        # Remove consecutive dots
        while ".." in sanitized:
            sanitized = sanitized.replace("..", ".")
        # Remove leading/trailing dots and slashes
        sanitized = sanitized.strip("./")
        return sanitized or f"test-{uuid4().hex[:8]}"

    def __enter__(self) -> "WorktreeManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup all worktrees."""
        removed = self.remove_all()
        if removed:
            logger.info(f"Cleaned up {removed} worktree(s) on context exit")
