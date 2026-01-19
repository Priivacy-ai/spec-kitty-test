"""Observability fixtures for logging and metrics capture in agentic E2E testing.

This module provides comprehensive observability for test execution:
- AgentOutputLogger: Captures stdout/stderr to log files
- GitStateCapture: Captures git repository state at workflow points
- WPTransitionLogger: Logs WP status transitions with timestamps
- ContainerMetricsCollector: Collects container CPU, memory, network metrics
- PostMortemExporter: Exports comprehensive data for failure analysis

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.

Success Criterion SC-006: "Test logs capture sufficient data to diagnose any
failure without re-running the test."
"""

import json
import shutil
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

import pytest

if TYPE_CHECKING:
    from .workflow_fixtures import TestRun
    from ..invoker.invocation_result import InvocationResult


# =============================================================================
# T031: Stdout/Stderr Capture
# =============================================================================


@dataclass
class OutputCapture:
    """Captured output from agent execution.

    Attributes:
        stdout: Captured standard output
        stderr: Captured standard error
        combined: Combined stdout and stderr
        exit_code: Process exit code
        duration_seconds: Execution duration
    """

    stdout: str = ""
    stderr: str = ""
    combined: str = ""
    exit_code: Optional[int] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "combined": self.combined,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
        }


class AgentOutputLogger:
    """Captures and logs agent stdout/stderr to files.

    Creates separate files for stdout, stderr, and combined output
    with timestamps in filenames and headers.

    Attributes:
        results_dir: Directory for results
        run_id: Unique identifier for this run
    """

    def __init__(self, results_dir: Path, run_id: str):
        """Initialize the logger.

        Args:
            results_dir: Base directory for results
            run_id: Unique identifier for this test run
        """
        self.results_dir = Path(results_dir)
        self.run_id = run_id
        self._log_dir = self.results_dir / run_id
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def create_log_files(
        self,
        agent_id: str,
        step: str,
    ) -> tuple[Path, Path, Path]:
        """Create log files for an agent execution step.

        Args:
            agent_id: ID of the agent
            step: Workflow step name

        Returns:
            Tuple of (stdout_path, stderr_path, combined_path)
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = f"{timestamp}_{agent_id}_{step}"

        stdout_path = self._log_dir / f"{prefix}_stdout.log"
        stderr_path = self._log_dir / f"{prefix}_stderr.log"
        combined_path = self._log_dir / f"{prefix}_combined.log"

        return stdout_path, stderr_path, combined_path

    @contextmanager
    def capture_output(
        self,
        agent_id: str,
        step: str,
    ):
        """Context manager that captures and logs output.

        Usage:
            with logger.capture_output("claude-code", "implement") as capture:
                # Run agent
                capture.stdout = "output from agent"
                capture.exit_code = 0
            print(capture.stdout)  # Access captured output

        Args:
            agent_id: ID of the agent
            step: Workflow step name

        Yields:
            OutputCapture instance to populate with captured data
        """
        stdout_path, stderr_path, combined_path = self.create_log_files(
            agent_id, step
        )

        capture = OutputCapture()
        start_time = datetime.utcnow()

        with (
            open(stdout_path, "w") as stdout_file,
            open(stderr_path, "w") as stderr_file,
            open(combined_path, "w") as combined_file,
        ):
            # Write headers
            header = (
                f"# Agent: {agent_id} | Step: {step} | "
                f"Started: {start_time.isoformat()}Z\n\n"
            )
            stdout_file.write(header)
            stderr_file.write(header)
            combined_file.write(header)

            try:
                yield capture
            finally:
                # Calculate duration
                capture.duration_seconds = (
                    datetime.utcnow() - start_time
                ).total_seconds()

                # Write captured content
                if capture.stdout:
                    stdout_file.write(capture.stdout)
                    combined_file.write(f"[STDOUT]\n{capture.stdout}\n")
                if capture.stderr:
                    stderr_file.write(capture.stderr)
                    combined_file.write(f"[STDERR]\n{capture.stderr}\n")

                # Update combined
                capture.combined = ""
                if capture.stdout:
                    capture.combined += f"[STDOUT]\n{capture.stdout}\n"
                if capture.stderr:
                    capture.combined += f"[STDERR]\n{capture.stderr}\n"

                # Write footer
                footer = (
                    f"\n# Completed: {datetime.utcnow().isoformat()}Z | "
                    f"Duration: {capture.duration_seconds:.2f}s | "
                    f"Exit: {capture.exit_code}\n"
                )
                stdout_file.write(footer)
                stderr_file.write(footer)
                combined_file.write(footer)

    def get_log_files(self) -> List[Path]:
        """Return all log files for this run.

        Returns:
            List of paths to log files
        """
        return list(self._log_dir.glob("*.log"))

    def get_log_dir(self) -> Path:
        """Return the log directory path.

        Returns:
            Path to the log directory
        """
        return self._log_dir

    # =========================================================================
    # T025: InvocationResult logging methods
    # =========================================================================

    def log_invocation(
        self,
        result: "InvocationResult",
        step: str = "invocation",
    ) -> Path:
        """Log an InvocationResult to files.

        Creates:
        - {timestamp}_{agent_id}_{step}_stdout.log
        - {timestamp}_{agent_id}_{step}_stderr.log
        - {timestamp}_{agent_id}_{step}_combined.log
        - {timestamp}_{agent_id}_{step}_result.json (metadata)

        Args:
            result: The InvocationResult to log
            step: Workflow step name (e.g., "implement", "review")

        Returns:
            Path to the combined log file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = f"{timestamp}_{result.agent_id}_{step}"

        stdout_path = self._log_dir / f"{prefix}_stdout.log"
        stderr_path = self._log_dir / f"{prefix}_stderr.log"
        combined_path = self._log_dir / f"{prefix}_combined.log"
        result_path = self._log_dir / f"{prefix}_result.json"

        # Write stdout
        with open(stdout_path, "w") as f:
            header = (
                f"# Agent: {result.agent_id} | Step: {step}\n"
                f"# Started: {result.started_at.isoformat()}Z\n"
                f"# Duration: {result.duration_seconds:.2f}s\n"
                f"# Outcome: {result.outcome.value}\n\n"
            )
            f.write(header)
            f.write(result.stdout or "")

        # Write stderr
        with open(stderr_path, "w") as f:
            f.write(result.stderr or "")

        # Write combined
        with open(combined_path, "w") as f:
            f.write("[INVOCATION METADATA]\n")
            f.write(f"Agent: {result.agent_id}\n")
            f.write(f"Step: {step}\n")
            f.write(f"Started: {result.started_at.isoformat()}Z\n")
            f.write(f"Completed: {result.completed_at.isoformat()}Z\n")
            f.write(f"Duration: {result.duration_seconds:.2f}s\n")
            f.write(f"Exit Code: {result.exit_code}\n")
            f.write(f"Outcome: {result.outcome.value}\n")
            if result.error_message:
                f.write(f"Error: {result.error_message}\n")
            f.write("\n[STDOUT]\n")
            f.write(result.stdout or "")
            f.write("\n[STDERR]\n")
            f.write(result.stderr or "")

        # Write JSON metadata
        with open(result_path, "w") as f:
            metadata = {
                "agent_id": result.agent_id,
                "step": step,
                "started_at": result.started_at.isoformat() + "Z",
                "completed_at": result.completed_at.isoformat() + "Z",
                "duration_seconds": result.duration_seconds,
                "exit_code": result.exit_code,
                "outcome": result.outcome.value,
                "timeout_exceeded": result.timeout_exceeded,
                "killed": result.killed,
                "error_message": result.error_message,
                "prompt_hash": result.prompt_hash,
                "worktree_path": result.worktree_path,
                "stdout_bytes": len((result.stdout or "").encode()),
                "stderr_bytes": len((result.stderr or "").encode()),
            }
            json.dump(metadata, f, indent=2)

        return combined_path

    def log_invocations(
        self,
        results: List["InvocationResult"],
        workflow: str = "workflow",
    ) -> List[Path]:
        """Log multiple invocations from a workflow.

        Args:
            results: List of InvocationResult to log
            workflow: Workflow name prefix for step names

        Returns:
            List of paths to combined log files
        """
        paths = []
        for i, result in enumerate(results):
            step = f"{workflow}_{i:02d}"
            path = self.log_invocation(result, step)
            paths.append(path)
        return paths

    def log_invocation_with_git(
        self,
        result: "InvocationResult",
        git_capture: "GitStateCapture",
        step: str = "invocation",
    ) -> tuple[Path, Optional["GitState"], "GitState"]:
        """Log invocation with git state capture.

        Args:
            result: The InvocationResult to log
            git_capture: GitStateCapture initialized with worktree
            step: Workflow step name

        Returns:
            Tuple of (combined_log_path, git_before, git_after)
            git_before is None (would need to be passed in)
        """
        # Capture git state after invocation
        git_after = git_capture.capture()

        # Log the invocation
        log_path = self.log_invocation(result, step)

        # Also save git state
        git_path = self._log_dir / f"{step}_git_state.json"
        git_capture.capture_to_file(git_path)

        return log_path, None, git_after

    @contextmanager
    def capture_with_git_state(
        self,
        worktree_path: str,
        step: str,
    ):
        """Context manager that captures git state before and after.

        Usage:
            with logger.capture_with_git_state(worktree, "implement") as ctx:
                result = invoker.invoke(...)
                ctx.set_result(result)
            # Git states and invocation logged automatically

        Args:
            worktree_path: Path to the git worktree
            step: Workflow step name

        Yields:
            CaptureContext with set_result() method
        """
        git_capture = GitStateCapture(worktree_path)
        before_state = git_capture.capture()

        class CaptureContext:
            def __init__(self):
                self.result: Optional["InvocationResult"] = None
                self.before_state = before_state
                self.after_state: Optional["GitState"] = None

            def set_result(self, r: "InvocationResult"):
                self.result = r

        ctx = CaptureContext()
        try:
            yield ctx
        finally:
            if ctx.result:
                ctx.after_state = git_capture.capture()
                self.log_invocation(ctx.result, step)

                # Log git diff
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                diff_path = self._log_dir / f"{timestamp}_{step}_git_diff.json"
                with open(diff_path, "w") as f:
                    # Get new commits by comparing commit hashes
                    before_hashes = {c["hash"] for c in ctx.before_state.recent_commits}
                    new_commits = [
                        c for c in ctx.after_state.recent_commits
                        if c["hash"] not in before_hashes
                    ]
                    json.dump({
                        "before": ctx.before_state.to_dict(),
                        "after": ctx.after_state.to_dict(),
                        "new_commits": new_commits,
                    }, f, indent=2)


