"""
Orchestrator dependency graph tests (WP05: T028, T029, T030).

Tests for:
- T028: Dependency parsing from WP frontmatter
- T029: Topological sort execution order
- T030: Circular dependency detection

These tests validate the core dependency graph functionality used by
the orchestrator to determine WP execution order.
"""
import pytest
from pathlib import Path
import yaml

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    topological_sort,
    parse_wp_dependencies,
    validate_dependencies,
    get_dependents,
)


# =============================================================================
# T028: Parse Dependencies from WP Frontmatter
# =============================================================================

class TestDependencyParsing:
    """Test T028: Dependency graph parsing from WP frontmatter."""

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_parse_dependencies_from_frontmatter(
        self, temp_feature_dir, create_wp_file
    ):
        """Test dependency graph parsing from WP frontmatter."""
        # Create feature with 4 WPs: WP01 (no deps), WP02 (depends on WP01),
        # WP03 (depends on WP01), WP04 (depends on WP02, WP03)
        create_wp_file(temp_feature_dir, "WP01", [])
        create_wp_file(temp_feature_dir, "WP02", ["WP01"])
        create_wp_file(temp_feature_dir, "WP03", ["WP01"])
        create_wp_file(temp_feature_dir, "WP04", ["WP02", "WP03"])

        # Parse dependency graph
        graph = build_dependency_graph(temp_feature_dir)

        # Validate graph structure
        assert graph["WP01"] == []
        assert graph["WP02"] == ["WP01"]
        assert graph["WP03"] == ["WP01"]
        assert set(graph["WP04"]) == {"WP02", "WP03"}

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_empty_dependencies_array(self, temp_feature_dir, create_wp_file):
        """Test WP with empty dependencies array is handled correctly."""
        create_wp_file(temp_feature_dir, "WP01", [])

        graph = build_dependency_graph(temp_feature_dir)

        assert "WP01" in graph
        assert graph["WP01"] == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_missing_dependencies_field_defaults_to_empty(self, temp_feature_dir):
        """Test WP without dependencies field defaults to empty list."""
        tasks_dir = temp_feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        # Create WP without dependencies field
        wp_file = tasks_dir / "WP01-test.md"
        content = """---
work_package_id: "WP01"
title: "Test WP"
lane: "planned"
---

# WP01

No dependencies field in frontmatter.
"""
        wp_file.write_text(content)

        graph = build_dependency_graph(temp_feature_dir)

        assert "WP01" in graph
        assert graph["WP01"] == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_parse_wp_dependencies_single_file(self, temp_feature_dir, create_wp_file):
        """Test parsing dependencies from a single WP file."""
        wp_file = create_wp_file(temp_feature_dir, "WP02", ["WP01"])

        deps = parse_wp_dependencies(wp_file)

        assert deps == ["WP01"]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_build_graph_from_tasks_directory(self, diamond_dependency_graph):
        """Test building graph from a feature directory with tasks subdirectory."""
        graph = build_dependency_graph(diamond_dependency_graph)

        assert len(graph) == 4
        assert "WP01" in graph
        assert "WP02" in graph
        assert "WP03" in graph
        assert "WP04" in graph

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_empty_feature_returns_empty_graph(self, temp_feature_dir):
        """Test empty feature directory returns empty graph."""
        # tasks dir exists but is empty
        tasks_dir = temp_feature_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)

        graph = build_dependency_graph(temp_feature_dir)

        assert graph == {}

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_nonexistent_tasks_directory(self, temp_feature_dir):
        """Test feature without tasks directory returns empty graph."""
        # Remove tasks dir
        tasks_dir = temp_feature_dir / "tasks"
        if tasks_dir.exists():
            tasks_dir.rmdir()

        graph = build_dependency_graph(temp_feature_dir)

        assert graph == {}

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_get_dependents_returns_reverse_lookup(self, diamond_dependency_graph):
        """Test get_dependents returns WPs that depend on given WP."""
        graph = build_dependency_graph(diamond_dependency_graph)

        # WP01 is depended on by WP02 and WP03
        dependents = get_dependents("WP01", graph)
        assert set(dependents) == {"WP02", "WP03"}

        # WP02 is depended on by WP04
        dependents = get_dependents("WP02", graph)
        assert "WP04" in dependents

        # WP04 has no dependents
        dependents = get_dependents("WP04", graph)
        assert dependents == []


