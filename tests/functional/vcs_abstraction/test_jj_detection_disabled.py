"""
T044: JJ Detection Disabled Tests

Verifies that is_jj_available() returns False even when jj binary is on PATH
and executable. This validates the jj rollback is complete.
"""
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.mark.functional
@pytest.mark.vcs
class TestJJDetectionAlwaysReturnsFalse:
    """Test that jj detection always returns False regardless of installation."""

    def test_jj_detection_returns_false_when_jj_installed(self):
        """JJ detection is disabled even when jj is on PATH."""
        with patch("shutil.which") as mock_which:
            # Mock jj binary existing at /usr/local/bin/jj
            mock_which.return_value = "/usr/local/bin/jj"

            # In current spec-kitty, jj detection is hardcoded to return False
            # The detection function should return False regardless of which()
            from specify_cli.core.vcs.detection import is_jj_available

            # Detection should still return False (disabled)
            result = is_jj_available()
            assert result is False, (
                "is_jj_available() should return False even when jj binary exists"
            )

    def test_jj_detection_disabled_with_real_jj(self):
        """JJ detection disabled regardless of real jj installation."""
        from specify_cli.core.vcs.detection import is_jj_available

        # Check if jj actually exists on system
        jj_path = shutil.which("jj")

        # Whether jj is installed or not, detection should return False
        result = is_jj_available()
        assert result is False, (
            "is_jj_available() should return False regardless of jj installation"
        )

        if jj_path:
            # If jj exists, this proves detection is truly disabled
            assert Path(jj_path).exists(), "jj binary found but not accessible"
            # Yet detection still returns False
            assert is_jj_available() is False

    @pytest.mark.adversarial
    def test_jj_detection_disabled_with_broken_jj(self):
        """JJ detection disabled even when jj binary is broken."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/jj"
            # Make jj --version fail
            mock_run.side_effect = FileNotFoundError("jj not found")

            from specify_cli.core.vcs.detection import is_jj_available

            # Detection should still be False (disabled, not error)
            result = is_jj_available()
            assert result is False, (
                "is_jj_available() should return False even with broken jj binary"
            )


@pytest.mark.functional
@pytest.mark.vcs
class TestJJDetectionEdgeCases:
    """Edge cases for jj detection being disabled."""

    def test_jj_detection_returns_false_multiple_times(self):
        """Repeated calls to is_jj_available() consistently return False."""
        from specify_cli.core.vcs.detection import is_jj_available

        # Call multiple times
        for i in range(10):
            result = is_jj_available()
            assert result is False, f"Call {i+1}: is_jj_available() returned True"

    @pytest.mark.adversarial
    def test_jj_detection_with_jj_version_available(self):
        """Detection returns False even if jj --version succeeds."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/jj"
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=b"jj 0.23.0\n",
                stderr=b""
            )

            from specify_cli.core.vcs.detection import is_jj_available

            # Even though jj --version would succeed, detection is disabled
            result = is_jj_available()
            assert result is False

    def test_jj_detection_does_not_call_subprocess(self):
        """Detection is hardcoded False - shouldn't even run jj commands."""
        with patch("subprocess.run") as mock_run:
            from specify_cli.core.vcs.detection import is_jj_available

            result = is_jj_available()
            assert result is False

            # Check if subprocess.run was called with jj
            jj_calls = [
                call for call in mock_run.call_args_list
                if call and call[0] and isinstance(call[0][0], list)
                and len(call[0][0]) > 0 and call[0][0][0] == "jj"
            ]
            # Should have zero jj subprocess calls (detection is hardcoded)
            assert len(jj_calls) == 0, (
                f"jj subprocess was called despite disabled detection: {jj_calls}"
            )
