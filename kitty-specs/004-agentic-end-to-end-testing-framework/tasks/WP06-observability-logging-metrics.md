---
work_package_id: WP06
title: 'Observability: Logging and Metrics Capture'
lane: "doing"
dependencies: []
subtasks:
- T031
- T032
- T033
- T034
- T035
phase: Phase 2 - Fixtures
assignee: ''
agent: "claude-opus"
shell_pid: "66526"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Observability: Logging and Metrics Capture

## Objective

Implement comprehensive observability for test execution: stdout/stderr capture, git state snapshots, WP transition logging with timestamps, container metrics collection, and post-mortem data export. This enables debugging any failure without re-running the test.

## Context

**Depends On**: WP03 (container fixtures), WP05 (workflow fixtures)
**User Stories Addressed**: US6 (Natural Failure Observation)
**Functional Requirements**: FR-027, FR-028, FR-029, FR-030, FR-031

Success Criterion SC-006: "Test logs capture sufficient data to diagnose any failure without re-running the test."

## Subtasks

### T031: Implement stdout/stderr capture to log files

Create `tests/agentic/fixtures/observability.py`:

```python
"""Observability fixtures for logging and metrics capture."""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO, BinaryIO
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

@dataclass
class OutputCapture:
    """Captured output from agent execution."""
    stdout: str = ""
    stderr: str = ""
    combined: str = ""
    exit_code: Optional[int] = None
    duration_seconds: float = 0.0

class AgentOutputLogger:
    """Captures and logs agent stdout/stderr to files."""

    def __init__(self, results_dir: Path, run_id: str):
        self.results_dir = results_dir
        self.run_id = run_id
        self._log_dir = results_dir / run_id
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def create_log_files(
        self,
        agent_id: str,
        step: str
    ) -> tuple[Path, Path, Path]:
        """Create log files for an agent execution step.

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
        step: str
    ):
        """Context manager that captures and logs output.

        Usage:
            with logger.capture_output("claude-code", "implement") as capture:
                # Run agent
                pass
            print(capture.stdout)  # Access captured output
        """
        stdout_path, stderr_path, combined_path = self.create_log_files(
            agent_id, step
        )

        capture = OutputCapture()
        start_time = datetime.utcnow()

        with open(stdout_path, 'w') as stdout_file, \
             open(stderr_path, 'w') as stderr_file, \
             open(combined_path, 'w') as combined_file:

            # Write headers
            header = f"# Agent: {agent_id} | Step: {step} | Started: {start_time.isoformat()}\n\n"
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

                # Write footer
                footer = f"\n# Completed: {datetime.utcnow().isoformat()} | Duration: {capture.duration_seconds:.2f}s | Exit: {capture.exit_code}\n"
                stdout_file.write(footer)
                stderr_file.write(footer)
                combined_file.write(footer)

    def get_log_files(self) -> list[Path]:
        """Return all log files for this run."""
        return list(self._log_dir.glob("*.log"))
```

**Acceptance Criteria**:
- Creates separate stdout/stderr and combined log files
- Timestamps in filenames and headers
- Duration and exit code captured
- Context manager for easy usage
- Log files persist in results directory

### T032: Implement git state capture at workflow points

Add git state capture:

```python
# In observability.py

import subprocess
import json

@dataclass
class GitState:
    """Captured git repository state."""
    branch: str
    commit_hash: str
    commit_message: str
    uncommitted_changes: list[str]
    untracked_files: list[str]
    recent_commits: list[dict]  # Last 5 commits

class GitStateCapture:
    """Captures git repository state at workflow points."""

    def __init__(self, worktree_path: str):
        self.worktree_path = worktree_path

    def capture(self) -> GitState:
        """Capture current git state."""
        return GitState(
            branch=self._get_branch(),
            commit_hash=self._get_commit_hash(),
            commit_message=self._get_commit_message(),
            uncommitted_changes=self._get_uncommitted_changes(),
            untracked_files=self._get_untracked_files(),
            recent_commits=self._get_recent_commits(5)
        )

    def _run_git(self, *args) -> str:
        """Run git command and return output."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.worktree_path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def _get_branch(self) -> str:
        return self._run_git("branch", "--show-current")

    def _get_commit_hash(self) -> str:
        return self._run_git("rev-parse", "HEAD")

    def _get_commit_message(self) -> str:
        return self._run_git("log", "-1", "--format=%s")

    def _get_uncommitted_changes(self) -> list[str]:
        output = self._run_git("diff", "--name-only")
        return output.split('\n') if output else []

    def _get_untracked_files(self) -> list[str]:
        output = self._run_git("ls-files", "--others", "--exclude-standard")
        return output.split('\n') if output else []

    def _get_recent_commits(self, n: int) -> list[dict]:
        output = self._run_git(
            "log", f"-{n}",
            "--format=%H|%s|%ai|%an"
        )
        commits = []
        for line in output.split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                        "author": parts[3]
                    })
        return commits

    def to_dict(self, state: GitState) -> dict:
        """Convert GitState to JSON-serializable dict."""
        return {
            "branch": state.branch,
            "commit_hash": state.commit_hash,
            "commit_message": state.commit_message,
            "uncommitted_changes": state.uncommitted_changes,
            "untracked_files": state.untracked_files,
            "recent_commits": state.recent_commits
        }

    def capture_to_file(self, output_path: Path) -> GitState:
        """Capture state and write to JSON file."""
        state = self.capture()
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(state), f, indent=2)
        return state
```