# =============================================================================
# T029: Topological Sort Execution Order
# =============================================================================

class TestTopologicalSort:
    """Test T029: Topological sort respects dependency order."""

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_respects_dependencies(self, diamond_dependency_graph):
        """Test WPs execute in dependency order."""
        graph = build_dependency_graph(diamond_dependency_graph)

        # Get execution order
        order = topological_sort(graph)

        # Get indices
        wp01_index = order.index("WP01")
        wp02_index = order.index("WP02")
        wp03_index = order.index("WP03")
        wp04_index = order.index("WP04")

        # Validate WP01 comes before WP02 and WP03
        assert wp01_index < wp02_index, "WP02 depends on WP01"
        assert wp01_index < wp03_index, "WP03 depends on WP01"
        assert wp02_index < wp04_index, "WP04 depends on WP02"
        assert wp03_index < wp04_index, "WP04 depends on WP03"

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_linear_chain(self, linear_dependency_chain):
        """Test topological sort on linear dependency chain."""
        graph = build_dependency_graph(linear_dependency_chain)

        order = topological_sort(graph)

        # Linear chain must be exactly in order
        assert order == ["WP01", "WP02", "WP03", "WP04", "WP05"]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_independent_wps(self, independent_wps_graph):
        """Test topological sort with independent WPs (no dependencies)."""
        graph = build_dependency_graph(independent_wps_graph)

        order = topological_sort(graph)

        # All WPs should be present (order may vary due to no deps)
        assert set(order) == {"WP01", "WP02", "WP03"}
        assert len(order) == 3

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_convergent_graph(self, convergent_dependency_graph):
        """Test topological sort where multiple WPs converge to one."""
        graph = build_dependency_graph(convergent_dependency_graph)

        order = topological_sort(graph)

        # WP04 must come last (after WP01, WP02, WP03)
        wp04_index = order.index("WP04")
        assert wp04_index == 3, "WP04 depends on all others, must be last"

        # WP01, WP02, WP03 can be in any order among themselves
        independent_wps = {"WP01", "WP02", "WP03"}
        first_three = set(order[:3])
        assert first_three == independent_wps

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_empty_graph(self):
        """Test topological sort on empty graph returns empty list."""
        graph = {}

        order = topological_sort(graph)

        assert order == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_single_node(self, temp_feature_dir, create_wp_file):
        """Test topological sort with single WP."""
        create_wp_file(temp_feature_dir, "WP01", [])
        graph = build_dependency_graph(temp_feature_dir)

        order = topological_sort(graph)

        assert order == ["WP01"]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_topological_sort_raises_on_cycle(self, circular_dependency_graph):
        """Test topological sort raises error on cyclic graph."""
        graph = build_dependency_graph(circular_dependency_graph)

        with pytest.raises(ValueError) as exc_info:
            topological_sort(graph)

        assert "cycle" in str(exc_info.value).lower()


# =============================================================================
# T030: Circular Dependency Detection
# =============================================================================

