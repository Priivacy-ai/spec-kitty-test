---
work_package_id: WP08
title: 'Fault Injection: Adversarial Testing Components'
lane: "done"
dependencies: []
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
phase: Phase 3 - Fault Injection
assignee: ''
agent: "claude-opus"
shell_pid: "77330"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Fault Injection: Adversarial Testing Components

## Objective

Implement the complete fault injection suite for adversarial testing: process crashes, timeouts, file corruption, git conflicts, authentication failures, and resource exhaustion scenarios. This enables red team testing of spec-kitty's error handling and recovery mechanisms.

## Context

**Depends On**: WP02 (containers), WP03 (fixtures)
**User Stories Addressed**: US5 (Adversarial Fault Injection)
**Functional Requirements**: FR-021, FR-022, FR-023, FR-024, FR-025, FR-026

Per research.md, fault injection uses:
- pytest-timeout for process control (E004)
- pytest-subprocess for fake processes (E004)
- Toxiproxy for network chaos (E005)
- Pumba for container chaos (E005)

## Subtasks

### T025: Implement process crash injection (SIGKILL, SIGTERM)

Create `tests/agentic/faults/process_faults.py`:

```python
"""Process fault injection for adversarial testing."""

import os
import signal
import subprocess
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

class ProcessSignal(Enum):
    """Signals that can be sent to processes."""
    SIGTERM = signal.SIGTERM  # Graceful termination
    SIGKILL = signal.SIGKILL  # Force kill
    SIGSTOP = signal.SIGSTOP  # Pause
    SIGCONT = signal.SIGCONT  # Resume

@dataclass
class ProcessFaultResult:
    """Result of a process fault injection."""
    signal_sent: ProcessSignal
    pid: int
    success: bool
    process_state: str  # "terminated", "killed", "paused", "resumed", "not_found"
    error: Optional[str] = None

class ProcessFaultInjector:
    """Injects process-level faults into running containers/processes."""

    def __init__(self, container_id: Optional[str] = None):
        """
        Args:
            container_id: If provided, faults are injected into container processes
        """
        self.container_id = container_id

    def kill_process(
        self,
        pid: int,
        signal_type: ProcessSignal = ProcessSignal.SIGTERM,
        wait_for_exit: bool = True,
        timeout: float = 5.0
    ) -> ProcessFaultResult:
        """Send signal to a process.

        Args:
            pid: Process ID to signal
            signal_type: Signal to send
            wait_for_exit: Whether to wait for process to exit
            timeout: Max time to wait for exit

        Returns:
            ProcessFaultResult with outcome details
        """
        try:
            if self.container_id:
                # Kill process inside container
                return self._kill_in_container(pid, signal_type, wait_for_exit, timeout)
            else:
                # Kill local process
                return self._kill_local(pid, signal_type, wait_for_exit, timeout)
        except Exception as e:
            return ProcessFaultResult(
                signal_sent=signal_type,
                pid=pid,
                success=False,
                process_state="error",
                error=str(e)
            )

    def _kill_local(
        self,
        pid: int,
        signal_type: ProcessSignal,
        wait_for_exit: bool,
        timeout: float
    ) -> ProcessFaultResult:
        """Kill a local process."""
        try:
            os.kill(pid, signal_type.value)
        except ProcessLookupError:
            return ProcessFaultResult(
                signal_sent=signal_type,
                pid=pid,
                success=False,
                process_state="not_found"
            )

        if wait_for_exit and signal_type in (ProcessSignal.SIGTERM, ProcessSignal.SIGKILL):
            # Wait for process to exit
            start = time.time()
            while time.time() - start < timeout:
                try:
                    os.kill(pid, 0)  # Check if still alive
                    time.sleep(0.1)
                except ProcessLookupError:
                    state = "terminated" if signal_type == ProcessSignal.SIGTERM else "killed"
                    return ProcessFaultResult(
                        signal_sent=signal_type,
                        pid=pid,
                        success=True,
                        process_state=state
                    )

            # Process didn't exit, try SIGKILL
            if signal_type == ProcessSignal.SIGTERM:
                os.kill(pid, signal.SIGKILL)
                return ProcessFaultResult(
                    signal_sent=ProcessSignal.SIGKILL,
                    pid=pid,
                    success=True,
                    process_state="killed",
                    error="SIGTERM timeout, escalated to SIGKILL"
                )

        state_map = {
            ProcessSignal.SIGSTOP: "paused",
            ProcessSignal.SIGCONT: "resumed",
        }
        return ProcessFaultResult(
            signal_sent=signal_type,
            pid=pid,
            success=True,
            process_state=state_map.get(signal_type, "signaled")
        )

    def _kill_in_container(
        self,
        pid: int,
        signal_type: ProcessSignal,
        wait_for_exit: bool,
        timeout: float
    ) -> ProcessFaultResult:
        """Kill a process inside a Docker container."""
        import docker
        client = docker.from_env()
        container = client.containers.get(self.container_id)

        # Get signal name without SIG prefix for kill command
        sig_name = signal_type.name.replace("SIG", "")

        result = container.exec_run(f"kill -{sig_name} {pid}")

        if result.exit_code != 0:
            return ProcessFaultResult(
                signal_sent=signal_type,
                pid=pid,
                success=False,
                process_state="error",
                error=result.output.decode()
            )

        if wait_for_exit:
            # Check if process exited
            start = time.time()
            while time.time() - start < timeout:
                check = container.exec_run(f"kill -0 {pid}")
                if check.exit_code != 0:  # Process gone
                    return ProcessFaultResult(
                        signal_sent=signal_type,
                        pid=pid,
                        success=True,
                        process_state="terminated"
                    )
                time.sleep(0.1)

        return ProcessFaultResult(
            signal_sent=signal_type,
            pid=pid,
            success=True,
            process_state="signaled"
        )

    def crash_agent_mid_task(
        self,
        container_id: str,
        delay_seconds: float = 5.0,
        signal_type: ProcessSignal = ProcessSignal.SIGKILL
    ) -> ProcessFaultResult:
        """Crash the main agent process after a delay.

        Simulates an unexpected agent crash mid-execution.
        """
        import docker
        import threading

        client = docker.from_env()
        container = client.containers.get(container_id)

        def delayed_kill():
            time.sleep(delay_seconds)
            # Find agent process (typically PID 1 or main process)
            result = container.exec_run("pgrep -f 'claude|codex|copilot|gemini'")
            if result.exit_code == 0:
                pid = int(result.output.decode().strip().split()[0])
                self._kill_in_container(pid, signal_type, wait_for_exit=False, timeout=1.0)

        thread = threading.Thread(target=delayed_kill, daemon=True)
        thread.start()

        return ProcessFaultResult(
            signal_sent=signal_type,
            pid=0,  # Unknown until triggered
            success=True,
            process_state="scheduled"
        )
```

