"""
Comprehensive circular dependency detection tests (WP13: T079).

Tests circular dependency detection with clear error messages.
"""
import pytest
from pathlib import Path
import yaml

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    topological_sort,
    validate_dependencies,
)


@pytest.fixture
def create_feature_with_deps(tmp_path):
    """Create feature with specified dependency graph."""
    def _create(dep_graph):
        """
        Args:
            dep_graph: dict mapping WP ID to list of dependencies
        """
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        for wp_id, deps in dep_graph.items():
            wp_file = tasks_dir / f"{wp_id}-test.md"
            frontmatter = {
                "work_package_id": wp_id,
                "title": f"Test {wp_id}",
                "dependencies": deps,
                "lane": "planned"
            }
            content = f"---\n{yaml.dump(frontmatter)}---\n\n# {wp_id}\n"
            wp_file.write_text(content)

        return tasks_dir.parent

    return _create


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestSimpleCircularDependency:
    """Test simple 2-node circular dependency."""

    def test_two_node_cycle(self, create_feature_with_deps):
        """Simple 2-node cycle: WP01 <-> WP02."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP02"],
            "WP02": ["WP01"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) > 0

        # Both nodes should appear in cycle
        first_cycle = cycles[0]
        assert "WP01" in first_cycle
        assert "WP02" in first_cycle

    def test_topological_sort_fails_on_cycle(self, create_feature_with_deps):
        """Topological sort should fail with cycle."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP02"],
            "WP02": ["WP01"]
        })

        graph = build_dependency_graph(feature_dir)

        with pytest.raises(ValueError, match="cycle"):
            topological_sort(graph)


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestLongCircularDependency:
    """Test long circular dependency chains."""

    def test_three_node_cycle(self, create_feature_with_deps):
        """3-node cycle: WP01 -> WP02 -> WP03 -> WP01."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP03"],  # WP01 depends on WP03
            "WP02": ["WP01"],  # WP02 depends on WP01
            "WP03": ["WP02"]   # WP03 depends on WP02 -> CYCLE
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        first_cycle = cycles[0]

        # All three should be in cycle
        assert "WP01" in first_cycle
        assert "WP02" in first_cycle
        assert "WP03" in first_cycle

    def test_four_node_cycle(self, create_feature_with_deps):
        """4-node cycle: WP01 -> WP02 -> WP03 -> WP04 -> WP01."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP04"],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
            "WP04": ["WP03"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None

    def test_five_node_cycle(self, create_feature_with_deps):
        """5-node cycle: WP01 -> WP02 -> WP03 -> WP04 -> WP05 -> WP01."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP05"],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
            "WP04": ["WP03"],
            "WP05": ["WP04"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestSelfDependency:
    """Test self-referential dependencies."""

    def test_self_dependency_detected(self, create_feature_with_deps):
        """Self-dependency: WP01 depends on WP01."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP01"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert "WP01" in cycles[0]

    def test_validate_catches_self_dependency(self, create_feature_with_deps):
        """validate_dependencies should catch self-reference."""
        feature_dir = create_feature_with_deps({
            "WP01": [],
            "WP02": []
        })

        graph = build_dependency_graph(feature_dir)

        is_valid, errors = validate_dependencies("WP01", ["WP01"], graph)

        assert not is_valid
        assert any("self" in err.lower() for err in errors)


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestMultipleIndependentCycles:
    """Test multiple independent cycles in same feature."""

    def test_two_independent_cycles(self, create_feature_with_deps):
        """Two independent cycles: WP01<->WP02 and WP03<->WP04."""
        feature_dir = create_feature_with_deps({
            "WP01": ["WP02"],
            "WP02": ["WP01"],
            "WP03": ["WP04"],
            "WP04": ["WP03"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        # Should find at least one cycle
        assert len(cycles) >= 1

    def test_cycle_plus_acyclic_subgraph(self, create_feature_with_deps):
        """One cycle plus separate acyclic subgraph."""
        feature_dir = create_feature_with_deps({
            # Cyclic part
            "WP01": ["WP02"],
            "WP02": ["WP01"],
            # Acyclic part
            "WP03": [],
            "WP04": ["WP03"],
            "WP05": ["WP04"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is not None
        # Cycle should only involve WP01, WP02
        first_cycle = cycles[0]
        assert "WP03" not in first_cycle
        assert "WP04" not in first_cycle
        assert "WP05" not in first_cycle


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestNoCircularDependency:
    """Test that non-cycles are not detected as cycles."""

    def test_diamond_not_cycle(self, create_feature_with_deps):
        """Diamond pattern is NOT a cycle."""
        feature_dir = create_feature_with_deps({
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP02", "WP03"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        # Should be None or empty - no cycles
        assert cycles is None or len(cycles) == 0

    def test_linear_chain_not_cycle(self, create_feature_with_deps):
        """Linear chain is NOT a cycle."""
        feature_dir = create_feature_with_deps({
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
            "WP04": ["WP03"],
            "WP05": ["WP04"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is None or len(cycles) == 0

    def test_convergent_not_cycle(self, create_feature_with_deps):
        """Convergent graph (multiple inputs to one) is NOT a cycle."""
        feature_dir = create_feature_with_deps({
            "WP01": [],
            "WP02": [],
            "WP03": [],
            "WP04": ["WP01", "WP02", "WP03"]
        })

        graph = build_dependency_graph(feature_dir)
        cycles = detect_cycles(graph)

        assert cycles is None or len(cycles) == 0