class TestCircularDependencyDetection:
    """Test T030: Circular dependency detection with clear error messages."""

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_detect_simple_two_node_cycle(self, temp_feature_dir, create_wp_file):
        """Test detection of simple 2-node cycle: WP01 <-> WP02."""
        create_wp_file(temp_feature_dir, "WP01", ["WP02"])
        create_wp_file(temp_feature_dir, "WP02", ["WP01"])

        graph = build_dependency_graph(temp_feature_dir)
        cycles = detect_cycles(graph)

        # Cycle should be found
        assert cycles is not None
        assert len(cycles) > 0

        # Both nodes should appear in cycle
        first_cycle = cycles[0]
        assert "WP01" in first_cycle
        assert "WP02" in first_cycle

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_detect_three_node_cycle(self, circular_dependency_graph):
        """Test detection of 3-node cycle: WP01 -> WP02 -> WP03 -> WP01."""
        graph = build_dependency_graph(circular_dependency_graph)
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) > 0

        first_cycle = cycles[0]
        # All three nodes should be in the cycle
        assert "WP01" in first_cycle
        assert "WP02" in first_cycle
        assert "WP03" in first_cycle

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_detect_self_referential_dependency(self, temp_feature_dir, create_wp_file):
        """Test detection of self-referential dependency: WP01 -> WP01."""
        create_wp_file(temp_feature_dir, "WP01", ["WP01"])

        graph = build_dependency_graph(temp_feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) > 0
        # Self-reference cycle contains WP01
        assert "WP01" in cycles[0]

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_no_cycle_in_linear_chain(self, linear_dependency_chain):
        """Test that linear chain is correctly detected as acyclic."""
        graph = build_dependency_graph(linear_dependency_chain)
        cycles = detect_cycles(graph)

        assert cycles is None or cycles == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_no_cycle_in_diamond_graph(self, diamond_dependency_graph):
        """Test that diamond graph (DAG) is correctly detected as acyclic."""
        graph = build_dependency_graph(diamond_dependency_graph)
        cycles = detect_cycles(graph)

        assert cycles is None or cycles == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_cycle_in_subgraph(self, temp_feature_dir, create_wp_file):
        """Test cycle detection when cycle is in part of larger graph."""
        # Acyclic part: WP01 -> WP02 -> WP03
        create_wp_file(temp_feature_dir, "WP01", [])
        create_wp_file(temp_feature_dir, "WP02", ["WP01"])
        create_wp_file(temp_feature_dir, "WP03", ["WP02"])

        # Cyclic part: WP04 -> WP05 -> WP06 -> WP04
        create_wp_file(temp_feature_dir, "WP04", ["WP06"])
        create_wp_file(temp_feature_dir, "WP05", ["WP04"])
        create_wp_file(temp_feature_dir, "WP06", ["WP05"])

        # Connect them
        create_wp_file(temp_feature_dir, "WP07", ["WP03", "WP04"])

        graph = build_dependency_graph(temp_feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) > 0

        # Cycle should involve WP04, WP05, WP06
        first_cycle = cycles[0]
        assert any(node in first_cycle for node in ["WP04", "WP05", "WP06"])

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_validate_dependencies_detects_self_reference(
        self, diamond_dependency_graph
    ):
        """Test validate_dependencies catches self-referential dependency."""
        graph = build_dependency_graph(diamond_dependency_graph)

        is_valid, errors = validate_dependencies("WP01", ["WP01"], graph)

        assert is_valid is False
        assert any("self" in err.lower() for err in errors)

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_validate_dependencies_detects_missing_dependency(
        self, diamond_dependency_graph
    ):
        """Test validate_dependencies catches reference to non-existent WP."""
        graph = build_dependency_graph(diamond_dependency_graph)

        is_valid, errors = validate_dependencies("WP01", ["WP99"], graph)

        assert is_valid is False
        assert any("WP99" in err for err in errors)

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_validate_dependencies_detects_invalid_format(
        self, diamond_dependency_graph
    ):
        """Test validate_dependencies catches invalid WP ID format."""
        graph = build_dependency_graph(diamond_dependency_graph)

        is_valid, errors = validate_dependencies("WP01", ["invalid_id"], graph)

        assert is_valid is False
        assert any("format" in err.lower() for err in errors)

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_validate_dependencies_accepts_valid_deps(self, diamond_dependency_graph):
        """Test validate_dependencies accepts valid dependencies."""
        graph = build_dependency_graph(diamond_dependency_graph)

        # WP04 depends on WP02 and WP03 - this is valid
        is_valid, errors = validate_dependencies("WP04", ["WP02", "WP03"], graph)

        assert is_valid is True
        assert errors == []

    @pytest.mark.functional
    @pytest.mark.orchestrator
    def test_long_cycle_detection(self, temp_feature_dir, create_wp_file):
        """Test detection of long cycle: WP01 -> ... -> WP05 -> WP01."""
        create_wp_file(temp_feature_dir, "WP01", ["WP05"])
        create_wp_file(temp_feature_dir, "WP02", ["WP01"])
        create_wp_file(temp_feature_dir, "WP03", ["WP02"])
        create_wp_file(temp_feature_dir, "WP04", ["WP03"])
        create_wp_file(temp_feature_dir, "WP05", ["WP04"])

        graph = build_dependency_graph(temp_feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        # All nodes should be involved in the cycle
        first_cycle = cycles[0]
        for wp_id in ["WP01", "WP02", "WP03", "WP04", "WP05"]:
            assert wp_id in first_cycle