**Acceptance Criteria**:
- Captures branch, commit hash, message
- Lists uncommitted changes and untracked files
- Includes recent commit history
- Exports to JSON for analysis
- Handles git errors gracefully

### T033: Implement WP status transition logging with timestamps

Add WP transition logging:

```python
# In observability.py

from typing import Callable

@dataclass
class WPTransition:
    """A single WP lane transition."""
    wp_id: str
    from_lane: str
    to_lane: str
    timestamp: datetime
    agent_id: Optional[str] = None
    duration_in_lane_seconds: Optional[float] = None

class WPTransitionLogger:
    """Logs WP status transitions with timestamps."""

    def __init__(self, results_dir: Path, run_id: str):
        self.results_dir = results_dir
        self.run_id = run_id
        self._transitions: list[WPTransition] = []
        self._current_lanes: dict[str, tuple[str, datetime]] = {}  # wp_id -> (lane, entered_at)
        self._log_file = results_dir / run_id / "wp_transitions.jsonl"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def record_transition(
        self,
        wp_id: str,
        from_lane: str,
        to_lane: str,
        agent_id: Optional[str] = None
    ) -> WPTransition:
        """Record a WP lane transition."""
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
            duration_in_lane_seconds=duration
        )

        self._transitions.append(transition)
        self._current_lanes[wp_id] = (to_lane, now)

        # Append to log file (JSONL format)
        with open(self._log_file, 'a') as f:
            f.write(json.dumps({
                "wp_id": transition.wp_id,
                "from_lane": transition.from_lane,
                "to_lane": transition.to_lane,
                "timestamp": transition.timestamp.isoformat() + "Z",
                "agent_id": transition.agent_id,
                "duration_in_lane_seconds": transition.duration_in_lane_seconds
            }) + "\n")

        return transition

    def get_transitions(self, wp_id: Optional[str] = None) -> list[WPTransition]:
        """Get all transitions, optionally filtered by WP ID."""
        if wp_id:
            return [t for t in self._transitions if t.wp_id == wp_id]
        return self._transitions.copy()

    def get_timeline(self) -> list[dict]:
        """Get chronological timeline of all transitions."""
        return sorted(
            [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "wp_id": t.wp_id,
                    "transition": f"{t.from_lane} -> {t.to_lane}",
                    "agent": t.agent_id,
                    "duration": t.duration_in_lane_seconds
                }
                for t in self._transitions
            ],
            key=lambda x: x["timestamp"]
        )
```

**Acceptance Criteria**:
- Records every lane transition with timestamp
- Calculates time spent in each lane
- JSONL log file for streaming writes
- Timeline view for debugging
- Tracks which agent caused transition

### T034: Implement container metrics capture (CPU, mem, net)

Add container metrics:

