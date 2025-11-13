"""
Category 4: Dashboard & State Tests

Tests state detection, work package tracking, and kanban lane structure.

Test Coverage:
1. Artifact Detection (3 tests)
   - Initial state after init (no features yet)
   - State after spec created
   - State after full workflow progression

2. Workflow Status Detection (2 tests)
   - Workflow stages detected correctly (specify → plan → tasks → implement)
   - Pending/complete/in_progress states accurate

3. Kanban Lane Structure (2 tests)
   - Lane directories created correctly (planned, doing, for_review, done)
   - Work package counting across lanes
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestArtifactDetection:
    """Test artifact detection after project init and feature creation."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initial_state_after_init(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Initial project state has no features, correct infrastructure"""
        project_name = "test_initial_state"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Check infrastructure exists
        kittify_dir = project_path / '.kittify'
        assert kittify_dir.exists(), ".kittify directory should exist"

        # Check no features exist yet
        specs_dir = project_path / 'kitty-specs'
        assert not specs_dir.exists() or len(list(specs_dir.iterdir())) == 0, \
            "No features should exist after init"

        # Check mission is activated
        active_mission = kittify_dir / 'active-mission'
        assert active_mission.exists() or active_mission.is_symlink(), \
            "Active mission should be set"

    def test_state_detection_with_artifacts(self, temp_project_dir, spec_kitty_repo_root):
        """Test: State detection recognizes created artifacts"""
        project_name = "test_with_artifacts"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create a feature manually to test state detection
        feature_dir = project_path / 'kitty-specs' / '001-test-feature'
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create spec.md
        spec_file = feature_dir / 'spec.md'
        spec_file.write_text("# Test Feature\n\nTest specification content")

        # Test that scanner can detect the artifacts
        from specify_cli.dashboard import get_feature_artifacts

        artifacts = get_feature_artifacts(feature_dir)

        assert artifacts['spec'] == True, "Should detect spec.md exists"
        assert artifacts['plan'] == False, "Should detect plan.md doesn't exist"
        assert artifacts['tasks'] == False, "Should detect tasks.md doesn't exist"
        assert artifacts['kanban'] == False, "Should detect tasks/ directory doesn't exist"

        # Now create plan.md
        plan_file = feature_dir / 'plan.md'
        plan_file.write_text("# Implementation Plan\n\nTest plan content")

        artifacts = get_feature_artifacts(feature_dir)
        assert artifacts['spec'] == True, "Should still detect spec.md"
        assert artifacts['plan'] == True, "Should now detect plan.md exists"

    def test_artifact_types_detected(self, temp_project_dir, spec_kitty_repo_root):
        """Test: All artifact types are correctly detected"""
        project_name = "test_artifact_types"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature with various artifacts
        feature_dir = project_path / 'kitty-specs' / '002-full-feature'
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create all possible artifacts
        (feature_dir / 'spec.md').write_text("# Spec")
        (feature_dir / 'plan.md').write_text("# Plan")
        (feature_dir / 'tasks.md').write_text("# Tasks")
        (feature_dir / 'research.md').write_text("# Research")
        (feature_dir / 'quickstart.md').write_text("# Quickstart")
        (feature_dir / 'data-model.md').write_text("# Data Model")

        contracts_dir = feature_dir / 'contracts'
        contracts_dir.mkdir()
        (contracts_dir / 'api.md').write_text("# API Contract")

        checklists_dir = feature_dir / 'checklists'
        checklists_dir.mkdir()
        (checklists_dir / 'requirements.md').write_text("# Requirements Checklist")

        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir()
        (tasks_dir / 'planned').mkdir()

        # Test artifact detection
        from specify_cli.dashboard import get_feature_artifacts

        artifacts = get_feature_artifacts(feature_dir)

        assert artifacts['spec'] == True, "Should detect spec.md"
        assert artifacts['plan'] == True, "Should detect plan.md"
        assert artifacts['tasks'] == True, "Should detect tasks.md"
        assert artifacts['research'] == True, "Should detect research.md"
        assert artifacts['quickstart'] == True, "Should detect quickstart.md"
        assert artifacts['data_model'] == True, "Should detect data-model.md"
        assert artifacts['contracts'] == True, "Should detect contracts/ directory"
        assert artifacts['checklists'] == True, "Should detect checklists/ directory"
        assert artifacts['kanban'] == True, "Should detect tasks/ kanban directory"


