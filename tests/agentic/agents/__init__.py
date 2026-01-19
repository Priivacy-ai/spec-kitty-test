"""
Agent configurations for host-based agent invocation.

This module provides the base protocol and enums for agent configurations,
as well as concrete implementations for supported agents.

Exports:
    - BaseAgentConfig: Protocol for agent configurations
    - PromptMethod: Enum for prompt delivery methods
    - AgentConstraint: Enum for agent selection constraints
    - ClaudeCodeConfig: Claude Code CLI configuration
    - CopilotConfig: GitHub Copilot CLI configuration
    - GeminiConfig: Google Gemini CLI configuration
    - ALL_AGENT_CONFIGS: List of all available agent configs
"""

from .base import AgentConstraint, BaseAgentConfig, PromptMethod
from .claude_code import ClaudeCodeConfig
from .copilot import CopilotConfig
from .gemini import GeminiConfig

# Registry of all available agent configs
ALL_AGENT_CONFIGS = [
    ClaudeCodeConfig(),
    CopilotConfig(),
    GeminiConfig(),
]

__all__ = [
    "AgentConstraint",
    "BaseAgentConfig",
    "PromptMethod",
    "ClaudeCodeConfig",
    "CopilotConfig",
    "GeminiConfig",
    "ALL_AGENT_CONFIGS",
]
