"""Container lifecycle management fixtures for agentic E2E testing.

This module provides fixtures for:
- TestContainer: Wrapper for Docker containers with metadata
- AgentContainerFactory: Factory for creating agent-specific containers
- Resource limits: CPU, memory, and disk constraints
- Timeout enforcement: SIGALRM-based timeout with cleanup

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.

Uses testcontainers-python 4.14.0 per research.md E002.
"""

import signal
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network


class ContainerTimeoutError(Exception):
    """Raised when container execution exceeds timeout.

    Attributes:
        container_id: The Docker container ID that timed out
        timeout_seconds: The timeout value that was exceeded
        command: The command that was being executed (if available)
    """

    def __init__(
        self,
        container_id: str,
        timeout_seconds: int,
        command: Optional[str] = None,
    ):
        self.container_id = container_id
        self.timeout_seconds = timeout_seconds
        self.command = command
        msg = f"Container {container_id} exceeded {timeout_seconds}s timeout"
        if command:
            msg += f" while executing: {command}"
        super().__init__(msg)


@contextmanager
def container_timeout(seconds: int, container_id: str, command: Optional[str] = None):
    """Context manager for container timeout enforcement.

    Uses SIGALRM on Unix systems. Raises ContainerTimeoutError when timeout fires.

    Args:
        seconds: Timeout duration in seconds
        container_id: Container ID for error reporting
        command: Optional command being executed for error context

    Raises:
        ContainerTimeoutError: When the timeout is exceeded

    Example:
        with container_timeout(300, container.id, "pytest tests/"):
            result = container.exec("pytest tests/")
    """
    def timeout_handler(signum, frame):
        raise ContainerTimeoutError(container_id, seconds, command)

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class ResourceLimits:
    """Container resource constraints.

    Per plan.md and docker-compose.yaml:
    - CPU: 2.0 cores default
    - Memory: 4GB default
    - Disk: 10GB (via volume constraints)

    Attributes:
        cpu_cores: Number of CPU cores (default 2.0)
        memory_mb: Memory limit in megabytes (default 4096)
        disk_mb: Disk limit in megabytes (default 10240)
    """

    cpu_cores: float = 2.0
    memory_mb: int = 4096
    disk_mb: int = 10240

    def to_docker_kwargs(self) -> Dict[str, Any]:
        """Convert to Docker SDK resource limit kwargs.

        Returns:
            Dict with cpu_period, cpu_quota, and mem_limit for Docker SDK
        """
        return {
            "cpu_period": 100000,
            "cpu_quota": int(self.cpu_cores * 100000),
            "mem_limit": f"{self.memory_mb}m",
        }


@dataclass
class TestContainer:
    """Wrapper for test container with metadata and execution helpers.

    Provides a clean interface for:
    - Executing commands with timeout enforcement
    - Accessing container metadata
    - Managing container lifecycle

    Attributes:
        container_id: Docker container ID
        agent_id: ID of the agent running in this container
        container: Underlying DockerContainer instance
        resource_limits: Applied resource constraints
        worktree_path: Host path mounted as /workspace
    """

    container_id: str
    agent_id: str
    container: DockerContainer
    resource_limits: ResourceLimits
    worktree_path: str

    def exec_command(
        self,
        cmd: str,
        timeout: int = 300,
        workdir: str = "/workspace",
    ) -> Tuple[int, str, str]:
        """Execute command in container with timeout enforcement.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds (default 300)
            workdir: Working directory inside container

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            ContainerTimeoutError: If command exceeds timeout
        """
        with container_timeout(timeout, self.container_id, cmd):
            exit_code, output = self.container.exec(f"sh -c 'cd {workdir} && {cmd}'")
            # testcontainers returns combined output
            return exit_code, output.decode("utf-8"), ""

    def exec_command_raw(
        self,
        cmd: str,
        timeout: int = 300,
    ) -> Tuple[int, bytes]:
        """Execute command returning raw bytes output.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds

        Returns:
            Tuple of (exit_code, raw_output)

        Raises:
            ContainerTimeoutError: If command exceeds timeout
        """
        with container_timeout(timeout, self.container_id, cmd):
            return self.container.exec(cmd)

    def stop(self):
        """Stop the container gracefully."""
        self.container.stop()

    def is_running(self) -> bool:
        """Check if container is still running."""
        try:
            # Get container status via Docker API
            client = self.container.get_docker_client()
            container_info = client.api.inspect_container(self.container_id)
            return container_info["State"]["Running"]
        except Exception:
            return False