# =============================================================================
# T032: Git State Capture
# =============================================================================


@dataclass
class GitState:
    """Captured git repository state.

    Attributes:
        branch: Current branch name
        commit_hash: Current commit SHA
        commit_message: Current commit message
        uncommitted_changes: List of modified files
        untracked_files: List of untracked files
        recent_commits: List of recent commits (last 5)
    """

    branch: str
    commit_hash: str
    commit_message: str
    uncommitted_changes: List[str]
    untracked_files: List[str]
    recent_commits: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "commit_message": self.commit_message,
            "uncommitted_changes": self.uncommitted_changes,
            "untracked_files": self.untracked_files,
            "recent_commits": self.recent_commits,
        }


class GitStateCapture:
    """Captures git repository state at workflow points.

    Provides methods to capture comprehensive git state including
    branch, commit info, uncommitted changes, and recent history.

    Attributes:
        worktree_path: Path to the git worktree
    """

    def __init__(self, worktree_path: str):
        """Initialize the capture.

        Args:
            worktree_path: Path to the git worktree
        """
        self.worktree_path = worktree_path

    def capture(self) -> GitState:
        """Capture current git state.

        Returns:
            GitState with all repository information
        """
        return GitState(
            branch=self._get_branch(),
            commit_hash=self._get_commit_hash(),
            commit_message=self._get_commit_message(),
            uncommitted_changes=self._get_uncommitted_changes(),
            untracked_files=self._get_untracked_files(),
            recent_commits=self._get_recent_commits(5),
        )

    def _run_git(self, *args: str) -> str:
        """Run git command and return output.

        Args:
            args: Git command arguments

        Returns:
            Command output as string (stripped)
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return ""

    def _get_branch(self) -> str:
        """Get current branch name."""
        return self._run_git("branch", "--show-current") or "HEAD"

    def _get_commit_hash(self) -> str:
        """Get current commit SHA."""
        return self._run_git("rev-parse", "HEAD") or "unknown"

    def _get_commit_message(self) -> str:
        """Get current commit message."""
        return self._run_git("log", "-1", "--format=%s") or ""

    def _get_uncommitted_changes(self) -> List[str]:
        """Get list of uncommitted changes."""
        output = self._run_git("diff", "--name-only")
        if not output:
            return []
        return [f for f in output.split("\n") if f]

    def _get_untracked_files(self) -> List[str]:
        """Get list of untracked files."""
        output = self._run_git("ls-files", "--others", "--exclude-standard")
        if not output:
            return []
        return [f for f in output.split("\n") if f]

    def _get_recent_commits(self, n: int) -> List[Dict[str, str]]:
        """Get list of recent commits.

        Args:
            n: Number of commits to retrieve

        Returns:
            List of commit dicts with hash, message, date, author
        """
        output = self._run_git(
            "log", f"-{n}", "--format=%H|%s|%ai|%an"
        )
        commits = []
        if not output:
            return commits
        for line in output.split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                        "author": parts[3],
                    })
        return commits

    def capture_to_file(self, output_path: Path) -> GitState:
        """Capture state and write to JSON file.

        Args:
            output_path: Path to write JSON file

        Returns:
            The captured GitState
        """
        state = self.capture()
        with open(output_path, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
        return state


# =============================================================================
# T033: WP Transition Logging
# =============================================================================


@dataclass
class WPTransition:
    """A single WP lane transition.

    Attributes:
        wp_id: Work package ID
        from_lane: Source lane
        to_lane: Destination lane
        timestamp: When the transition occurred
        agent_id: Agent that triggered the transition
        duration_in_lane_seconds: Time spent in the source lane
    """

    wp_id: str
    from_lane: str
    to_lane: str
    timestamp: datetime
    agent_id: Optional[str] = None
    duration_in_lane_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "wp_id": self.wp_id,
            "from_lane": self.from_lane,
            "to_lane": self.to_lane,
            "timestamp": self.timestamp.isoformat() + "Z",
            "agent_id": self.agent_id,
            "duration_in_lane_seconds": self.duration_in_lane_seconds,
        }


class WPTransitionLogger:
    """Logs WP status transitions with timestamps.

    Tracks all lane transitions and calculates time spent in each lane.
    Writes to JSONL file for streaming writes.

    Attributes:
        results_dir: Directory for results
        run_id: Unique identifier for this run
    """

    def __init__(self, results_dir: Path, run_id: str):
        """Initialize the logger.

        Args:
            results_dir: Base directory for results
            run_id: Unique identifier for this test run
        """
        self.results_dir = Path(results_dir)
        self.run_id = run_id
        self._transitions: List[WPTransition] = []
        self._current_lanes: Dict[str, tuple[str, datetime]] = {}
        self._log_file = self.results_dir / run_id / "wp_transitions.jsonl"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def record_transition(
        self,
        wp_id: str,
        from_lane: str,
        to_lane: str,
        agent_id: Optional[str] = None,
    ) -> WPTransition:
        """Record a WP lane transition.

        Args:
            wp_id: Work package ID
            from_lane: Source lane
            to_lane: Destination lane
            agent_id: Agent that triggered the transition

        Returns:
            The recorded WPTransition
        """
        now = datetime.utcnow()

        # Calculate duration in previous lane
        duration = None
        if wp_id in self._current_lanes:
            prev_lane, entered_at = self._current_lanes[wp_id]
            if prev_lane == from_lane:
                duration = (now - entered_at).total_seconds()

        transition = WPTransition(
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            timestamp=now,
            agent_id=agent_id,
            duration_in_lane_seconds=duration,
        )

        self._transitions.append(transition)
        self._current_lanes[wp_id] = (to_lane, now)

        # Append to log file (JSONL format)
        with open(self._log_file, "a") as f:
            f.write(json.dumps(transition.to_dict()) + "\n")

        return transition

    def get_transitions(
        self,
        wp_id: Optional[str] = None,
    ) -> List[WPTransition]:
        """Get all transitions, optionally filtered by WP ID.

        Args:
            wp_id: Optional WP ID to filter by

        Returns:
            List of transitions
        """
        if wp_id:
            return [t for t in self._transitions if t.wp_id == wp_id]
        return self._transitions.copy()

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of all transitions.

        Returns:
            List of transition dicts sorted by timestamp
        """
        return sorted(
            [
                {
                    "timestamp": t.timestamp.isoformat() + "Z",
                    "wp_id": t.wp_id,
                    "transition": f"{t.from_lane} -> {t.to_lane}",
                    "agent": t.agent_id,
                    "duration": t.duration_in_lane_seconds,
                }
                for t in self._transitions
            ],
            key=lambda x: x["timestamp"],
        )

    def get_log_file(self) -> Path:
        """Return the path to the JSONL log file.

        Returns:
            Path to the log file
        """
        return self._log_file


