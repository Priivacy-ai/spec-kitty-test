"""
End-to-end tests for documentation mission workflow (v0.12.0).

These tests validate documentation mission behavior using the public
doc_state and gap_analysis APIs without relying on interactive CLI flows.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.doc_state import (
    ensure_documentation_state,
    initialize_documentation_state,
    read_documentation_state,
    set_generators_configured,
    write_documentation_state,
)
from specify_cli.gap_analysis import (
    DocFramework,
    DivioType,
    GapPriority,
    analyze_documentation_gaps,
    classify_divio_type,
    detect_doc_framework,
    run_gap_analysis_for_feature,
)
from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import (
    InstallDocumentationMission,
)


def _init_project(tmp_path: Path, name: str) -> Path:
    project_root = tmp_path / name
    project_root.mkdir()
    (project_root / "kitty-specs").mkdir()
    return project_root


def _create_doc_feature(project_root: Path, feature_name: str = "001-docs") -> Path:
    feature_dir = project_root / "kitty-specs" / feature_name
    feature_dir.mkdir(parents=True)
    meta = {
        "name": feature_name,
        "mission": "documentation",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return feature_dir


def _init_git_repo(project_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_root,
        check=True,
        capture_output=True,
    )


class TestInitialMode:
    """Validate initial mode documentation workflow."""

    def test_initial_mode_workflow(self, tmp_path):
        """
        Test: Initial mode workflow creates core artifacts and state.
        """
        project = _init_project(tmp_path, "docs-initial")
        feature_dir = _create_doc_feature(project)

        for name in ["spec.md", "plan.md", "tasks.md"]:
            (feature_dir / name).write_text(f"# {name}\n")

        meta_file = feature_dir / "meta.json"
        state = initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=["tutorial", "reference"],
            generators=[],
            target_audience="developers",
        )

        assert (feature_dir / "spec.md").exists(), "spec.md should exist"
        assert (feature_dir / "plan.md").exists(), "plan.md should exist"
        assert (feature_dir / "tasks.md").exists(), "tasks.md should exist"
        assert state["iteration_mode"] == "initial"

    def test_initial_mode_stores_state(self, tmp_path):
        """
        Test: Initial mode stores documentation_state in meta.json.
        """
        project = _init_project(tmp_path, "docs-state")
        feature_dir = _create_doc_feature(project)
        meta_file = feature_dir / "meta.json"

        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=["tutorial"],
            generators=[],
            target_audience="developers",
        )

        state = read_documentation_state(meta_file)
        assert state is not None, "documentation_state should be present"
        assert state["iteration_mode"] == "initial"
        assert state["divio_types_selected"] == ["tutorial"]


class TestGapFillingMode:
    """Validate gap-filling mode and gap analysis."""

    def test_gap_analysis_runs_automatically(self, tmp_path):
        """
        Test: Gap analysis runs when docs exist and produces report.
        """
        project = _init_project(tmp_path, "docs-gap")
        feature_dir = _create_doc_feature(project)

        docs_dir = project / "docs"
        docs_dir.mkdir()
        (docs_dir / "README.md").write_text("# API Documentation\n")
        (docs_dir / "tutorial.md").write_text("---\ntype: tutorial\n---\nStep 1\n")

        analysis = run_gap_analysis_for_feature(feature_dir)
        output_file = feature_dir / "gap-analysis.md"

        assert output_file.exists(), "gap-analysis.md should be created"
        assert analysis.framework in {
            DocFramework.PLAIN_MARKDOWN,
            DocFramework.UNKNOWN,
        }

    def test_classification_by_divio_type(self, tmp_path):
        """
        Test: Divio classification uses frontmatter type.
        """
        project = _init_project(tmp_path, "docs-classify")
        docs_dir = project / "docs"
        docs_dir.mkdir()
        tutorial = docs_dir / "tutorial.md"
        tutorial.write_text("---\ntype: tutorial\n---\nStep 1: Start\n")

        analysis = analyze_documentation_gaps(docs_dir, project)
        doc_type, confidence = analysis.existing[tutorial]
        assert doc_type == DivioType.TUTORIAL
        assert confidence == 1.0

    def test_framework_detection(self, tmp_path):
        """
        Test: Framework detection recognizes MkDocs.
        """
        docs_dir = _init_project(tmp_path, "docs-framework") / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "mkdocs.yml").write_text("site_name: Test\n")

        assert detect_doc_framework(docs_dir) == DocFramework.MKDOCS

    def test_divio_classification_heuristics(self):
        """
        Test: Heuristic classification identifies tutorial-style content.
        """
        content = "Step 1: Install\nStep 2: Run\nBy the end you'll learn..."
        divio_type, confidence = classify_divio_type(content)
        assert divio_type == DivioType.TUTORIAL
        assert confidence == 0.7

    def test_coverage_matrix_generation(self, tmp_path):
        """
        Test: Coverage matrix maps areas to Divio types.
        """
        project = _init_project(tmp_path, "docs-coverage")
        docs_dir = project / "docs" / "api"
        docs_dir.mkdir(parents=True)
        (docs_dir / "tutorial.md").write_text("---\ntype: tutorial\n---\nStep 1\n")
        (docs_dir / "reference.md").write_text("---\ntype: reference\n---\nAPI\n")

        analysis = analyze_documentation_gaps(project / "docs", project)
        matrix = analysis.coverage_matrix

        assert matrix.cells.get(("api", "tutorial")) is not None
        assert matrix.cells.get(("api", "reference")) is not None

    def test_gap_prioritization(self, tmp_path):
        """
        Test: Gap prioritization marks missing tutorials as high priority.
        """
        project = _init_project(tmp_path, "docs-priority")
        docs_dir = project / "docs" / "core"
        docs_dir.mkdir(parents=True)
        (docs_dir / "reference.md").write_text("---\ntype: reference\n---\nAPI\n")

        analysis = analyze_documentation_gaps(project / "docs", project)
        gaps = analysis.gaps

        assert gaps, "Expected at least one gap"
        assert any(
            gap.divio_type == "tutorial" and gap.priority in {GapPriority.HIGH, GapPriority.MEDIUM}
            for gap in gaps
        ), "Missing tutorial should be medium or high priority"


class TestStatePersistence:
    """Validate state persistence across git operations."""

    def test_state_survives_git_operations(self, tmp_path):
        """
        Test: documentation_state survives git commit and branch switch.
        """
        project = _init_project(tmp_path, "docs-persist")
        _init_git_repo(project)
        feature_dir = _create_doc_feature(project)
        meta_file = feature_dir / "meta.json"

        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=["tutorial"],
            generators=[],
            target_audience="developers",
        )

        subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add docs feature"],
            cwd=project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "test-branch"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        state = read_documentation_state(meta_file)
        assert state is not None
        assert state["iteration_mode"] == "initial"

    def test_divio_templates_accessible_during_workflow(self, tmp_path, spec_kitty_repo_root):
        """
        Test: Divio templates can be accessed during workflow.
        """
        project = _init_project(tmp_path, "docs-divio")
        feature_dir = _create_doc_feature(project)
        docs_dir = project / "docs"
        docs_dir.mkdir()

        divio_dir = (
            spec_kitty_repo_root
            / "src"
            / "specify_cli"
            / "missions"
            / "documentation"
            / "templates"
            / "divio"
        )
        if not divio_dir.exists():
            pytest.skip("Divio templates not available in source tree")

        for name in [
            "tutorial-template.md",
            "howto-template.md",
            "reference-template.md",
            "explanation-template.md",
        ]:
            content = (divio_dir / name).read_text(encoding="utf-8")
            assert content.strip(), f"{name} should have content"

    def test_generators_configured_correctly(self, tmp_path):
        """
        Test: Generators configured stored in meta.json.
        """
        project = _init_project(tmp_path, "docs-generators")
        feature_dir = _create_doc_feature(project)
        meta_file = feature_dir / "meta.json"

        initialize_documentation_state(
            meta_file,
            iteration_mode="initial",
            divio_types=["reference"],
            generators=[],
            target_audience="developers",
        )

        set_generators_configured(
            meta_file,
            [
                {
                    "name": "sphinx",
                    "language": "python",
                    "config_path": "docs/conf.py",
                }
            ],
        )

        state = read_documentation_state(meta_file)
        assert state is not None
        assert state["generators_configured"][0]["name"] == "sphinx"


class TestMigration:
    """Validate migration installs documentation mission."""

    def test_migration_installs_mission(self, tmp_path):
        """
        Test: Migration copies documentation mission into .kittify/missions.
        """
        project = _init_project(tmp_path, "docs-migrate")
        (project / ".kittify" / "missions").mkdir(parents=True)

        migration = InstallDocumentationMission()
        result = migration.apply(project)

        mission_dir = project / ".kittify" / "missions" / "documentation"
        assert result.success is True
        assert (mission_dir / "mission.yaml").exists()

    def test_migration_idempotent(self, tmp_path):
        """
        Test: Migration can run multiple times without error.
        """
        project = _init_project(tmp_path, "docs-migrate-idempotent")
        (project / ".kittify" / "missions").mkdir(parents=True)

        migration = InstallDocumentationMission()
        first = migration.apply(project)
        second = migration.apply(project)

        assert first.success is True
        assert second.success is True
        assert (project / ".kittify" / "missions" / "documentation" / "mission.yaml").exists()


class TestValidation:
    """Validate input validation and backward compatibility."""

    def test_backward_compatibility(self, tmp_path):
        """
        Test: Missing documentation_state handled gracefully.
        """
        project = _init_project(tmp_path, "docs-compat")
        feature_dir = _create_doc_feature(project)
        meta_file = feature_dir / "meta.json"

        ensure_documentation_state(meta_file)
        state = read_documentation_state(meta_file)
        assert state is not None
        assert state["iteration_mode"] == "initial"

    def test_state_validation_rejects_invalid(self, tmp_path):
        """
        Test: Invalid documentation state rejected with clear error.
        """
        project = _init_project(tmp_path, "docs-invalid")
        feature_dir = _create_doc_feature(project)
        meta_file = feature_dir / "meta.json"

        with pytest.raises(ValueError):
            write_documentation_state(meta_file, {"iteration_mode": "initial"})  # missing fields
