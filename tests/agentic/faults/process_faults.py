"""Process fault injection for adversarial testing.

This module provides fault injectors that simulate process-level failures:
- SIGTERM: Graceful termination signal
- SIGKILL: Immediate process death (no cleanup)
- Timeout simulation: Artificial delays, container pause

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import os
import signal
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..fixtures.container_fixtures import TestContainer


class TriggerCondition(Enum):
    """When to trigger the fault injection.

    IMMEDIATE: Inject fault immediately when triggered
    DELAYED: Inject fault after a specified delay
    ON_EVENT: Inject fault when a specific event occurs
    RANDOM: Inject fault at random within a time window
    """

    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    ON_EVENT = "on_event"
    RANDOM = "random"


class FaultInjectionError(Exception):
    """Base exception for fault injection failures."""

    pass


class ProcessNotFoundError(FaultInjectionError):
    """Raised when target process cannot be found."""

    pass


class ContainerNotRunningError(FaultInjectionError):
    """Raised when target container is not running."""

    pass


@dataclass
class FaultInjectionResult:
    """Result of a fault injection operation.

    Attributes:
        success: Whether the fault was successfully injected
        fault_type: Type of fault that was injected
        target: What was targeted (PID, container ID, etc.)
        injected_at: When the fault was injected
        metadata: Additional context about the injection
        error: Error message if injection failed
    """

    success: bool
    fault_type: str
    target: str
    injected_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseFaultInjector(ABC):
    """Abstract base class for fault injectors.

    All fault injectors support:
    - Targeting both local processes and containers
    - Configurable trigger conditions
    - Backup and restore for reversibility
    - Logging and observation of injected faults
    """

    def __init__(
        self,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
        on_event: Optional[str] = None,
    ):
        """Initialize fault injector.

        Args:
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger (ignored otherwise)
            on_event: Event name for ON_EVENT trigger (ignored otherwise)
        """
        self.trigger = trigger
        self.delay_seconds = delay_seconds
        self.on_event = on_event
        self._injections: List[FaultInjectionResult] = []
        self._backup_state: Dict[str, Any] = {}

    @property
    def injections(self) -> List[FaultInjectionResult]:
        """Get all injection results."""
        return self._injections.copy()

    @abstractmethod
    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject the fault into the target.

        Args:
            target: Target for fault injection (process, container, etc.)
            **kwargs: Additional parameters for specific fault types

        Returns:
            FaultInjectionResult with details of the injection
        """
        pass

    @abstractmethod
    def can_restore(self) -> bool:
        """Check if this fault type can be restored.

        Returns:
            True if fault can be undone, False otherwise
        """
        pass

    def restore(self) -> bool:
        """Restore the target to pre-fault state if possible.

        Returns:
            True if restoration succeeded, False otherwise
        """
        return False

    def _apply_trigger_delay(self) -> None:
        """Apply delay based on trigger condition."""
        if self.trigger == TriggerCondition.DELAYED and self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        elif self.trigger == TriggerCondition.RANDOM:
            import random

            delay = random.uniform(0, self.delay_seconds)
            time.sleep(delay)


