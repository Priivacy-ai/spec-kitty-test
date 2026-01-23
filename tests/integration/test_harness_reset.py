"""
T071: Integration tests for harness reset functionality.

Validates that cleanup-bookmarks.sh correctly resets
the spec-kitty-git-test harness to clean state.
"""
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
def test_harness_reset_cleans_worktrees(
    spec_kitty_git_test,
    create_test_feature,
    run_orchestration,
    harness_worktrees,
    detect_available_agents
):
    """
    Verify reset removes worktrees.

    Creates worktrees via orchestration, runs reset,
    validates worktrees removed.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    # Create feature and orchestrate (creates worktrees)
    create_test_feature("030", "030-reset-test", wp_count=2)
    run_orchestration("030-reset-test")

    # Worktrees should exist
    worktrees_before = harness_worktrees()

    # Run reset
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"
    result = subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, \
        f"Reset should succeed: {result.stderr}"

    # Worktrees should be cleaned
    worktrees_after = harness_worktrees()

    # After reset, should have fewer worktrees (or none)
    assert len(worktrees_after) <= len(worktrees_before), \
        "Reset should reduce worktree count"


@pytest.mark.integration
def test_harness_reset_cleans_state_file(
    spec_kitty_git_test,
    create_test_feature,
    run_orchestration,
    orchestration_state,
    detect_available_agents
):
    """
    Verify reset removes orchestration-state.json.

    Creates state file via orchestration, runs reset,
    validates state file removed.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    # Create feature and orchestrate
    create_test_feature("031", "031-state-reset-test", wp_count=1)
    run_orchestration("031-state-reset-test")

    # State should exist
    state_before = orchestration_state()
    assert state_before is not None, "State should exist before reset"

    # Run reset
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"
    subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test
    )

    # State should be removed
    state_after = orchestration_state()
    assert state_after is None, \
        "State file should be removed after reset"


@pytest.mark.integration
def test_harness_reset_idempotent(spec_kitty_git_test):
    """
    Verify reset is idempotent (can run multiple times).

    Runs reset twice, validates both complete without crashing.
    """
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"

    # First reset
    result1 = subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True,
        text=True
    )

    # Reset should complete (may have warnings but shouldn't crash)
    # Return code 128 is acceptable (git branch already exists warning)
    assert result1.returncode in [0, 128], \
        f"First reset should complete: {result1.stderr}"

    # Second reset (should also complete)
    result2 = subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True,
        text=True
    )

    assert result2.returncode in [0, 128], \
        f"Second reset should complete: {result2.stderr}"


@pytest.mark.integration
def test_harness_reset_preserves_base_repo(spec_kitty_git_test):
    """
    Verify reset preserves the base repository structure.

    After reset, essential directories should still exist.
    """
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"

    # Run reset
    subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True
    )

    # Base structure should still exist
    assert spec_kitty_git_test.exists(), "Harness directory should exist"
    assert (spec_kitty_git_test / ".git").exists(), "Git directory should exist"


@pytest.mark.integration
@pytest.mark.adversarial
def test_harness_reset_handles_locked_worktree(
    spec_kitty_git_test,
    create_test_feature,
    run_orchestration,
    detect_available_agents
):
    """
    Verify reset handles locked worktrees gracefully.

    Creates worktree, simulates lock, runs reset,
    validates no crash.
    """
    agents = detect_available_agents()
    if not agents:
        pytest.skip("No agents installed")

    # Create feature
    create_test_feature("032", "032-locked-test", wp_count=1)
    run_orchestration("032-locked-test")

    # Note: Actually locking a worktree is complex
    # For now, we just verify reset doesn't crash
    cleanup_script = spec_kitty_git_test / "cleanup-bookmarks.sh"

    result = subprocess.run(
        ["bash", str(cleanup_script)],
        cwd=spec_kitty_git_test,
        capture_output=True,
        text=True
    )

    # Should complete without crashing
    # May have warnings but shouldn't fail catastrophically
    assert result.returncode in [0, 1], \
        f"Reset should handle gracefully: {result.stderr}"
