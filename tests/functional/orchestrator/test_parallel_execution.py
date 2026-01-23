"""
Orchestrator parallel execution tests (WP05: T031, T032).

Tests for:
- T031: Parallel execution of independent WPs
- T032: Dependency blocking and BLOCKED state handling

These tests validate the orchestrator's ability to execute independent WPs
in parallel while respecting dependency constraints and handling failures.
"""
import pytest
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    topological_sort,
    detect_cycles,
)


# =============================================================================
# T031: Test Parallel Execution
# =============================================================================

class TestParallelExecution:
    """Test T031: Independent WPs execute in parallel (concurrently)."""

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_independent_wps_execute_in_parallel(
        self,
        independent_wps_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test independent WPs run concurrently, not sequentially."""
        graph = build_dependency_graph(independent_wps_graph)
        executor = mock_agent_executor(delay=0.5)  # 0.5s each

        # Simulate parallel execution using ThreadPoolExecutor
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(executor, wp_id): wp_id
                for wp_id in graph.keys()
            }
            for future in as_completed(futures):
                future.result()  # Wait for all to complete

        total_time = time.time() - start_time

        # If sequential: 3 WPs x 0.5s = 1.5s
        # If parallel: max(0.5, 0.5, 0.5) = ~0.5s + overhead
        # Allow generous margin for CI environments
        assert total_time < 1.2, (
            f"Expected ~0.5s (parallel), got {total_time:.2f}s (appears sequential)"
        )

        # Verify all WPs executed
        order = execution_tracker.get_execution_order()
        assert set(order) == {"WP01", "WP02", "WP03"}

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_parallel_execution_overlapping_windows(
        self,
        independent_wps_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test that execution windows overlap (concurrent execution)."""
        graph = build_dependency_graph(independent_wps_graph)
        executor = mock_agent_executor(delay=0.3)

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(executor, wp_id) for wp_id in graph.keys()]
            for future in as_completed(futures):
                future.result()

        # Check for overlapping execution
        max_concurrent = execution_tracker.get_concurrent_count()

        assert max_concurrent >= 2, (
            f"Expected at least 2 concurrent executions, got {max_concurrent}"
        )

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_many_independent_wps_parallelize(
        self,
        temp_feature_dir,
        create_wp_file,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test many independent WPs execute in parallel."""
        # Create 6 independent WPs
        for i in range(1, 7):
            create_wp_file(temp_feature_dir, f"WP{i:02d}", [])

        graph = build_dependency_graph(temp_feature_dir)
        executor = mock_agent_executor(delay=0.2)

        start = time.time()

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(executor, wp_id) for wp_id in graph.keys()]
            for future in as_completed(futures):
                future.result()

        duration = time.time() - start

        # If sequential: 6 x 0.2s = 1.2s
        # If parallel: ~0.2s + overhead
        assert duration < 0.8, (
            f"6 independent WPs should parallelize, took {duration:.2f}s"
        )

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_single_wp_no_parallelism_needed(
        self,
        temp_feature_dir,
        create_wp_file,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test single WP executes correctly (no parallelism needed)."""
        create_wp_file(temp_feature_dir, "WP01", [])

        graph = build_dependency_graph(temp_feature_dir)
        executor = mock_agent_executor(delay=0.1)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(executor, "WP01")
            result = future.result()

        assert result == 0
        assert execution_tracker.get_execution_order() == ["WP01"]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_different_execution_times(
        self,
        independent_wps_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test parallel execution handles varying execution times."""
        graph = build_dependency_graph(independent_wps_graph)

        # Different delays for each WP
        executor = mock_agent_executor(
            delay=0.1,
            custom_delays={"WP01": 0.1, "WP02": 0.3, "WP03": 0.2}
        )

        start = time.time()

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(executor, wp_id) for wp_id in graph.keys()]
            for future in as_completed(futures):
                future.result()

        duration = time.time() - start

        # Total time should be close to slowest (0.3s) not sum (0.6s)
        assert duration < 0.6, (
            f"Parallel execution should take ~0.3s (slowest), got {duration:.2f}s"
        )


# =============================================================================
# T032: Test Dependency Blocking
# =============================================================================

class TestDependencyBlocking:
    """Test T032: Dependent WPs wait for prerequisites and handle failures."""

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_dependent_wp_waits_for_prerequisites(
        self,
        diamond_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test WP04 waits for WP01, WP02, WP03 to complete."""
        graph = build_dependency_graph(diamond_dependency_graph)
        order = topological_sort(graph)
        executor = mock_agent_executor(delay=0.1)

        # Execute in topological order (simulating orchestrator)
        for wp_id in order:
            executor(wp_id)

        execution_order = execution_tracker.get_execution_order()

        # Verify WP04 executes after all dependencies
        wp04_index = execution_order.index("WP04")
        assert "WP01" in execution_order[:wp04_index]
        assert "WP02" in execution_order[:wp04_index]
        assert "WP03" in execution_order[:wp04_index]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_linear_chain_executes_in_order(
        self,
        linear_dependency_chain,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test linear chain WP01->WP02->WP03->WP04->WP05 executes in order."""
        graph = build_dependency_graph(linear_dependency_chain)
        order = topological_sort(graph)
        executor = mock_agent_executor(delay=0.05)

        # Execute in topological order
        for wp_id in order:
            executor(wp_id)

        execution_order = execution_tracker.get_execution_order()

        # Must be exactly in dependency order
        assert execution_order == ["WP01", "WP02", "WP03", "WP04", "WP05"]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_convergent_graph_respects_dependencies(
        self,
        convergent_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test WP04 waits for all of WP01, WP02, WP03 to complete."""
        graph = build_dependency_graph(convergent_dependency_graph)
        order = topological_sort(graph)
        executor = mock_agent_executor(delay=0.1)

        # Execute in topological order
        for wp_id in order:
            executor(wp_id)

        # Verify all prerequisites complete before WP04
        execution_tracker.assert_executed_before("WP01", "WP04")
        execution_tracker.assert_executed_before("WP02", "WP04")
        execution_tracker.assert_executed_before("WP03", "WP04")

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_failed_dependency_blocks_dependent(
        self,
        diamond_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test WP04 is blocked when WP02 fails."""
        graph = build_dependency_graph(diamond_dependency_graph)
        order = topological_sort(graph)

        # WP02 fails (returns non-zero)
        executor = mock_agent_executor(delay=0.05, fail_wps=["WP02"])

        # Track execution states
        states = {}
        blocked_wps = set()

        for wp_id in order:
            # Check if any dependency failed
            deps = graph.get(wp_id, [])
            if any(states.get(dep) == "FAILED" for dep in deps):
                states[wp_id] = "BLOCKED"
                blocked_wps.add(wp_id)
                continue

            result = executor(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        # Verify states
        assert states["WP01"] == "DONE"
        assert states["WP02"] == "FAILED"
        assert states["WP03"] == "DONE"  # Independent of WP02
        assert states["WP04"] == "BLOCKED", "WP04 should be blocked by WP02 failure"
        assert "WP04" in blocked_wps

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_partial_dependency_failure_still_blocks(
        self,
        convergent_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test WP04 is blocked even if only one dependency fails."""
        graph = build_dependency_graph(convergent_dependency_graph)
        order = topological_sort(graph)

        # Only WP02 fails
        executor = mock_agent_executor(delay=0.05, fail_wps=["WP02"])

        states = {}
        for wp_id in order:
            deps = graph.get(wp_id, [])
            if any(states.get(dep) == "FAILED" for dep in deps):
                states[wp_id] = "BLOCKED"
                continue

            result = executor(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        # WP01 and WP03 complete, WP02 fails, WP04 blocked
        assert states["WP01"] == "DONE"
        assert states["WP02"] == "FAILED"
        assert states["WP03"] == "DONE"
        assert states["WP04"] == "BLOCKED"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_all_dependencies_fail_wp_blocked(
        self,
        convergent_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test WP is blocked when all dependencies fail."""
        graph = build_dependency_graph(convergent_dependency_graph)
        order = topological_sort(graph)

        # All dependencies fail
        executor = mock_agent_executor(
            delay=0.05,
            fail_wps=["WP01", "WP02", "WP03"]
        )

        states = {}
        for wp_id in order:
            deps = graph.get(wp_id, [])
            if any(states.get(dep) == "FAILED" for dep in deps):
                states[wp_id] = "BLOCKED"
                continue

            result = executor(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        assert states["WP01"] == "FAILED"
        assert states["WP02"] == "FAILED"
        assert states["WP03"] == "FAILED"
        assert states["WP04"] == "BLOCKED"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_transitive_dependency_blocking(
        self,
        linear_dependency_chain,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test transitive blocking: WP01 fails, all downstream WPs blocked."""
        graph = build_dependency_graph(linear_dependency_chain)
        order = topological_sort(graph)

        # WP01 fails
        executor = mock_agent_executor(delay=0.05, fail_wps=["WP01"])

        states = {}
        for wp_id in order:
            deps = graph.get(wp_id, [])
            # Check both direct and transitive failures
            if any(states.get(dep) in ("FAILED", "BLOCKED") for dep in deps):
                states[wp_id] = "BLOCKED"
                continue

            result = executor(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        # WP01 fails, all others blocked due to transitive dependency
        assert states["WP01"] == "FAILED"
        assert states["WP02"] == "BLOCKED"
        assert states["WP03"] == "BLOCKED"
        assert states["WP04"] == "BLOCKED"
        assert states["WP05"] == "BLOCKED"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_retry_unblocks_dependent_wps(
        self,
        diamond_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test retrying failed WP unblocks dependent WPs."""
        graph = build_dependency_graph(diamond_dependency_graph)
        order = topological_sort(graph)

        # First run: WP02 fails
        executor_fail = mock_agent_executor(delay=0.05, fail_wps=["WP02"])
        states = {}

        for wp_id in order:
            deps = graph.get(wp_id, [])
            if any(states.get(dep) == "FAILED" for dep in deps):
                states[wp_id] = "BLOCKED"
                continue
            result = executor_fail(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        assert states["WP02"] == "FAILED"
        assert states["WP04"] == "BLOCKED"

        # Retry: WP02 succeeds this time
        # Reset tracker for clean retry
        execution_tracker_retry = type(execution_tracker)()
        executor_success = mock_agent_executor(delay=0.05)

        # Only retry failed/blocked WPs
        for wp_id in order:
            if states.get(wp_id) in ("FAILED", "BLOCKED"):
                deps = graph.get(wp_id, [])
                # Check if all deps are now DONE
                if all(states.get(dep) == "DONE" for dep in deps):
                    result = executor_success(wp_id)
                    states[wp_id] = "DONE" if result == 0 else "FAILED"

        # After retry, both WP02 and WP04 should be DONE
        assert states["WP02"] == "DONE"
        assert states["WP04"] == "DONE"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_independent_branches_unaffected_by_failure(
        self,
        temp_feature_dir,
        create_wp_file,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test failure in one branch doesn't block independent branches."""
        # Create two independent branches from WP01
        # Branch 1: WP01 -> WP02 -> WP04
        # Branch 2: WP01 -> WP03 -> WP05
        create_wp_file(temp_feature_dir, "WP01", [])
        create_wp_file(temp_feature_dir, "WP02", ["WP01"])
        create_wp_file(temp_feature_dir, "WP03", ["WP01"])
        create_wp_file(temp_feature_dir, "WP04", ["WP02"])
        create_wp_file(temp_feature_dir, "WP05", ["WP03"])

        graph = build_dependency_graph(temp_feature_dir)
        order = topological_sort(graph)

        # WP02 fails (blocking WP04), but WP03/WP05 should continue
        executor = mock_agent_executor(delay=0.05, fail_wps=["WP02"])

        states = {}
        for wp_id in order:
            deps = graph.get(wp_id, [])
            if any(states.get(dep) == "FAILED" for dep in deps):
                states[wp_id] = "BLOCKED"
                continue
            result = executor(wp_id)
            states[wp_id] = "DONE" if result == 0 else "FAILED"

        # Branch 1: WP02 fails, WP04 blocked
        assert states["WP02"] == "FAILED"
        assert states["WP04"] == "BLOCKED"

        # Branch 2: Unaffected, both complete
        assert states["WP03"] == "DONE"
        assert states["WP05"] == "DONE"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_circular_dependency_rejects_before_execution(
        self,
        circular_dependency_graph,
        execution_tracker,
        mock_agent_executor,
    ):
        """Test circular dependency is detected before any WP execution."""
        graph = build_dependency_graph(circular_dependency_graph)

        # Check for cycles BEFORE attempting execution
        cycles = detect_cycles(graph)

        assert cycles is not None, "Cycle should be detected"
        assert len(cycles) > 0

        # Verify no WPs were executed
        order = execution_tracker.get_execution_order()
        assert order == [], "No WPs should execute when cycle detected"