class TestWorkflowStatusDetection:
    """Test workflow status detection based on artifacts."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_workflow_stages_detected_correctly(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Workflow stages progress correctly based on artifacts"""
        project_name = "test_workflow_stages"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        feature_dir = project_path / 'kitty-specs' / '003-workflow-test'
        feature_dir.mkdir(parents=True, exist_ok=True)

        from specify_cli.dashboard import get_feature_artifacts, get_workflow_status

        # Stage 1: No artifacts (all pending)
        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        assert workflow['specify'] == 'pending', "specify should be pending without spec.md"
        assert workflow['plan'] == 'pending', "plan should be pending"
        assert workflow['tasks'] == 'pending', "tasks should be pending"
        assert workflow['implement'] == 'pending', "implement should be pending"

        # Stage 2: Spec created (specify complete, rest pending)
        (feature_dir / 'spec.md').write_text("# Spec")
        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        assert workflow['specify'] == 'complete', "specify should be complete with spec.md"
        assert workflow['plan'] == 'pending', "plan should still be pending"
        assert workflow['tasks'] == 'pending', "tasks should still be pending"
        assert workflow['implement'] == 'pending', "implement should still be pending"

        # Stage 3: Plan created (specify+plan complete)
        (feature_dir / 'plan.md').write_text("# Plan")
        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        assert workflow['specify'] == 'complete', "specify should remain complete"
        assert workflow['plan'] == 'complete', "plan should now be complete"
        assert workflow['tasks'] == 'pending', "tasks should still be pending"
        assert workflow['implement'] == 'pending', "implement should still be pending"

        # Stage 4: Tasks created (specify+plan+tasks complete, implement in_progress)
        (feature_dir / 'tasks.md').write_text("# Tasks")
        (feature_dir / 'tasks').mkdir()
        (feature_dir / 'tasks' / 'planned').mkdir()

        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        assert workflow['specify'] == 'complete', "specify should remain complete"
        assert workflow['plan'] == 'complete', "plan should remain complete"
        assert workflow['tasks'] == 'complete', "tasks should now be complete"
        assert workflow['implement'] == 'in_progress', "implement should be in_progress with kanban"

    def test_workflow_status_without_kanban(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Implement status is 'pending' without kanban directory"""
        project_name = "test_no_kanban"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        feature_dir = project_path / 'kitty-specs' / '004-no-kanban'
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create spec, plan, and tasks.md but NO tasks/ directory
        (feature_dir / 'spec.md').write_text("# Spec")
        (feature_dir / 'plan.md').write_text("# Plan")
        (feature_dir / 'tasks.md').write_text("# Tasks")

        from specify_cli.dashboard import get_feature_artifacts, get_workflow_status

        artifacts = get_feature_artifacts(feature_dir)
        workflow = get_workflow_status(artifacts)

        assert workflow['specify'] == 'complete', "specify should be complete"
        assert workflow['plan'] == 'complete', "plan should be complete"
        assert workflow['tasks'] == 'complete', "tasks should be complete"
        assert workflow['implement'] == 'pending', \
            "implement should be pending without kanban directory"


class TestKanbanLaneStructure:
    """Test kanban lane structure and work package tracking."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_kanban_lane_directories_structure(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Kanban lanes follow expected directory structure (planned, doing, for_review, done)"""
        project_name = "test_kanban_structure"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        feature_dir = project_path / 'kitty-specs' / '005-kanban-test'
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create spec to make it a valid feature
        (feature_dir / 'spec.md').write_text("# Spec")

        # Create kanban structure
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir()

        # Create all four lanes
        for lane in ['planned', 'doing', 'for_review', 'done']:
            lane_dir = tasks_dir / lane
            lane_dir.mkdir()
            assert lane_dir.exists(), f"{lane} lane should exist"
            assert lane_dir.is_dir(), f"{lane} should be a directory"

        # Test scanner recognizes the structure
        from specify_cli.dashboard import scan_feature_kanban

        lanes = scan_feature_kanban(project_path, '005-kanban-test')

        assert 'planned' in lanes, "Should have planned lane"
        assert 'doing' in lanes, "Should have doing lane"
        assert 'for_review' in lanes, "Should have for_review lane"
        assert 'done' in lanes, "Should have done lane"

        # All lanes should be empty initially
        assert len(lanes['planned']) == 0, "planned lane should be empty"
        assert len(lanes['doing']) == 0, "doing lane should be empty"
        assert len(lanes['for_review']) == 0, "for_review lane should be empty"
        assert len(lanes['done']) == 0, "done lane should be empty"

    def test_work_package_counting_across_lanes(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Work packages are correctly counted across lanes"""
        project_name = "test_wp_counting"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        feature_dir = project_path / 'kitty-specs' / '006-wp-count'
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create spec
        (feature_dir / 'spec.md').write_text("# Spec")

        # Create kanban with work packages
        tasks_dir = feature_dir / 'tasks'
        tasks_dir.mkdir()

        # Create lanes
        planned_dir = tasks_dir / 'planned'
        doing_dir = tasks_dir / 'doing'
        done_dir = tasks_dir / 'done'

        planned_dir.mkdir()
        doing_dir.mkdir()
        done_dir.mkdir()

        # Create work packages with frontmatter
        wp01 = planned_dir / 'WP01-setup-database.md'
        wp01.write_text("""---
work_package_id: WP01
lane: planned
---

# Work Package Prompt: Setup Database

Test work package 1
""")

        wp02 = doing_dir / 'WP02-implement-api.md'
        wp02.write_text("""---
work_package_id: WP02
lane: doing
---

# Work Package Prompt: Implement API

Test work package 2
""")

        wp03 = done_dir / 'WP03-write-tests.md'
        wp03.write_text("""---
work_package_id: WP03
lane: done
---

# Work Package Prompt: Write Tests

Test work package 3
""")

        # Test scanner counts work packages correctly
        from specify_cli.dashboard import scan_all_features

        features = scan_all_features(project_path)

        assert len(features) == 1, "Should find one feature"
        feature = features[0]

        kanban_stats = feature['kanban_stats']
        assert kanban_stats['planned'] == 1, "Should count 1 work package in planned"
        assert kanban_stats['doing'] == 1, "Should count 1 work package in doing"
        assert kanban_stats['for_review'] == 0, "Should count 0 work packages in for_review"
        assert kanban_stats['done'] == 1, "Should count 1 work package in done"
        assert kanban_stats['total'] == 3, "Should count 3 total work packages"