# =============================================================================
# T034: Container Metrics Collection
# =============================================================================


@dataclass
class ContainerMetrics:
    """Snapshot of container resource usage.

    Attributes:
        timestamp: When the metrics were collected
        cpu_percent: CPU usage percentage
        memory_used_mb: Memory used in MB
        memory_percent: Memory usage percentage
        memory_limit_mb: Memory limit in MB
        network_rx_bytes: Network bytes received
        network_tx_bytes: Network bytes transmitted
        disk_read_bytes: Disk bytes read
        disk_write_bytes: Disk bytes written
    """

    timestamp: datetime
    cpu_percent: float
    memory_used_mb: int
    memory_percent: float
    memory_limit_mb: int
    network_rx_bytes: int
    network_tx_bytes: int
    disk_read_bytes: int
    disk_write_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_used_mb": self.memory_used_mb,
            "memory_percent": round(self.memory_percent, 2),
            "memory_limit_mb": self.memory_limit_mb,
            "network_rx_bytes": self.network_rx_bytes,
            "network_tx_bytes": self.network_tx_bytes,
            "disk_read_bytes": self.disk_read_bytes,
            "disk_write_bytes": self.disk_write_bytes,
        }


class ContainerMetricsCollector:
    """Collects metrics from running containers.

    Uses Docker stats API to collect resource usage metrics.
    Supports both one-shot collection and streaming.
    """

    def __init__(self):
        """Initialize the collector.

        Note: Docker client is created on first use to avoid
        import errors when Docker is not available.
        """
        self._client = None

    def _get_client(self):
        """Get or create Docker client."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}")
        return self._client

    def collect(self, container_id: str) -> ContainerMetrics:
        """Collect current metrics from container.

        Args:
            container_id: Docker container ID

        Returns:
            ContainerMetrics with current resource usage

        Raises:
            RuntimeError: If Docker is not available
            docker.errors.NotFound: If container not found
        """
        client = self._get_client()
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)

        # Parse CPU stats
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"].get("system_cpu_usage", 0)
            - stats["precpu_stats"].get("system_cpu_usage", 0)
        )
        cpu_percent = 0.0
        if system_delta > 0:
            num_cpus = len(
                stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
            )
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Parse memory stats
        memory_used = stats["memory_stats"].get("usage", 0)
        memory_limit = stats["memory_stats"].get("limit", 1)
        memory_percent = (memory_used / memory_limit) * 100.0 if memory_limit else 0.0

        # Parse network stats
        networks = stats.get("networks", {})
        rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
        tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())

        # Parse disk I/O stats
        io_stats = stats.get("blkio_stats", {}).get(
            "io_service_bytes_recursive", []
        ) or []
        read_bytes = sum(
            s.get("value", 0) for s in io_stats if s.get("op") == "Read"
        )
        write_bytes = sum(
            s.get("value", 0) for s in io_stats if s.get("op") == "Write"
        )

        return ContainerMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_used_mb=memory_used // (1024 * 1024),
            memory_percent=memory_percent,
            memory_limit_mb=memory_limit // (1024 * 1024),
            network_rx_bytes=rx_bytes,
            network_tx_bytes=tx_bytes,
            disk_read_bytes=read_bytes,
            disk_write_bytes=write_bytes,
        )

    def stream_metrics(
        self,
        container_id: str,
        interval_seconds: float = 1.0,
        max_samples: Optional[int] = None,
    ) -> Iterator[ContainerMetrics]:
        """Stream metrics at regular intervals.

        Args:
            container_id: Docker container ID
            interval_seconds: Time between samples
            max_samples: Maximum samples to collect (None for unlimited)

        Yields:
            ContainerMetrics at each interval

        Stops when:
            - Container is not found (stopped)
            - max_samples reached
        """
        samples = 0
        while max_samples is None or samples < max_samples:
            try:
                yield self.collect(container_id)
                samples += 1
                time.sleep(interval_seconds)
            except Exception:
                break  # Container stopped or error


# =============================================================================
# T035: Post-Mortem Export
# =============================================================================


class PostMortemExporter:
    """Exports comprehensive data for failure analysis.

    Creates a complete export bundle with:
    - Test run summary
    - Full test run data
    - WP transitions
    - Git state
    - Container metrics
    - All log files
    - INDEX.md for navigation

    Attributes:
        results_dir: Directory for results
        run_id: Unique identifier for this run
        output_logger: AgentOutputLogger instance
        transition_logger: WPTransitionLogger instance
    """

    def __init__(
        self,
        results_dir: Path,
        run_id: str,
        output_logger: AgentOutputLogger,
        transition_logger: WPTransitionLogger,
    ):
        """Initialize the exporter.

        Args:
            results_dir: Base directory for results
            run_id: Unique identifier for this test run
            output_logger: Logger for agent output
            transition_logger: Logger for WP transitions
        """
        self.results_dir = Path(results_dir)
        self.run_id = run_id
        self.output_logger = output_logger
        self.transition_logger = transition_logger
        self._export_dir = self.results_dir / run_id / "post_mortem"

    def export(
        self,
        test_run: "TestRun",
        git_state: Optional[GitState] = None,
        container_metrics: Optional[List[ContainerMetrics]] = None,
        invocations: Optional[List["InvocationResult"]] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Export all data for post-mortem analysis.

        Args:
            test_run: TestRun instance with execution data
            git_state: Optional git state snapshot
            container_metrics: Optional container metrics history
            invocations: Optional list of InvocationResults from agent calls
            additional_context: Optional additional context dict

        Returns:
            Path to the export directory
        """
        self._export_dir.mkdir(parents=True, exist_ok=True)

        # 1. Export test run summary
        summary_path = self._export_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(
                {
                    "run_id": test_run.run_id,
                    "path_id": test_run.path_id,
                    "status": test_run.status.value,
                    "failure_reason": test_run.failure_reason,
                    "started_at": test_run.started_at.isoformat() + "Z",
                    "completed_at": (
                        test_run.completed_at.isoformat() + "Z"
                        if test_run.completed_at
                        else None
                    ),
                    "agent_assignments": test_run.agent_assignments,
                    "total_observations": len(test_run.observations),
                },
                f,
                indent=2,
            )

        # 2. Export full test run
        run_path = self._export_dir / "test_run.json"
        with open(run_path, "w") as f:
            json.dump(test_run.to_json(), f, indent=2)

        # 3. Export WP transitions
        transitions_path = self._export_dir / "transitions.json"
        with open(transitions_path, "w") as f:
            json.dump(self.transition_logger.get_timeline(), f, indent=2)

        # 4. Export git state if provided
        if git_state:
            git_path = self._export_dir / "git_state.json"
            with open(git_path, "w") as f:
                json.dump(git_state.to_dict(), f, indent=2)

        # 5. Export container metrics if provided
        if container_metrics:
            metrics_path = self._export_dir / "container_metrics.json"
            with open(metrics_path, "w") as f:
                json.dump(
                    [m.to_dict() for m in container_metrics],
                    f,
                    indent=2,
                )

        # 6. Copy all log files
        logs_dir = self._export_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        for log_file in self.output_logger.get_log_files():
            shutil.copy(log_file, logs_dir / log_file.name)

        # 7. Export invocations if provided
        if invocations:
            invocations_path = self._export_dir / "invocations.json"
            with open(invocations_path, "w") as f:
                json.dump(
                    [self._invocation_to_dict(inv) for inv in invocations],
                    f,
                    indent=2,
                )

            # Also export individual invocation logs
            invocations_dir = self._export_dir / "invocation_logs"
            invocations_dir.mkdir(exist_ok=True)
            for i, inv in enumerate(invocations):
                inv_path = invocations_dir / f"invocation_{i:02d}_{inv.agent_id}.json"
                with open(inv_path, "w") as f:
                    json.dump(self._invocation_to_dict(inv), f, indent=2)

        # 8. Export additional context
        if additional_context:
            context_path = self._export_dir / "context.json"
            with open(context_path, "w") as f:
                json.dump(additional_context, f, indent=2)

        # 9. Create index file
        self._write_index(test_run, has_invocations=bool(invocations))

        return self._export_dir

    def _invocation_to_dict(self, inv: "InvocationResult") -> Dict[str, Any]:
        """Convert InvocationResult to JSON-serializable dict.

        Args:
            inv: InvocationResult to convert

        Returns:
            JSON-serializable dictionary
        """
        return {
            "agent_id": inv.agent_id,
            "started_at": inv.started_at.isoformat() + "Z",
            "completed_at": inv.completed_at.isoformat() + "Z",
            "duration_seconds": inv.duration_seconds,
            "exit_code": inv.exit_code,
            "outcome": inv.outcome.value,
            "timeout_exceeded": inv.timeout_exceeded,
            "killed": inv.killed,
            "error_message": inv.error_message,
            "prompt_hash": inv.prompt_hash,
            "worktree_path": inv.worktree_path,
            "stdout_preview": (inv.stdout or "")[:1000],
            "stderr_preview": (inv.stderr or "")[:1000],
            "stdout_bytes": len((inv.stdout or "").encode()),
            "stderr_bytes": len((inv.stderr or "").encode()),
            "parsed_response": (
                inv.parsed_response.to_dict()
                if inv.parsed_response else None
            ),
        }

    def _write_index(self, test_run: "TestRun", has_invocations: bool = False):
        """Write INDEX.md file for navigation.

        Args:
            test_run: TestRun instance for status info
            has_invocations: Whether invocations were exported
        """
        index_path = self._export_dir / "INDEX.md"

        # Build dynamic sections based on what was exported
        invocation_files = ""
        invocation_step = ""
        if has_invocations:
            invocation_files = """- `invocations.json` - All agent invocations
- `invocation_logs/` - Individual invocation details
"""
            invocation_step = "2. Check `invocations.json` for agent outputs at each step\n"

        with open(index_path, "w") as f:
            f.write(f"""# Post-Mortem Export: {test_run.run_id}

**Status**: {test_run.status.value}
**Failure Reason**: {test_run.failure_reason or "N/A"}
**Exported**: {datetime.utcnow().isoformat()}Z

## Files

- `summary.json` - Quick overview
- `test_run.json` - Full TestRun data
- `transitions.json` - WP lane transitions
- `git_state.json` - Git repository state
- `container_metrics.json` - Resource usage
- `logs/` - Agent stdout/stderr logs
{invocation_files}- `context.json` - Additional context

## How to Analyze

1. Start with `summary.json` for the failure reason
{invocation_step}3. Check `transitions.json` for workflow progression
4. Review `logs/` for agent output at failure point
5. Compare `git_state.json` for code changes
6. Check `container_metrics.json` for resource issues
""")

    def get_export_dir(self) -> Path:
        """Return the export directory path.

        Returns:
            Path to the export directory
        """
        return self._export_dir


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def output_logger(tmp_path) -> AgentOutputLogger:
    """Create an output logger for tests.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        AgentOutputLogger instance
    """
    results_dir = tmp_path / "results"
    return AgentOutputLogger(results_dir, "test-run")


