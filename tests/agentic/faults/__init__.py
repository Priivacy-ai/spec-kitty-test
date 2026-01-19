"""Fault injection components for adversarial testing.

This module provides fault injectors for testing spec-kitty's error
handling and recovery mechanisms:

- process_faults.py: SIGTERM, SIGKILL, process crashes (WP08)
- file_faults.py: File corruption, disk full, permissions (WP08)
- network_faults.py: Toxiproxy integration for network chaos (WP08)
- auth_faults.py: Credential invalidation, expiration (WP08)
- resource_faults.py: Memory pressure, CPU stress, OOM (WP08)

All fault injectors support:
- Backup and restore for reversibility
- Trigger conditions (immediate, delayed, random)
- Container and local process targeting
"""

# Exports will be added as fault injectors are implemented in WP08
