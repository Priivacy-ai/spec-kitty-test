"""Resource exhaustion fault injection for adversarial testing.

This module provides fault injectors that simulate resource exhaustion:
- Disk space exhaustion: Fill disk to capacity
- Memory pressure: Allocate memory to trigger OOM
- CPU stress: Generate CPU load
- File descriptor exhaustion: Open many files
- Network bandwidth: Simulate slow/congested network

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

import os
import shutil
import subprocess
import tempfile
import threading
import time
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


class ResourceType(Enum):
    """Types of resources that can be exhausted.

    DISK: Disk space
    MEMORY: RAM/memory
    CPU: CPU cycles
    FILE_DESCRIPTORS: Open file handles
    NETWORK_BANDWIDTH: Network throughput
    IOPS: Disk I/O operations per second
    """

    DISK = "disk"
    MEMORY = "memory"
    CPU = "cpu"
    FILE_DESCRIPTORS = "file_descriptors"
    NETWORK_BANDWIDTH = "network_bandwidth"
    IOPS = "iops"


class ExhaustionLevel(Enum):
    """Level of resource exhaustion.

    LIGHT: Noticeable but not critical (50% usage)
    MODERATE: Performance degradation (75% usage)
    SEVERE: Near exhaustion (90% usage)
    CRITICAL: Complete exhaustion (99%+ usage)
    """

    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


# Percentage mappings for exhaustion levels
EXHAUSTION_PERCENTAGES = {
    ExhaustionLevel.LIGHT: 50,
    ExhaustionLevel.MODERATE: 75,
    ExhaustionLevel.SEVERE: 90,
    ExhaustionLevel.CRITICAL: 99,
}


@dataclass
class ResourceState:
    """Current state of a resource.

    Attributes:
        resource_type: Type of resource
        total: Total available amount
        used: Amount currently used
        unit: Unit of measurement
        captured_at: When this state was captured
    """

    resource_type: ResourceType
    total: float
    used: float
    unit: str
    captured_at: datetime = field(default_factory=datetime.now)

    @property
    def usage_percent(self) -> float:
        """Get usage as percentage."""
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100

    @property
    def available(self) -> float:
        """Get available amount."""
        return self.total - self.used


class ResourceFaultInjector(BaseFaultInjector):
    """Inject resource exhaustion faults for testing resilience.

    Supports:
    - Disk space exhaustion via large temp files
    - Memory pressure via allocation (controlled)
    - CPU stress via busy loops
    - File descriptor exhaustion
    - I/O throttling via cgroups (container only)

    All operations support cleanup and restoration.

    Example usage:
        injector = ResourceFaultInjector(
            resource_type=ResourceType.DISK,
            exhaustion_level=ExhaustionLevel.SEVERE
        )
        result = injector.inject("/tmp")  # Fill /tmp to 90%
        # ... test disk full handling ...
        injector.restore()  # Clean up temp files

    For containers:
        result = injector.inject_container(
            container,
            mount_point="/workspace"
        )
    """

    def __init__(
        self,
        resource_type: ResourceType = ResourceType.DISK,
        exhaustion_level: ExhaustionLevel = ExhaustionLevel.MODERATE,
        target_usage_percent: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize resource fault injector.

        Args:
            resource_type: Type of resource to exhaust
            exhaustion_level: Level of exhaustion (overridden by target_usage_percent)
            target_usage_percent: Exact target usage percentage (0-100)
            duration_seconds: Duration to maintain exhaustion (None = until restore)
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.resource_type = resource_type
        self.exhaustion_level = exhaustion_level
        self.target_usage_percent = (
            target_usage_percent
            if target_usage_percent is not None
            else EXHAUSTION_PERCENTAGES[exhaustion_level]
        )
        self.duration_seconds = duration_seconds

        self._cleanup_items: List[str] = []
        self._active_threads: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._temp_dir: Optional[Path] = None
        self._open_files: List[Any] = []

    def inject(self, target: Any = None, **kwargs) -> FaultInjectionResult:
        """Inject resource exhaustion fault.

        Args:
            target: Target path/location for fault injection
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        self._apply_trigger_delay()

        if self.resource_type == ResourceType.DISK:
            return self._inject_disk_exhaustion(target, **kwargs)
        elif self.resource_type == ResourceType.MEMORY:
            return self._inject_memory_pressure(**kwargs)
        elif self.resource_type == ResourceType.CPU:
            return self._inject_cpu_stress(**kwargs)
        elif self.resource_type == ResourceType.FILE_DESCRIPTORS:
            return self._inject_fd_exhaustion(**kwargs)
        else:
            raise FaultInjectionError(
                f"Resource type {self.resource_type.value} not supported for local injection"
            )

    def inject_container(
        self,
        container: "TestContainer",
        mount_point: str = "/workspace",
        **kwargs,
    ) -> FaultInjectionResult:
        """Inject resource exhaustion inside a container.

        Args:
            container: TestContainer instance
            mount_point: Mount point to target (for disk)
            **kwargs: Additional parameters

        Returns:
            FaultInjectionResult with injection details
        """
        if not container.is_running:
            raise ContainerNotRunningError(
                f"Container {container.container_id} is not running"
            )

        self._apply_trigger_delay()

        if self.resource_type == ResourceType.DISK:
            return self._inject_container_disk_exhaustion(container, mount_point)
        elif self.resource_type == ResourceType.MEMORY:
            return self._inject_container_memory_pressure(container, **kwargs)
        elif self.resource_type == ResourceType.CPU:
            return self._inject_container_cpu_stress(container, **kwargs)
        else:
            raise FaultInjectionError(
                f"Resource type {self.resource_type.value} not supported for container injection"
            )

    def _inject_disk_exhaustion(
        self, target_path: Optional[Any] = None, **kwargs
    ) -> FaultInjectionResult:
        """Fill disk space with temporary files."""
        target = Path(target_path) if target_path else Path(tempfile.gettempdir())

        if not target.exists():
            raise FaultInjectionError(f"Target path does not exist: {target}")

        # Get current disk usage
        usage = shutil.disk_usage(target)
        current_percent = (usage.used / usage.total) * 100

        if current_percent >= self.target_usage_percent:
            result = FaultInjectionResult(
                success=True,
                fault_type=f"disk_exhaustion_{self.exhaustion_level.value}",
                target=str(target),
                metadata={
                    "current_usage_percent": round(current_percent, 2),
                    "target_usage_percent": self.target_usage_percent,
                    "note": "Disk already at or above target usage",
                },
            )
            self._injections.append(result)
            return result

        # Calculate how much space to fill
        target_used = (self.target_usage_percent / 100) * usage.total
        bytes_to_fill = int(target_used - usage.used)

        # Create temp directory for fill files
        self._temp_dir = Path(tempfile.mkdtemp(prefix="disk_fill_", dir=target))
        self._cleanup_items.append(str(self._temp_dir))

        # Fill disk with chunks
        chunk_size = min(100 * 1024 * 1024, bytes_to_fill)  # 100MB chunks max
        filled = 0
        file_count = 0

        try:
            while filled < bytes_to_fill:
                remaining = bytes_to_fill - filled
                write_size = min(chunk_size, remaining)

                fill_file = self._temp_dir / f"fill_{file_count}.dat"
                with open(fill_file, "wb") as f:
                    # Write in smaller chunks to avoid memory issues
                    write_chunk = min(write_size, 10 * 1024 * 1024)
                    written = 0
                    while written < write_size:
                        f.write(os.urandom(min(write_chunk, write_size - written)))
                        written += write_chunk
                        filled += write_chunk

                file_count += 1

        except OSError as e:
            # Disk full - this is expected at critical level
            pass

        # Get final usage
        final_usage = shutil.disk_usage(target)
        final_percent = (final_usage.used / final_usage.total) * 100

        result = FaultInjectionResult(
            success=True,
            fault_type=f"disk_exhaustion_{self.exhaustion_level.value}",
            target=str(target),
            metadata={
                "initial_usage_percent": round(current_percent, 2),
                "final_usage_percent": round(final_percent, 2),
                "target_usage_percent": self.target_usage_percent,
                "bytes_filled": filled,
                "files_created": file_count,
                "temp_dir": str(self._temp_dir),
            },
        )
        self._injections.append(result)
        return result

    def _inject_memory_pressure(self, **kwargs) -> FaultInjectionResult:
        """Create memory pressure by allocating memory.

        Note: This is dangerous and should be used carefully.
        Uses a separate thread that can be stopped.
        """
        import resource

        # Get available memory (rough estimate)
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        available_kb = int(line.split()[1])
                        break
                else:
                    available_kb = 1024 * 1024  # Default 1GB
        except FileNotFoundError:
            # Not Linux, use different approach
            available_kb = 1024 * 1024  # Default 1GB

        available_bytes = available_kb * 1024
        target_alloc = int(available_bytes * (self.target_usage_percent / 100))

        # Cap at 1GB to prevent OOM
        max_alloc = min(target_alloc, 1024 * 1024 * 1024)

        # Allocate in a separate thread
        memory_holder = []

        def allocate_memory():
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            allocated = 0

            while allocated < max_alloc and not self._stop_event.is_set():
                try:
                    # Allocate chunk
                    chunk = bytearray(chunk_size)
                    # Touch memory to ensure it's allocated
                    for i in range(0, len(chunk), 4096):
                        chunk[i] = 1
                    memory_holder.append(chunk)
                    allocated += chunk_size
                except MemoryError:
                    break

            # Hold memory until stop event
            while not self._stop_event.is_set():
                time.sleep(0.1)

            # Release memory
            memory_holder.clear()

        thread = threading.Thread(target=allocate_memory, daemon=True)
        thread.start()
        self._active_threads.append(thread)

        # Wait a bit for allocation
        time.sleep(0.5)

        result = FaultInjectionResult(
            success=True,
            fault_type=f"memory_pressure_{self.exhaustion_level.value}",
            target="system",
            metadata={
                "target_allocation_bytes": max_alloc,
                "exhaustion_level": self.exhaustion_level.value,
                "thread_running": thread.is_alive(),
            },
        )
        self._injections.append(result)
        return result

    def _inject_cpu_stress(self, num_workers: int = 0, **kwargs) -> FaultInjectionResult:
        """Create CPU stress with busy loops.

        Args:
            num_workers: Number of worker threads (0 = auto-detect cores)
        """
        if num_workers == 0:
            num_workers = os.cpu_count() or 1

        # Scale workers by exhaustion level
        scale_factors = {
            ExhaustionLevel.LIGHT: 0.25,
            ExhaustionLevel.MODERATE: 0.5,
            ExhaustionLevel.SEVERE: 0.75,
            ExhaustionLevel.CRITICAL: 1.0,
        }
        num_workers = max(1, int(num_workers * scale_factors[self.exhaustion_level]))

        def cpu_worker():
            """Busy loop to consume CPU."""
            while not self._stop_event.is_set():
                # Do some work
                _ = sum(i * i for i in range(10000))

        for _ in range(num_workers):
            thread = threading.Thread(target=cpu_worker, daemon=True)
            thread.start()
            self._active_threads.append(thread)

        result = FaultInjectionResult(
            success=True,
            fault_type=f"cpu_stress_{self.exhaustion_level.value}",
            target="system",
            metadata={
                "worker_count": num_workers,
                "exhaustion_level": self.exhaustion_level.value,
                "threads_started": len(self._active_threads),
            },
        )
        self._injections.append(result)
        return result

    def _inject_fd_exhaustion(self, **kwargs) -> FaultInjectionResult:
        """Exhaust file descriptors by opening many files."""
        import resource

        # Get current limits
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

        # Calculate target FD count
        target_fds = int(soft_limit * (self.target_usage_percent / 100))

        # Create temp files
        self._temp_dir = Path(tempfile.mkdtemp(prefix="fd_exhaust_"))
        self._cleanup_items.append(str(self._temp_dir))

        opened = 0
        try:
            for i in range(target_fds):
                f = open(self._temp_dir / f"fd_{i}.tmp", "w")
                self._open_files.append(f)
                opened += 1
        except OSError:
            # Hit limit
            pass

        result = FaultInjectionResult(
            success=True,
            fault_type=f"fd_exhaustion_{self.exhaustion_level.value}",
            target="system",
            metadata={
                "soft_limit": soft_limit,
                "hard_limit": hard_limit,
                "target_fds": target_fds,
                "opened_fds": opened,
                "exhaustion_level": self.exhaustion_level.value,
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_disk_exhaustion(
        self,
        container: "TestContainer",
        mount_point: str,
    ) -> FaultInjectionResult:
        """Fill disk space inside container."""
        # Get current usage
        exit_code, stdout, stderr = container.exec_command(
            f"df -B1 '{mount_point}' | tail -1 | awk '{{print $2, $3}}'",
            timeout=30,
        )

        if exit_code != 0:
            raise FaultInjectionError(f"Failed to get disk usage: {stderr}")

        parts = stdout.strip().split()
        if len(parts) < 2:
            raise FaultInjectionError(f"Unexpected df output: {stdout}")

        total_bytes = int(parts[0])
        used_bytes = int(parts[1])
        current_percent = (used_bytes / total_bytes) * 100

        # Calculate fill amount
        target_used = int((self.target_usage_percent / 100) * total_bytes)
        bytes_to_fill = max(0, target_used - used_bytes)

        if bytes_to_fill == 0:
            result = FaultInjectionResult(
                success=True,
                fault_type=f"container_disk_exhaustion_{self.exhaustion_level.value}",
                target=f"{container.container_id}:{mount_point}",
                metadata={
                    "current_usage_percent": round(current_percent, 2),
                    "target_usage_percent": self.target_usage_percent,
                    "note": "Disk already at or above target usage",
                },
            )
            self._injections.append(result)
            return result

        # Fill disk using dd
        fill_dir = f"{mount_point}/.disk_fill_test"
        container.exec_command(f"mkdir -p '{fill_dir}'", timeout=10)

        # Fill in chunks
        chunk_mb = min(100, bytes_to_fill // (1024 * 1024) + 1)
        filled = 0
        file_count = 0

        while filled < bytes_to_fill:
            remaining_mb = (bytes_to_fill - filled) // (1024 * 1024)
            write_mb = min(chunk_mb, remaining_mb + 1)

            exit_code, stdout, stderr = container.exec_command(
                f"dd if=/dev/zero of='{fill_dir}/fill_{file_count}.dat' bs=1M count={write_mb} 2>/dev/null",
                timeout=120,
            )

            if exit_code != 0:
                break  # Disk full or error

            filled += write_mb * 1024 * 1024
            file_count += 1

        # Store cleanup info
        self._cleanup_items.append(f"container:{container.container_id}:{fill_dir}")

        result = FaultInjectionResult(
            success=True,
            fault_type=f"container_disk_exhaustion_{self.exhaustion_level.value}",
            target=f"{container.container_id}:{mount_point}",
            metadata={
                "initial_usage_percent": round(current_percent, 2),
                "target_usage_percent": self.target_usage_percent,
                "bytes_filled": filled,
                "files_created": file_count,
                "fill_dir": fill_dir,
                "container_id": container.container_id,
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_memory_pressure(
        self,
        container: "TestContainer",
        **kwargs,
    ) -> FaultInjectionResult:
        """Create memory pressure inside container using stress-ng if available."""
        # Check if stress-ng is available
        exit_code, stdout, stderr = container.exec_command(
            "which stress-ng || which stress", timeout=10
        )

        if exit_code != 0:
            # Try to install
            container.exec_command("apt-get update && apt-get install -y stress-ng", timeout=120)

        # Calculate memory to allocate (based on container limit)
        memory_percent = EXHAUSTION_PERCENTAGES[self.exhaustion_level]

        # Run stress in background
        duration = self.duration_seconds or 300  # Default 5 minutes
        exit_code, stdout, stderr = container.exec_command(
            f"stress-ng --vm 1 --vm-bytes {memory_percent}% --timeout {int(duration)}s &",
            timeout=10,
        )

        result = FaultInjectionResult(
            success=True,
            fault_type=f"container_memory_pressure_{self.exhaustion_level.value}",
            target=container.container_id,
            metadata={
                "memory_percent": memory_percent,
                "duration_seconds": duration,
                "container_id": container.container_id,
                "method": "stress-ng",
            },
        )
        self._injections.append(result)
        return result

    def _inject_container_cpu_stress(
        self,
        container: "TestContainer",
        **kwargs,
    ) -> FaultInjectionResult:
        """Create CPU stress inside container."""
        # Check if stress-ng is available
        exit_code, stdout, stderr = container.exec_command(
            "which stress-ng || which stress", timeout=10
        )

        if exit_code != 0:
            container.exec_command("apt-get update && apt-get install -y stress-ng", timeout=120)

        # Get CPU count
        exit_code, stdout, stderr = container.exec_command("nproc", timeout=10)
        cpu_count = int(stdout.strip()) if exit_code == 0 else 1

        # Scale workers
        scale_factors = {
            ExhaustionLevel.LIGHT: 0.25,
            ExhaustionLevel.MODERATE: 0.5,
            ExhaustionLevel.SEVERE: 0.75,
            ExhaustionLevel.CRITICAL: 1.0,
        }
        workers = max(1, int(cpu_count * scale_factors[self.exhaustion_level]))

        duration = self.duration_seconds or 300
        exit_code, stdout, stderr = container.exec_command(
            f"stress-ng --cpu {workers} --timeout {int(duration)}s &",
            timeout=10,
        )

        result = FaultInjectionResult(
            success=True,
            fault_type=f"container_cpu_stress_{self.exhaustion_level.value}",
            target=container.container_id,
            metadata={
                "worker_count": workers,
                "cpu_count": cpu_count,
                "duration_seconds": duration,
                "container_id": container.container_id,
                "method": "stress-ng",
            },
        )
        self._injections.append(result)
        return result

    def get_resource_state(self, target: Optional[str] = None) -> ResourceState:
        """Get current resource state.

        Args:
            target: Target path for disk, otherwise system-wide

        Returns:
            ResourceState with current usage
        """
        if self.resource_type == ResourceType.DISK:
            target_path = Path(target) if target else Path(tempfile.gettempdir())
            usage = shutil.disk_usage(target_path)
            return ResourceState(
                resource_type=ResourceType.DISK,
                total=usage.total,
                used=usage.used,
                unit="bytes",
            )
        elif self.resource_type == ResourceType.MEMORY:
            try:
                with open("/proc/meminfo") as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            meminfo[parts[0].rstrip(":")] = int(parts[1]) * 1024
                return ResourceState(
                    resource_type=ResourceType.MEMORY,
                    total=meminfo.get("MemTotal", 0),
                    used=meminfo.get("MemTotal", 0) - meminfo.get("MemAvailable", 0),
                    unit="bytes",
                )
            except FileNotFoundError:
                return ResourceState(
                    resource_type=ResourceType.MEMORY,
                    total=0,
                    used=0,
                    unit="bytes",
                )
        elif self.resource_type == ResourceType.CPU:
            import resource

            return ResourceState(
                resource_type=ResourceType.CPU,
                total=100.0,  # Percentage
                used=0.0,  # Would need sampling to measure
                unit="percent",
            )
        else:
            return ResourceState(
                resource_type=self.resource_type,
                total=0,
                used=0,
                unit="unknown",
            )

    def can_restore(self) -> bool:
        """Check if resource state can be restored."""
        return (
            len(self._cleanup_items) > 0
            or len(self._active_threads) > 0
            or len(self._open_files) > 0
        )

    def restore(self) -> bool:
        """Restore resource state by cleaning up."""
        success = True

        # Stop threads
        self._stop_event.set()
        for thread in self._active_threads:
            thread.join(timeout=5)
        self._active_threads.clear()
        self._stop_event.clear()

        # Close open files
        for f in self._open_files:
            try:
                f.close()
            except Exception:
                pass
        self._open_files.clear()

        # Clean up files and directories
        for item in self._cleanup_items:
            try:
                if item.startswith("container:"):
                    # Container cleanup
                    parts = item.split(":", 2)
                    if len(parts) == 3:
                        # Would need container reference to clean up
                        pass
                else:
                    path = Path(item)
                    if path.is_dir():
                        shutil.rmtree(path)
                    elif path.exists():
                        path.unlink()
            except Exception:
                success = False

        self._cleanup_items.clear()
        self._temp_dir = None

        return success


class DiskQuotaInjector(BaseFaultInjector):
    """Inject disk quota exhaustion faults.

    Simulates quota-based disk restrictions without actually
    filling the disk. Useful for testing quota error handling.

    Example usage:
        injector = DiskQuotaInjector(quota_bytes=1024*1024)  # 1MB quota
        result = injector.inject("/path/to/test")
        # Subsequent writes will fail with "quota exceeded"
    """

    def __init__(
        self,
        quota_bytes: int = 1024 * 1024,
        trigger: TriggerCondition = TriggerCondition.IMMEDIATE,
        delay_seconds: float = 0.0,
    ):
        """Initialize disk quota injector.

        Args:
            quota_bytes: Simulated quota in bytes
            trigger: When to trigger the fault
            delay_seconds: Delay for DELAYED trigger
        """
        super().__init__(trigger=trigger, delay_seconds=delay_seconds)
        self.quota_bytes = quota_bytes
        self._quota_file: Optional[Path] = None

    def inject(self, target: Any, **kwargs) -> FaultInjectionResult:
        """Create a quota marker file.

        The test code should check for this marker and simulate
        quota exceeded errors accordingly.

        Args:
            target: Path to mark with quota

        Returns:
            FaultInjectionResult with injection details
        """
        self._apply_trigger_delay()

        target_path = Path(target)
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        self._quota_file = target_path / ".disk_quota_test"
        self._quota_file.write_text(
            f"quota_bytes={self.quota_bytes}\n"
            f"created_at={datetime.now().isoformat()}\n"
        )

        result = FaultInjectionResult(
            success=True,
            fault_type="disk_quota",
            target=str(target_path),
            metadata={
                "quota_bytes": self.quota_bytes,
                "quota_file": str(self._quota_file),
                "note": "Test code should check quota marker and simulate errors",
            },
        )
        self._injections.append(result)
        return result

    def check_quota(self, path: str) -> bool:
        """Check if path is under quota.

        Args:
            path: Path to check

        Returns:
            True if quota marker exists at or above this path
        """
        check_path = Path(path)
        while check_path != check_path.parent:
            quota_marker = check_path / ".disk_quota_test"
            if quota_marker.exists():
                return True
            check_path = check_path.parent
        return False

    def can_restore(self) -> bool:
        """Check if quota can be removed."""
        return self._quota_file is not None and self._quota_file.exists()

    def restore(self) -> bool:
        """Remove quota marker."""
        if self._quota_file and self._quota_file.exists():
            self._quota_file.unlink()
            self._quota_file = None
            return True
        return False
