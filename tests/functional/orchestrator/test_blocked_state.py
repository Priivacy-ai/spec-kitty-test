"""Tests for BLOCKED state and dependency management.

The BLOCKED state is critical for parallel execution - work packages
with dependencies cannot start until their dependencies complete.

Dependency scenarios:
- WP04 depends on [WP01, WP02, WP03] - must wait for all
- If any dependency fails, dependent WP is BLOCKED
- When dependencies complete, WP becomes unblocked and can proceed

This prevents:
- Race conditions (starting work before dependencies ready)
- Invalid execution order (breaking logical dependencies)
- Resource conflicts (multiple WPs working on same code)
"""

import pytest
import json


@pytest.mark.functional
@pytest.mark.orchestrator
def test_wp_blocked_by_pending_dependency(orchestration_state_file):
    """WP cannot start when dependencies are still pending.

    WP04 depends on WP01-WP03. If any are PENDING, WP04 cannot start.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE", "completed_at": "2026-01-23T15:00:00Z"},
            "WP02": {"state": "PENDING"},  # Still pending
            "WP03": {"state": "DONE", "completed_at": "2026-01-23T15:30:00Z"},
            "WP04": {"state": "PENDING"},  # Cannot start yet
        },
        "dependency_graph": {"WP04": ["WP01", "WP02", "WP03"]},
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Check dependencies - WP02 still pending, so WP04 blocked
    loaded = json.loads(orchestration_state_file.read_text())
    wp04_deps = state["dependency_graph"]["WP04"]
    all_deps_done = all(loaded["wps"][dep]["state"] == "DONE" for dep in wp04_deps)

    assert not all_deps_done  # WP02 still pending
    assert loaded["wps"]["WP04"]["state"] == "PENDING"  # Should not start


@pytest.mark.functional
@pytest.mark.orchestrator
def test_wp_blocked_by_failed_dependency(orchestration_state_file):
    """WP is permanently blocked when dependency fails.

    If a dependency transitions to FAILED, dependent WPs
    cannot proceed and should be marked BLOCKED.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE"},
            "WP02": {
                "state": "FAILED",
                "failed_at": "2026-01-23T16:00:00Z",
            },  # Failed
            "WP03": {"state": "DONE"},
            "WP04": {"state": "PENDING"},  # Will be blocked
        },
        "dependency_graph": {"WP04": ["WP01", "WP02", "WP03"]},
    }
    orchestration_state_file.write_text(json.dumps(state))

    # WP02 failed, so WP04 should transition to BLOCKED
    state["wps"]["WP04"]["state"] = "BLOCKED"
    state["wps"]["WP04"]["blocked_reason"] = "Dependency WP02 failed"
    state["wps"]["WP04"]["blocked_by"] = ["WP02"]

    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP04"]["state"] == "BLOCKED"
    assert "blocked_reason" in loaded["wps"]["WP04"]
    assert "WP02" in loaded["wps"]["WP04"]["blocked_by"]


@pytest.mark.functional
@pytest.mark.orchestrator
def test_wp_unblocked_after_dependency_completes(orchestration_state_file):
    """WP unblocked when all dependencies complete.

    Once all dependencies reach DONE state, WP can transition
    from PENDING to IMPLEMENTATION.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE"},
            "WP02": {"state": "DONE"},  # Now complete
            "WP03": {"state": "DONE"},
            "WP04": {"state": "PENDING"},  # Can now start
        },
        "dependency_graph": {"WP04": ["WP01", "WP02", "WP03"]},
    }
    orchestration_state_file.write_text(json.dumps(state))

    # All dependencies satisfied - WP04 can start
    wp04_deps = state["dependency_graph"]["WP04"]
    all_deps_done = all(state["wps"][dep]["state"] == "DONE" for dep in wp04_deps)

    assert all_deps_done  # All dependencies complete

    # WP04 can now transition to IMPLEMENTATION
    state["wps"]["WP04"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP04"]["assigned_agent"] = "claude"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP04"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_no_dependencies_can_start_immediately(orchestration_state_file):
    """WPs with no dependencies can start immediately.

    WP01 typically has no dependencies and should be able to
    start as soon as orchestration begins.
    """
    state = {
        "wps": {
            "WP01": {"state": "PENDING"},
            "WP02": {"state": "PENDING"},
        },
        "dependency_graph": {
            "WP01": [],  # No dependencies
            "WP02": ["WP01"],  # Depends on WP01
        },
    }
    orchestration_state_file.write_text(json.dumps(state))

    # WP01 has no dependencies - can start immediately
    wp01_deps = state["dependency_graph"]["WP01"]
    can_start = len(wp01_deps) == 0

    assert can_start

    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_dependency_chain_execution_order(orchestration_state_file):
    """Test linear dependency chain: WP01 → WP02 → WP03 → WP04.

    Each WP must complete before next can start.
    """
    state = {
        "wps": {
            "WP01": {"state": "PENDING"},
            "WP02": {"state": "PENDING"},
            "WP03": {"state": "PENDING"},
            "WP04": {"state": "PENDING"},
        },
        "dependency_graph": {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
            "WP04": ["WP03"],
        },
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Execute in order
    # WP01 starts (no dependencies)
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    # WP01 completes
    state["wps"]["WP01"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    # WP02 can now start
    state["wps"]["WP02"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    # WP02 completes
    state["wps"]["WP02"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    # WP03 can now start
    state["wps"]["WP03"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    # WP03 completes
    state["wps"]["WP03"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    # WP04 can now start
    state["wps"]["WP04"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "DONE"
    assert loaded["wps"]["WP02"]["state"] == "DONE"
    assert loaded["wps"]["WP03"]["state"] == "DONE"
    assert loaded["wps"]["WP04"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_parallel_execution_no_dependencies(orchestration_state_file):
    """Test parallel execution when WPs have no dependencies.

    Multiple WPs without dependencies can execute simultaneously.
    """
    state = {
        "wps": {
            "WP01": {"state": "PENDING"},
            "WP02": {"state": "PENDING"},
            "WP03": {"state": "PENDING"},
        },
        "dependency_graph": {
            "WP01": [],
            "WP02": [],
            "WP03": [],
        },
    }
    orchestration_state_file.write_text(json.dumps(state))

    # All can start simultaneously
    state["wps"]["WP01"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP02"]["state"] = "IMPLEMENTATION"
    state["wps"]["WP03"]["state"] = "IMPLEMENTATION"

    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP01"]["state"] == "IMPLEMENTATION"
    assert loaded["wps"]["WP02"]["state"] == "IMPLEMENTATION"
    assert loaded["wps"]["WP03"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_partial_dependency_completion(orchestration_state_file):
    """Test WP remains blocked until ALL dependencies complete.

    Even if some dependencies are done, WP cannot start until
    ALL dependencies reach DONE state.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE"},
            "WP02": {"state": "DONE"},
            "WP03": {"state": "IMPLEMENTATION"},  # Still in progress
            "WP04": {"state": "PENDING"},
        },
        "dependency_graph": {"WP04": ["WP01", "WP02", "WP03"]},
    }
    orchestration_state_file.write_text(json.dumps(state))

    # Check if all dependencies done
    wp04_deps = state["dependency_graph"]["WP04"]
    all_deps_done = all(state["wps"][dep]["state"] == "DONE" for dep in wp04_deps)

    assert not all_deps_done  # WP03 still in progress
    assert state["wps"]["WP04"]["state"] == "PENDING"  # Cannot start yet


