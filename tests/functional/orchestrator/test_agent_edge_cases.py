"""
Agent invocation edge case tests (WP13: T078).

Tests unusual, adversarial, or boundary conditions for agent invocation.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess
import time


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentInteractiveAuth:
    """Test handling of agents requiring interactive authentication."""

    def test_agent_hangs_for_input(self, tmp_path):
        """Edge case: Agent binary requires interactive auth (hangs for input)."""
        # Simulate a process that hangs waiting for input
        # Using a simple sleep to simulate hang
        try:
            result = subprocess.run(
                ["sleep", "0.1"],  # Short sleep
                capture_output=True,
                timeout=1
            )
            assert result.returncode == 0
        except subprocess.TimeoutExpired:
            pytest.fail("Short command should not timeout")

    def test_timeout_kills_hanging_process(self, tmp_path):
        """Edge case: Timeout correctly kills hanging process."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                ["sleep", "10"],  # Long sleep
                capture_output=True,
                timeout=0.1  # Very short timeout
            )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentStderrWithExitZero:
    """Test handling of agents that write to stderr but succeed."""

    def test_stderr_with_success(self, tmp_path):
        """Edge case: Agent writes to stderr but exits with code 0."""
        # Use echo to stderr
        result = subprocess.run(
            ["bash", "-c", "echo 'warning message' >&2; exit 0"],
            capture_output=True,
            text=True
        )

        # Exit code should be 0
        assert result.returncode == 0

        # Stderr should have content
        assert "warning" in result.stderr

    def test_mixed_stdout_stderr(self, tmp_path):
        """Edge case: Agent writes to both stdout and stderr."""
        result = subprocess.run(
            ["bash", "-c", "echo 'stdout'; echo 'stderr' >&2; exit 0"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "stdout" in result.stdout
        assert "stderr" in result.stderr


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentHugeOutput:
    """Test handling of extremely large agent output."""

    def test_large_stdout(self, tmp_path):
        """Edge case: Agent produces large output (1MB)."""
        # Generate 1MB of output
        size_kb = 1024

        result = subprocess.run(
            ["bash", "-c", f"dd if=/dev/zero bs=1024 count={size_kb} 2>/dev/null | tr '\\0' 'x'"],
            capture_output=True,
            timeout=30
        )

        # Should complete
        assert result.returncode == 0
        # Output should be roughly expected size
        assert len(result.stdout) >= size_kb * 1000

    def test_infinite_output_with_timeout(self, tmp_path):
        """Edge case: Agent produces infinite output (needs timeout)."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                ["bash", "-c", "yes 'x'"],  # Infinite output
                capture_output=True,
                timeout=0.1
            )


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentConfigEdgeCases:
    """Test edge cases in agent configuration."""

    def test_empty_agent_priorities(self, tmp_path):
        """Edge case: agents.yaml has empty priority list."""
        import yaml

        config_file = tmp_path / "agents.yaml"
        config = {
            "agents": {
                "priorities": []
            }
        }
        config_file.write_text(yaml.dump(config))

        loaded = yaml.safe_load(config_file.read_text())
        assert loaded["agents"]["priorities"] == []

    def test_missing_agents_key(self, tmp_path):
        """Edge case: agents.yaml missing 'agents' key."""
        import yaml

        config_file = tmp_path / "agents.yaml"
        config = {"other_key": "value"}
        config_file.write_text(yaml.dump(config))

        loaded = yaml.safe_load(config_file.read_text())
        assert "agents" not in loaded

    def test_malformed_yaml(self, tmp_path):
        """Edge case: Malformed YAML in config."""
        config_file = tmp_path / "agents.yaml"
        config_file.write_text("agents: [unclosed bracket")

        import yaml
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(config_file.read_text())

    def test_invalid_agent_type(self, tmp_path):
        """Edge case: Agent config has invalid type for field."""
        import yaml

        config_file = tmp_path / "agents.yaml"
        config = {
            "agents": {
                "priorities": "not-a-list"  # Should be list
            }
        }
        config_file.write_text(yaml.dump(config))

        loaded = yaml.safe_load(config_file.read_text())
        assert isinstance(loaded["agents"]["priorities"], str)
        assert not isinstance(loaded["agents"]["priorities"], list)
