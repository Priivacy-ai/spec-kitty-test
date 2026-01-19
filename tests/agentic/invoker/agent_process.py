"""
AgentProcess: Subprocess wrapper for agent invocations.

Provides timeout management, output capture, and clean termination
for agent subprocesses.
"""

import hashlib
import signal
import subprocess
import threading
from datetime import datetime, timezone
from typing import List, Optional

from .invocation_result import (
    InvocationOutcome,
    InvocationResult,
    ParsedAgentResponse,
)


class AgentProcess:
    """
    Wrapper around a running subprocess with timeout management,
    output capture, and clean termination.
    """

    def __init__(
        self,
        agent_id: str,
        process: subprocess.Popen,
        timeout_seconds: float,
        worktree_path: str,
        prompt_hash: Optional[str] = None,
        stdin_input: Optional[bytes] = None,
    ):
        """
        Initialize an AgentProcess wrapper.

        Args:
            agent_id: Identifier for the agent (e.g., "claude", "copilot")
            process: The subprocess.Popen instance to wrap
            timeout_seconds: Maximum time to wait before killing
            worktree_path: Path to the git worktree for this invocation
            prompt_hash: Optional SHA256 hash of the prompt (computed if not provided)
            stdin_input: Optional bytes to send to process stdin via communicate()
        """
        self.agent_id = agent_id
        self._process = process
        self._timeout = timeout_seconds
        self._worktree = worktree_path
        self._started_at = datetime.now(timezone.utc)
        self._stdout_buffer: List[str] = []
        self._stderr_buffer: List[str] = []
        self._completed = False
        self._killed = False
        self._timeout_exceeded = False
        self._prompt_hash = prompt_hash or ""
        self._stdin_input = stdin_input
        self._lock = threading.Lock()

    @property
    def pid(self) -> int:
        """Process ID of the wrapped subprocess."""
        return self._process.pid

    @property
    def is_running(self) -> bool:
        """Check if the process is still alive."""
        return self._process.poll() is None

    @property
    def elapsed_seconds(self) -> float:
        """Time elapsed since process started."""
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    def get_stdout(self) -> str:
        """Get buffered stdout content."""
        with self._lock:
            return "".join(self._stdout_buffer)

    def get_stderr(self) -> str:
        """Get buffered stderr content."""
        with self._lock:
            return "".join(self._stderr_buffer)

    def kill(
        self, signal_num: int = signal.SIGTERM, grace_period: float = 5.0
    ) -> None:
        """
        Gracefully kill the process with fallback to SIGKILL.

        Args:
            signal_num: Initial signal to send (default SIGTERM)
            grace_period: Seconds to wait before SIGKILL
        """
        with self._lock:
            self._killed = True

        if not self.is_running:
            return

        try:
            self._process.send_signal(signal_num)
            try:
                self._process.wait(timeout=grace_period)
            except subprocess.TimeoutExpired:
                self.force_kill()
        except ProcessLookupError:
            pass  # Process already dead

    def force_kill(self) -> None:
        """Immediately kill the process with SIGKILL."""
        if not self.is_running:
            return

        try:
            self._process.kill()
            self._process.wait(timeout=1.0)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass

        with self._lock:
            self._killed = True

    def wait(self, timeout: Optional[float] = None) -> InvocationResult:
        """
        Wait for process completion or timeout.

        Args:
            timeout: Override timeout (uses instance timeout if None)

        Returns:
            InvocationResult with complete execution data
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        timer: Optional[threading.Timer] = None
        timeout_event = threading.Event()

        def on_timeout():
            timeout_event.set()
            with self._lock:
                self._timeout_exceeded = True
            self.kill()

        if effective_timeout > 0:
            timer = threading.Timer(effective_timeout, on_timeout)
            timer.start()

        try:
            stdout, stderr = self._process.communicate(input=self._stdin_input)

            with self._lock:
                if stdout:
                    self._stdout_buffer.append(
                        stdout.decode("utf-8", errors="replace")
                    )
                if stderr:
                    self._stderr_buffer.append(
                        stderr.decode("utf-8", errors="replace")
                    )
                self._completed = True

        except Exception:
            # Process might have been killed by timeout
            pass
        finally:
            if timer:
                timer.cancel()

        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - self._started_at).total_seconds()

        stdout_str = self.get_stdout()
        stderr_str = self.get_stderr()
        exit_code = self._process.returncode if self._process.returncode is not None else -1

        # Determine outcome
        with self._lock:
            timeout_exceeded = self._timeout_exceeded
            killed = self._killed

        outcome = self._determine_outcome(exit_code, timeout_exceeded)

        # Create parsed response (minimal for now)
        parsed_response: Optional[ParsedAgentResponse] = None
        if outcome == InvocationOutcome.SUCCESS:
            parsed_response = ParsedAgentResponse.from_raw(stdout_str, stderr_str)

        error_message: Optional[str] = None
        if outcome == InvocationOutcome.TIMEOUT:
            error_message = f"Process exceeded timeout of {effective_timeout}s"
        elif outcome == InvocationOutcome.FAILURE:
            error_message = f"Process exited with code {exit_code}"
        elif outcome == InvocationOutcome.CRASH:
            error_message = f"Process crashed (exit code {exit_code})"

        return InvocationResult(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=exit_code,
            started_at=self._started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            outcome=outcome,
            parsed_response=parsed_response,
            agent_id=self.agent_id,
            prompt_hash=self._prompt_hash,
            worktree_path=self._worktree,
            error_message=error_message,
            timeout_exceeded=timeout_exceeded,
            killed=killed,
        )

    def _determine_outcome(
        self, exit_code: int, timeout_exceeded: bool
    ) -> InvocationOutcome:
        """Determine the invocation outcome based on exit state."""
        if timeout_exceeded:
            return InvocationOutcome.TIMEOUT

        if exit_code == 0:
            return InvocationOutcome.SUCCESS

        # Negative exit codes typically indicate signals
        if exit_code < 0:
            return InvocationOutcome.CRASH

        # Non-zero positive exit code
        return InvocationOutcome.FAILURE

    @staticmethod
    def compute_prompt_hash(prompt: str) -> str:
        """Compute SHA256 hash of a prompt for deduplication."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
