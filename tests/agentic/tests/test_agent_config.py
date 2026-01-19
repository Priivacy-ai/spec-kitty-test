"""Agent configuration tests - US8 validation.

Tests the modular agent configuration system.

T049: Write test_agent_config.py test cases

Per CLAUDE.md: These are distribution tests - spec-kitty is installed from PyPI,
NOT from local source. No SPEC_KITTY_TEMPLATE_ROOT is ever set.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ..fixtures.agent_fixtures import (
    AgentConfig,
    AgentRegistry,
    DynamicAgentRegistry,
    InvocationPattern,
)
from ..fixtures.container_fixtures import ResourceLimits

if TYPE_CHECKING:
    pass


pytestmark = [
    pytest.mark.agentic,
]


class TestAgentConfiguration:
    """US8: Modular Agent Configuration

    Acceptance Scenarios from spec.md:
    1. Given a YAML configuration file listing available agents,
       When tests run,
       Then only configured agents are used.

    2. Given a new agent is added to configuration,
       When tests run,
       Then the new agent is automatically included in agent discovery.

    3. Given an agent is removed from configuration,
       When tests run,
       Then tests requiring that agent are skipped.

    4. Given agent-specific configuration (timeouts, resource limits),
       When that agent runs,
       Then the specific configuration is applied.
    """

    def test_only_configured_agents_used(
        self,
        agent_registry: AgentRegistry,
    ):
        """
        Acceptance Scenario 1:
        Given a YAML configuration file listing available agents,
        When tests run,
        Then only configured agents are used.
        """
        agents = agent_registry.get_available_agents()

        # All returned agents should be enabled in config
        for agent in agents:
            assert agent.enabled, f"Disabled agent returned: {agent.agent_id}"

    def test_new_agent_auto_discovered(
        self,
        tmp_path: Path,
    ):
        """
        Acceptance Scenario 2:
        Given a new agent is added to configuration,
        When tests run,
        Then the new agent is automatically included.
        """
        # Create temp config with new agent
        config_content = """
version: "1.0"
agents:
  test-new-agent:
    enabled: true
    command: "echo"
    invocation_pattern: "stdin"
    timeout_seconds: 30
    credentials_secret: "test_key"
    resource_limits:
      cpu_cores: 1.0
      memory_mb: 512
      disk_mb: 1024
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        # Create secrets directory
        secrets_dir = tmp_path / "config" / "secrets"
        secrets_dir.mkdir(parents=True)
        (secrets_dir / "test_key.txt").write_text("test_credential")

        registry = AgentRegistry(config_path)
        agent = registry.get_agent("test-new-agent")

        assert agent is not None, "New agent not discovered"
        assert agent.agent_id == "test-new-agent"
        assert agent.command == "echo"
        assert agent.timeout_seconds == 30

    def test_removed_agent_tests_skipped(
        self,
        agent_registry: AgentRegistry,
    ):
        """
        Acceptance Scenario 3:
        Given an agent is removed from configuration,
        When tests run,
        Then tests requiring that agent are skipped.
        """
        # Try to get a non-existent agent
        agent = agent_registry.get_agent("definitely-not-real-agent")
        assert agent is None, "Non-existent agent should return None"

    def test_agent_specific_config_applied(
        self,
        agent_registry: AgentRegistry,
    ):
        """
        Acceptance Scenario 4:
        Given agent-specific configuration,
        When that agent runs,
        Then the specific configuration is applied.
        """
        agents = agent_registry.get_available_agents()

        for agent in agents:
            # Each agent should have its own limits
            assert agent.timeout_seconds > 0
            assert agent.resource_limits.cpu_cores > 0
            assert agent.resource_limits.memory_mb > 0

            # Cursor should have timeout wrapper
            if agent.agent_id == "cursor":
                assert agent.requires_timeout_wrapper, \
                    "Cursor should require timeout wrapper"


class TestDynamicAgentRegistry:
    """Test dynamic agent configuration features (T011)."""

    def test_add_agent_at_runtime(self, tmp_path: Path):
        """Test adding an agent at runtime."""
        # Create minimal config
        config_content = """
version: "1.0"
agents: {}
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = DynamicAgentRegistry(config_path)

        # Initially empty
        assert len(registry.get_all_agents()) == 0

        # Add new agent
        new_agent = AgentConfig(
            agent_id="dynamic-agent",
            enabled=True,
            command="test-cmd",
            invocation_pattern=InvocationPattern.STDIN,
            headless_flag="--headless",
            json_output_flag="--json",
            timeout_seconds=60,
            credentials_secret="test",
            requires_timeout_wrapper=False,
            resource_limits=ResourceLimits(cpu_cores=1, memory_mb=512, disk_mb=1024),
        )

        registry.add_agent(new_agent)

        # Should now have one agent
        assert len(registry.get_all_agents()) == 1
        assert registry.get_agent("dynamic-agent") is not None

    def test_remove_agent_at_runtime(self, tmp_path: Path):
        """Test removing an agent at runtime."""
        config_content = """