class ProcessFaultInjector(BaseFaultInjector):
    """Inject process-level faults via signals.

    Supports:
    - SIGTERM: Graceful termination (allows cleanup handlers)
    - SIGKILL: Immediate death (no cleanup possible)
    - SIGSTOP/SIGCONT: Pause and resume process

    Example usage:
        injector = ProcessFaultInjector(signal_type=signal.SIGKILL)
        result = injector.inject(pid=12345)
        assert result.success
        assert not injector.can_restore()  # SIGKILL is not reversible

    For containers:
        injector = ProcessFaultInjector(signal_type=signal.SIGTERM)
        result = injector.inject_container(container, process_name="spec-kitty")
    """

    def __init__(
        self,
        signal_type: signal.Signals = signal.SIGTERM,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize process fault injector.

        Args:
            signal_type: Signal to send (SIGTERM, SIGKILL, SIGSTOP, SIGCONT)
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.signal_type = signal_type
        self._stopped_pids: List[int] = []

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject signal fault into a process.

        Args:
            target: Process ID (int) to signal
            **kwargs: Unused, for interface compatibility

        Returns:
            FaultInjectionResult with injection details

        Raises:
            ProcessNotFoundError: If PID does not exist
        """
        pid = int(target)
        self._apply_trigger_delay()

        try:
            # Check if process exists
            os.kill(pid, 0)
        except ProcessLookupError:
            result = FaultInjectionResult(
                success=False,
                fault_type=f"signal_{self.signal_type.name}",
                target=str(pid),
                error=f"Process {pid} not found",
            )
            self._injections.append(result)
            raise ProcessNotFoundError(f"Process {pid} not found")
        except PermissionError:
            result = FaultInjectionResult(
                success=False,
                fault_type=f"signal_{self.signal_type.name}",
                target=str(pid),
                error=f"Permission denied for process {pid}",
            )
            self._injections.append(result)
            raise FaultInjectionError(f"Permission denied for process {pid}")

        try:
            os.kill(pid, self.signal_type)

            # Track stopped processes for restore
            if self.signal_type == signal.SIGSTOP:
                self._stopped_pids.append(pid)

            result = FaultInjectionResult(
                success=True,
                fault_type=f"signal_{self.signal_type.name}",
                target=str(pid),
                metadata={
                    "signal": self.signal_type.name,
                    "signal_value": self.signal_type.value,
                    "trigger": self.trigger.value,
                },
            )
            self._injections.append(result)
            return result

        except Exception as e:
            result = FaultInjectionResult(
                success=False,
                fault_type=f"signal_{self.signal_type.name}",
                target=str(pid),
                error=str(e),
            )
            self._injections.append(result)
            raise FaultInjectionError(f"Failed to send signal to {pid}: {e}")

    def inject_container(
        self,
        container: "TestContainer",
        process_name: Optional[str] = None,
    ) -> FaultInjectionResult:
        """Inject signal fault into a process inside a container.

        Args:
            container: TestContainer instance
            process_name: Name of process to signal (None for main process)

        Returns:
            FaultInjectionResult with injection details

        Raises:
            ContainerNotRunningError: If container is not running
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        self._apply_trigger_delay()

        # Find the target PID inside the container
        if process_name:
            # Use pgrep to find process by name
            exit_code, stdout, stderr = container.exec_command(
                f"pgrep -f '{process_name}'", timeout=10
            )
            if exit_code != 0 or not stdout.strip():
                result = FaultInjectionResult(
                    success=False,
                    fault_type=f"container_signal_{self.signal_type.name}",
                    target=f"{container.container_id}:{process_name}",
                    error=f"Process '{process_name}' not found in container",
                )
                self._injections.append(result)
                raise ProcessNotFoundError(
                    f"Process '{process_name}' not found in container"
                )
            pid = stdout.strip().split()[0]
        else:
            # Signal PID 1 (main process)
            pid = "1"

        # Send signal inside container
        exit_code, stdout, stderr = container.exec_command(
            f"kill -{self.signal_type.value} {pid}", timeout=10
        )

        success = exit_code == 0
        result = FaultInjectionResult(
            success=success,
            fault_type=f"container_signal_{self.signal_type.name}",
            target=f"{container.container_id}:{pid}",
            metadata={
                "signal": self.signal_type.name,
                "container_id": container.container_id,
                "process_name": process_name,
                "pid_in_container": pid,
            },
            error=stderr if not success else None,
        )
        self._injections.append(result)
        return result

    def can_restore(self) -> bool:
        """Check if signal can be reversed.

        Only SIGSTOP can be reversed (via SIGCONT).

        Returns:
            True if SIGSTOP was used and processes were stopped
        """
        return self.signal_type == signal.SIGSTOP and len(self._stopped_pids) > 0

    def restore(self) -> bool:
        """Resume stopped processes via SIGCONT.

        Returns:
            True if all stopped processes were resumed
        """
        if not self.can_restore():
            return False

        success = True
        for pid in self._stopped_pids[:]:
            try:
                os.kill(pid, signal.SIGCONT)
                self._stopped_pids.remove(pid)
            except (ProcessLookupError, PermissionError):
                success = False

        return success


class TimeoutFaultInjector(BaseFaultInjector):
    """Inject timeout-related faults.

    Supports:
    - Artificial delays: Sleep before/during operations
    - Container pause: Docker pause/unpause
    - Response delays: Slow down command execution

    Example usage:
        # Inject a 30-second delay
        injector = TimeoutFaultInjector(delay_type="artificial", delay_seconds=30)
        result = injector.inject(container)

        # Pause a container (simulates complete freeze)
        injector = TimeoutFaultInjector(delay_type="container_pause")
        result = injector.inject(container)
        # ... test timeout handling ...
        injector.restore()  # Unpause
    """

    DELAY_TYPES = ["artificial", "container_pause", "slow_command"]

    def __init__(
        self,
        delay_type: str = "artificial",
        delay_seconds: float = 30.0,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
    ):
        """Initialize timeout fault injector.

        Args:
            delay_type: Type of delay to inject
            delay_seconds: Duration of delay (for artificial/slow_command)
            trigger: When to trigger the fault

        Raises:
            ValueError: If delay_type is not recognized
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)

        if delay_type not in self.DELAY_TYPES:
            raise ValueError(
                f"Unknown delay_type: {delay_type}. "
                f"Must be one of: {self.DELAY_TYPES}"
            )

        self.delay_type = delay_type
        self.delay_duration = delay_seconds
        self._paused_containers: List["TestContainer"] = []

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject timeout fault.

        Args:
            target: For container_pause, a TestContainer. Otherwise unused.
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        self._apply_trigger_delay()

        if self.delay_type == "artificial":
            return self._inject_artificial_delay(target)
        elif self.delay_type == "container_pause":
            return self._inject_container_pause(target)
        elif self.delay_type == "slow_command":
            return self._inject_slow_command(target, **kwargs)
        else:
            raise FaultInjectionError(f"Unknown delay type: {self.delay_type}")

    def _inject_artificial_delay(self, target: Any) -> FaultInjectionResult:
        """Simply sleep for the specified duration.

        This is useful for testing timeout handling when the delay
        is known and controlled.
        """
        time.sleep(self.delay_duration)

        result = FaultInjectionResult(
            success=True,
            fault_type="artificial_delay",
            target=str(target) if target else "none",
            metadata={
                "delay_seconds": self.delay_duration,
                "delay_type": self.delay_type,
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_pause(
        self, container: "TestContainer"
    ) -> FaultInjectionResult:
        """Pause a Docker container.

        This simulates a complete freeze - the container's processes
        are suspended and won't respond to any input.
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        import subprocess

        try:
            subprocess.run(
                ["docker", "pause", container.container_id],
                check=True,
                capture_output=True,
                timeout=30,
            )

            self._paused_containers.append(container)

            result = FaultInjectionResult(
                success=True,
                fault_type="container_pause",
                target=container.container_id,
                metadata={
                    "container_id": container.container_id,
                    "agent_id": container.agent_id,
                },
            )
            self._injections.append(result)
            return result

        except subprocess.CalledProcessError as e:
            result = FaultInjectionResult(
                success=False,
                fault_type="container_pause",
                target=container.container_id,
                error=f"Failed to pause container: {e.stderr.decode()}",
            )
            self._injections.append(result)
            raise FaultInjectionError(f"Failed to pause container: {e}")
        except subprocess.TimeoutExpired:
            result = FaultInjectionResult(
                success=False,
                fault_type="container_pause",
                target=container.container_id,
                error="Docker pause command timed out",
            )
            self._injections.append(result)
            raise FaultInjectionError("Docker pause command timed out")

    def _inject_slow_command(
        self, container: "TestContainer", command: str = ""
    ) -> FaultInjectionResult:
        """Execute a command with artificial delay prefix.

        Wraps the command with a sleep to simulate slow execution.
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        slow_command = f"sleep {self.delay_duration} && {command}"

        exit_code, stdout, stderr = container.exec_command(
            slow_command, timeout=int(self.delay_duration) + 60
        )

        result = FaultInjectionResult(
            success=exit_code == 0,
            fault_type="slow_command",
            target=container.container_id,
            metadata={
                "original_command": command,
                "delay_seconds": self.delay_duration,
                "exit_code": exit_code,
                "stdout_preview": stdout[:500] if stdout else "",
            },
            error=stderr if exit_code != 0 else None,
        )
        self._injections.append(result)
        return result

    def can_restore(self) -> bool:
        """Check if timeout fault can be reversed.

        Only container_pause can be reversed (via unpause).

        Returns:
            True if containers were paused
        """
        return self.delay_type == "container_pause" and len(self._paused_containers) > 0

    def restore(self) -> bool:
        """Unpause paused containers.

        Returns:
            True if all paused containers were unpaused
        """
        if not self.can_restore():
            return False

        import subprocess

        success = True
        for container in self._paused_containers[:]:
            try:
                subprocess.run(
                    ["docker", "unpause", container.container_id],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                self._paused_containers.remove(container)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                success = False

        return success


class ProcessCrashInjector(BaseFaultInjector):
    """Inject controlled process crashes for testing recovery.

    Simulates various crash scenarios:
    - Segmentation fault (SIGSEGV)
    - Abort (SIGABRT)
    - Illegal instruction (SIGILL)
    - Exit with error code

    Example usage:
        injector = ProcessCrashInjector(crash_type="segfault")
        result = injector.inject_container(container, "spec-kitty")
        # Test that workflow handles the crash gracefully
    """

    CRASH_TYPES = ["segfault", "abort", "illegal", "exit_error", "oom_kill"]

    def __init__(
        self,
        crash_type: str = "exit_error",
        exit_code: int = 1,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize crash injector.

        Args:
            crash_type: Type of crash to simulate
            exit_code: Exit code for exit_error type
            trigger: When to trigger the crash
            delay_seconds: Delay before crash

        Raises:
            ValueError: If crash_type is not recognized
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)

        if crash_type not in self.CRASH_TYPES:
            raise ValueError(
                f"Unknown crash_type: {crash_type}. "
                f"Must be one of: {self.CRASH_TYPES}"
            )

        self.crash_type = crash_type
        self.exit_code = exit_code

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Inject crash into target process.

        For local processes, sends appropriate signal.
        For containers, executes crash-inducing command.

        Args:
            target: Process ID (int) or TestContainer
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        self._apply_trigger_delay()

        if isinstance(target, int):
            return self._inject_local_crash(target)
        else:
            return self._inject_container_crash(target, **kwargs)

    def _inject_local_crash(self, pid: int) -> FaultInjectionResult:
        """Inject crash into local process via signal."""
        signal_map = {
            "segfault": signal.SIGSEGV,
            "abort": signal.SIGABRT,
            "illegal": signal.SIGILL,
            "exit_error": signal.SIGTERM,  # Will cause non-zero exit
            "oom_kill": signal.SIGKILL,  # Simulates OOM killer
        }

        sig = signal_map.get(self.crash_type, signal.SIGTERM)

        try:
            os.kill(pid, sig)
            result = FaultInjectionResult(
                success=True,
                fault_type=f"crash_{self.crash_type}",
                target=str(pid),
                metadata={
                    "crash_type": self.crash_type,
                    "signal": sig.name,
                },
            )
            self._injections.append(result)
            return result
        except Exception as e:
            result = FaultInjectionResult(
                success=False,
                fault_type=f"crash_{self.crash_type}",
                target=str(pid),
                error=str(e),
            )
            self._injections.append(result)
            raise FaultInjectionError(f"Failed to inject crash: {e}")

    def _inject_container_crash(
        self,
        container: "TestContainer",
        process_name: Optional[str] = None,
    ) -> FaultInjectionResult:
        """Inject crash into process inside container."""
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        # Build crash command based on type
        crash_commands = {
            "segfault": "kill -SEGV $$",
            "abort": "kill -ABRT $$",
            "illegal": "kill -ILL $$",
            "exit_error": f"exit {self.exit_code}",
            "oom_kill": "kill -KILL $$",
        }

        cmd = crash_commands.get(self.crash_type, "exit 1")

        if process_name:
            # Kill specific process
            cmd = f"pkill -{self._get_signal_name()} -f '{process_name}'"

        exit_code, stdout, stderr = container.exec_command(cmd, timeout=30)

        # For crashes, non-zero exit is expected
        expected_failure = self.crash_type != "exit_error" or self.exit_code != 0

        result = FaultInjectionResult(
            success=True,  # Crash was successfully injected
            fault_type=f"container_crash_{self.crash_type}",
            target=f"{container.container_id}:{process_name or 'main'}",
            metadata={
                "crash_type": self.crash_type,
                "command": cmd,
                "exit_code": exit_code,
                "container_id": container.container_id,
            },
        )
        self._injections.append(result)
        return result

    def _get_signal_name(self) -> str:
        """Get signal name for crash type."""
        signal_names = {
            "segfault": "SEGV",
            "abort": "ABRT",
            "illegal": "ILL",
            "exit_error": "TERM",
            "oom_kill": "KILL",
        }
        return signal_names.get(self.crash_type, "TERM")

    def can_restore(self) -> bool:
        """Crashes cannot be restored."""
        return False
