"""Agentic End-to-End Testing Framework for spec-kitty.

This package provides a containerized, adversarial testing framework for
validating spec-kitty's multi-agent orchestrator with up to 9 AI coding agents.

The framework supports three test paths:
- Single-agent: One agent performs both implementation and review
- Cross-review: Different agents for implementation vs review
- Parallel-three: Three agents working on independent WPs in parallel

Key features:
- Container isolation via Docker for safe agent execution
- Real agent testing with actual credentials (no mocks)
- Fault injection for adversarial testing
- Distribution testing (PyPI packages, not development code)
- Comprehensive observability and logging

Directory structure:
- config/: Agent and test path configurations
- containers/: Docker infrastructure
- fixtures/: pytest fixtures for test setup
- paths/: Test path implementations
- faults/: Fault injection components
- tests/: Test implementations
- results/: Test output (git-ignored)
"""

__version__ = "0.1.0"
