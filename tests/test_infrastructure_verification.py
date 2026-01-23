"""Verification tests for test infrastructure (WP01).

This test file verifies that the test infrastructure foundation is working:
- Markers are registered correctly
- Fixtures are available and functional
- Auto-skip logic works as expected
"""

import pytest
from pathlib import Path


@pytest.mark.functional
def test_functional_marker_works():
    """Verify functional marker is registered and usable."""
    assert True


@pytest.mark.integration
def test_integration_marker_works():
    """Verify integration marker is registered and usable."""
    assert True


@pytest.mark.distribution
def test_distribution_marker_works():
    """Verify distribution marker is registered and usable."""
    assert True


@pytest.mark.orchestrator
def test_orchestrator_marker_works():
    """Verify orchestrator marker is registered and usable."""
    assert True


@pytest.mark.vcs
def test_vcs_marker_works():
    """Verify vcs marker is registered and usable."""
    assert True


@pytest.mark.adversarial
def test_adversarial_marker_works():
    """Verify adversarial marker is registered and usable."""
    assert True


@pytest.mark.regression
def test_regression_marker_works():
    """Verify regression marker is registered and usable."""
    assert True


@pytest.mark.slow
def test_slow_marker_works():
    """Verify slow marker is registered and usable."""
    assert True


@pytest.mark.requires_agent("nonexistent_agent_xyz")
def test_requires_agent_skip():
    """This should be skipped (nonexistent agent).

    If this test runs and fails, the requires_agent auto-skip logic is broken.
    """
    pytest.fail("Should have been skipped - agent 'nonexistent_agent_xyz' does not exist")


def test_detect_available_agents(detect_available_agents):
    """Verify agent detection fixture works."""
    assert isinstance(detect_available_agents, list)
    # List may be empty if no agents installed, but should be a list


def test_spec_kitty_git_test_fixture(spec_kitty_git_test):
    """Verify harness fixture works (skips if not available).

    This test will skip if the harness is not available, which is expected
    and correct behavior. If the harness IS available, verify it's a valid path.
    """
    assert isinstance(spec_kitty_git_test, Path)
    assert spec_kitty_git_test.exists()
    assert spec_kitty_git_test.is_dir()


def test_mock_subprocess_runner_import():
    """Verify MockSubprocessRunner can be imported."""
    from tests.fixtures import MockSubprocessRunner
    assert MockSubprocessRunner is not None

    # Test basic functionality
    mock = MockSubprocessRunner()
    result = mock.run(['echo', 'test'])
    assert result.returncode == 0
    assert ('echo', ['test']) in mock.get_commands()


def test_command_logger_import():
    """Verify CommandLogger can be imported."""
    from tests.fixtures import CommandLogger
    assert CommandLogger is not None

    # Test basic functionality
    logger = CommandLogger()
    logger.start_logging()
    logger.log_command('git', ['status'])
    logger.stop_logging()
    assert len(logger.get_commands()) == 1
    assert logger.get_commands()[0] == ('git', ['status'])


def test_mock_subprocess_runner_assert_no_jj():
    """Verify MockSubprocessRunner.assert_no_jj_commands works."""
    from tests.fixtures import MockSubprocessRunner

    mock = MockSubprocessRunner()
    mock.run(['git', 'status'])
    mock.run(['git', 'commit'])

    # Should not raise - no jj commands
    mock.assert_no_jj_commands()


def test_mock_subprocess_runner_detects_jj():
    """Verify MockSubprocessRunner detects jj commands."""
    from tests.fixtures import MockSubprocessRunner

    mock = MockSubprocessRunner()
    mock.run(['jj', 'log'])

    # Should raise - jj command executed
    with pytest.raises(AssertionError, match="Expected no jj commands"):
        mock.assert_no_jj_commands()


def test_command_logger_pattern_matching():
    """Verify CommandLogger pattern matching works."""
    from tests.fixtures import CommandLogger

    logger = CommandLogger()
    logger.start_logging()
    logger.log_command('git', ['status'])
    logger.log_command('jj', ['log'])
    logger.log_command('git', ['commit'])
    logger.stop_logging()

    # Get only git commands
    git_commands = logger.get_commands('git')
    assert len(git_commands) == 2
    assert all(cmd[0] == 'git' for cmd in git_commands)

    # Assert no hg commands
    logger.assert_no_commands('hg')

    # Assert jj command exists
    logger.assert_command_exists('jj')
