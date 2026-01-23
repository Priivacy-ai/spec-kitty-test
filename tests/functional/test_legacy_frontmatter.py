"""
Legacy frontmatter compatibility tests (WP13: T088).

Tests backward compatibility with old frontmatter formats
(missing dependency fields, old schema versions).
"""
import pytest
from pathlib import Path
import yaml

from specify_cli.core.dependency_graph import (
    parse_wp_dependencies,
    build_dependency_graph,
)
from specify_cli.frontmatter import read_frontmatter


@pytest.fixture
def create_legacy_wp(tmp_path):
    """Create WP files with legacy (pre-0.11.0) frontmatter."""
    def _create(wp_id, frontmatter_fields, include_dependencies=False):
        """
        Args:
            wp_id: WP identifier
            frontmatter_fields: Dict of frontmatter fields
            include_dependencies: If False, omit dependencies field entirely
        """
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Build frontmatter without dependencies if not included
        fm = {"work_package_id": wp_id}
        fm.update(frontmatter_fields)

        if not include_dependencies and "dependencies" in fm:
            del fm["dependencies"]

        wp_file = tasks_dir / f"{wp_id}-test.md"
        content = f"---\n{yaml.dump(fm)}---\n\n# {wp_id}\n\nContent\n"
        wp_file.write_text(content)

        return wp_file

    return _create


@pytest.mark.functional
@pytest.mark.adversarial
class TestOldFrontmatterWithoutDependencies:
    """Test WP frontmatter without dependencies field (pre-0.11.0 format)."""

    def test_missing_dependencies_field(self, create_legacy_wp):
        """Legacy WP without dependencies field should default to empty."""
        wp_file = create_legacy_wp(
            "WP01",
            {"title": "Old Format WP", "lane": "planned"},
            include_dependencies=False
        )

        deps = parse_wp_dependencies(wp_file)

        assert deps == [], "Missing dependencies should default to empty list"

    def test_legacy_frontmatter_readable(self, create_legacy_wp):
        """Legacy frontmatter should still be readable."""
        wp_file = create_legacy_wp(
            "WP02",
            {"title": "Legacy WP", "lane": "doing", "assignee": "test-user"},
            include_dependencies=False
        )

        frontmatter, content = read_frontmatter(wp_file)

        assert frontmatter["work_package_id"] == "WP02"
        assert frontmatter["title"] == "Legacy WP"
        assert frontmatter.get("dependencies", []) == []


@pytest.mark.functional
@pytest.mark.adversarial
class TestOldSchemaVersions:
    """Test handling of old schema versions."""

    def test_no_schema_version_field(self, create_legacy_wp):
        """WP without schema_version field should work."""
        wp_file = create_legacy_wp(
            "WP03",
            {"title": "No Schema", "lane": "planned"},
            include_dependencies=False
        )

        frontmatter, _ = read_frontmatter(wp_file)

        assert "schema_version" not in frontmatter
        # Should still work
        assert frontmatter["work_package_id"] == "WP03"

    def test_old_schema_version(self, create_legacy_wp, tmp_path):
        """WP with old schema version should be handled."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP04-test.md"
        content = """---
work_package_id: WP04
title: Old Schema
schema_version: "0.10.0"
lane: planned
---

# WP04
"""
        wp_file.write_text(content)

        frontmatter, _ = read_frontmatter(wp_file)

        assert frontmatter["schema_version"] == "0.10.0"


@pytest.mark.functional
@pytest.mark.adversarial
class TestMixedLegacyAndNewFormats:
    """Test features with mix of legacy and new format WPs."""

    def test_mixed_format_feature(self, tmp_path):
        """Feature with both legacy and new format WPs."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        # Legacy format (no dependencies field)
        (tasks_dir / "WP01-legacy.md").write_text("""---
work_package_id: WP01
title: Legacy WP
lane: planned
---
# WP01
""")

        # New format (with dependencies field)
        (tasks_dir / "WP02-new.md").write_text("""---
work_package_id: WP02
title: New WP
dependencies:
  - WP01
lane: planned
---
# WP02
""")

        feature_dir = tasks_dir.parent
        graph = build_dependency_graph(feature_dir)

        assert "WP01" in graph
        assert "WP02" in graph
        assert graph["WP01"] == []  # Legacy defaults to empty
        assert graph["WP02"] == ["WP01"]  # New format preserved


@pytest.mark.functional
@pytest.mark.adversarial
class TestFrontmatterFieldVariations:
    """Test various frontmatter field format variations."""

    def test_subtasks_as_list(self, create_legacy_wp):
        """Subtasks field as YAML list."""
        wp_file = create_legacy_wp(
            "WP05",
            {
                "title": "With Subtasks",
                "subtasks": ["T001", "T002", "T003"],
                "lane": "planned"
            },
            include_dependencies=True
        )

        frontmatter, _ = read_frontmatter(wp_file)

        assert frontmatter["subtasks"] == ["T001", "T002", "T003"]

    def test_history_field_variations(self, tmp_path):
        """History field with different formats."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP06-test.md"
        content = """---
work_package_id: WP06
title: With History
lane: planned
history:
  - timestamp: "2026-01-01T00:00:00Z"
    lane: planned
    agent: system
    action: Created
  - timestamp: "2026-01-02T00:00:00Z"
    lane: doing
    agent: claude
    action: Started
---
# WP06
"""
        wp_file.write_text(content)

        frontmatter, _ = read_frontmatter(wp_file)

        assert len(frontmatter["history"]) == 2
        assert frontmatter["history"][0]["lane"] == "planned"

    def test_optional_fields_missing(self, create_legacy_wp):
        """All optional fields missing should work."""
        wp_file = create_legacy_wp(
            "WP07",
            {"lane": "planned"},  # Only required fields
            include_dependencies=False
        )

        frontmatter, _ = read_frontmatter(wp_file)

        assert frontmatter["work_package_id"] == "WP07"
        assert frontmatter["lane"] == "planned"


@pytest.mark.functional
@pytest.mark.adversarial
class TestDependenciesFieldVariations:
    """Test various ways dependencies field might appear."""

    def test_dependencies_as_yaml_flow_sequence(self, tmp_path):
        """Dependencies as YAML flow sequence [WP01, WP02]."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP08-test.md"
        content = """---
work_package_id: WP08
title: Flow Sequence
dependencies: [WP01, WP02]
lane: planned
---
# WP08
"""
        wp_file.write_text(content)

        deps = parse_wp_dependencies(wp_file)

        assert deps == ["WP01", "WP02"]

    def test_dependencies_as_yaml_block_sequence(self, tmp_path):
        """Dependencies as YAML block sequence."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP09-test.md"
        content = """---
work_package_id: WP09
title: Block Sequence
dependencies:
  - WP01
  - WP02
  - WP03
lane: planned
---
# WP09
"""
        wp_file.write_text(content)

        deps = parse_wp_dependencies(wp_file)

        assert deps == ["WP01", "WP02", "WP03"]

    def test_dependencies_with_quoted_values(self, tmp_path):
        """Dependencies with quoted string values."""
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP10-test.md"
        content = """---
work_package_id: WP10
title: Quoted
dependencies:
  - "WP01"
  - 'WP02'
lane: planned
---
# WP10
"""
        wp_file.write_text(content)

        deps = parse_wp_dependencies(wp_file)

        assert deps == ["WP01", "WP02"]
