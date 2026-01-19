"""Configuration module for agentic E2E testing.

This module provides access to agent and test path configurations
loaded from YAML files.

Configuration Files:
- agents.yaml: Agent definitions (commands, timeouts, resource limits)
- paths.yaml: Test path definitions (single-agent, cross-review, parallel)

Secrets:
- secrets/: Git-ignored directory for API keys and credentials
  Credentials are mounted into containers via Docker secrets.
"""

from pathlib import Path

# Configuration directory path
CONFIG_DIR = Path(__file__).parent

# Configuration file paths
AGENTS_CONFIG = CONFIG_DIR / "agents.yaml"
PATHS_CONFIG = CONFIG_DIR / "paths.yaml"
SECRETS_DIR = CONFIG_DIR / "secrets"
