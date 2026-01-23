"""
Pytest Marker Definitions for Comprehensive Test Suite

This module defines custom pytest markers used to categorize and filter tests.
These markers are registered in conftest.py via pytest_configure hook.
"""

# Marker definitions for pytest.ini or conftest.py registration
# Format: "marker_name: description"

MARKER_DEFINITIONS = {
    # Test tier markers
    "functional": "Fast functional tests with mocked dependencies (<10 min)",
    "integration": "Integration tests using real orchestration (adaptive timing)",
    "distribution": "Distribution tests validating PyPI user experience (no bypasses, <45 min)",

    # Feature area markers
    "orchestrator": "Tests for orchestrator system (state machine, agents, execution)",
    "vcs": "Tests for VCS abstraction (git/jj isolation, detection, factory)",
    "data_loss": "Tests for data loss prevention (cleanup, corruption, conflicts)",
    "templates": "Tests for template bundling and resolution",
    "migrations": "Tests for migration execution and registry",

    # Agent requirement markers
    "requires_agent": "Test requires specific agent to be installed (parametrized)",
    "requires_claude": "Test requires Claude Code agent",
    "requires_opencode": "Test requires OpenCode agent",
    "requires_codex": "Test requires GitHub Codex agent",
    "requires_copilot": "Test requires GitHub Copilot agent",
    "requires_gemini": "Test requires Google Gemini agent",

    # Test philosophy markers
    "adversarial": "Adversarial test designed to break spec-kitty with edge cases",
    "regression": "Regression test for previously discovered bugs",

    # Special requirement markers (existing, included for completeness)
    "jj": "Test requires jujutsu VCS (auto-skip if not installed)",
    "upgrade": "Test validates upgrade paths between versions",

    # Performance markers
    "slow": "Test takes >30 seconds (may be skipped for quick test runs)",
    "very_slow": "Test takes >2 minutes (skipped by default)",
}


# Marker groups for running related tests together
MARKER_GROUPS = {
    # Run all unit tests (fast)
    "unit": ["functional"],

    # Run all integration tests (real orchestration)
    "real": ["integration"],

    # Run all distribution tests (PyPI experience)
    "pypi": ["distribution"],

    # Run all orchestrator-related tests across tiers
    "all_orchestrator": ["orchestrator"],

    # Run all VCS-related tests across tiers
    "all_vcs": ["vcs", "jj"],

    # Run critical path tests (quick smoke test)
    "critical": ["functional", "distribution"],

    # Run comprehensive suite (everything)
    "comprehensive": ["functional", "integration", "distribution"],
}


# pytest.mark decorator usage examples for documentation
MARKER_USAGE_EXAMPLES = """
# Basic tier markers
@pytest.mark.functional
def test_state_machine_transitions():
    # Fast unit test with mocks
    ...

@pytest.mark.integration
def test_real_orchestration_cycle(spec_kitty_git_test):
    # Real orchestration using test harness
    ...

@pytest.mark.distribution
def test_fresh_install_workflow(no_template_bypass):
    # PyPI user experience test
    ...

# Feature area markers (can combine with tier)
@pytest.mark.functional
@pytest.mark.orchestrator
def test_agent_selection_logic():
    ...

@pytest.mark.distribution
@pytest.mark.vcs
def test_jj_never_invoked_from_package():
    ...

# Agent requirement markers
@pytest.mark.integration
@pytest.mark.requires_agent("claude")
def test_claude_implementation(detect_available_agents):
    # Only runs if Claude Code is installed
    ...

@pytest.mark.requires_claude
@pytest.mark.requires_opencode
def test_cross_agent_review():
    # Requires both Claude and OpenCode
    ...

# Adversarial testing markers
@pytest.mark.functional
@pytest.mark.adversarial
@pytest.mark.orchestrator
def test_circular_dependency_detection():
    # Edge case: circular WP dependencies
    ...

@pytest.mark.distribution
@pytest.mark.adversarial
@pytest.mark.data_loss
def test_worktree_cleanup_with_locked_files():
    # Edge case: file locks during cleanup
    ...

# Performance markers
@pytest.mark.integration
@pytest.mark.slow
def test_full_10wp_orchestration():
    # Takes >30s
    ...
"""


# Command-line examples for running specific test groups
CLI_EXAMPLES = """
# Run only functional tests (fast)
pytest -m functional

# Run only integration tests (real orchestration)
pytest -m integration

# Run only distribution tests (PyPI experience)
pytest -m distribution

# Run all orchestrator tests across all tiers
pytest -m orchestrator

# Run all VCS tests
pytest -m vcs

# Run only tests that require Claude agent
pytest -m requires_claude

# Run adversarial tests only
pytest -m adversarial

# Run quick smoke test (functional + distribution, no integration)
pytest -m "functional or distribution"

# Run comprehensive suite (everything)
pytest -m "functional or integration or distribution"

# Run everything except slow tests
pytest -m "not slow and not very_slow"

# Run only orchestrator functional tests
pytest -m "functional and orchestrator"

# Run only distribution tests for VCS abstraction
pytest -m "distribution and vcs"

# Exclude integration tests (for quick iteration)
pytest -m "not integration"
"""


# Auto-skip configuration for markers
# This is used in conftest.py pytest_collection_modifyitems hook
AUTO_SKIP_CONFIG = {
    # Skip jj tests when jj not installed (existing behavior)
    "jj": {
        "condition": "not _jj_is_available()",
        "reason": "jj (jujutsu) not installed",
    },

    # Skip agent-specific tests when agent not installed
    "requires_claude": {
        "condition": "'claude-code' not in detect_installed_agents()",
        "reason": "Claude Code agent not installed",
    },
    "requires_opencode": {
        "condition": "'opencode' not in detect_installed_agents()",
        "reason": "OpenCode agent not installed",
    },
    "requires_codex": {
        "condition": "'codex' not in detect_installed_agents()",
        "reason": "GitHub Codex agent not installed",
    },
    "requires_copilot": {
        "condition": "'copilot' not in detect_installed_agents()",
        "reason": "GitHub Copilot agent not installed",
    },
    "requires_gemini": {
        "condition": "'gemini' not in detect_installed_agents()",
        "reason": "Google Gemini agent not installed",
    },
}


# Parametrized requires_agent marker implementation
# This allows @pytest.mark.requires_agent("claude") syntax
def requires_agent_impl(agent_id: str):
    """
    Implementation of requires_agent parametrized marker.

    Usage in conftest.py:

        def pytest_collection_modifyitems(config, items):
            installed_agents = detect_installed_agents()
            for item in items:
                # Handle requires_agent marker
                for marker in item.iter_markers(name="requires_agent"):
                    required_agent = marker.args[0]
                    if required_agent not in installed_agents:
                        skip = pytest.mark.skip(
                            reason=f"Agent '{required_agent}' not installed"
                        )
                        item.add_marker(skip)
    """
    pass  # Actual implementation in conftest.py


# Export marker definitions
__all__ = [
    "MARKER_DEFINITIONS",
    "MARKER_GROUPS",
    "MARKER_USAGE_EXAMPLES",
    "CLI_EXAMPLES",
    "AUTO_SKIP_CONFIG",
]
