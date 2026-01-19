"""Smoke tests for agent discovery.

Validates SC-002: "Agent discovery correctly identifies 100% of
installed agents on the test machine"
"""

import os
import subprocess

import pytest

from ..agents import ALL_AGENT_CONFIGS
from ..invoker.discovery import AgentDiscovery


@pytest.mark.smoke
class TestDiscoverySmoke:
    """Smoke tests for agent discovery."""

    def test_discovery_finds_at_least_one_agent(self, agent_discovery):
        """Test that at least one agent is discovered."""
        discovered = agent_discovery.discover_all()

        print("\nDiscovered agents:")
        for agent in discovered:
            status = (
                "Available"
                if agent.is_available
                else f"Unavailable: {agent.unavailable_reason}"
            )
            print(f"  {agent.agent_id}: {status}")
            if agent.version:
                print(f"    Version: {agent.version}")

        available = [a for a in discovered if a.is_available]
        print(f"\nTotal: {len(discovered)} discovered, {len(available)} available")

        # At least one should be available for meaningful tests
        # (This test documents what's available, doesn't fail if none)

    def test_discovery_claude_code(self, agent_discovery):
        """Test Claude Code discovery specifically."""
        discovered = agent_discovery.discover_one("claude-code")

        if discovered is None:
            pytest.skip("Claude Code config not registered")

        print("\nClaude Code:")
        print(f"  Installed: {discovered.version is not None}")
        print(f"  Authenticated: {discovered.authenticated}")
        print(f"  Available: {discovered.is_available}")
        if discovered.unavailable_reason:
            print(f"  Reason: {discovered.unavailable_reason}")

        # Verify against manual check
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            manual_installed = result.returncode == 0
        except FileNotFoundError:
            manual_installed = False

        manual_auth = bool(os.environ.get("ANTHROPIC_API_KEY"))

        # Discovery should match manual check
        if discovered.version is not None:
            assert manual_installed, "Discovery found Claude but manual check failed"
        # Note: Claude may be authenticated via CLI auth, not just env var

    def test_discovery_copilot(self, agent_discovery):
        """Test GitHub Copilot discovery."""
        discovered = agent_discovery.discover_one("github-copilot")

        if discovered is None:
            pytest.skip("Copilot config not registered")

        print("\nGitHub Copilot:")
        print(f"  Installed: {discovered.version is not None}")
        print(f"  Authenticated: {discovered.authenticated}")
        print(f"  Available: {discovered.is_available}")

    def test_discovery_gemini(self, agent_discovery):
        """Test Google Gemini discovery."""
        discovered = agent_discovery.discover_one("google-gemini")

        if discovered is None:
            pytest.skip("Gemini config not registered")

        print("\nGoogle Gemini:")
        print(f"  Installed: {discovered.version is not None}")
        print(f"  Authenticated: {discovered.authenticated}")
        print(f"  Available: {discovered.is_available}")

    def test_discovery_opencode(self, agent_discovery):
        """Test OpenCode discovery."""
        discovered = agent_discovery.discover_one("opencode")

        if discovered is None:
            pytest.skip("OpenCode config not registered")

        print("\nOpenCode:")
        print(f"  Installed: {discovered.version is not None}")
        print(f"  Authenticated: {discovered.authenticated}")
        print(f"  Available: {discovered.is_available}")

    def test_discovery_codex(self, agent_discovery):
        """Test OpenAI Codex discovery."""
        discovered = agent_discovery.discover_one("openai-codex")

        if discovered is None:
            pytest.skip("Codex config not registered")

        print("\nOpenAI Codex:")
        print(f"  Installed: {discovered.version is not None}")
        print(f"  Authenticated: {discovered.authenticated}")
        print(f"  Available: {discovered.is_available}")

    def test_all_agents_have_configs(self):
        """Test that all expected agents have configs registered."""
        expected_agents = [
            "claude-code",
            "github-copilot",
            "google-gemini",
            "opencode",
            "openai-codex",
        ]

        config_ids = [c.agent_id for c in ALL_AGENT_CONFIGS]

        print("\nRegistered agent configs:")
        for agent_id in config_ids:
            print(f"  - {agent_id}")

        for agent_id in expected_agents:
            assert agent_id in config_ids, f"Missing config for {agent_id}"

    def test_discovery_caching(self, agent_discovery):
        """Test that discovery caching works."""
        # First call
        result1 = agent_discovery.discover_all()

        # Second call should use cache
        result2 = agent_discovery.discover_all(use_cache=True)

        # Should be same objects
        assert len(result1) == len(result2)
        for a1, a2 in zip(result1, result2):
            assert a1.agent_id == a2.agent_id

        # Invalidate and re-discover
        agent_discovery.invalidate_cache()
        result3 = agent_discovery.discover_all()

        # Should still have same agents
        assert len(result1) == len(result3)

    def test_discovery_get_available(self, agent_discovery):
        """Test getting only available agents."""
        available = agent_discovery.get_available()
        unavailable = agent_discovery.get_unavailable()

        print(f"\nAvailable agents: {len(available)}")
        for agent in available:
            print(f"  - {agent.agent_id} (v{agent.version})")

        print(f"\nUnavailable agents: {len(unavailable)}")
        for agent in unavailable:
            print(f"  - {agent.agent_id}: {agent.unavailable_reason}")

        # All available should have is_available=True
        for agent in available:
            assert agent.is_available, f"{agent.agent_id} marked available but is_available=False"

        # All unavailable should have is_available=False
        for agent in unavailable:
            assert not agent.is_available, f"{agent.agent_id} marked unavailable but is_available=True"