```python
# In observability.py

import docker
from typing import Iterator

@dataclass
class ContainerMetrics:
    """Snapshot of container resource usage."""
    timestamp: datetime
    cpu_percent: float
    memory_used_mb: int
    memory_percent: float
    memory_limit_mb: int
    network_rx_bytes: int
    network_tx_bytes: int
    disk_read_bytes: int
    disk_write_bytes: int

class ContainerMetricsCollector:
    """Collects metrics from running containers."""

    def __init__(self):
        self._client = docker.from_env()

    def collect(self, container_id: str) -> ContainerMetrics:
        """Collect current metrics from container."""
        container = self._client.containers.get(container_id)
        stats = container.stats(stream=False)

        # Parse CPU stats
        cpu_delta = (
            stats['cpu_stats']['cpu_usage']['total_usage'] -
            stats['precpu_stats']['cpu_usage']['total_usage']
        )
        system_delta = (
            stats['cpu_stats']['system_cpu_usage'] -
            stats['precpu_stats']['system_cpu_usage']
        )
        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * 100.0

        # Parse memory stats
        memory_used = stats['memory_stats'].get('usage', 0)
        memory_limit = stats['memory_stats'].get('limit', 1)
        memory_percent = (memory_used / memory_limit) * 100.0

        # Parse network stats
        networks = stats.get('networks', {})
        rx_bytes = sum(n.get('rx_bytes', 0) for n in networks.values())
        tx_bytes = sum(n.get('tx_bytes', 0) for n in networks.values())

        # Parse disk I/O stats
        io_stats = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', [])
        read_bytes = sum(s.get('value', 0) for s in io_stats if s.get('op') == 'Read')
        write_bytes = sum(s.get('value', 0) for s in io_stats if s.get('op') == 'Write')

        return ContainerMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_used_mb=memory_used // (1024 * 1024),
            memory_percent=memory_percent,
            memory_limit_mb=memory_limit // (1024 * 1024),
            network_rx_bytes=rx_bytes,
            network_tx_bytes=tx_bytes,
            disk_read_bytes=read_bytes,
            disk_write_bytes=write_bytes
        )

    def stream_metrics(
        self,
        container_id: str,
        interval_seconds: float = 1.0
    ) -> Iterator[ContainerMetrics]:
        """Stream metrics at regular intervals."""
        import time
        while True:
            try:
                yield self.collect(container_id)
                time.sleep(interval_seconds)
            except docker.errors.NotFound:
                break  # Container stopped

    def to_dict(self, metrics: ContainerMetrics) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": metrics.timestamp.isoformat() + "Z",
            "cpu_percent": round(metrics.cpu_percent, 2),
            "memory_used_mb": metrics.memory_used_mb,
            "memory_percent": round(metrics.memory_percent, 2),
            "memory_limit_mb": metrics.memory_limit_mb,
            "network_rx_bytes": metrics.network_rx_bytes,
            "network_tx_bytes": metrics.network_tx_bytes,
            "disk_read_bytes": metrics.disk_read_bytes,
            "disk_write_bytes": metrics.disk_write_bytes
        }
```

**Acceptance Criteria**:
- Collects CPU, memory, network, disk metrics
- Uses Docker stats API
- Streaming mode for continuous collection
- JSON export for analysis
- Handles container not found gracefully

### T035: Implement post-mortem data export for failures

Add post-mortem export:

