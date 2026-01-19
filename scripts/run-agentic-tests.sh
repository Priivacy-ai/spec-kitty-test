#!/bin/bash
# scripts/run-agentic-tests.sh
#
# Run agentic E2E tests with common filter patterns.
#
# T039: Implement test filtering (by agent, path, scenario)
#
# Usage:
#   ./scripts/run-agentic-tests.sh                    # Run all agentic tests
#   ./scripts/run-agentic-tests.sh -k "claude"        # Claude agent only
#   ./scripts/run-agentic-tests.sh -m "single_agent"  # Single-agent tests
#   ./scripts/run-agentic-tests.sh -m "not slow"      # Fast tests only
#   ./scripts/run-agentic-tests.sh --help             # Show pytest help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_ROOT"

echo "Running agentic E2E tests..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Run pytest with agentic test path
pytest tests/agentic/ -v "$@"
