"""Command logger for tracking VCS command execution.

This module provides CommandLogger, a utility class for logging and analyzing
subprocess commands executed during tests. Useful for verifying VCS behavior.
"""

from typing import List, Tuple, Optional, Pattern
import re


class CommandLogger:
    """Tracks VCS command execution for testing purposes.

    This class provides structured logging of subprocess commands with
    pattern matching and assertion capabilities.

    Usage:
        logger = CommandLogger()
        logger.start_logging()

        # Execute commands
        subprocess.run(['git', 'status'])
        subprocess.run(['git', 'commit', '-m', 'test'])

        logger.stop_logging()

        # Verify behavior
        logger.assert_no_commands('jj')
        git_commands = logger.get_commands('git')
        assert len(git_commands) == 2
    """

    def __init__(self):
        """Initialize with empty command log."""
        self._commands: List[Tuple[str, List[str]]] = []
        self._logging = False

    def start_logging(self):
        """Start logging subprocess commands."""
        self._logging = True
        self._commands = []

    def stop_logging(self):
        """Stop logging and return captured commands."""
        self._logging = False
        return self._commands

    def log_command(self, binary: str, args: List[str]):
        """Log a command execution.

        Args:
            binary: Command binary name (e.g., 'git', 'jj')
            args: List of command arguments
        """
        if self._logging:
            self._commands.append((binary, args))

    def get_commands(self, pattern: Optional[str] = None) -> List[Tuple[str, List[str]]]:
        """Get logged commands, optionally filtered by pattern.

        Args:
            pattern: Optional regex pattern to match against binary name

        Returns:
            List of (binary, args) tuples matching pattern
        """
        if pattern is None:
            return self._commands

        regex = re.compile(pattern)
        return [(binary, args) for binary, args in self._commands if regex.match(binary)]

    def assert_no_commands(self, pattern: str):
        """Assert no commands matching pattern were executed.

        Args:
            pattern: Regex pattern to match against binary name

        Raises:
            AssertionError: If any matching commands found
        """
        matching = self.get_commands(pattern)
        assert not matching, f"Expected no commands matching '{pattern}', found: {matching}"

    def assert_command_count(self, pattern: str, expected_count: int):
        """Assert specific number of commands matching pattern.

        Args:
            pattern: Regex pattern to match against binary name
            expected_count: Expected number of matching commands

        Raises:
            AssertionError: If count doesn't match
        """
        matching = self.get_commands(pattern)
        actual_count = len(matching)
        assert actual_count == expected_count, (
            f"Expected {expected_count} commands matching '{pattern}', found {actual_count}: {matching}"
        )

    def assert_command_exists(self, pattern: str):
        """Assert at least one command matching pattern was executed.

        Args:
            pattern: Regex pattern to match against binary name

        Raises:
            AssertionError: If no matching commands found
        """
        matching = self.get_commands(pattern)
        assert matching, f"Expected at least one command matching '{pattern}', found none"

    def reset(self):
        """Clear the command log."""
        self._commands = []
        self._logging = False