**Acceptance Criteria**:
- SIGTERM and SIGKILL supported
- Works for local and container processes
- Escalation from SIGTERM to SIGKILL on timeout
- Delayed crash for mid-task testing
- Clear result reporting

### T026: Implement timeout injection (delayed responses)

Add timeout injection:

```python
# In process_faults.py or new file faults/timeout_faults.py

import threading
from contextlib import contextmanager

class TimeoutFaultInjector:
    """Injects timeout conditions into test execution."""

    def __init__(self):
        self._active_delays: dict[str, threading.Timer] = {}

    def inject_delay(
        self,
        target_id: str,
        delay_seconds: float,
        callback: Optional[Callable] = None
    ) -> str:
        """Inject a delay before a callback executes.

        Args:
            target_id: Identifier for this delay
            delay_seconds: How long to delay
            callback: Function to call after delay

        Returns:
            delay_id for cancellation
        """
        delay_id = f"{target_id}_{time.time()}"

        def delayed_callback():
            if callback:
                callback()
            self._active_delays.pop(delay_id, None)

        timer = threading.Timer(delay_seconds, delayed_callback)
        timer.start()
        self._active_delays[delay_id] = timer

        return delay_id

    def cancel_delay(self, delay_id: str) -> bool:
        """Cancel a pending delay."""
        timer = self._active_delays.pop(delay_id, None)
        if timer:
            timer.cancel()
            return True
        return False

    @contextmanager
    def simulate_slow_response(self, delay_seconds: float):
        """Context manager that adds delay to any operation within.

        Usage:
            with injector.simulate_slow_response(30):
                agent.execute()  # Will timeout if agent timeout < 30s
        """
        start = time.time()
        yield
        elapsed = time.time() - start
        remaining = delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def force_timeout(
        self,
        container_id: str,
        after_seconds: float
    ) -> None:
        """Force a container to timeout by pausing it.

        Uses SIGSTOP to pause all processes, making them appear hung.
        """
        import docker
        client = docker.from_env()
        container = client.containers.get(container_id)

        def pause_container():
            container.pause()

        timer = threading.Timer(after_seconds, pause_container)
        timer.start()
        self._active_delays[container_id] = timer
```

