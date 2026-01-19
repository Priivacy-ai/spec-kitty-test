"""
Invoker module for host-based agent subprocess invocations.

This module provides the infrastructure for invoking AI coding agents
as subprocesses, capturing their output, and managing git worktree
isolation for test runs.

Exports:
    - InvocationOutcome: Enum for invocation outcomes
    - InvocationResult: Immutable result of agent invocation
    - ParsedAgentResponse: Structured data from agent output
    - AgentProcess: Subprocess wrapper with timeout management
    - WorktreeInfo: Metadata about a git worktree
    - WorktreeManager: Create and manage isolated worktrees
    - AgentInvoker: Main controller for agent invocations
    - AgentDiscovery: Runtime agent detection
    - DiscoveredAgent: Result of agent discovery
    - AvailabilityResult: Agent availability check result
"""

from .invocation_result import (
    InvocationOutcome,
    InvocationResult,
    ParsedAgentResponse,
)
from .agent_process import AgentProcess
from .worktree_manager import WorktreeInfo, WorktreeManager
from .agent_invoker import AgentInvoker
from .discovery import AgentDiscovery, AvailabilityResult, DiscoveredAgent

__all__ = [
    "InvocationOutcome",
    "InvocationResult",
    "ParsedAgentResponse",
    "AgentProcess",
    "WorktreeInfo",
    "WorktreeManager",
    "AgentInvoker",
    "AgentDiscovery",
    "AvailabilityResult",
    "DiscoveredAgent",
]
