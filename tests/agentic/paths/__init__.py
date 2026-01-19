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

# Exports will be added as path classes are implemented in WP04 and WP07