**Acceptance Criteria**:
- Delays can be injected at specific points
- Delays can be cancelled
- Container pause simulates hung process
- Context manager for easy timeout testing

### T027: Implement state file corruption injection

Create `tests/agentic/faults/file_faults.py`:

```python
"""File system fault injection."""

import json
import random
import string
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum

class CorruptionType(Enum):
    """Types of file corruption."""
    TRUNCATE = "truncate"  # Cut file short
    GARBAGE = "garbage"  # Insert random bytes
    INVALID_JSON = "invalid_json"  # Break JSON syntax
    EMPTY = "empty"  # Zero-length file
    PERMISSION = "permission"  # Remove read/write
    MISSING = "missing"  # Delete file

@dataclass
class FileCorruptionResult:
    """Result of file corruption."""
    file_path: str
    corruption_type: CorruptionType
    success: bool
    original_size: int
    corrupted_size: int
    backup_path: Optional[str] = None
    error: Optional[str] = None

class FileFaultInjector:
    """Injects file system faults for testing."""

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Args:
            backup_dir: Where to store backups for restoration
        """
        self.backup_dir = backup_dir or Path("/tmp/fault_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._backups: dict[str, Path] = {}

    def corrupt_file(
        self,
        file_path: Union[str, Path],
        corruption_type: CorruptionType,
        create_backup: bool = True
    ) -> FileCorruptionResult:
        """Corrupt a file with specified corruption type.

        Args:
            file_path: Path to file to corrupt
            corruption_type: How to corrupt the file
            create_backup: Whether to backup original first

        Returns:
            FileCorruptionResult with details
        """
        path = Path(file_path)

        if not path.exists() and corruption_type != CorruptionType.MISSING:
            return FileCorruptionResult(
                file_path=str(path),
                corruption_type=corruption_type,
                success=False,
                original_size=0,
                corrupted_size=0,
                error="File not found"
            )

        original_size = path.stat().st_size if path.exists() else 0
        backup_path = None

        # Create backup
        if create_backup and path.exists():
            backup_path = self.backup_dir / f"{path.name}.{random.randint(1000, 9999)}.bak"
            backup_path.write_bytes(path.read_bytes())
            self._backups[str(path)] = backup_path

        try:
            corrupted_size = self._apply_corruption(path, corruption_type)
            return FileCorruptionResult(
                file_path=str(path),
                corruption_type=corruption_type,
                success=True,
                original_size=original_size,
                corrupted_size=corrupted_size,
                backup_path=str(backup_path) if backup_path else None
            )
        except Exception as e:
            return FileCorruptionResult(
                file_path=str(path),
                corruption_type=corruption_type,
                success=False,
                original_size=original_size,
                corrupted_size=0,
                error=str(e)
            )

    def _apply_corruption(self, path: Path, corruption_type: CorruptionType) -> int:
        """Apply corruption and return new size."""
        if corruption_type == CorruptionType.TRUNCATE:
            content = path.read_bytes()
            truncated = content[:len(content) // 2]
            path.write_bytes(truncated)
            return len(truncated)

        elif corruption_type == CorruptionType.GARBAGE:
            content = path.read_bytes()
            # Insert garbage at random position
            pos = random.randint(0, len(content))
            garbage = bytes(random.choices(range(256), k=100))
            corrupted = content[:pos] + garbage + content[pos:]
            path.write_bytes(corrupted)
            return len(corrupted)

        elif corruption_type == CorruptionType.INVALID_JSON:
            content = path.read_text()
            # Break JSON by removing closing brace/bracket
            corrupted = content.rstrip().rstrip('}').rstrip(']')
            path.write_text(corrupted)
            return len(corrupted)

        elif corruption_type == CorruptionType.EMPTY:
            path.write_bytes(b'')
            return 0

        elif corruption_type == CorruptionType.PERMISSION:
            import os
            os.chmod(path, 0o000)
            return path.stat().st_size

        elif corruption_type == CorruptionType.MISSING:
            size = path.stat().st_size if path.exists() else 0
            path.unlink(missing_ok=True)
            return 0

        return 0

    def corrupt_wp_state(
        self,
        worktree_path: str,
        wp_id: str
    ) -> FileCorruptionResult:
        """Corrupt a WP's task file (common test scenario)."""
        # Find WP file
        wp_dir = Path(worktree_path) / "kitty-specs"
        wp_files = list(wp_dir.rglob(f"**/tasks/{wp_id}*.md"))

        if not wp_files:
            return FileCorruptionResult(
                file_path=f"{wp_id}.md",
                corruption_type=CorruptionType.MISSING,
                success=False,
                original_size=0,
                corrupted_size=0,
                error=f"WP file not found for {wp_id}"
            )

        return self.corrupt_file(wp_files[0], CorruptionType.INVALID_JSON)

    def restore_file(self, file_path: Union[str, Path]) -> bool:
        """Restore a file from backup."""
        path_str = str(file_path)
        backup = self._backups.get(path_str)

        if backup and backup.exists():
            Path(file_path).write_bytes(backup.read_bytes())
            backup.unlink()
            del self._backups[path_str]
            return True
        return False

    def restore_all(self) -> int:
        """Restore all backed up files."""
        restored = 0
        for path in list(self._backups.keys()):
            if self.restore_file(path):
                restored += 1
        return restored
```