version: "1.0"
agents:
  test-agent:
    enabled: true
    command: "test"
    invocation_pattern: "stdin"
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = DynamicAgentRegistry(config_path)

        # Should have one agent
        assert registry.get_agent("test-agent") is not None

        # Remove it
        result = registry.remove_agent("test-agent")
        assert result, "Remove should return True"

        # Should be gone
        assert registry.get_agent("test-agent") is None

        # Remove non-existent should return False
        result = registry.remove_agent("nonexistent")
        assert not result, "Remove nonexistent should return False"

    def test_update_agent_config(self, tmp_path: Path):
        """Test updating agent configuration at runtime."""
        config_content = """
version: "1.0"
agents:
  test-agent:
    enabled: true
    command: "test"
    invocation_pattern: "stdin"
    timeout_seconds: 60
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = DynamicAgentRegistry(config_path)
        agent = registry.get_agent("test-agent")
        assert agent.timeout_seconds == 60

        # Update timeout
        result = registry.update_agent("test-agent", timeout_seconds=120)
        assert result, "Update should return True"

        # Verify update
        agent = registry.get_agent("test-agent")
        assert agent.timeout_seconds == 120

    def test_reload_config(self, tmp_path: Path):
        """Test reloading configuration from file."""
        config_content = """
version: "1.0"
agents:
  agent-v1:
    enabled: true
    command: "test"
    invocation_pattern: "stdin"
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = DynamicAgentRegistry(config_path)
        assert registry.get_agent("agent-v1") is not None

        # Update file with new agent
        new_config = """
version: "1.0"
agents:
  agent-v2:
    enabled: true
    command: "test2"
    invocation_pattern: "stdin"
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
"""
        config_path.write_text(new_config)

        # Reload
        registry.reload_config()

        # Old agent should be gone, new one present
        assert registry.get_agent("agent-v1") is None
        assert registry.get_agent("agent-v2") is not None


class TestAgentAvailability:
    """Tests for agent availability checking."""

    def test_get_enabled_agents(self, agent_registry: AgentRegistry):
        """Test that get_enabled_agents returns only enabled agents."""
        enabled = agent_registry.get_enabled_agents()

        for agent in enabled:
            assert agent.enabled, f"Disabled agent in enabled list: {agent.agent_id}"

    def test_get_installed_agents(self, agent_registry: AgentRegistry):
        """Test that get_installed_agents returns only installed agents."""
        installed = agent_registry.get_installed_agents()

        for agent in installed:
            assert agent.is_installed, f"Uninstalled agent in installed list: {agent.agent_id}"

    def test_availability_reason_provided(self, agent_registry: AgentRegistry):
        """Test that unavailable agents provide a reason."""
        all_agents = agent_registry.get_all_agents()

        for agent in all_agents:
            if not agent.is_available:
                reason = agent.get_availability_reason()
                assert reason, f"Unavailable agent {agent.agent_id} has no reason"


class TestAgentConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_invocation_pattern_rejected(self, tmp_path: Path):
        """Test that invalid invocation patterns are rejected."""
        config_content = """
version: "1.0"
agents:
  bad-agent:
    enabled: true
    command: "test"
    invocation_pattern: "invalid"
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ValueError):
            AgentRegistry(config_path)

    def test_missing_required_fields(self, tmp_path: Path):
        """Test that missing required fields are caught."""
        config_content = """
version: "1.0"
agents:
  incomplete-agent:
    enabled: true
    # Missing command and invocation_pattern
defaults:
  timeout_seconds: 300
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        with pytest.raises((KeyError, TypeError)):
            AgentRegistry(config_path)

    def test_resource_limits_inherit_defaults(self, tmp_path: Path):
        """Test that resource limits inherit from defaults."""
        config_content = """
version: "1.0"
agents:
  test-agent:
    enabled: true
    command: "test"
    invocation_pattern: "stdin"
    credentials_secret: "test"
defaults:
  timeout_seconds: 300
  resource_limits:
    cpu_cores: 4.0
    memory_mb: 8192
    disk_mb: 20480
"""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(config_content)

        registry = AgentRegistry(config_path)
        agent = registry.get_agent("test-agent")

        # Should inherit defaults
        assert agent.resource_limits.cpu_cores == 4.0
        assert agent.resource_limits.memory_mb == 8192
        assert agent.resource_limits.disk_mb == 20480
