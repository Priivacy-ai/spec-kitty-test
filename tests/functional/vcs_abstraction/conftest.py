"""
VCS Abstraction Test Fixtures

Provides fixtures for testing VCS abstraction layer including:
- VCSContext for managing VCS testing state
- Subprocess command logger for capturing all VCS commands
- Feature VCS lock fixture for testing meta.json vcs field
"""
import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch


class VCSContext:
    """Context for VCS testing with command logging.

    Provides methods to mock subprocess.run, log all commands,
    and assert that only expected VCS types are used.
    """

    def __init__(self, vcs_type="git", detection_override=None):
        """Initialize VCS context.

        Args:
            vcs_type: The VCS type being simulated ("git" or "jj")
            detection_override: Dict of VCS detection overrides, e.g., {"jj": False}
        """
        self.vcs_type = vcs_type
        self.detection_override = detection_override or {}
        self.command_log = []
        self.feature_vcs_lock = vcs_type

    def mock_subprocess_run(self, *args, **kwargs):
        """Mock subprocess.run and log commands.

        Captures the command being executed and returns a successful mock result.
        """
        if args and isinstance(args[0], (list, tuple)):
            cmd = args[0]
            binary = cmd[0] if cmd else "unknown"
            self.command_log.append((binary, list(cmd)))

        # Return successful mock result
        return Mock(
            returncode=0,
            stdout=b"",
            stderr=b"",
            check_returncode=lambda: None
        )

    def assert_no_jj_commands(self):
        """Assert no jj commands were executed."""
        jj_cmds = [cmd for binary, cmd in self.command_log if binary == "jj"]
        assert not jj_cmds, f"Found jj commands when jj should be disabled: {jj_cmds}"

    def assert_only_git_commands(self):
        """Assert only git commands (no jj) in VCS operations."""
        vcs_cmds = [(binary, cmd) for binary, cmd in self.command_log
                    if binary in ["git", "jj"]]
        jj_cmds = [cmd for binary, cmd in vcs_cmds if binary == "jj"]
        assert not jj_cmds, f"Found jj commands in git-only path: {jj_cmds}"
        assert any(binary == "git" for binary, _ in vcs_cmds), \
            "No git commands found (expected git operations)"

    def get_vcs_commands(self):
        """Return all VCS commands (git or jj)."""
        return [(binary, cmd) for binary, cmd in self.command_log
                if binary in ["git", "jj"]]

    def clear_log(self):
        """Clear the command log."""
        self.command_log.clear()


@pytest.fixture
def vcs_context():
    """Fixture providing VCS testing context with command logging."""
    return VCSContext(vcs_type="git")


@pytest.fixture
def vcs_context_with_jj_installed():
    """Fixture with jj installed but detection disabled.

    Simulates a system where jj binary is on PATH but spec-kitty
    has disabled jj detection (always returns False).
    """
    ctx = VCSContext(vcs_type="git")
    # Simulate jj installed but detection returns False
    ctx.detection_override = {"jj": False}
    return ctx


@pytest.fixture
def command_logger(vcs_context):
    """Fixture that patches subprocess.run to log commands.

    All subprocess.run calls during the test are captured in
    vcs_context.command_log for later assertion.
    """
    with patch('subprocess.run', side_effect=vcs_context.mock_subprocess_run):
        yield vcs_context
    # After test, vcs_context.command_log contains all commands


@pytest.fixture
def vcs_command_filter():
    """Helper to filter VCS commands from command log."""
    def filter_commands(command_log, binary=None):
        if binary:
            return [cmd for bin, cmd in command_log if bin == binary]
        # Return all VCS commands (git or jj)
        return [cmd for bin, cmd in command_log if bin in ["git", "jj"]]
    return filter_commands


@pytest.fixture
def mock_jj_detection_disabled():
    """Mock jj detection to always return False.

    This simulates the current state where jj is disabled in spec-kitty
    even if the jj binary is installed on the system.
    """
    def mock_is_jj_available():
        return False

    # Patch the detection function at the most common location
    # Note: The actual function location may vary, so we patch multiple locations
    with patch.object(
        __import__('shutil'),
        'which',
        side_effect=lambda x: "/usr/local/bin/jj" if x == "jj" else None
    ):
        yield


@pytest.fixture
def feature_with_vcs_lock(tmp_path):
    """Create test feature with VCS specified in meta.json.

    Returns a factory function that creates features with specific VCS locks.
    """
    def create_feature(feature_number, vcs_type="git"):
        feature_dir = tmp_path / "kitty-specs" / f"{feature_number}-test"
        feature_dir.mkdir(parents=True)

        # Create meta.json with VCS lock
        meta = {
            "feature_number": feature_number,
            "slug": f"{feature_number}-test",
            "vcs": vcs_type,
            "created_at": "2026-01-23T16:00:00Z"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        return feature_dir

    return create_feature


@pytest.fixture
def multiple_features_with_vcs(tmp_path):
    """Create multiple features with different VCS settings.

    Returns a factory function that creates a batch of features.
    """
    def create_features(specs):
        """Create features from a list of (feature_number, vcs_type) tuples."""
        features = []
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir(parents=True, exist_ok=True)

        for feature_number, vcs_type in specs:
            feature_dir = kitty_specs / f"{feature_number}-test"
            feature_dir.mkdir(parents=True)

            meta = {
                "feature_number": feature_number,
                "slug": f"{feature_number}-test",
                "vcs": vcs_type,
                "created_at": "2026-01-23T16:00:00Z"
            }
            (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))
            features.append(feature_dir)

        return features

    return create_features