**Acceptance Criteria**:
- Multiple corruption types supported
- Automatic backup before corruption
- Restore capability
- WP-specific corruption helper
- Permission-based corruption

### T028: Implement git conflict injection

Add git conflict injection to `file_faults.py` or create `git_faults.py`:

```python
"""Git conflict injection for testing."""

import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class GitConflictResult:
    """Result of git conflict injection."""
    file_path: str
    success: bool
    conflict_markers: bool
    branches: tuple[str, str]
    error: Optional[str] = None

class GitFaultInjector:
    """Injects git-related faults."""

    def __init__(self, worktree_path: str):
        self.worktree_path = Path(worktree_path)

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        """Run git command in worktree."""
        return subprocess.run(
            ["git", *args],
            cwd=self.worktree_path,
            capture_output=True,
            text=True
        )

    def create_merge_conflict(
        self,
        file_path: str,
        content_a: str,
        content_b: str,
        branch_a: str = "branch-a",
        branch_b: str = "branch-b"
    ) -> GitConflictResult:
        """Create a merge conflict on a specific file.

        Creates two branches with conflicting changes to the same file,
        then attempts to merge them.

        Args:
            file_path: Relative path within worktree
            content_a: Content in first branch
            content_b: Conflicting content in second branch
            branch_a: Name for first branch
            branch_b: Name for second branch

        Returns:
            GitConflictResult with conflict details
        """
        full_path = self.worktree_path / file_path

        try:
            # Get current branch
            current = self._run_git("branch", "--show-current").stdout.strip()

            # Create and checkout branch A
            self._run_git("checkout", "-b", branch_a)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content_a)
            self._run_git("add", file_path)
            self._run_git("commit", "-m", f"Change in {branch_a}")

            # Go back and create branch B
            self._run_git("checkout", current)
            self._run_git("checkout", "-b", branch_b)
            full_path.write_text(content_b)
            self._run_git("add", file_path)
            self._run_git("commit", "-m", f"Change in {branch_b}")

            # Try to merge - should conflict
            merge_result = self._run_git("merge", branch_a)

            has_conflict = merge_result.returncode != 0 and "CONFLICT" in merge_result.stdout

            return GitConflictResult(
                file_path=file_path,
                success=True,
                conflict_markers=has_conflict,
                branches=(branch_a, branch_b),
                error=None if has_conflict else "Merge succeeded unexpectedly"
            )

        except Exception as e:
            return GitConflictResult(
                file_path=file_path,
                success=False,
                conflict_markers=False,
                branches=(branch_a, branch_b),
                error=str(e)
            )

    def create_status_file_conflict(self, wp_id: str) -> GitConflictResult:
        """Create conflict on a WP status file (common scenario).

        Simulates two agents trying to update the same WP's lane.
        """
        wp_file = f"kitty-specs/test-feature/tasks/{wp_id}-test.md"

        content_a = f"""---
work_package_id: "{wp_id}"
lane: "doing"
agent: "agent-a"
---
"""
        content_b = f"""---
work_package_id: "{wp_id}"
lane: "for_review"
agent: "agent-b"
---
"""
        return self.create_merge_conflict(
            file_path=wp_file,
            content_a=content_a,
            content_b=content_b,
            branch_a="agent-a-update",
            branch_b="agent-b-update"
        )

    def abort_merge(self) -> bool:
        """Abort an in-progress merge."""
        result = self._run_git("merge", "--abort")
        return result.returncode == 0

    def resolve_conflict(
        self,
        file_path: str,
        resolution: str
    ) -> bool:
        """Resolve a conflict with specific content."""
        full_path = self.worktree_path / file_path
        full_path.write_text(resolution)
        self._run_git("add", file_path)
        return True
```

