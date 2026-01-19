"""File and Git fault injection for adversarial testing.

This module provides fault injectors that simulate filesystem and git failures:
- File corruption: Binary corruption, truncation, encoding issues
- Permission changes: Read-only, no-execute, ownership changes
- Git conflicts: Merge conflicts, detached HEAD, corrupted refs

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import hashlib
import os
import random
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .process_faults import (
    BaseFaultInjector,
    ContainerNotRunningError,
    FaultInjectionError,
    FaultInjectionResult,
    TriggerCondition,
)

if TYPE_CHECKING:
    from ..fixtures.container_fixtures import TestContainer


class CorruptionType(Enum):
    """Types of file corruption to inject.

    RANDOM_BYTES: Replace random portions with random bytes
    TRUNCATE: Truncate file to partial size
    ZERO_FILL: Fill portions with null bytes
    BIT_FLIP: Flip random bits in the file
    ENCODING_ERROR: Inject invalid UTF-8 sequences
    APPEND_GARBAGE: Append random data to end of file
    """

    RANDOM_BYTES = "random_bytes"
    TRUNCATE = "truncate"
    ZERO_FILL = "zero_fill"
    BIT_FLIP = "bit_flip"
    ENCODING_ERROR = "encoding_error"
    APPEND_GARBAGE = "append_garbage"


class PermissionFault(Enum):
    """Types of permission faults to inject.

    READ_ONLY: Remove write permission
    NO_READ: Remove read permission
    NO_EXECUTE: Remove execute permission
    NO_ACCESS: Remove all permissions
    WRONG_OWNER: Change ownership (requires root)
    """

    READ_ONLY = "read_only"
    NO_READ = "no_read"
    NO_EXECUTE = "no_execute"
    NO_ACCESS = "no_access"
    WRONG_OWNER = "wrong_owner"


@dataclass
class FileBackup:
    """Backup of a file for restoration.

    Attributes:
        original_path: Path to the original file
        backup_path: Path to the backup copy
        original_mode: Original file permissions
        original_content_hash: SHA256 of original content
        created_at: When backup was created
    """

    original_path: Path
    backup_path: Path
    original_mode: int
    original_content_hash: str
    created_at: datetime = field(default_factory=datetime.now)


class FileFaultInjector(BaseFaultInjector):
    """Inject file-level faults for testing error handling.

    Supports:
    - File corruption (various types)
    - Permission modifications
    - File deletion with backup
    - Disk space simulation (via file expansion)

    All operations support backup and restore for test cleanup.

    Example usage:
        injector = FileFaultInjector(
            corruption_type=CorruptionType.TRUNCATE,
            corruption_ratio=0.5  # Truncate to 50%
        )
        result = injector.inject("/path/to/spec.md")
        # ... test error handling ...
        injector.restore()  # Restore original file

    For containers:
        result = injector.inject_container(
            container,
            "/workspace/.kittify/feature/spec.md"
        )
    """

    def __init__(
        self,
        corruption_type: CorruptionType = CorruptionType.RANDOM_BYTES,
        corruption_ratio: float = 0.1,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
        backup_dir: Optional[Path] = None,
    ):
        """Initialize file fault injector.

        Args:
            corruption_type: Type of corruption to apply
            corruption_ratio: Ratio of file to corrupt (0.0-1.0)
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
            backup_dir: Directory for backups (uses tempdir if None)
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.corruption_type = corruption_type
        self.corruption_ratio = max(0.0, min(1.0, corruption_ratio))
        self.backup_dir = backup_dir or Path(tempfile.mkdtemp(prefix="fault_backup_"))
        self._backups: Dict[str, FileBackup] = {}

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject file corruption fault.

        Args:
            target: Path to file to corrupt (str or Path)
            **kwargs: Additional parameters (corruption_type override)

        Returns:
            FaultInjectionResult with injection details

        Raises:
            FaultInjectionError: If file cannot be corrupted
        """
        file_path = Path(target)

        if not file_path.exists():
            result = FaultInjectionResult(
                success=False,
                fault_type=f"file_corruption_{self.corruption_type.value}",
                target=str(file_path),
                error=f"File not found: {file_path}",
            )
            self._injections.append(result)
            raise FaultInjectionError(f"File not found: {file_path}")

        self._apply_trigger_delay()

        # Create backup first
        backup = self._create_backup(file_path)
        self._backups[str(file_path)] = backup

        try:
            # Apply corruption based on type
            corruption_type = kwargs.get("corruption_type", self.corruption_type)

            if corruption_type == CorruptionType.RANDOM_BYTES:
                self._corrupt_random_bytes(file_path)
            elif corruption_type == CorruptionType.TRUNCATE:
                self._corrupt_truncate(file_path)
            elif corruption_type == CorruptionType.ZERO_FILL:
                self._corrupt_zero_fill(file_path)
            elif corruption_type == CorruptionType.BIT_FLIP:
                self._corrupt_bit_flip(file_path)
            elif corruption_type == CorruptionType.ENCODING_ERROR:
                self._corrupt_encoding(file_path)
            elif corruption_type == CorruptionType.APPEND_GARBAGE:
                self._corrupt_append_garbage(file_path)

            result = FaultInjectionResult(
                success=True,
                fault_type=f"file_corruption_{corruption_type.value}",
                target=str(file_path),
                metadata={
                    "corruption_type": corruption_type.value,
                    "corruption_ratio": self.corruption_ratio,
                    "original_hash": backup.original_content_hash,
                    "backup_path": str(backup.backup_path),
                },
            )
            self._injections.append(result)
            return result

        except Exception as e:
            # Restore on failure
            self._restore_file(file_path)
            result = FaultInjectionResult(
                success=False,
                fault_type=f"file_corruption_{self.corruption_type.value}",
                target=str(file_path),
                error=str(e),
            )
            self._injections.append(result)
            raise FaultInjectionError(f"Failed to corrupt file: {e}")

    def inject_container(
        self,
        container: "TestContainer",
        file_path: str,
        **kwargs,
    ) -> FaultInjectionResult:
        """Inject file corruption inside a container.

        Args:
            container: TestContainer instance
            file_path: Path inside container to corrupt
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        self._apply_trigger_delay()

        # Check if file exists
        exit_code, stdout, stderr = container.exec_command(
            f"test -f '{file_path}' && echo 'exists'", timeout=10
        )
        if "exists" not in stdout:
            raise FaultInjectionError(f"File not found in container: {file_path}")

        # Create backup inside container
        backup_path = f"/tmp/fault_backup_{os.urandom(4).hex()}"
        container.exec_command(f"cp '{file_path}' '{backup_path}'", timeout=30)

        # Apply corruption based on type
        corruption_type = kwargs.get("corruption_type", self.corruption_type)
        cmd = self._get_container_corruption_command(
            file_path, corruption_type, self.corruption_ratio
        )

        exit_code, stdout, stderr = container.exec_command(cmd, timeout=60)

        success = exit_code == 0
        result = FaultInjectionResult(
            success=success,
            fault_type=f"container_file_corruption_{corruption_type.value}",
            target=f"{container.container_id}:{file_path}",
            metadata={
                "corruption_type": corruption_type.value,
                "corruption_ratio": self.corruption_ratio,
                "backup_path": backup_path,
                "container_id": container.container_id,
            },
            error=stderr if not success else None,
        )
        self._injections.append(result)
        return result

    def _create_backup(self, file_path: Path) -> FileBackup:
        """Create a backup of the file."""
        backup_name = f"{file_path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        backup_path = self.backup_dir / backup_name

        # Copy file
        shutil.copy2(file_path, backup_path)

        # Calculate hash
        with open(file_path, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()

        return FileBackup(
            original_path=file_path,
            backup_path=backup_path,
            original_mode=file_path.stat().st_mode,
            original_content_hash=content_hash,
        )

    def _corrupt_random_bytes(self, file_path: Path) -> None:
        """Replace random portions with random bytes."""
        with open(file_path, "rb") as f:
            content = bytearray(f.read())

        if not content:
            return

        num_bytes = max(1, int(len(content) * self.corruption_ratio))
        positions = random.sample(range(len(content)), min(num_bytes, len(content)))

        for pos in positions:
            content[pos] = random.randint(0, 255)

        with open(file_path, "wb") as f:
            f.write(content)

    def _corrupt_truncate(self, file_path: Path) -> None:
        """Truncate file to a fraction of its size."""
        with open(file_path, "rb") as f:
            content = f.read()

        new_size = max(1, int(len(content) * (1 - self.corruption_ratio)))

        with open(file_path, "wb") as f:
            f.write(content[:new_size])

    def _corrupt_zero_fill(self, file_path: Path) -> None:
        """Fill portions of file with null bytes."""
        with open(file_path, "rb") as f:
            content = bytearray(f.read())

        if not content:
            return

        num_bytes = max(1, int(len(content) * self.corruption_ratio))
        start = random.randint(0, max(0, len(content) - num_bytes))

        for i in range(start, min(start + num_bytes, len(content))):
            content[i] = 0

        with open(file_path, "wb") as f:
            f.write(content)

    def _corrupt_bit_flip(self, file_path: Path) -> None:
        """Flip random bits in the file."""
        with open(file_path, "rb") as f:
            content = bytearray(f.read())

        if not content:
            return

        num_bits = max(1, int(len(content) * 8 * self.corruption_ratio))

        for _ in range(num_bits):
            byte_pos = random.randint(0, len(content) - 1)
            bit_pos = random.randint(0, 7)
            content[byte_pos] ^= 1 << bit_pos

        with open(file_path, "wb") as f:
            f.write(content)

    def _corrupt_encoding(self, file_path: Path) -> None:
        """Inject invalid UTF-8 sequences."""
        with open(file_path, "rb") as f:
            content = bytearray(f.read())

        if not content:
            return

        # Invalid UTF-8 sequences
        invalid_sequences = [
            b"\xff\xfe",  # Invalid start bytes
            b"\xc0\xaf",  # Overlong encoding
            b"\xed\xa0\x80",  # Surrogate half
            b"\xf4\x90\x80\x80",  # Out of range
        ]

        num_insertions = max(1, int(len(content) * self.corruption_ratio / 4))

        for _ in range(num_insertions):
            pos = random.randint(0, len(content))
            seq = random.choice(invalid_sequences)
            content[pos:pos] = seq

        with open(file_path, "wb") as f:
            f.write(content)

    def _corrupt_append_garbage(self, file_path: Path) -> None:
        """Append random garbage to end of file."""
        with open(file_path, "ab") as f:
            garbage_size = max(1, int(os.path.getsize(file_path) * self.corruption_ratio))
            f.write(os.urandom(garbage_size))

    def _get_container_corruption_command(
        self, file_path: str, corruption_type: CorruptionType, ratio: float
    ) -> str:
        """Generate bash command for container corruption."""
        commands = {
            CorruptionType.RANDOM_BYTES: (
                f"dd if=/dev/urandom bs=1 count=$(($(stat -c%s '{file_path}') * {int(ratio * 100)} / 100)) "
                f"seek=$((RANDOM % $(stat -c%s '{file_path}'))) of='{file_path}' conv=notrunc 2>/dev/null"
            ),
            CorruptionType.TRUNCATE: (
                f"truncate -s $(( $(stat -c%s '{file_path}') * {int((1-ratio) * 100)} / 100 )) '{file_path}'"
            ),
            CorruptionType.ZERO_FILL: (
                f"dd if=/dev/zero bs=1 count=$(($(stat -c%s '{file_path}') * {int(ratio * 100)} / 100)) "
                f"seek=$((RANDOM % $(stat -c%s '{file_path}'))) of='{file_path}' conv=notrunc 2>/dev/null"
            ),
            CorruptionType.APPEND_GARBAGE: (
                f"dd if=/dev/urandom bs=1 count=$(($(stat -c%s '{file_path}') * {int(ratio * 100)} / 100)) "
                f">> '{file_path}' 2>/dev/null"
            ),
        }
        return commands.get(
            corruption_type,
            f"echo 'CORRUPTED' >> '{file_path}'"
        )

    def _restore_file(self, file_path: Path) -> bool:
        """Restore a single file from backup."""
        key = str(file_path)
        if key not in self._backups:
            return False

        backup = self._backups[key]
        try:
            shutil.copy2(backup.backup_path, backup.original_path)
            os.chmod(backup.original_path, backup.original_mode)
            del self._backups[key]
            return True
        except Exception:
            return False

    def can_restore(self) -> bool:
        """Check if files can be restored."""
        return len(self._backups) > 0

    def restore(self) -> bool:
        """Restore all backed up files."""
        if not self.can_restore():
            return False

        success = True
        for file_path in list(self._backups.keys()):
            if not self._restore_file(Path(file_path)):
                success = False

        return success

    def cleanup(self) -> None:
        """Clean up backup directory."""
        try:
            shutil.rmtree(self.backup_dir)
        except Exception:
            pass


class PermissionFaultInjector(BaseFaultInjector):
    """Inject permission-related faults.

    Modifies file/directory permissions to test error handling
    for permission denied scenarios.

    Example usage:
        injector = PermissionFaultInjector(
            permission_fault=PermissionFault.READ_ONLY
        )
        result = injector.inject("/path/to/file.py")
        # ... test write failure handling ...
        injector.restore()
    """

    def __init__(
        self,
        permission_fault: PermissionFault = PermissionFault.READ_ONLY,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize permission fault injector.

        Args:
            permission_fault: Type of permission fault to inject
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.permission_fault = permission_fault
        self._original_modes: Dict[str, int] = {}

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject permission fault.

        Args:
            target: Path to file/directory
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        file_path = Path(target)

        if not file_path.exists():
            raise FaultInjectionError(f"Path not found: {file_path}")

        self._apply_trigger_delay()

        # Save original mode
        original_mode = file_path.stat().st_mode
        self._original_modes[str(file_path)] = original_mode

        try:
            new_mode = self._calculate_new_mode(original_mode)
            os.chmod(file_path, new_mode)

            result = FaultInjectionResult(
                success=True,
                fault_type=f"permission_{self.permission_fault.value}",
                target=str(file_path),
                metadata={
                    "permission_fault": self.permission_fault.value,
                    "original_mode": oct(original_mode),
                    "new_mode": oct(new_mode),
                },
            )
            self._injections.append(result)
            return result

        except Exception as e:
            del self._original_modes[str(file_path)]
            raise FaultInjectionError(f"Failed to change permissions: {e}")

    def _calculate_new_mode(self, original_mode: int) -> int:
        """Calculate new mode based on fault type."""
        import stat

        if self.permission_fault == PermissionFault.READ_ONLY:
            # Remove write permissions
            return original_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        elif self.permission_fault == PermissionFault.NO_READ:
            # Remove read permissions
            return original_mode & ~(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        elif self.permission_fault == PermissionFault.NO_EXECUTE:
            # Remove execute permissions
            return original_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        elif self.permission_fault == PermissionFault.NO_ACCESS:
            # Remove all permissions
            return 0o000
        else:
            return original_mode

    def can_restore(self) -> bool:
        """Check if permissions can be restored."""
        return len(self._original_modes) > 0

    def restore(self) -> bool:
        """Restore original permissions."""
        if not self.can_restore():
            return False

        success = True
        for path, mode in list(self._original_modes.items()):
            try:
                os.chmod(path, mode)
                del self._original_modes[path]
            except Exception:
                success = False

        return success


class GitFaultInjector(BaseFaultInjector):
    """Inject Git-related faults for testing conflict handling.

    Supports:
    - Merge conflicts: Create conflicting changes
    - Detached HEAD: Checkout specific commit
    - Corrupted refs: Damage .git/refs
    - Lock files: Create stale lock files
    - Dirty worktree: Leave uncommitted changes

    Example usage:
        injector = GitFaultInjector(fault_type="merge_conflict")
        result = injector.inject(
            repo_path="/path/to/repo",
            target_file="spec.md"
        )
        # ... test conflict resolution ...
        injector.restore()  # Reset to clean state
    """

    FAULT_TYPES = [
        "merge_conflict",
        "detached_head",
        "corrupted_refs",
        "stale_lock",
        "dirty_worktree",
        "missing_remote",
    ]

    def __init__(
        self,
        fault_type: str = "merge_conflict",
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize Git fault injector.

        Args:
            fault_type: Type of Git fault to inject
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger

        Raises:
            ValueError: If fault_type is not recognized
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)

        if fault_type not in self.FAULT_TYPES:
            raise ValueError(
                f"Unknown fault_type: {fault_type}. "
                f"Must be one of: {self.FAULT_TYPES}"
            )

        self.fault_type = fault_type
        self._backup_state: Dict[str, Any] = {}

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject Git fault.

        Args:
            target: Path to git repository
            **kwargs: Additional parameters (target_file, branch_name, etc.)

        Returns:
            FaultInjectionResult with injection details
        """
        repo_path = Path(target)

        if not (repo_path / ".git").exists():
            raise FaultInjectionError(f"Not a git repository: {repo_path}")

        self._apply_trigger_delay()

        if self.fault_type == "merge_conflict":
            return self._inject_merge_conflict(repo_path, **kwargs)
        elif self.fault_type == "detached_head":
            return self._inject_detached_head(repo_path, **kwargs)
        elif self.fault_type == "corrupted_refs":
            return self._inject_corrupted_refs(repo_path, **kwargs)
        elif self.fault_type == "stale_lock":
            return self._inject_stale_lock(repo_path, **kwargs)
        elif self.fault_type == "dirty_worktree":
            return self._inject_dirty_worktree(repo_path, **kwargs)
        elif self.fault_type == "missing_remote":
            return self._inject_missing_remote(repo_path, **kwargs)
        else:
            raise FaultInjectionError(f"Unknown fault type: {self.fault_type}")

    def inject_container(
        self,
        container: "TestContainer",
        repo_path: str = "/workspace",
        **kwargs,
    ) -> FaultInjectionResult:
        """Inject Git fault inside a container.

        Args:
            container: TestContainer instance
            repo_path: Path to repository inside container
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        self._apply_trigger_delay()

        # Verify it's a git repo
        exit_code, stdout, stderr = container.exec_command(
            f"test -d '{repo_path}/.git' && echo 'is_git'", timeout=10
        )
        if "is_git" not in stdout:
            raise FaultInjectionError(f"Not a git repository: {repo_path}")

        cmd = self._get_container_git_command(repo_path, **kwargs)
        exit_code, stdout, stderr = container.exec_command(cmd, timeout=60)

        result = FaultInjectionResult(
            success=exit_code == 0,
            fault_type=f"container_git_{self.fault_type}",
            target=f"{container.container_id}:{repo_path}",
            metadata={
                "fault_type": self.fault_type,
                "repo_path": repo_path,
                "container_id": container.container_id,
                "command": cmd,
            },
            error=stderr if exit_code != 0 else None,
        )
        self._injections.append(result)
        return result

    def _inject_merge_conflict(
        self, repo_path: Path, target_file: str = "README.md", **kwargs
    ) -> FaultInjectionResult:
        """Create a merge conflict scenario."""
        import subprocess

        # Save current state
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        self._backup_state["original_branch"] = current_branch
        self._backup_state["repo_path"] = str(repo_path)

        conflict_branch = f"conflict-{os.urandom(4).hex()}"

        try:
            # Create and switch to conflict branch
            subprocess.run(
                ["git", "checkout", "-b", conflict_branch],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Modify file on conflict branch
            target_path = repo_path / target_file
            if target_path.exists():
                with open(target_path, "a") as f:
                    f.write(f"\n<!-- Conflict branch change: {conflict_branch} -->\n")
            else:
                with open(target_path, "w") as f:
                    f.write(f"# Created by conflict test\nBranch: {conflict_branch}\n")

            subprocess.run(
                ["git", "add", target_file],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Conflict branch change: {conflict_branch}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Switch back to original branch
            subprocess.run(
                ["git", "checkout", current_branch],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Make conflicting change
            with open(target_path, "a") as f:
                f.write(f"\n<!-- Main branch change: {current_branch} -->\n")

            subprocess.run(
                ["git", "add", target_file],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Main branch change: {current_branch}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Attempt merge (will fail)
            merge_result = subprocess.run(
                ["git", "merge", conflict_branch, "--no-edit"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            self._backup_state["conflict_branch"] = conflict_branch

            result = FaultInjectionResult(
                success=True,  # Conflict created successfully
                fault_type="git_merge_conflict",
                target=str(repo_path),
                metadata={
                    "target_file": target_file,
                    "conflict_branch": conflict_branch,
                    "original_branch": current_branch,
                    "merge_output": merge_result.stderr,
                },
            )
            self._injections.append(result)
            return result

        except Exception as e:
            raise FaultInjectionError(f"Failed to create merge conflict: {e}")

    def _inject_detached_head(
        self, repo_path: Path, commits_back: int = 1, **kwargs
    ) -> FaultInjectionResult:
        """Put repository in detached HEAD state."""
        import subprocess

        # Save current state
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        self._backup_state["original_branch"] = current_branch
        self._backup_state["repo_path"] = str(repo_path)

        try:
            # Get commit hash
            commit_hash = subprocess.run(
                ["git", "rev-parse", f"HEAD~{commits_back}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            # Checkout specific commit
            subprocess.run(
                ["git", "checkout", commit_hash],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            result = FaultInjectionResult(
                success=True,
                fault_type="git_detached_head",
                target=str(repo_path),
                metadata={
                    "commit_hash": commit_hash,
                    "commits_back": commits_back,
                    "original_branch": current_branch,
                },
            )
            self._injections.append(result)
            return result

        except Exception as e:
            raise FaultInjectionError(f"Failed to create detached HEAD: {e}")

    def _inject_corrupted_refs(
        self, repo_path: Path, ref_type: str = "heads", **kwargs
    ) -> FaultInjectionResult:
        """Corrupt .git/refs files."""
        refs_dir = repo_path / ".git" / "refs" / ref_type

        if not refs_dir.exists():
            raise FaultInjectionError(f"Refs directory not found: {refs_dir}")

        # Backup refs
        backup_dir = Path(tempfile.mkdtemp(prefix="git_refs_backup_"))
        shutil.copytree(refs_dir, backup_dir / ref_type)
        self._backup_state["refs_backup"] = str(backup_dir)
        self._backup_state["refs_dir"] = str(refs_dir)

        # Corrupt a ref file
        ref_files = list(refs_dir.glob("*"))
        if ref_files:
            target_ref = ref_files[0]
            with open(target_ref, "w") as f:
                f.write("corrupted_hash_value_not_a_real_commit")

        result = FaultInjectionResult(
            success=True,
            fault_type="git_corrupted_refs",
            target=str(repo_path),
            metadata={
                "refs_type": ref_type,
                "corrupted_file": str(target_ref) if ref_files else None,
            },
        )
        self._injections.append(result)
        return result

    def _inject_stale_lock(
        self, repo_path: Path, lock_type: str = "index", **kwargs
    ) -> FaultInjectionResult:
        """Create stale lock files."""
        lock_files = {
            "index": repo_path / ".git" / "index.lock",
            "head": repo_path / ".git" / "HEAD.lock",
            "config": repo_path / ".git" / "config.lock",
        }

        lock_path = lock_files.get(lock_type, lock_files["index"])

        # Create lock file
        with open(lock_path, "w") as f:
            f.write(f"lock_pid={os.getpid()}")

        self._backup_state["lock_file"] = str(lock_path)

        result = FaultInjectionResult(
            success=True,
            fault_type="git_stale_lock",
            target=str(repo_path),
            metadata={
                "lock_type": lock_type,
                "lock_path": str(lock_path),
            },
        )
        self._injections.append(result)
        return result

    def _inject_dirty_worktree(
        self, repo_path: Path, num_files: int = 3, **kwargs
    ) -> FaultInjectionResult:
        """Leave uncommitted changes in worktree."""
        created_files = []

        for i in range(num_files):
            file_path = repo_path / f"dirty_file_{i}_{os.urandom(4).hex()}.tmp"
            with open(file_path, "w") as f:
                f.write(f"Dirty worktree test file {i}\n")
            created_files.append(str(file_path))

        self._backup_state["dirty_files"] = created_files

        result = FaultInjectionResult(
            success=True,
            fault_type="git_dirty_worktree",
            target=str(repo_path),
            metadata={
                "num_files": num_files,
                "created_files": created_files,
            },
        )
        self._injections.append(result)
        return result

    def _inject_missing_remote(
        self, repo_path: Path, remote_name: str = "origin", **kwargs
    ) -> FaultInjectionResult:
        """Remove or corrupt remote configuration."""
        import subprocess

        # Get current remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            self._backup_state["original_remote"] = result.stdout.strip()
            self._backup_state["remote_name"] = remote_name
            self._backup_state["repo_path"] = str(repo_path)

            # Set to invalid URL
            subprocess.run(
                ["git", "remote", "set-url", remote_name, "git://invalid.host/repo.git"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        injection_result = FaultInjectionResult(
            success=True,
            fault_type="git_missing_remote",
            target=str(repo_path),
            metadata={
                "remote_name": remote_name,
                "original_url": self._backup_state.get("original_remote"),
            },
        )
        self._injections.append(injection_result)
        return injection_result

    def _get_container_git_command(self, repo_path: str, **kwargs) -> str:
        """Generate git fault command for container."""
        target_file = kwargs.get("target_file", "README.md")

        commands = {
            "merge_conflict": (
                f"cd '{repo_path}' && "
                f"git checkout -b conflict-$RANDOM && "
                f"echo 'conflict' >> {target_file} && "
                f"git add {target_file} && "
                f"git commit -m 'conflict' && "
                f"git checkout - && "
                f"echo 'main change' >> {target_file} && "
                f"git add {target_file} && "
                f"git commit -m 'main' && "
                f"git merge conflict-$RANDOM --no-edit || true"
            ),
            "detached_head": f"cd '{repo_path}' && git checkout HEAD~1",
            "stale_lock": f"echo 'lock' > '{repo_path}/.git/index.lock'",
            "dirty_worktree": (
                f"cd '{repo_path}' && "
                f"echo 'dirty' > dirty_file_1.tmp && "
                f"echo 'dirty' > dirty_file_2.tmp"
            ),
        }

        return commands.get(self.fault_type, "true")

    def can_restore(self) -> bool:
        """Check if Git state can be restored."""
        return bool(self._backup_state)

    def restore(self) -> bool:
        """Restore Git repository to original state."""
        if not self.can_restore():
            return False

        import subprocess

        repo_path = self._backup_state.get("repo_path")
        if not repo_path:
            return False

        success = True

        try:
            # Restore branch if in detached head or merge conflict
            if "original_branch" in self._backup_state:
                subprocess.run(
                    ["git", "checkout", "-f", self._backup_state["original_branch"]],
                    cwd=repo_path,
                    capture_output=True,
                )

                # Clean up merge state
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=repo_path,
                    capture_output=True,
                )

                # Delete conflict branch
                if "conflict_branch" in self._backup_state:
                    subprocess.run(
                        ["git", "branch", "-D", self._backup_state["conflict_branch"]],
                        cwd=repo_path,
                        capture_output=True,
                    )

            # Restore corrupted refs
            if "refs_backup" in self._backup_state:
                refs_backup = Path(self._backup_state["refs_backup"])
                refs_dir = Path(self._backup_state["refs_dir"])
                if refs_backup.exists():
                    shutil.rmtree(refs_dir, ignore_errors=True)
                    shutil.copytree(refs_backup / refs_dir.name, refs_dir)
                    shutil.rmtree(refs_backup)

            # Remove lock files
            if "lock_file" in self._backup_state:
                lock_file = Path(self._backup_state["lock_file"])
                if lock_file.exists():
                    lock_file.unlink()

            # Remove dirty files
            if "dirty_files" in self._backup_state:
                for file_path in self._backup_state["dirty_files"]:
                    try:
                        Path(file_path).unlink()
                    except FileNotFoundError:
                        pass

            # Restore remote URL
            if "original_remote" in self._backup_state:
                subprocess.run(
                    [
                        "git",
                        "remote",
                        "set-url",
                        self._backup_state["remote_name"],
                        self._backup_state["original_remote"],
                    ],
                    cwd=repo_path,
                    capture_output=True,
                )

            self._backup_state.clear()

        except Exception:
            success = False

        return success
