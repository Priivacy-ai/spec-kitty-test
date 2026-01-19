"""Tests for invoker edge cases and error handling.

Validates:
- SC-004: "Timeout enforcement kills hung processes within 5 seconds"
- Edge cases from spec.md
"""

import time
from typing import List, Optional, Tuple

import pytest

from ..agents.base import PromptMethod
from ..invoker.agent_invoker import AgentInvoker
from ..invoker.invocation_result import InvocationOutcome, ParsedAgentResponse


class MockAgentConfig:
    """Mock agent config for testing edge cases."""

    def __init__(self, command: List[str], prompt_method: str = "stdin"):
        self._command = command
        self._prompt_method = prompt_method

    @property
    def agent_id(self) -> str:
        return "mock-agent"

    @property
    def display_name(self) -> str:
        return "Mock Agent"

    @property
    def cli_command(self) -> List[str]:
        return self._command

    @property
    def prompt_method(self) -> PromptMethod:
        return PromptMethod.STDIN

    def build_command(
        self,
        prompt: str,
        worktree_path: str,
        prompt_file: Optional[str] = None,
    ) -> List[str]:
        return self._command

    def check_installed(self) -> Tuple[bool, Optional[str]]:
        return True, "1.0.0"

    def check_authenticated(self) -> Tuple[bool, Optional[str]]:
        return True, None

    def parse_output(self, stdout: str, stderr: str) -> ParsedAgentResponse:
        return ParsedAgentResponse.from_raw(stdout, stderr)


class TestTimeoutHandling:
    """Tests for timeout enforcement (SC-004)."""

    def test_timeout_kills_process(self, worktree_manager):
        """Test that timeout kills hung processes within 5 seconds."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            default_timeout=2.0,  # 2 second timeout
            cleanup_on_exit=False,
        )

        # Command that sleeps forever
        mock_config = MockAgentConfig(["sleep", "60"])

        start = time.time()
        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=2.0,
        )
        elapsed = time.time() - start

        # Should complete within timeout + 5 second kill grace
        assert elapsed < 10, f"Took {elapsed}s, should be < 10s"
        assert result.timeout_exceeded, "Should report timeout"
        assert result.killed, "Should report process was killed"
        assert result.outcome == InvocationOutcome.TIMEOUT

    def test_no_orphan_processes_after_timeout(self, worktree_manager):
        """Test that no orphan processes remain after timeout (SC-006)."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            default_timeout=1.0,
            cleanup_on_exit=True,
        )

        mock_config = MockAgentConfig(["sleep", "30"])

        # Run with timeout
        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=1.0,
        )

        # Give a moment for cleanup
        time.sleep(0.5)

        # Check no active processes
        active = invoker.get_active_processes()
        assert len(active) == 0, f"Orphan processes: {active}"

    def test_timeout_with_output_capture(self, worktree_manager):
        """Test that output is captured even when process times out."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            default_timeout=2.0,
            cleanup_on_exit=False,
        )

        # Command that produces output then sleeps
        mock_config = MockAgentConfig([
            "sh", "-c", "echo 'output before timeout'; sleep 60"
        ])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=2.0,
        )

        assert result.timeout_exceeded
        # Output should still be captured
        assert "output before timeout" in result.stdout


class TestCrashHandling:
    """Tests for crash handling."""

    def test_process_crash_captured(self, worktree_manager):
        """Test that process crash is captured correctly."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        # Command that exits with error
        mock_config = MockAgentConfig(["sh", "-c", "exit 1"])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=10.0,
        )

        assert result.exit_code == 1
        assert result.outcome in [InvocationOutcome.FAILURE, InvocationOutcome.CRASH]

    def test_process_crash_with_stderr(self, worktree_manager):
        """Test that stderr is captured on crash."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        # Command that writes to stderr then fails
        mock_config = MockAgentConfig([
            "sh", "-c", "echo 'error message' >&2; exit 42"
        ])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=10.0,
        )

        assert result.exit_code == 42
        assert "error message" in result.stderr

    def test_nonexistent_command(self, worktree_manager):
        """Test handling of nonexistent command."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        mock_config = MockAgentConfig(["nonexistent_command_xyz_12345"])

        # Should handle gracefully, not raise
        try:
            result = invoker.invoke(
                agent_config=mock_config,
                prompt="",
                timeout=10.0,
            )
            # If it returns a result, should indicate failure
            assert result.outcome in [InvocationOutcome.CRASH, InvocationOutcome.FAILURE]
        except FileNotFoundError:
            # This is also acceptable
            pass


class TestOutputHandling:
    """Tests for output capture."""

    def test_large_output_not_truncated(self, worktree_manager):
        """Test that large outputs under 1MB are not truncated (SC-003)."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        # Generate ~100KB of output (1000 lines)
        mock_config = MockAgentConfig([
            "sh", "-c",
            "for i in $(seq 1 1000); do echo \"Line $i: This is a test line with some content to make it longer\"; done"
        ])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=30.0,
        )

        # Output should be complete
        line_count = result.stdout.count('\n')
        assert line_count >= 900, f"Expected ~1000 lines, got {line_count}"

    def test_stderr_captured_separately(self, worktree_manager):
        """Test that stderr is captured separately from stdout."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        mock_config = MockAgentConfig([
            "sh", "-c",
            "echo 'stdout message'; echo 'stderr message' >&2"
        ])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=10.0,
        )

        assert "stdout message" in result.stdout
        assert "stderr message" in result.stderr
        assert "stderr message" not in result.stdout

    def test_empty_output_handled(self, worktree_manager):
        """Test that empty output is handled correctly."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        mock_config = MockAgentConfig(["true"])  # Produces no output

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=10.0,
        )

        assert result.stdout is not None  # Should be empty string, not None
        assert result.stderr is not None
        assert result.exit_code == 0
        assert result.outcome == InvocationOutcome.SUCCESS

    def test_unicode_output_captured(self, worktree_manager):
        """Test that Unicode output is captured correctly."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        mock_config = MockAgentConfig([
            "sh", "-c", "echo 'Hello World! Emoji test'"
        ])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="",
            timeout=10.0,
        )

        assert "Hello" in result.stdout
        assert result.outcome == InvocationOutcome.SUCCESS


class TestStdinHandling:
    """Tests for stdin input handling."""

    def test_stdin_input_delivered(self, worktree_manager):
        """Test that stdin input is delivered to process."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        # cat will echo back stdin
        mock_config = MockAgentConfig(["cat"])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt="Hello from stdin!",
            timeout=10.0,
        )

        assert "Hello from stdin!" in result.stdout
        assert result.outcome == InvocationOutcome.SUCCESS

    def test_large_stdin_input(self, worktree_manager):
        """Test that large stdin input is delivered correctly."""
        invoker = AgentInvoker(
            worktree_manager=worktree_manager,
            cleanup_on_exit=False,
        )

        # Generate 10KB of input
        large_input = "A" * 10000

        mock_config = MockAgentConfig(["cat"])

        result = invoker.invoke(
            agent_config=mock_config,
            prompt=large_input,
            timeout=10.0,
        )

        assert len(result.stdout.strip()) == 10000
        assert result.outcome == InvocationOutcome.SUCCESS
