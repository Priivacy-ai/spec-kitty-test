#!/bin/bash
# Test environment validation and setup for v0.12.0 adversarial testing
# Purpose: Validate all prerequisites before implementing critical test coverage
set -e

echo "🔍 Validating test environment for v0.12.0 critical test coverage..."
echo ""

# 1. Check spec-kitty installed
if ! command -v spec-kitty &> /dev/null; then
    echo "❌ spec-kitty not found"
    echo "   Install with: pip install -e ~/Code/spec-kitty"
    echo "   (Must install from source, not PyPI, for development testing)"
    exit 1
fi

# 2. Check version ≥0.11.0
VERSION=$(spec-kitty --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

if [ -z "$VERSION" ]; then
    echo "❌ Could not determine spec-kitty version"
    echo "   Run: spec-kitty --version"
    exit 1
fi

MAJOR=$(echo "$VERSION" | cut -d. -f1)
MINOR=$(echo "$VERSION" | cut -d. -f2)

# Version check: need ≥0.11.0
if [ "$MAJOR" -lt 0 ] || { [ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 11 ]; }; then
    echo "❌ spec-kitty version $VERSION too old (need ≥0.11.0 for workspace-per-WP features)"
    echo "   Upgrade with: cd ~/Code/spec-kitty && git pull && pip install -e ."
    exit 1
fi

echo "✅ spec-kitty version $VERSION"

# 3. Check Git version ≥2.25 (sparse-checkout support)
GIT_VERSION=$(git --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)

if [ -z "$GIT_VERSION" ]; then
    echo "❌ Could not determine Git version"
    exit 1
fi

GIT_MAJOR=$(echo "$GIT_VERSION" | cut -d. -f1)
GIT_MINOR=$(echo "$GIT_VERSION" | cut -d. -f2)

# Git version check: need ≥2.25 for sparse-checkout
if [ "$GIT_MAJOR" -lt 2 ] || { [ "$GIT_MAJOR" -eq 2 ] && [ "$GIT_MINOR" -lt 25 ]; }; then
    echo "❌ Git version $GIT_VERSION too old (need ≥2.25 for sparse-checkout support)"
    echo "   macOS: brew upgrade git"
    echo "   Linux: sudo apt-get update && sudo apt-get install git"
    exit 1
fi

echo "✅ Git version $GIT_VERSION"

# 4. Check ~/Code/spec-kitty exists (for test writer reference)
if [ ! -d "$HOME/Code/spec-kitty" ]; then
    echo "⚠️  ~/Code/spec-kitty not found"
    echo "   Test writer needs this directory for implementation code reference"
    echo "   Clone with: git clone <repo-url> ~/Code/spec-kitty"
else
    echo "✅ ~/Code/spec-kitty found"
fi

# 5. Check spec-kitty is installed from ~/Code/spec-kitty (not PyPI)
SPEC_KITTY_LOCATION=$(pip show spec-kitty-cli 2>/dev/null | grep "Location:" | cut -d: -f2- | xargs)

if [ -z "$SPEC_KITTY_LOCATION" ]; then
    echo "❌ spec-kitty-cli not installed via pip"
    echo "   Install with: pip install -e ~/Code/spec-kitty"
    exit 1
fi

# Check if location points to ~/Code/spec-kitty
if [[ "$SPEC_KITTY_LOCATION" != *"Code/spec-kitty"* ]]; then
    echo "❌ spec-kitty installed from: $SPEC_KITTY_LOCATION"
    echo "   Must be installed from ~/Code/spec-kitty for development testing"
    echo "   Reinstall with: pip uninstall spec-kitty-cli && pip install -e ~/Code/spec-kitty"
    exit 1
fi

echo "✅ spec-kitty installed from source"

# 6. Check git user.name/email configured (required for commits in tests)
GIT_USER=$(git config user.name 2>/dev/null)
GIT_EMAIL=$(git config user.email 2>/dev/null)

if [ -z "$GIT_USER" ] || [ -z "$GIT_EMAIL" ]; then
    echo "❌ Git user.name or user.email not configured"
    echo "   Required for test commits"
    echo "   Set with:"
    echo "     git config --global user.name 'Your Name'"
    echo "     git config --global user.email 'you@example.com'"
    exit 1
fi

echo "✅ Git user configured: $GIT_USER <$GIT_EMAIL>"

# 7. Check Python version ≥3.11
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)

if [ -z "$PYTHON_VERSION" ]; then
    echo "❌ Could not determine Python version"
    echo "   Run: python3 --version"
    exit 1
fi

PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "❌ Python version $PYTHON_VERSION too old (need ≥3.11 for spec-kitty)"
    echo "   Upgrade Python to 3.11 or higher"
    exit 1
fi

echo "✅ Python version $PYTHON_VERSION"

# 8. Check pytest installed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "❌ pytest not installed"
    echo "   Install with: pip install pytest pytest-anyio"
    exit 1
fi

PYTEST_VERSION=$(python3 -c "import pytest; print(pytest.__version__)" 2>/dev/null)
echo "✅ pytest version $PYTEST_VERSION"

# Success summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test environment ready for adversarial testing!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment Summary:"
echo "  • spec-kitty: $VERSION (from source)"
echo "  • Git: $GIT_VERSION"
echo "  • Python: $PYTHON_VERSION"
echo "  • pytest: $PYTEST_VERSION"
echo "  • User: $GIT_USER <$GIT_EMAIL>"
echo ""
echo "Run tests with:"
echo "  pytest tests/functional/test_sparse_checkout_infrastructure.py -xvs"
echo "  pytest tests/distribution/test_documentation_mission_distribution.py -xvs"
echo "  pytest tests/ -v  # Full suite (546 tests)"
echo ""
echo "Track bugs in: findings/test-infrastructure/v0.12.0-bugs-found.md"
echo ""