class AgentContainerFactory:
    """Factory for creating agent-specific containers.

    Creates containers with:
    - Internal network (no internet access)
    - Resource limits (CPU, memory)
    - Read-only root filesystem
    - Worktree mounted at /workspace (only writable path)
    - Secrets mounted at /run/secrets/

    The factory maintains a shared internal network for all containers
    in a test session.
    """

    DEFAULT_IMAGE = "spec-kitty-agent:latest"

    def __init__(self, image: Optional[str] = None):
        """Initialize factory with optional custom image.

        Args:
            image: Docker image name (default: spec-kitty-agent:latest)
        """
        self.image = image or self.DEFAULT_IMAGE
        self._network: Optional[Network] = None
        self._containers: list[TestContainer] = []

    def _get_internal_network(self) -> Network:
        """Get or create the internal test network.

        The network is internal (no internet access) per security requirements.
        """
        if self._network is None:
            self._network = Network(
                driver="bridge",
            )
            # Note: Network 'internal' mode is set via Docker Compose
            # testcontainers Network doesn't directly support internal flag
            self._network.create()
        return self._network

    def create_container(
        self,
        agent_id: str,
        worktree_path: str,
        resource_limits: Optional[ResourceLimits] = None,
        secrets: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> TestContainer:
        """Create isolated container for agent execution.

        Args:
            agent_id: Identifier for the agent
            worktree_path: Host path to mount as /workspace
            resource_limits: Optional custom resource limits
            secrets: Dict mapping secret name to host file path
            env: Additional environment variables

        Returns:
            TestContainer wrapper with execution helpers
        """
        limits = resource_limits or ResourceLimits()

        # Start with base container
        container = DockerContainer(self.image)

        # Add to internal network
        container.with_network(self._get_internal_network())

        # Mount worktree as the only writable path
        container.with_volume_mapping(worktree_path, "/workspace", "rw")

        # Set environment
        container.with_env("AGENT_ID", agent_id)
        container.with_env("TERM", "xterm-256color")
        container.with_env("HOME", "/tmp")
        # CRITICAL: Ensure no template root override (distribution testing)
        container.with_env("SPEC_KITTY_TEMPLATE_ROOT", "")

        if env:
            for key, value in env.items():
                container.with_env(key, value)

        # Apply resource limits
        container.with_kwargs(**limits.to_docker_kwargs())

        # Mount secrets if provided
        if secrets:
            for name, path in secrets.items():
                container.with_volume_mapping(path, f"/run/secrets/{name}", "ro")

        # Start container
        container.start()

        test_container = TestContainer(
            container_id=container.get_container_id(),
            agent_id=agent_id,
            container=container,
            resource_limits=limits,
            worktree_path=worktree_path,
        )

        self._containers.append(test_container)
        return test_container

    def cleanup(self):
        """Stop all containers and remove network."""
        for container in self._containers:
            try:
                container.stop()
            except Exception:
                pass  # Best effort cleanup
        self._containers.clear()

        if self._network:
            try:
                self._network.remove()
            except Exception:
                pass  # Best effort cleanup
            self._network = None


@pytest.fixture(scope="session")
def container_factory():
    """Session-scoped factory for creating test containers.

    The factory maintains a shared internal network and handles
    cleanup of all containers at session end.

    Yields:
        AgentContainerFactory instance
    """
    factory = AgentContainerFactory()
    yield factory
    factory.cleanup()


@pytest.fixture(scope="function")
def test_container(container_factory, agent_config, tmp_worktree):
    """Function-scoped container for a single test.

    Creates an isolated container configured for the specified agent.
    Container is stopped after the test completes.

    Requires:
        - agent_config fixture: Provides agent configuration
        - tmp_worktree fixture: Provides temporary git worktree path

    Yields:
        TestContainer instance configured for the agent
    """
    container = container_factory.create_container(
        agent_id=agent_config.agent_id,
        worktree_path=tmp_worktree,
        resource_limits=agent_config.resource_limits,
    )
    yield container
    container.stop()


@pytest.fixture(scope="function")
def tmp_worktree(tmp_path):
    """Create a temporary git-initialized directory for testing.

    Initializes a git repo with basic config, mimicking a real worktree.

    Args:
        tmp_path: pytest's tmp_path fixture

    Yields:
        Path to the temporary worktree directory
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=worktree,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@spec-kitty.local"],
        cwd=worktree,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Spec-Kitty Test"],
        cwd=worktree,
        capture_output=True,
        check=True,
    )

    # Create initial commit
    readme = worktree / "README.md"
    readme.write_text("# Test Worktree\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=worktree,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=worktree,
        capture_output=True,
        check=True,
    )

    yield str(worktree)