**Acceptance Criteria**:
- Creates real git merge conflicts
- WP status file conflict helper
- Abort and resolution methods
- Works within container worktrees

### T029: Implement auth failure injection

Create `tests/agentic/faults/auth_faults.py`:

```python
"""Authentication failure injection."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from contextlib import contextmanager

@dataclass
class AuthFaultResult:
    """Result of auth fault injection."""
    agent_id: str
    fault_type: str
    success: bool
    original_value: Optional[str] = None
    error: Optional[str] = None

class AuthFaultInjector:
    """Injects authentication failures."""

    def __init__(self, secrets_dir: Path):
        self.secrets_dir = secrets_dir
        self._original_values: dict[str, str] = {}

    def invalidate_credentials(
        self,
        agent_id: str,
        credential_file: str
    ) -> AuthFaultResult:
        """Replace valid credentials with invalid ones.

        Args:
            agent_id: Agent whose credentials to invalidate
            credential_file: Name of credential file (e.g., "claude_api_key.txt")

        Returns:
            AuthFaultResult with details
        """
        cred_path = self.secrets_dir / credential_file

        if not cred_path.exists():
            return AuthFaultResult(
                agent_id=agent_id,
                fault_type="invalidate",
                success=False,
                error=f"Credential file not found: {cred_path}"
            )

        # Backup original
        original = cred_path.read_text()
        self._original_values[str(cred_path)] = original

        # Write invalid credentials
        cred_path.write_text("INVALID_API_KEY_FOR_TESTING")

        return AuthFaultResult(
            agent_id=agent_id,
            fault_type="invalidate",
            success=True,
            original_value="[redacted]"
        )

    def remove_credentials(
        self,
        agent_id: str,
        credential_file: str
    ) -> AuthFaultResult:
        """Remove credential file entirely."""
        cred_path = self.secrets_dir / credential_file

        if cred_path.exists():
            # Backup
            self._original_values[str(cred_path)] = cred_path.read_text()
            cred_path.unlink()

        return AuthFaultResult(
            agent_id=agent_id,
            fault_type="remove",
            success=True
        )

    def expire_credentials(
        self,
        agent_id: str,
        credential_file: str
    ) -> AuthFaultResult:
        """Simulate expired credentials (format depends on credential type)."""
        cred_path = self.secrets_dir / credential_file

        if not cred_path.exists():
            return AuthFaultResult(
                agent_id=agent_id,
                fault_type="expire",
                success=False,
                error="Credential file not found"
            )

        # Backup
        self._original_values[str(cred_path)] = cred_path.read_text()

        # Write expired-looking token
        cred_path.write_text("EXPIRED_TOKEN_2024-01-01")

        return AuthFaultResult(
            agent_id=agent_id,
            fault_type="expire",
            success=True
        )

    @contextmanager
    def temporary_auth_failure(
        self,
        agent_id: str,
        credential_file: str
    ):
        """Context manager for temporary auth failure.

        Usage:
            with injector.temporary_auth_failure("claude-code", "claude_api_key.txt"):
                # Agent will fail auth here
                agent.execute()
            # Credentials restored after context
        """
        result = self.invalidate_credentials(agent_id, credential_file)
        try:
            yield result
        finally:
            self.restore_credentials(credential_file)

    def restore_credentials(self, credential_file: str) -> bool:
        """Restore original credentials."""
        cred_path = self.secrets_dir / credential_file
        path_str = str(cred_path)

        if path_str in self._original_values:
            cred_path.write_text(self._original_values[path_str])
            del self._original_values[path_str]
            return True
        return False

    def restore_all(self) -> int:
        """Restore all modified credentials."""
        restored = 0
        for path_str, value in list(self._original_values.items()):
            Path(path_str).write_text(value)
            del self._original_values[path_str]
            restored += 1
        return restored
```

