"""
Agent configurations for host-based agent invocation.

This module provides the base protocol and enums for agent configurations,
as well as concrete implementations for supported agents.

Exports:
    - BaseAgentConfig: Protocol for agent configurations
    - PromptMethod: Enum for prompt delivery methods
    - AgentConstraint: Enum for agent selection constraints
"""

from .base import AgentConstraint, BaseAgentConfig, PromptMethod

__all__ = [
    "AgentConstraint",
    "BaseAgentConfig",
    "PromptMethod",
]