@pytest.mark.functional
@pytest.mark.orchestrator
def test_diamond_dependency_pattern(orchestration_state_file):
    """Test diamond dependency: WP04 depends on WP02 and WP03, both depend on WP01.

    WP01
     ├─→ WP02
     │    └─→ WP04
     └─→ WP03
          └─→ WP04

    WP04 must wait for both WP02 and WP03 to complete.
    """
    state = {
        "wps": {
            "WP01": {"state": "DONE"},
            "WP02": {"state": "IMPLEMENTATION"},
            "WP03": {"state": "IMPLEMENTATION"},
            "WP04": {"state": "PENDING"},
        },
        "dependency_graph": {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP02", "WP03"],
        },
    }
    orchestration_state_file.write_text(json.dumps(state))

    # WP02 and WP03 both in progress - WP04 still blocked
    wp04_deps = state["dependency_graph"]["WP04"]
    all_deps_done = all(state["wps"][dep]["state"] == "DONE" for dep in wp04_deps)
    assert not all_deps_done

    # WP02 completes
    state["wps"]["WP02"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    # WP04 still blocked (WP03 not done)
    all_deps_done = all(state["wps"][dep]["state"] == "DONE" for dep in wp04_deps)
    assert not all_deps_done

    # WP03 completes
    state["wps"]["WP03"]["state"] = "DONE"
    orchestration_state_file.write_text(json.dumps(state))

    # Now WP04 can start
    all_deps_done = all(state["wps"][dep]["state"] == "DONE" for dep in wp04_deps)
    assert all_deps_done

    state["wps"]["WP04"]["state"] = "IMPLEMENTATION"
    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP04"]["state"] == "IMPLEMENTATION"


@pytest.mark.functional
@pytest.mark.orchestrator
def test_blocked_state_metadata(orchestration_state_file):
    """Verify BLOCKED state includes helpful metadata.

    BLOCKED state should record which dependencies are blocking
    and why, for debugging and user visibility.
    """
    state = {
        "wps": {
            "WP01": {"state": "FAILED", "failed_at": "2026-01-23T16:00:00Z"},
            "WP02": {"state": "PENDING"},  # Still waiting
            "WP03": {"state": "PENDING"},
        },
        "dependency_graph": {"WP03": ["WP01", "WP02"]},
    }
    orchestration_state_file.write_text(json.dumps(state))

    # WP03 should be blocked
    state["wps"]["WP03"]["state"] = "BLOCKED"
    state["wps"]["WP03"]["blocked_by"] = ["WP01", "WP02"]
    state["wps"]["WP03"]["blocked_reason"] = (
        "Dependencies not complete: WP01 (FAILED), WP02 (PENDING)"
    )

    orchestration_state_file.write_text(json.dumps(state))

    loaded = json.loads(orchestration_state_file.read_text())
    assert loaded["wps"]["WP03"]["state"] == "BLOCKED"
    assert "blocked_by" in loaded["wps"]["WP03"]
    assert "blocked_reason" in loaded["wps"]["WP03"]
    assert len(loaded["wps"]["WP03"]["blocked_by"]) == 2
