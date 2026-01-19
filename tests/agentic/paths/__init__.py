"""Test path implementations for agentic E2E testing.

A TestPath defines a workflow template that can be instantiated with
specific agents at runtime. This module provides:

- base_path.py: Abstract TestPath base class with agent slots (WP04)
- single_agent.py: Single-agent workflow (implement + self-review) (WP04)
- cross_review.py: Two-agent workflow (different agents for review) (WP07)
- parallel_three.py: Three-agent parallel execution (WP07)

Agent slots are filled at runtime based on available agents, enabling
the same test path to run with different agent combinations.
"""

from itertools import permutations
from typing import Callable, Dict, List, Optional, TypeVar

import pytest

from .base_path import (
    AgentRole,
    AgentSlot,
    EventType,
    TestPath,
    TestPathConfig,
    TestRun,
    TestStatus,
    WorkflowObservation,
    WorkflowStep,
)
from .single_agent import SingleAgentPath
from .cross_review import CrossReviewPath
from .parallel_three import ParallelThreePath, ParallelWorkItem, WorkItemResult

# Type variable for decorator return type preservation
F = TypeVar("F", bound=Callable)


def generate_agent_combinations(
    available_agents: List[str],
    path: TestPath,
    max_combinations: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Generate valid agent assignment combinations for a path.

    Creates all valid combinations of agents that can fill the slots
    in a test path, respecting same_as and different_from constraints.

    Args:
        available_agents: List of available agent IDs
        path: TestPath to generate combinations for
        max_combinations: Maximum combinations to return (for test performance)

    Returns:
        List of slot_id -> agent_id assignment dicts

    Example:
        >>> combos = generate_agent_combinations(
        ...     ["claude", "copilot"],
        ...     single_agent_path,
        ...     max_combinations=5
        ... )
        >>> combos[0]
        {"implementer": "claude", "reviewer": "claude"}
    """
    slots = path.agent_slots
    required_slots = [s for s in slots if s.required]

    if len(available_agents) < _min_agents_needed(slots):
        return []

    # Generate combinations based on constraints
    combinations_list = _generate_constrained_combinations(available_agents, slots)

    if max_combinations and len(combinations_list) > max_combinations:
        combinations_list = combinations_list[:max_combinations]

    return combinations_list


def _min_agents_needed(slots: List[AgentSlot]) -> int:
    """Calculate minimum number of distinct agents needed for slots.

    Accounts for same_as (reduces count) and different_from (increases count)
    constraints.

    Args:
        slots: List of agent slots

    Returns:
        Minimum number of distinct agents required
    """
    required_slots = [s for s in slots if s.required]

    if not required_slots:
        return 0

    # Build groups of slots that must be the same
    same_groups: Dict[str, List[str]] = {}
    for slot in required_slots:
        if slot.same_as:
            if slot.same_as not in same_groups:
                same_groups[slot.same_as] = [slot.same_as]
            same_groups[slot.same_as].append(slot.slot_id)
        else:
            # Start its own group
            if slot.slot_id not in same_groups:
                found = False
                for group in same_groups.values():
                    if slot.slot_id in group:
                        found = True
                        break
                if not found:
                    same_groups[slot.slot_id] = [slot.slot_id]

    # Count distinct groups
    distinct_groups = len(set(tuple(sorted(g)) for g in same_groups.values()))

    # Check if any different_from constraints require more agents
    for slot in required_slots:
        if slot.different_from:
            # The slot and different_from slot need different agents
            # This is already handled by groups if they're in different groups
            pass

    return max(1, distinct_groups)


def _generate_constrained_combinations(
    agents: List[str],
    slots: List[AgentSlot],
) -> List[Dict[str, str]]:
    """Generate combinations respecting slot constraints.

    Handles same_as (slots must use same agent) and different_from
    (slots must use different agents) constraints.

    Args:
        agents: Available agent IDs
        slots: Agent slots with constraints

    Returns:
        List of valid assignment dictionaries
    """
    required_slots = [s for s in slots if s.required]

    if not required_slots:
        return [{}]

    combinations_list = []

    # Check if all slots can be the same agent (e.g., single-agent path)
    all_same = all(
        s.same_as is not None or s.different_from is None for s in required_slots
    )

    # Check if we have same_as constraints that link slots
    same_as_map: Dict[str, str] = {}  # slot_id -> canonical slot it must match
    for slot in required_slots:
        if slot.same_as:
            same_as_map[slot.slot_id] = slot.same_as

    # Get slots that must be different from each other
    different_pairs: List[tuple] = []
    for slot in required_slots:
        if slot.different_from:
            different_pairs.append((slot.slot_id, slot.different_from))

    # Build groups of slots that must share the same agent
    groups: List[List[str]] = []
    assigned_to_group: Dict[str, int] = {}

    for slot in required_slots:
        if slot.slot_id in assigned_to_group:
            continue

        # Find all slots that must be same as this one
        group = [slot.slot_id]
        assigned_to_group[slot.slot_id] = len(groups)

        # Add any slot that has same_as pointing to this slot
        for s in required_slots:
            if s.same_as == slot.slot_id and s.slot_id not in assigned_to_group:
                group.append(s.slot_id)
                assigned_to_group[s.slot_id] = len(groups)

        # Handle transitive same_as
        if slot.same_as and slot.same_as in assigned_to_group:
            # Merge into existing group
            existing_group_idx = assigned_to_group[slot.same_as]
            for sid in group:
                assigned_to_group[sid] = existing_group_idx
            groups[existing_group_idx].extend(group)
        else:
            groups.append(group)

    # Now generate combinations for groups
    num_groups = len(groups)

    if num_groups == 0:
        return [{}]

    # For each permutation of agents assigned to groups
    for perm in permutations(agents, min(num_groups, len(agents))):
        assignment: Dict[str, str] = {}

        # Assign each group to an agent
        for group_idx, agent in enumerate(perm):
            if group_idx >= len(groups):
                break
            for slot_id in groups[group_idx]:
                assignment[slot_id] = agent

        # Check if assignment is complete
        if len(assignment) < len(required_slots):
            continue

        # Validate different_from constraints
        valid = True
        for slot_a, slot_b in different_pairs:
            if slot_a in assignment and slot_b in assignment:
                if assignment[slot_a] == assignment[slot_b]:
                    valid = False
                    break

        if valid:
            combinations_list.append(assignment)

    return combinations_list


def agent_combo_ids(combos: List[Dict[str, str]]) -> List[str]:
    """Generate readable test IDs for agent combinations.

    Creates human-readable IDs for pytest parametrization that
    show which agents are assigned to which slots.

    Args:
        combos: List of slot_id -> agent_id assignments

    Returns:
        List of test ID strings

    Example:
        >>> combos = [{"impl": "claude", "rev": "copilot"}]
        >>> agent_combo_ids(combos)
        ["impl=claude+rev=copilot"]
    """
    ids = []
    for combo in combos:
        # Sort by slot_id for consistent ordering
        parts = [f"{k}={v}" for k, v in sorted(combo.items())]
        ids.append("+".join(parts))
    return ids


def parametrize_agent_combos(
    path_id: str,
    max_combos: int = 10,
) -> Callable[[F], F]:
    """Decorator factory to parametrize tests over agent combinations.

    Creates a pytest.mark.parametrize decorator that generates
    test cases for all valid agent combinations of a path.

    Usage:
        @parametrize_agent_combos("single-agent", max_combos=5)
        def test_single_agent_workflow(agent_assignments, available_agents):
            ...

    Args:
        path_id: ID of the test path to generate combinations for
        max_combos: Maximum number of combinations to test

    Returns:
        Decorator function that parametrizes the test
    """
    def decorator(func: F) -> F:
        # Store metadata for dynamic parametrization
        func._path_id = path_id  # type: ignore
        func._max_combos = max_combos  # type: ignore

        # The actual parametrization happens at collection time
        # using the pytest_generate_tests hook in conftest.py
        return func

    return decorator


# Exports
__all__ = [
    # Base classes and types
    "AgentRole",
    "AgentSlot",
    "EventType",
    "TestPath",
    "TestPathConfig",
    "TestRun",
    "TestStatus",
    "WorkflowObservation",
    "WorkflowStep",
    # Path implementations
    "SingleAgentPath",
    "CrossReviewPath",
    "ParallelThreePath",
    # Parallel path helpers
    "ParallelWorkItem",
    "WorkItemResult",
    # Utilities
    "agent_combo_ids",
    "generate_agent_combinations",
    "parametrize_agent_combos",
]
