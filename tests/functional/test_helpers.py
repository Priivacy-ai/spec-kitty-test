"""Shared helper functions for functional tests."""

import json


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
