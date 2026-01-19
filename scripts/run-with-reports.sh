#!/bin/bash
# scripts/run-with-reports.sh
#
# Run agentic E2E tests with JUnit XML and other reports.
#
# T040: Generate JUnit XML test reports
#
# Usage:
#   ./scripts/run-with-reports.sh                     # Run all with reports
#   ./scripts/run-with-reports.sh -m "single_agent"   # Specific markers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/tests/agentic/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Navigate to project root
cd "$PROJECT_ROOT"

# Create results directory
mkdir -p "$OUTPUT_DIR"

echo "Running agentic E2E tests with reports..."
echo "Project root: $PROJECT_ROOT"
echo "Output dir: $OUTPUT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Run pytest with JUnit XML output
pytest tests/agentic/ \
    --junitxml="$OUTPUT_DIR/junit-$TIMESTAMP.xml" \
    --tb=short \
    -v \
    "$@"

echo ""
echo "Reports generated:"
echo "  - JUnit XML: $OUTPUT_DIR/junit-$TIMESTAMP.xml"