```python
# In observability.py

class PostMortemExporter:
    """Exports comprehensive data for failure analysis."""

    def __init__(
        self,
        results_dir: Path,
        run_id: str,
        output_logger: AgentOutputLogger,
        transition_logger: WPTransitionLogger
    ):
        self.results_dir = results_dir
        self.run_id = run_id
        self.output_logger = output_logger
        self.transition_logger = transition_logger
        self._export_dir = results_dir / run_id / "post_mortem"

    def export(
        self,
        test_run: 'TestRun',
        git_state: Optional[GitState] = None,
        container_metrics: Optional[list[ContainerMetrics]] = None,
        additional_context: Optional[dict] = None
    ) -> Path:
        """Export all data for post-mortem analysis.

        Returns:
            Path to the export directory
        """
        self._export_dir.mkdir(parents=True, exist_ok=True)

        # 1. Export test run summary
        summary_path = self._export_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump({
                "run_id": test_run.run_id,
                "path_id": test_run.path_id,
                "status": test_run.status.value,
                "failure_reason": test_run.failure_reason,
                "started_at": test_run.started_at.isoformat() + "Z",
                "completed_at": test_run.completed_at.isoformat() + "Z" if test_run.completed_at else None,
                "agent_assignments": test_run.agent_assignments,
                "total_observations": len(test_run.observations)
            }, f, indent=2)

        # 2. Export full test run
        run_path = self._export_dir / "test_run.json"
        with open(run_path, 'w') as f:
            json.dump(test_run.to_json(), f, indent=2)

        # 3. Export WP transitions
        transitions_path = self._export_dir / "transitions.json"
        with open(transitions_path, 'w') as f:
            json.dump(self.transition_logger.get_timeline(), f, indent=2)

        # 4. Export git state if provided
        if git_state:
            git_path = self._export_dir / "git_state.json"
            with open(git_path, 'w') as f:
                json.dump(GitStateCapture("").to_dict(git_state), f, indent=2)

        # 5. Export container metrics if provided
        if container_metrics:
            metrics_path = self._export_dir / "container_metrics.json"
            collector = ContainerMetricsCollector()
            with open(metrics_path, 'w') as f:
                json.dump(
                    [collector.to_dict(m) for m in container_metrics],
                    f, indent=2
                )

        # 6. Copy all log files
        logs_dir = self._export_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        for log_file in self.output_logger.get_log_files():
            import shutil
            shutil.copy(log_file, logs_dir / log_file.name)

        # 7. Export additional context
        if additional_context:
            context_path = self._export_dir / "context.json"
            with open(context_path, 'w') as f:
                json.dump(additional_context, f, indent=2)

        # 8. Create index file
        index_path = self._export_dir / "INDEX.md"
        with open(index_path, 'w') as f:
            f.write(f"""# Post-Mortem Export: {test_run.run_id}

**Status**: {test_run.status.value}
**Failure Reason**: {test_run.failure_reason or "N/A"}
**Exported**: {datetime.utcnow().isoformat()}

## Files

- `summary.json` - Quick overview
- `test_run.json` - Full TestRun data
- `transitions.json` - WP lane transitions
- `git_state.json` - Git repository state
- `container_metrics.json` - Resource usage
- `logs/` - Agent stdout/stderr logs
- `context.json` - Additional context

## How to Analyze

1. Start with `summary.json` for the failure reason
2. Check `transitions.json` for workflow progression
3. Review `logs/` for agent output at failure point
4. Compare `git_state.json` for code changes
5. Check `container_metrics.json` for resource issues
""")

        return self._export_dir


@pytest.fixture
def output_logger(tmp_path):
    """Create an output logger for tests."""
    results_dir = tmp_path / "results"
    return AgentOutputLogger(results_dir, "test-run")

@pytest.fixture
def transition_logger(tmp_path):
    """Create a transition logger for tests."""
    results_dir = tmp_path / "results"
    return WPTransitionLogger(results_dir, "test-run")

@pytest.fixture
def git_state_capture(tmp_worktree):
    """Create a git state capture for tests."""
    return GitStateCapture(tmp_worktree)
```

**Acceptance Criteria**:
- Exports complete TestRun to JSON
- Copies all log files
- Exports git state snapshot
- Exports container metrics
- INDEX.md explains how to analyze
- Single export directory per failure

## Technical Notes

- JSONL format for streaming writes (transitions)
- Docker Python SDK for container metrics
- Post-mortem export is triggered automatically on test failure
- All timestamps in ISO 8601 format with Z suffix

## Files to Create/Modify

1. `tests/agentic/fixtures/observability.py` (create)
2. `tests/agentic/fixtures/__init__.py` (update exports)
3. `tests/agentic/conftest.py` (import fixtures)

## Verification

```bash
# Import check
python -c "
from tests.agentic.fixtures.observability import (
    AgentOutputLogger, GitStateCapture, WPTransitionLogger,
    ContainerMetricsCollector, PostMortemExporter
)
"

# Unit tests
pytest tests/agentic/fixtures/test_observability.py -v
```

## Definition of Done

- [ ] AgentOutputLogger captures stdout/stderr
- [ ] GitStateCapture captures repo state
- [ ] WPTransitionLogger with timestamps
- [ ] ContainerMetricsCollector with Docker stats
- [ ] PostMortemExporter creates analysis bundle
- [ ] INDEX.md in export directory
- [ ] All fixtures exposed in conftest.py
- [ ] Unit tests pass

## Activity Log

- 2026-01-19T14:40:37Z – claude-opus – shell_pid=61948 – lane=doing – Started implementation via workflow command
- 2026-01-19T14:44:25Z – claude-opus – shell_pid=61948 – lane=for_review – Ready for review: AgentOutputLogger, GitStateCapture, WPTransitionLogger, ContainerMetricsCollector, PostMortemExporter implemented. All classes export timestamped data in JSON/JSONL format. INDEX.md provides analysis guidance. All fixtures registered in conftest.py.
- 2026-01-19T14:47:36Z – claude-opus – shell_pid=66526 – lane=doing – Started review via workflow command
