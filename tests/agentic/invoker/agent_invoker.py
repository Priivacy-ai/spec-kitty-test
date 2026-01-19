"""
AgentInvoker: Main controller for invoking AI coding agents via subprocess.

Provides methods for synchronous and asynchronous invocation, constraint-based
agent selection, and comprehensive process lifecycle management.
"""

import atexit
import hashlib
import os
import signal
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from .agent_process import AgentProcess
from .invocation_result import InvocationOutcome, InvocationResult, ParsedAgentResponse
from .worktree_manager import WorktreeManager
from ..agents.base import AgentConstraint, BaseAgentConfig, PromptMethod


class AgentInvoker:
    """
    Controller for invoking AI coding agents as subprocesses.

    Handles:
    - Synchronous and asynchronous invocation
    - Prompt delivery via stdin, file, or argument
    - Constraint-based agent selection for cross-review workflows
    - Process lifecycle management and cleanup
    """

    # Threshold for writing prompt to file instead of passing directly
    LARGE_PROMPT_THRESHOLD = 100 * 1024  # 100KB

    def __init__(
        self,
        worktree_manager: WorktreeManager,
        default_timeout: float = 1800.0,  # 30 minutes
        cleanup_on_exit: bool = True,
    ):
        """
        Initialize the AgentInvoker.

        Args:
            worktree_manager: WorktreeManager for creating isolated worktrees
            default_timeout: Default timeout in seconds (30 min default)
            cleanup_on_exit: Whether to cleanup processes on exit
        """
        self._worktree_manager = worktree_manager
        self._default_timeout = default_timeout
        self._cleanup_on_exit = cleanup_on_exit
        self._active_processes: Dict[str, AgentProcess] = {}
        self._lock = threading.Lock()

        if cleanup_on_exit:
            atexit.register(self._cleanup_all)
            self._setup_signal_handlers()

    def invoke(
        self,
        agent_config: BaseAgentConfig,
        prompt: str,
        worktree: Optional[str] = None,
        timeout: Optional[float] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> InvocationResult:
        """
        Invoke an agent synchronously and return the result.

        Args:
            agent_config: Configuration for the agent to invoke
            prompt: The prompt text to send to the agent
            worktree: Optional worktree path (created if not provided)
            timeout: Optional timeout override
            env_overrides: Optional environment variable overrides

        Returns:
            InvocationResult with complete execution data
        """
        agent_process = self.invoke_async(
            agent_config=agent_config,
            prompt=prompt,
            worktree=worktree,
            timeout=timeout,
            env_overrides=env_overrides,
        )

        try:
            result = agent_process.wait()
        finally:
            # Untrack the process when done
            self._untrack_process(agent_process)

        return result

    def invoke_async(
        self,
        agent_config: BaseAgentConfig,
        prompt: str,
        worktree: Optional[str] = None,
        timeout: Optional[float] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> AgentProcess:
        """
        Start an agent process and return immediately.

        The returned AgentProcess can be:
        - wait()'ed on to get the result
        - kill()'ed if needed
        - checked via is_running property

        Args:
            agent_config: Configuration for the agent to invoke
            prompt: The prompt text to send to the agent
            worktree: Optional worktree path (created if not provided)
            timeout: Optional timeout override
            env_overrides: Optional environment variable overrides

        Returns:
            AgentProcess wrapper for the running subprocess
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout

        # Create worktree if not provided
        if worktree is None:
            worktree_info = self._worktree_manager.create()
            worktree_path = worktree_info.path
        else:
            worktree_path = worktree

        # Compute prompt hash for deduplication
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        # Handle prompt file for large prompts or FILE method
        prompt_file: Optional[str] = None
        if (
            agent_config.prompt_method == PromptMethod.FILE
            or len(prompt.encode("utf-8")) > self.LARGE_PROMPT_THRESHOLD
        ):
            prompt_file = self._write_prompt_file(prompt, worktree_path)

        # Build command
        command = agent_config.build_command(
            prompt=prompt,
            worktree_path=worktree_path,
            prompt_file=prompt_file,
        )

        # Prepare environment
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        # Determine stdin input
        stdin_input: Optional[bytes] = None
        if agent_config.prompt_method == PromptMethod.STDIN:
            stdin_input = prompt.encode("utf-8")

        # Start subprocess
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin_input else None,
            cwd=worktree_path,
            env=env,
        )

        # Create AgentProcess wrapper - stdin_input is passed here and
        # handled by communicate() in AgentProcess.wait()
        agent_process = AgentProcess(
            agent_id=agent_config.agent_id,
            process=process,
            timeout_seconds=effective_timeout,
            worktree_path=worktree_path,
            prompt_hash=prompt_hash,
            stdin_input=stdin_input,
        )

        # Track the process
        self._track_process(agent_process)

        return agent_process

    def invoke_with_constraint(
        self,
        constraint: AgentConstraint,
        available_agents: List[BaseAgentConfig],
        previous_agent: Optional[BaseAgentConfig] = None,
        prompt: str = "",
        worktree: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[BaseAgentConfig, InvocationResult]:
        """
        Select an agent based on constraint and invoke it.

        Args:
            constraint: SAME_AS, DIFFERENT_FROM, or ANY
            available_agents: List of available agent configs
            previous_agent: The agent used previously (required for SAME_AS/DIFFERENT_FROM)
            prompt: The prompt to send
            worktree: Optional worktree path
            timeout: Optional timeout

        Returns:
            Tuple of (selected_agent_config, invocation_result)

        Raises:
            ValueError: If constraint cannot be satisfied
        """
        selected = self._select_agent(constraint, available_agents, previous_agent)
        result = self.invoke(selected, prompt, worktree, timeout)
        return (selected, result)

    def _select_agent(
        self,
        constraint: AgentConstraint,
        available_agents: List[BaseAgentConfig],
        previous_agent: Optional[BaseAgentConfig],
    ) -> BaseAgentConfig:
        """Select an agent based on constraint."""
        if constraint == AgentConstraint.SAME_AS:
            if previous_agent is None:
                raise ValueError("SAME_AS constraint requires previous_agent")
            return previous_agent

        elif constraint == AgentConstraint.DIFFERENT_FROM:
            if previous_agent is None:
                raise ValueError("DIFFERENT_FROM constraint requires previous_agent")
            candidates = [
                a for a in available_agents if a.agent_id != previous_agent.agent_id
            ]
            if not candidates:
                raise ValueError(
                    f"No agent different from {previous_agent.agent_id} available"
                )
            return candidates[0]

        elif constraint == AgentConstraint.ANY:
            if not available_agents:
                raise ValueError("No available agents")
            return available_agents[0]

        else:
            raise ValueError(f"Unknown constraint: {constraint}")

    def kill_all(self) -> int:
        """
        Kill all active processes and return count killed.

        Use this for explicit cleanup in tests.

        Returns:
            Number of processes killed
        """
        count = 0
        with self._lock:
            for process in list(self._active_processes.values()):
                if process.is_running:
                    process.kill()
                    count += 1
            self._active_processes.clear()
        return count

    def get_active_processes(self) -> List[AgentProcess]:
        """
        Return list of currently active processes.

        Returns:
            List of AgentProcess instances that are still running
        """
        with self._lock:
            return [p for p in self._active_processes.values() if p.is_running]

    def _track_process(self, process: AgentProcess) -> None:
        """Add a process to active tracking."""
        process_id = f"{process.agent_id}-{uuid4().hex[:8]}"
        with self._lock:
            self._active_processes[process_id] = process

    def _untrack_process(self, process: AgentProcess) -> None:
        """Remove a process from active tracking."""
        with self._lock:
            # Find and remove by matching the process object
            for pid, tracked in list(self._active_processes.items()):
                if tracked is process:
                    del self._active_processes[pid]
                    break

    def _cleanup_all(self) -> None:
        """Kill all active processes. Called by atexit."""
        with self._lock:
            for process in list(self._active_processes.values()):
                try:
                    if process.is_running:
                        process.kill()
                except Exception:
                    pass  # Best effort cleanup
            self._active_processes.clear()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers to cleanup on termination."""
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        def sigterm_handler(signum, frame):
            self._cleanup_all()
            # Call original handler or default behavior
            if callable(original_sigterm):
                original_sigterm(signum, frame)
            else:
                raise SystemExit(128 + signum)

        def sigint_handler(signum, frame):
            self._cleanup_all()
            # Call original handler or raise KeyboardInterrupt
            if callable(original_sigint):
                original_sigint(signum, frame)
            else:
                raise KeyboardInterrupt()

        signal.signal(signal.SIGTERM, sigterm_handler)
        signal.signal(signal.SIGINT, sigint_handler)

    def _write_prompt_file(self, prompt: str, worktree_path: str) -> str:
        """Write prompt to a temporary file and return the path."""
        prompt_dir = Path(worktree_path) / ".spec-kitty-prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        prompt_file = prompt_dir / f"prompt_{timestamp}_{prompt_hash}.md"

        prompt_file.write_text(prompt, encoding="utf-8")
        return str(prompt_file)

    @property
    def worktree_manager(self) -> WorktreeManager:
        """Access to the worktree manager."""
        return self._worktree_manager
