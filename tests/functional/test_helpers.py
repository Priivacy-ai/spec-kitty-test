"""Shared helper functions for functional tests."""

import json
import subprocess
from typing import Tuple


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from script output that may contain log messages.

    Scripts often output log messages before JSON. This function finds
    the first line starting with { and parses it as JSON.

    Args:
        output: Script stdout containing potential JSON

    Returns:
        Parsed JSON dict, or None if no valid JSON found
    """
    for line in output.strip().split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


# Version Compatibility Helpers for 0.5.2 vs 0.5.3+ testing


def check_command_exists(command: list[str]) -> bool:
    """
    Check if a spec-kitty command exists.

    Args:
        command: Command to check (e.g., ['spec-kitty', 'diagnostics', '--help'])

    Returns:
        True if command exists, False otherwise
    """
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False
    )

    # Command exists if it doesn't show "No such command" error
    return "No such command" not in result.stderr and result.returncode != 2


def get_diagnostics_command() -> Tuple[list[str], str]:
    """
    Get the appropriate diagnostics command for current spec-kitty version.

    Returns:
        Tuple of (command_list, version_label)
        - 0.5.2: (['spec-kitty', 'diagnostics'], 'v0.5.2')
        - 0.5.3+: (['spec-kitty', 'verify-setup', '--diagnostics'], 'v0.5.3+')
    """
    # Check if standalone diagnostics command exists (0.5.2)
    if check_command_exists(['spec-kitty', 'diagnostics', '--help']):
        return (['spec-kitty', 'diagnostics'], 'v0.5.2')

    # Otherwise use consolidated verify-setup (0.5.3+)
    return (['spec-kitty', 'verify-setup', '--diagnostics'], 'v0.5.3+')


def get_check_tools_command() -> Tuple[list[str], str]:
    """
    Get the appropriate check tools command for current spec-kitty version.

    Returns:
        Tuple of (command_list, version_label)
        - 0.5.2: (['spec-kitty', 'check'], 'v0.5.2')
        - 0.5.3+: (['spec-kitty', 'verify-setup', '--check-tools'], 'v0.5.3+')
    """
    # Check if standalone check command exists (0.5.2)
    if check_command_exists(['spec-kitty', 'check', '--help']):
        return (['spec-kitty', 'check'], 'v0.5.2')

    # Otherwise use consolidated verify-setup (0.5.3+)
    return (['spec-kitty', 'verify-setup'], 'v0.5.3+')


def has_ascii_banner() -> bool:
    """
    Check if verify-setup shows ASCII banner.

    Returns:
        True for 0.5.2 (has banner), False for 0.5.3+ (no banner)
    """
    # If standalone diagnostics exists, we're on 0.5.2 which has banner
    return check_command_exists(['spec-kitty', 'diagnostics', '--help'])
