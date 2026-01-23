"""
Boundary condition tests (WP13: T081).

Tests empty features, single WP, 100+ WPs, and other boundary conditions.
"""
import pytest
from pathlib import Path
import yaml
import re

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    topological_sort,
    detect_cycles,
)


@pytest.fixture
def create_feature(tmp_path):
    """Create feature with specified number of WPs."""
    def _create(wp_count, dependency_graph=None):
        """
        Args:
            wp_count: Number of WPs to create
            dependency_graph: Optional dict mapping WP ID to dependencies
        """
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create spec.md
        (feature_dir / "spec.md").write_text("# Test Feature")

        # Create meta.json
        (feature_dir / "meta.json").write_text('{"vcs": "git"}')

        # Default to linear dependencies if none specified
        if dependency_graph is None:
            dependency_graph = {}
            for i in range(1, wp_count + 1):
                wp_id = f"WP{i:02d}"
                if i == 1:
                    dependency_graph[wp_id] = []
                else:
                    prev_id = f"WP{i-1:02d}"
                    dependency_graph[wp_id] = [prev_id]

        # Create WP files
        for wp_id, deps in dependency_graph.items():
            wp_file = tasks_dir / f"{wp_id}-test.md"
            frontmatter = {
                "work_package_id": wp_id,
                "title": f"Test {wp_id}",
                "dependencies": deps,
                "lane": "planned"
            }
            content = f"---\n{yaml.dump(frontmatter)}---\n\n# {wp_id}\n"
            wp_file.write_text(content)

        return feature_dir

    return _create


@pytest.mark.functional
@pytest.mark.adversarial
class TestEmptyFeature:
    """Test handling of empty features."""

    def test_feature_with_no_wps(self, tmp_path):
        """Feature with no work packages."""
        feature_dir = tmp_path / "empty-feature"
        feature_dir.mkdir()

        (feature_dir / "spec.md").write_text("# Empty Feature")
        (feature_dir / "meta.json").write_text('{"vcs": "git"}')

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Build graph should return empty
        graph = build_dependency_graph(feature_dir)
        assert graph == {}

    def test_topological_sort_empty_graph(self):
        """Topological sort on empty graph."""
        graph = {}
        order = topological_sort(graph)
        assert order == []

    def test_detect_cycles_empty_graph(self):
        """Cycle detection on empty graph."""
        graph = {}
        cycles = detect_cycles(graph)
        assert cycles is None or len(cycles) == 0


@pytest.mark.functional
@pytest.mark.adversarial
class TestSingleWPFeature:
    """Test handling of single WP features."""

    def test_single_wp_no_dependencies(self, create_feature):
        """Feature with single work package, no dependencies."""
        feature_dir = create_feature(1, {"WP01": []})

        graph = build_dependency_graph(feature_dir)
        assert len(graph) == 1
        assert "WP01" in graph
        assert graph["WP01"] == []

    def test_single_wp_topological_sort(self, create_feature):
        """Topological sort with single WP."""
        feature_dir = create_feature(1, {"WP01": []})

        graph = build_dependency_graph(feature_dir)
        order = topological_sort(graph)

        assert order == ["WP01"]


@pytest.mark.functional
@pytest.mark.adversarial
class TestLargeWPCount:
    """Test handling of large WP counts."""

    def test_twenty_wp_linear_chain(self, create_feature):
        """Feature with 20 WPs in linear chain."""
        feature_dir = create_feature(20)

        graph = build_dependency_graph(feature_dir)
        assert len(graph) == 20

        order = topological_sort(graph)
        assert len(order) == 20
        assert order[0] == "WP01"
        assert order[-1] == "WP20"

    def test_fifty_wp_feature(self, create_feature):
        """Feature with 50 WPs."""
        # Create all independent for speed
        deps = {f"WP{i:02d}": [] for i in range(1, 51)}
        feature_dir = create_feature(50, deps)

        graph = build_dependency_graph(feature_dir)
        assert len(graph) == 50

        order = topological_sort(graph)
        assert len(order) == 50

    @pytest.mark.slow
    def test_max_wp_feature(self, create_feature):
        """Feature with 99 WPs (maximum supported, WP01-WP99)."""
        # System only supports 2-digit WP IDs (WP01-WP99)
        # WP100+ would be invalid format
        # Create linear chain
        deps = {}
        for i in range(1, 100):
            wp_id = f"WP{i:02d}"
            if i == 1:
                deps[wp_id] = []
            else:
                prev_id = f"WP{i-1:02d}"
                deps[wp_id] = [prev_id]

        feature_dir = create_feature(99, deps)

        graph = build_dependency_graph(feature_dir)
        # Should handle 99 WPs without timeout or crash
        assert len(graph) == 99

        order = topological_sort(graph)
        assert len(order) == 99
        assert order[0] == "WP01"
        assert order[-1] == "WP99"


@pytest.mark.functional
@pytest.mark.adversarial
class TestWPIDEdgeCases:
    """Test WP ID format edge cases."""

    def test_valid_wp_ids(self):
        """Valid WP ID formats."""
        valid_ids = ["WP01", "WP02", "WP10", "WP99"]
        pattern = re.compile(r"^WP\d{2}$")

        for wp_id in valid_ids:
            assert pattern.match(wp_id), f"{wp_id} should be valid"

    def test_invalid_wp_ids(self):
        """Invalid WP ID formats."""
        invalid_ids = ["WP1", "WP001", "WPXX", "wp01", "WP100", "WP-01"]
        pattern = re.compile(r"^WP\d{2}$")

        for wp_id in invalid_ids:
            assert not pattern.match(wp_id), f"{wp_id} should be invalid"

    def test_wp_id_case_sensitivity(self):
        """WP IDs should be case-sensitive."""
        pattern = re.compile(r"^WP\d{2}$")

        assert pattern.match("WP01")
        assert not pattern.match("wp01")
        assert not pattern.match("Wp01")


@pytest.mark.functional
@pytest.mark.adversarial
class TestDependencyGraphBoundaries:
    """Test dependency graph boundary conditions."""

    def test_all_wps_independent(self, create_feature):
        """All WPs are independent (no dependencies)."""
        deps = {f"WP{i:02d}": [] for i in range(1, 11)}
        feature_dir = create_feature(10, deps)

        graph = build_dependency_graph(feature_dir)
        order = topological_sort(graph)

        # All should be present
        assert len(order) == 10

    def test_all_wps_depend_on_one(self, create_feature):
        """All WPs depend on WP01."""
        deps = {"WP01": []}
        for i in range(2, 11):
            deps[f"WP{i:02d}"] = ["WP01"]

        feature_dir = create_feature(10, deps)

        graph = build_dependency_graph(feature_dir)
        order = topological_sort(graph)

        # WP01 must be first
        assert order[0] == "WP01"

    def test_one_wp_depends_on_all(self, create_feature):
        """One WP depends on all others."""
        deps = {f"WP{i:02d}": [] for i in range(1, 10)}
        deps["WP10"] = [f"WP{i:02d}" for i in range(1, 10)]

        feature_dir = create_feature(10, deps)

        graph = build_dependency_graph(feature_dir)
        order = topological_sort(graph)

        # WP10 must be last
        assert order[-1] == "WP10"