@pytest.fixture
def transition_logger(tmp_path) -> WPTransitionLogger:
    """Create a transition logger for tests.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        WPTransitionLogger instance
    """
    results_dir = tmp_path / "results"
    return WPTransitionLogger(results_dir, "test-run")


@pytest.fixture
def git_state_capture(tmp_worktree) -> GitStateCapture:
    """Create a git state capture for tests.

    Args:
        tmp_worktree: Temporary git worktree fixture

    Returns:
        GitStateCapture instance
    """
    return GitStateCapture(tmp_worktree)


@pytest.fixture
def container_metrics_collector() -> ContainerMetricsCollector:
    """Create a container metrics collector for tests.

    Returns:
        ContainerMetricsCollector instance
    """
    return ContainerMetricsCollector()


@pytest.fixture
def post_mortem_exporter(
    tmp_path,
    output_logger: AgentOutputLogger,
    transition_logger: WPTransitionLogger,
) -> PostMortemExporter:
    """Create a post-mortem exporter for tests.

    Args:
        tmp_path: pytest's tmp_path fixture
        output_logger: Output logger fixture
        transition_logger: Transition logger fixture

    Returns:
        PostMortemExporter instance
    """
    results_dir = tmp_path / "results"
    return PostMortemExporter(
        results_dir,
        "test-run",
        output_logger,
        transition_logger,
    )