**Acceptance Criteria**:
- Invalidate, remove, and expire credential types
- Automatic backup and restore
- Context manager for scoped failures
- Works with Docker secrets mount

### T030: Implement resource exhaustion injection

Create `tests/agentic/faults/resource_faults.py`:

```python
"""Resource exhaustion fault injection."""

import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import threading

@dataclass
class ResourceFaultResult:
    """Result of resource fault injection."""
    fault_type: str
    target: str
    success: bool
    details: dict
    error: Optional[str] = None

class ResourceFaultInjector:
    """Injects resource exhaustion conditions."""

    def __init__(self, container_id: Optional[str] = None):
        self.container_id = container_id
        self._cleanup_tasks: list = []

    def exhaust_disk_space(
        self,
        path: str,
        fill_mb: int = 1000
    ) -> ResourceFaultResult:
        """Fill disk space to trigger disk full errors.

        Args:
            path: Directory to fill
            fill_mb: Megabytes to write

        Returns:
            ResourceFaultResult
        """
        fill_path = Path(path) / ".disk_fill_test"

        try:
            # Write large file
            with open(fill_path, 'wb') as f:
                # Write in chunks to avoid memory issues
                chunk = b'X' * (1024 * 1024)  # 1MB chunk
                for _ in range(fill_mb):
                    f.write(chunk)

            self._cleanup_tasks.append(lambda: fill_path.unlink(missing_ok=True))

            return ResourceFaultResult(
                fault_type="disk_full",
                target=path,
                success=True,
                details={"filled_mb": fill_mb, "fill_file": str(fill_path)}
            )
        except OSError as e:
            # Disk actually full is also "success" for this test
            if "No space left" in str(e):
                return ResourceFaultResult(
                    fault_type="disk_full",
                    target=path,
                    success=True,
                    details={"filled_mb": "full", "error": str(e)}
                )
            return ResourceFaultResult(
                fault_type="disk_full",
                target=path,
                success=False,
                details={},
                error=str(e)
            )

    def exhaust_memory(
        self,
        container_id: str,
        allocation_mb: int = 5000
    ) -> ResourceFaultResult:
        """Trigger OOM condition in container.

        Runs a process that allocates memory until killed.
        """
        import docker
        client = docker.from_env()
        container = client.containers.get(container_id)

        # Run memory hog
        cmd = f"python3 -c \"x = [bytearray(1024*1024) for _ in range({allocation_mb})]\""
        result = container.exec_run(cmd, detach=False)

        # Exit code 137 = killed by OOM
        oom_triggered = result.exit_code == 137

        return ResourceFaultResult(
            fault_type="memory_pressure",
            target=container_id,
            success=oom_triggered,
            details={
                "exit_code": result.exit_code,
                "allocation_mb": allocation_mb,
                "oom_triggered": oom_triggered
            }
        )

    def exhaust_file_descriptors(
        self,
        count: int = 10000
    ) -> ResourceFaultResult:
        """Open many file descriptors to exhaust limit."""
        files = []

        try:
            for i in range(count):
                f = tempfile.TemporaryFile()
                files.append(f)

            self._cleanup_tasks.append(lambda: [f.close() for f in files])

            return ResourceFaultResult(
                fault_type="fd_exhaustion",
                target="local",
                success=True,
                details={"opened": len(files)}
            )
        except OSError as e:
            # "Too many open files" is success for this test
            if "Too many open files" in str(e):
                return ResourceFaultResult(
                    fault_type="fd_exhaustion",
                    target="local",
                    success=True,
                    details={"opened": len(files), "error": str(e)}
                )
            return ResourceFaultResult(
                fault_type="fd_exhaustion",
                target="local",
                success=False,
                details={},
                error=str(e)
            )

    def cpu_stress(
        self,
        container_id: str,
        duration_seconds: int = 30,
        workers: int = 4
    ) -> ResourceFaultResult:
        """Stress CPU to cause throttling.

        Uses stress tool or pure Python CPU loop.
        """
        import docker
        client = docker.from_env()
        container = client.containers.get(container_id)

        # Try stress tool first, fall back to Python
        stress_cmd = f"timeout {duration_seconds} stress --cpu {workers} || " \
                     f"python3 -c 'import time; start=time.time(); " \
                     f"[sum(range(10**7)) for _ in range(1000) if time.time()-start < {duration_seconds}]'"

        # Run in background
        result = container.exec_run(stress_cmd, detach=True)

        return ResourceFaultResult(
            fault_type="cpu_stress",
            target=container_id,
            success=True,
            details={"duration": duration_seconds, "workers": workers}
        )

    def cleanup(self) -> int:
        """Run all cleanup tasks."""
        cleaned = 0
        for task in self._cleanup_tasks:
            try:
                task()
                cleaned += 1
            except Exception:
                pass
        self._cleanup_tasks.clear()
        return cleaned
```

