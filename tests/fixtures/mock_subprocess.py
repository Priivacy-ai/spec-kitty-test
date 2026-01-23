"""Mock subprocess runner for VCS command testing.

This module provides MockSubprocessRunner, a utility class for capturing
and verifying subprocess commands during tests. Used primarily for VCS
abstraction tests to ensure jj commands are never invoked.
"""

from typing import List, Tuple, Optional, Union
import subprocess


class MockSubprocessRunner:
    """Mocks subprocess.run to capture and log all executed commands.

    This class is useful for testing VCS abstraction logic to verify that
    when git is the active VCS, no jj commands are executed.

    Usage:
        mock_runner = MockSubprocessRunner()
        mock_runner.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="success", stderr=""
        )

        # Patch subprocess.run
        with patch('subprocess.run', mock_runner.run):
            # Run code that should only use git
            result = subprocess.run(['git', 'status'])

        # Verify no jj commands
        mock_runner.assert_no_jj_commands()
    """

    def __init__(self):
        """Initialize with empty command log."""
        self.commands: List[Tuple[str, List[str]]] = []
        self.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

    def run(self, cmd: Union[List[str], str], *args, **kwargs) -> subprocess.CompletedProcess:
        """Mock subprocess.run that logs commands.

        Args:
            cmd: Command to execute (list or string)
            *args: Additional positional arguments (ignored)
            **kwargs: Keyword arguments (ignored)

        Returns:
            The configured return_value
        """
        # Extract binary and args
        if isinstance(cmd, list):
            binary = cmd[0] if cmd else ""
            cmd_args = cmd[1:] if len(cmd) > 1 else []
        else:
            parts = cmd.split()
            binary = parts[0] if parts else ""
            cmd_args = parts[1:] if len(parts) > 1 else []

        self.commands.append((binary, cmd_args))
        return self.return_value

    def assert_no_jj_commands(self):
        """Assert no jj commands were executed.

        Raises:
            AssertionError: If any jj commands were logged
        """
        jj_commands = [cmd for cmd in self.commands if cmd[0] == "jj"]
        assert not jj_commands, f"Expected no jj commands, found: {jj_commands}"

    def assert_only_git_commands(self):
        """Assert only git commands were executed (no jj).

        Raises:
            AssertionError: If any non-git VCS commands were logged
        """
        for binary, args in self.commands:
            if binary in ("jj", "hg", "fossil"):
                raise AssertionError(
                    f"Expected only git commands, found {binary} command: {binary} {' '.join(args)}"
                )

    def get_commands(self) -> List[Tuple[str, List[str]]]:
        """Get list of all captured commands.

        Returns:
            List of (binary, args) tuples
        """
        return self.commands

    def reset(self):
        """Clear the command log."""
        self.commands = []
