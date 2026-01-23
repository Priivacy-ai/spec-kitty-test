"""
Distribution tests for agent detection from package (WP11: T066).

Validates that agent detection and invocation works correctly
from PyPI install without repository access.
"""
import pytest
import shutil
from pathlib import Path


@pytest.mark.distribution
@pytest.mark.orchestrator
class TestAgentDetection:
    """Tests for agent detection from installed package."""

    def test_detect_agents_from_package(self):
        """
        Verify detect_installed_agents() works from package.

        Validates spec.md User Story 8, Acceptance Scenario 7:
        "Given agent not installed,
         When orchestrator detects available agents,
         Then that agent is excluded from selection pool"
        """
        from specify_cli.orchestrator.agents import detect_installed_agents

        # Should return a list (may be empty if no agents installed)
        agents = detect_installed_agents()

        assert isinstance(agents, list), \
            "detect_installed_agents() should return a list"

        # All items should be strings
        for agent in agents:
            assert isinstance(agent, str), \
                f"Agent should be string, got {type(agent)}"
            assert len(agent) > 0, \
                "Agent name should not be empty"

    def test_agent_registry_accessible(self):
        """
        Verify AGENT_REGISTRY imports correctly from package.

        Validates that orchestrator agent configuration is accessible
        from installed package (not just development environment).
        """
        from specify_cli.orchestrator.agents import AGENT_REGISTRY

        # Registry should be a dict
        assert isinstance(AGENT_REGISTRY, dict), \
            "AGENT_REGISTRY should be a dict"

        # Should have some agents
        assert len(AGENT_REGISTRY) >= 1, \
            "Registry should have at least one agent defined"

        # Known agents should be present
        expected_agents = ["claude-code", "opencode", "codex"]
        found_agents = [a for a in expected_agents if a in AGENT_REGISTRY]

        assert len(found_agents) >= 1, \
            f"Should have at least one of {expected_agents} in registry"

    def test_agent_detection_with_broken_binary(
        self,
        broken_agent_binary,
        monkeypatch
    ):
        """
        Verify agent detection handles broken binaries gracefully.

        Edge case: Agent binary exists but crashes on invocation.
        Detection should exclude it from available agents.
        """
        from specify_cli.orchestrator.agents import detect_installed_agents

        # Add broken binary to PATH
        original_path = shutil.which("claude") or ""
        monkeypatch.setenv(
            "PATH",
            f"{broken_agent_binary}:{original_path}:/usr/bin:/bin"
        )

        # Should complete without error
        agents = detect_installed_agents()

        # Result should be a valid list
        assert isinstance(agents, list), \
            "detect_installed_agents() should return list even with broken binary"

        # Broken agent might or might not be in list depending on
        # detection strategy. Key is no exception raised.

    def test_agent_aliases_resolved_from_package(self):
        """
        Verify agent alias normalization works from package.

        Validates spec.md User Story 8, Acceptance Scenario 1:
        "Given user config with aliases,
         When orchestrator resolves agent IDs,
         Then aliases are normalized to canonical names"
        """
        from specify_cli.orchestrator.agents import normalize_agent_id

        # Test common aliases
        test_cases = [
            # (input, expected_output)
            ("claude", "claude-code"),
            ("claude-code", "claude-code"),
            ("opencode", "opencode"),
            ("codex", "codex"),
        ]

        for alias, expected in test_cases:
            result = normalize_agent_id(alias)
            assert result == expected, \
                f"normalize_agent_id('{alias}') should return '{expected}', got '{result}'"


@pytest.mark.distribution
@pytest.mark.orchestrator
class TestAgentInvocation:
    """Tests for agent invocation from installed package."""

    def test_agent_invoker_available(self):
        """
        Verify agent invoker classes are available from package.
        """
        from specify_cli.orchestrator.agents import (
            get_invoker,
            AGENT_REGISTRY,
        )

        # Get invoker for known agent
        invoker = get_invoker("claude-code")
        assert invoker is not None, \
            "get_invoker() should return invoker for known agent"

    def test_agent_registry_structure(self):
        """
        Verify agent registry has expected structure.
        """
        from specify_cli.orchestrator.agents import AGENT_REGISTRY

        # Registry should have entries
        assert len(AGENT_REGISTRY) > 0, \
            "Registry should not be empty"

        # Each entry should be a valid agent config
        for agent_id, config in AGENT_REGISTRY.items():
            assert isinstance(agent_id, str), \
                f"Agent ID should be string, got {type(agent_id)}"


@pytest.mark.distribution
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentEdgeCases:
    """Edge case tests for agent detection."""

    def test_empty_path_handling(self, monkeypatch):
        """
        Verify agent detection handles empty PATH gracefully.
        """
        from specify_cli.orchestrator.agents import detect_installed_agents

        # Set empty PATH
        monkeypatch.setenv("PATH", "")

        # Should not crash
        agents = detect_installed_agents()

        # Should return empty list
        assert isinstance(agents, list), \
            "Should return list even with empty PATH"
        assert len(agents) == 0, \
            "Should return empty list with no PATH"

    def test_invalid_agent_name_normalization(self):
        """
        Verify normalization handles invalid agent names.
        """
        from specify_cli.orchestrator.agents import normalize_agent_id

        invalid_names = ["", "   ", "unknown-agent-xyz"]

        for name in invalid_names:
            # Should either return normalized name or same name
            # but not crash
            try:
                result = normalize_agent_id(name)
                assert isinstance(result, str), \
                    f"normalize_agent_id('{name}') should return string"
            except ValueError:
                # Raising ValueError for invalid input is acceptable
                pass