**Acceptance Criteria**:
- Disk full simulation
- OOM trigger detection
- File descriptor exhaustion
- CPU stress (throttling)
- Automatic cleanup

## Technical Notes

- Fault injectors are composable
- All faults should be reversible/cleanable
- Container faults use Docker SDK
- Resource faults may require elevated permissions

## Files to Create/Modify

1. `tests/agentic/faults/process_faults.py` (create)
2. `tests/agentic/faults/file_faults.py` (create)
3. `tests/agentic/faults/auth_faults.py` (create)
4. `tests/agentic/faults/resource_faults.py` (create)
5. `tests/agentic/faults/__init__.py` (update exports)
6. `tests/agentic/conftest.py` (add fault fixtures)

## Verification

```bash
# Import check
python -c "
from tests.agentic.faults.process_faults import ProcessFaultInjector
from tests.agentic.faults.file_faults import FileFaultInjector
"

# Unit tests (some require Docker)
pytest tests/agentic/faults/ -v
```

## Definition of Done

- [ ] ProcessFaultInjector with SIGTERM/SIGKILL
- [ ] TimeoutFaultInjector with delays
- [ ] FileFaultInjector with corruption types
- [ ] GitFaultInjector with merge conflicts
- [ ] AuthFaultInjector with credential manipulation
- [ ] ResourceFaultInjector with exhaustion
- [ ] All injectors have cleanup methods
- [ ] Unit tests for each fault type

## Activity Log

- 2026-01-19T14:56:15Z – claude-opus – shell_pid=70542 – lane=doing – Started implementation via workflow command
- 2026-01-19T15:05:53Z – claude-opus – shell_pid=70542 – lane=for_review – Moved to for_review
- 2026-01-19T15:06:36Z – claude-opus – shell_pid=77330 – lane=doing – Started review via workflow command
- 2026-01-19T15:16:10Z – claude-opus – shell_pid=77330 – lane=done – Review passed: All 6 subtasks verified - T025 process crash (SIGTERM/SIGKILL/SIGSTOP/SIGCONT), T026 timeout injection (artificial/container_pause/slow_command), T027 file corruption (6 corruption types with backup/restore), T028 git conflicts (merge_conflict/detached_head/stale_lock/etc), T029 auth failures (7 fault types, 8 credential types), T030 resource exhaustion (disk/memory/CPU/FD with 4 exhaustion levels). All imports verified, comprehensive adversarial testing suite complete.
