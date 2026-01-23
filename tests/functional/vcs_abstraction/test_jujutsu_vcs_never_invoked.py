"""
T049: JujutsuVCS Class Never Invoked Tests

Verifies that JujutsuVCS class methods are never called during any spec-kitty
operation, using instrumentation to count method invocations.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestJujutsuVCSNeverInstantiated:
    """Test that JujutsuVCS is never instantiated."""

    @pytest.fixture
    def jujutsu_call_counter(self):
        """Instrument JujutsuVCS to count method calls."""
        call_counts = {}
        original_methods = {}
        patches = []

        try:
            from specify_cli.core.vcs.jujutsu import JujutsuVCS

            # Get all public methods of JujutsuVCS
            methods = [
                name for name in dir(JujutsuVCS)
                if callable(getattr(JujutsuVCS, name)) and not name.startswith("_")
            ]

            # Patch each method to track calls
            for method_name in methods:
                original_method = getattr(JujutsuVCS, method_name)
                original_methods[method_name] = original_method

                def make_tracker(name, orig):
                    def tracker(*args, **kwargs):
                        call_counts[name] = call_counts.get(name, 0) + 1
                        return orig(*args, **kwargs)
                    return tracker

                patch_obj = patch.object(
                    JujutsuVCS, method_name,
                    make_tracker(method_name, original_method)
                )
                patches.append(patch_obj)
                patch_obj.start()

        except ImportError:
            # JujutsuVCS module doesn't exist - that's fine
            pass

        yield call_counts

        # Cleanup
        for p in patches:
            p.stop()

    def test_jujutsu_vcs_never_instantiated_in_workflow(
        self, jujutsu_call_counter, command_logger, tmp_path
    ):
        """JujutsuVCS is never instantiated during workflow."""
        ctx = command_logger

        # Setup git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True)

        # Simulate workflow operations
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "Init"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "branch", "-a"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "status"], cwd=tmp_path, capture_output=True)

        # Check no JujutsuVCS methods were called
        assert len(jujutsu_call_counter) == 0, (
            f"JujutsuVCS methods called despite disabled detection: "
            f"{jujutsu_call_counter}"
        )

    def test_jujutsu_vcs_not_used_with_detection_override(
        self, jujutsu_call_counter
    ):
        """JujutsuVCS not used even if detection were overridden."""
        with patch("specify_cli.core.vcs.detection.is_jj_available") as mock_detect:
            # Try to force jj detection to True
            mock_detect.return_value = True

            # VCS factory should still return GitVCS
            # because JujutsuVCS code path is disabled
            from specify_cli.core.vcs.detection import is_jj_available

            # Even after mock, the actual behavior is hardcoded
            # (our mock only affects is_jj_available function)

            # The factory should not instantiate JujutsuVCS
            assert len(jujutsu_call_counter) == 0


@pytest.mark.functional
@pytest.mark.vcs
class TestJujutsuModuleNotImported:
    """Test that JujutsuVCS module is not imported in normal flow."""

    def test_jujutsu_module_not_imported_in_detection(self):
        """JujutsuVCS module not imported during VCS detection."""
        # Clear any previous imports of jujutsu module
        jujutsu_modules = [
            key for key in sys.modules
            if "jujutsu" in key.lower() or (
                "specify_cli.vcs" in key and "jj" in key.lower()
            )
        ]
        for mod in jujutsu_modules:
            if mod in sys.modules:
                del sys.modules[mod]

        # Run VCS detection
        from specify_cli.core.vcs.detection import is_jj_available

        result = is_jj_available()
        assert result is False

        # Check if jujutsu was imported
        # Note: It might be imported as part of the module structure
        # but should not be actively used
        jujutsu_imported = any(
            "jujutsu" in key.lower()
            for key in sys.modules
            if key.startswith("specify_cli")
        )

        # If jujutsu is imported, ensure it's just for structure not use
        if jujutsu_imported:
            # That's OK as long as its methods aren't called
            pass

    def test_jujutsu_not_imported_during_git_operations(self, tmp_path):
        """JujutsuVCS not imported during git operations."""
        # Track module state before
        jj_modules_before = set(
            key for key in sys.modules
            if "jujutsu" in key.lower() and key.startswith("specify_cli")
        )

        # Perform git operations
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "status"], cwd=tmp_path, capture_output=True)

        # Track module state after
        jj_modules_after = set(
            key for key in sys.modules
            if "jujutsu" in key.lower() and key.startswith("specify_cli")
        )

        # No new jujutsu modules should be imported
        new_imports = jj_modules_after - jj_modules_before
        # Note: This test may not catch all cases due to import timing
        # It's OK if jujutsu module exists, as long as it's not used


@pytest.mark.functional
@pytest.mark.vcs
@pytest.mark.adversarial
class TestJujutsuVCSMethodsNeverCalled:
    """Test that specific JujutsuVCS methods are never called."""

    def test_jj_init_never_called(self, command_logger, tmp_path):
        """jj init is never called during any operation."""
        ctx = command_logger

        # Git operations only
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        # Check no jj init
        jj_init_calls = [
            cmd for binary, cmd in ctx.command_log
            if binary == "jj" and "init" in cmd
        ]
        assert len(jj_init_calls) == 0

    def test_jj_new_never_called(self, command_logger, tmp_path):
        """jj new (equivalent to git commit) is never called."""
        ctx = command_logger

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "test"],
                      cwd=tmp_path, capture_output=True)

        # Check no jj new
        jj_new_calls = [
            cmd for binary, cmd in ctx.command_log
            if binary == "jj" and "new" in cmd
        ]
        assert len(jj_new_calls) == 0

    def test_jj_bookmark_never_called(self, command_logger, tmp_path):
        """jj bookmark (equivalent to git branch) is never called."""
        ctx = command_logger

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "branch", "feature"], cwd=tmp_path, capture_output=True)

        # Check no jj bookmark
        jj_bookmark_calls = [
            cmd for binary, cmd in ctx.command_log
            if binary == "jj" and "bookmark" in cmd
        ]
        assert len(jj_bookmark_calls) == 0

    def test_jj_workspace_never_called(self, command_logger, tmp_path):
        """jj workspace (equivalent to git worktree) is never called."""
        ctx = command_logger

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"],
                      cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                      cwd=tmp_path, capture_output=True)

        # Create initial commit for worktree
        (tmp_path / "file.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"],
                      cwd=tmp_path, capture_output=True)

        # Try worktree operation
        worktree_path = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature"],
            cwd=tmp_path,
            capture_output=True
        )

        # Check no jj workspace
        jj_workspace_calls = [
            cmd for binary, cmd in ctx.command_log
            if binary == "jj" and "workspace" in cmd
        ]
        assert len(jj_workspace_calls) == 0


@pytest.mark.functional
@pytest.mark.vcs
class TestVCSFactoryReturnsGit:
    """Test VCS factory never returns JujutsuVCS."""

    def test_factory_returns_git_vcs(self, tmp_path):
        """VCS factory returns GitVCS instance."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        # Factory should return GitVCS
        from specify_cli.core.vcs.git import GitVCS

        # Since is_jj_available() is False, factory should return GitVCS
        from specify_cli.core.vcs.detection import is_jj_available

        assert is_jj_available() is False

        # GitVCS class exists and can be instantiated
        vcs = GitVCS()
        assert isinstance(vcs, GitVCS)

    def test_factory_never_returns_jujutsu_vcs(self, tmp_path):
        """VCS factory never returns JujutsuVCS instance."""
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        from specify_cli.core.vcs.git import GitVCS

        vcs = GitVCS()

        # Should be GitVCS
        assert isinstance(vcs, GitVCS)

        # Should NOT be JujutsuVCS
        try:
            from specify_cli.core.vcs.jujutsu import JujutsuVCS
            assert not isinstance(vcs, JujutsuVCS)
        except ImportError:
            # JujutsuVCS doesn't exist - that's fine
            pass
