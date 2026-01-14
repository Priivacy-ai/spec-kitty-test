"""
Documentation Mission Distribution Tests (v0.12.0)

Validates documentation mission assets load from the installed package without
SPEC_KITTY_TEMPLATE_ROOT or local repo paths.
"""
from __future__ import annotations

import importlib.resources as resources
import os
import shutil
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment without development overrides."""
    env = os.environ.copy()
    for key in list(env.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            env.pop(key, None)
    for key in list(os.environ.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            monkeypatch.delenv(key, raising=False)
    return env


@pytest.fixture
def doc_mission_source():
    """Return filesystem path to documentation mission packaged files."""
    mission = resources.files("specify_cli").joinpath("missions", "documentation")
    with resources.as_file(mission) as mission_path:
        yield Path(mission_path)


@pytest.fixture
def temp_project_with_doc_mission(tmp_path, doc_mission_source):
    """Create a temp project with documentation mission copied into .kittify."""
    project_dir = tmp_path / "project"
    missions_dir = project_dir / ".kittify" / "missions"
    missions_dir.mkdir(parents=True, exist_ok=True)
    dest = missions_dir / "documentation"
    shutil.copytree(doc_mission_source, dest)
    return project_dir


def _load_mission_yaml_from_package() -> dict:
    mission_yaml = resources.files("specify_cli").joinpath(
        "missions", "documentation", "mission.yaml"
    )
    content = mission_yaml.read_text(encoding="utf-8")
    return yaml.safe_load(content) or {}


class TestMissionLoading:
    """Validate documentation mission loads from pip package."""

    def test_documentation_mission_loads_from_package(self, clean_environment):
        """
        Test: Documentation mission is present in package resources.
        """
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ, (
            "Test setup error: Must simulate PyPI user environment\n"
            "DO NOT SHIP v0.12.0"
        )

        mission_yaml = resources.files("specify_cli").joinpath(
            "missions", "documentation", "mission.yaml"
        )
        assert mission_yaml.is_file(), (
            "CRITICAL: Documentation mission.yaml missing from package\n"
            "DO NOT SHIP v0.12.0 - mission not bundled"
        )

    def test_mission_yaml_accessible_and_valid(self, clean_environment):
        """
        Test: mission.yaml accessible and parses correctly.
        """
        try:
            mission_data = _load_mission_yaml_from_package()
        except Exception as exc:
            pytest.fail(
                "CRITICAL: Unable to read mission.yaml from package\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0"
            )

        assert isinstance(mission_data, dict), (
            "Mission config must parse into a mapping\n"
            "DO NOT SHIP v0.12.0 - invalid mission.yaml"
        )
        assert "name" in mission_data, (
            "Mission config missing name field\n"
            "DO NOT SHIP v0.12.0 - invalid mission.yaml"
        )
        assert "workflow" in mission_data, (
            "Mission config missing workflow field\n"
            "DO NOT SHIP v0.12.0 - invalid mission.yaml"
        )

    def test_mission_metadata_correct(self, clean_environment):
        """
        Test: Mission name and version metadata correct.
        """
        mission_data = _load_mission_yaml_from_package()
        assert mission_data.get("name") == "Documentation Kitty", (
            f"Expected mission name 'Documentation Kitty', got {mission_data.get('name')}\n"
            "DO NOT SHIP v0.12.0 - mission metadata mismatch"
        )
        assert mission_data.get("version") == "1.0.0", (
            f"Expected mission version '1.0.0', got {mission_data.get('version')}\n"
            "DO NOT SHIP v0.12.0 - mission metadata mismatch"
        )

    def test_workflow_phases_order(self, clean_environment):
        """
        Test: Workflow phases are present and ordered correctly.
        """
        mission_data = _load_mission_yaml_from_package()
        phases = [phase.get("name") for phase in mission_data.get("workflow", {}).get("phases", [])]
        assert phases == ["discover", "audit", "design", "generate", "validate", "publish"], (
            f"Unexpected workflow phases: {phases}\n"
            "DO NOT SHIP v0.12.0 - workflow mismatch"
        )

    def test_required_artifacts_defined(self, clean_environment):
        """
        Test: Required artifacts defined correctly.
        """
        mission_data = _load_mission_yaml_from_package()
        required = mission_data.get("artifacts", {}).get("required", [])
        expected = {"spec.md", "plan.md", "tasks.md", "gap-analysis.md"}
        assert expected.issubset(set(required)), (
            f"Missing required artifacts: {expected - set(required)}\n"
            "DO NOT SHIP v0.12.0 - artifact definitions broken"
        )

    def test_optional_artifacts_defined(self, clean_environment):
        """
        Test: Optional artifacts defined correctly.
        """
        mission_data = _load_mission_yaml_from_package()
        optional = mission_data.get("artifacts", {}).get("optional", [])
        expected = {
            "divio-templates/",
            "generator-configs/",
            "audit-report.md",
            "research.md",
            "release.md",
        }
        assert expected.issubset(set(optional)), (
            f"Missing optional artifacts: {expected - set(optional)}\n"
            "DO NOT SHIP v0.12.0 - artifact definitions broken"
        )

    def test_workspace_conventions_correct(self, clean_environment):
        """
        Test: Workspace path conventions correct.
        """
        mission_data = _load_mission_yaml_from_package()
        paths = mission_data.get("paths", {})
        assert paths.get("workspace") == "docs/", (
            f"Expected workspace 'docs/', got {paths.get('workspace')}\n"
            "DO NOT SHIP v0.12.0 - path conventions broken"
        )
        assert paths.get("deliverables") == "docs/output/", (
            f"Expected deliverables 'docs/output/', got {paths.get('deliverables')}\n"
            "DO NOT SHIP v0.12.0 - path conventions broken"
        )
        assert paths.get("documentation") == "docs/", (
            f"Expected documentation 'docs/', got {paths.get('documentation')}\n"
            "DO NOT SHIP v0.12.0 - path conventions broken"
        )


class TestCommandTemplates:
    """Validate command templates load from pip package."""

    def test_specify_template_accessible(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: specify command template accessible and non-empty.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        try:
            content = mission.get_command_template("specify").read_text(encoding="utf-8")
        except Exception as exc:
            pytest.fail(
                "CRITICAL: specify template not accessible\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - template missing"
            )
        assert content.strip(), (
            "Specify template should not be empty\n"
            "DO NOT SHIP v0.12.0 - template missing"
        )

    def test_plan_template_accessible(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: plan command template accessible and non-empty.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        content = mission.get_command_template("plan").read_text(encoding="utf-8")
        assert content.strip(), (
            "Plan template should not be empty\n"
            "DO NOT SHIP v0.12.0 - template missing"
        )

    def test_tasks_template_accessible(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: tasks command template accessible and non-empty.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        content = mission.get_command_template("tasks").read_text(encoding="utf-8")
        assert content.strip(), (
            "Tasks template should not be empty\n"
            "DO NOT SHIP v0.12.0 - template missing"
        )

    def test_implement_template_accessible(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: implement command template accessible and non-empty.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        content = mission.get_command_template("implement").read_text(encoding="utf-8")
        assert content.strip(), (
            "Implement template should not be empty\n"
            "DO NOT SHIP v0.12.0 - template missing"
        )

    def test_review_template_accessible(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: review command template accessible and non-empty.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        content = mission.get_command_template("review").read_text(encoding="utf-8")
        assert content.strip(), (
            "Review template should not be empty\n"
            "DO NOT SHIP v0.12.0 - template missing"
        )

    def test_templates_have_expected_structure(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: All command templates have expected structure.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        for name in ["specify", "plan", "tasks", "implement", "review"]:
            content = mission.get_command_template(name).read_text(encoding="utf-8")
            assert content.startswith("---"), (
                f"{name} template missing YAML frontmatter\n"
                "DO NOT SHIP v0.12.0 - template malformed"
            )
            assert "#" in content, (
                f"{name} template missing markdown headings\n"
                "DO NOT SHIP v0.12.0 - template malformed"
            )
            assert len(content) > 200, (
                f"{name} template suspiciously short ({len(content)} chars)\n"
                "DO NOT SHIP v0.12.0 - template malformed"
            )


class TestTemplatePackaging:
    """Validate template packaging and loading mechanism."""

    def test_templates_load_via_importlib(self, clean_environment):
        """
        Test: Templates load via importlib.resources from package.
        """
        template = resources.files("specify_cli").joinpath(
            "missions", "documentation", "command-templates", "specify.md"
        )
        try:
            content = template.read_text(encoding="utf-8")
        except Exception as exc:
            pytest.fail(
                "CRITICAL: specify template not readable via importlib.resources\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )
        assert content.strip(), (
            "Template content empty when loaded via importlib.resources\n"
            "DO NOT SHIP v0.12.0 - packaging broken"
        )

    def test_no_template_path_leakage(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: Templates do not leak local repo paths or SPEC_KITTY_TEMPLATE_ROOT.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        forbidden = [
            "/Users/",
            "/home/",
            "C:\\",
            str(Path.home()),
            "SPEC_KITTY_TEMPLATE_ROOT",
        ]
        template_paths = [
            mission.get_command_template(name)
            for name in ["specify", "plan", "tasks", "implement", "review"]
        ]
        divio_dir = mission.templates_dir / "divio"
        template_paths.extend(sorted(divio_dir.glob("*.md")))

        for template_path in template_paths:
            content = template_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in content, (
                    f"Template contains forbidden path: {pattern}\n"
                    f"Template: {template_path}\n"
                    "DO NOT SHIP v0.12.0 - path leakage"
                )


class TestMissionRegistry:
    """Validate mission registry and retrieval."""

    def test_mission_registered_in_registry(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: Mission registered in discover_missions registry.
        """
        from specify_cli.mission import discover_missions

        missions = discover_missions(temp_project_with_doc_mission)
        assert "documentation" in missions, (
            f"Documentation mission not discovered: {list(missions.keys())}\n"
            "DO NOT SHIP v0.12.0 - mission registry broken"
        )

    def test_mission_metadata_correct_in_registry(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: Mission metadata from registry is correct.
        """
        from specify_cli.mission import discover_missions

        mission, _source = discover_missions(temp_project_with_doc_mission)["documentation"]
        assert mission.name == "Documentation Kitty", (
            f"Expected mission name 'Documentation Kitty', got {mission.name}\n"
            "DO NOT SHIP v0.12.0 - mission metadata mismatch"
        )
        assert mission.domain == "other", (
            f"Expected mission domain 'other', got {mission.domain}\n"
            "DO NOT SHIP v0.12.0 - mission metadata mismatch"
        )
        assert mission.version == "1.0.0", (
            f"Expected mission version '1.0.0', got {mission.version}\n"
            "DO NOT SHIP v0.12.0 - mission metadata mismatch"
        )

    def test_get_mission_by_name_returns_valid_mission(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: get_mission_by_name returns a valid Mission object.
        """
        from specify_cli.mission import Mission, get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        assert isinstance(mission, Mission), (
            "get_mission_by_name should return Mission instance\n"
            "DO NOT SHIP v0.12.0 - mission loading broken"
        )

    def test_mission_validation_passes_pydantic(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: Mission config validates via Pydantic model.
        """
        from specify_cli.mission import MissionConfig, get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        assert isinstance(mission.config, MissionConfig), (
            "Mission config should be validated MissionConfig model\n"
            "DO NOT SHIP v0.12.0 - mission validation broken"
        )

    def test_all_divio_templates_present(self, clean_environment, temp_project_with_doc_mission):
        """
        Test: All Divio templates present in documentation mission.
        """
        from specify_cli.mission import get_mission_by_name

        mission = get_mission_by_name(
            "documentation", temp_project_with_doc_mission / ".kittify"
        )
        divio_dir = mission.templates_dir / "divio"
        expected = {
            "tutorial-template.md",
            "howto-template.md",
            "reference-template.md",
            "explanation-template.md",
        }
        found = {p.name for p in divio_dir.glob("*.md")}
        assert expected.issubset(found), (
            f"Missing Divio templates: {expected - found}\n"
            "DO NOT SHIP v0.12.0 - templates not bundled"
        )
        for template_name in expected:
            content = (divio_dir / template_name).read_text(encoding="utf-8")
            assert content.strip(), (
                f"{template_name} should not be empty\n"
                "DO NOT SHIP v0.12.0 - templates not bundled"
            )
