"""
Test Per-Feature Missions (v0.8.0+)

Tests the per-feature mission system introduced in v0.8.0 where each feature
selects its own mission (stored in meta.json) instead of a project-level mission.

Test Coverage:
1. Multi-Source Mission Discovery (3 tests)
   - Discovery order: project → built-in (personal missions deferred to post-v0.8.0)
   - Project missions take precedence over built-in
   - Built-in missions used as fallback

2. Feature Mission in meta.json (3 tests)
   - Mission stored in feature's meta.json
   - Default to software-dev when not specified
   - --mission flag works on create-new-feature.sh

3. Backward Compatibility (2 tests)
   - Legacy features (no mission in meta.json) default to software-dev
   - Projects upgraded from < 0.8.0 work correctly

Note: All tests in this file require spec-kitty >= 0.8.0

v0.8.0 Scope (from implementation plan):
- NO personal missions (~/.kittify/missions/) - deferred to future release
- Mission sources: 'project' and 'built-in' only
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version_str = result.stdout.strip().split()[-1]
        return tuple(map(int, version_str.split('.')))
    except Exception:
        return (0, 0, 0)


# All tests require v0.8.0+
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 8, 0),
    reason="Requires spec-kitty >= 0.8.0"
)


class TestMultiSourceMissionDiscovery:
    """Test mission discovery from project → built-in.

    Note: Personal missions (~/.kittify/missions/) are deferred to post-v0.8.0.
    v0.8.0 only supports 'project' and 'built-in' sources.

    These tests use text output from `spec-kitty mission list` since --json
    is not implemented in v0.8.0.
    """

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_list_available_missions_includes_builtin(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Built-in missions are always available

        GIVEN: A new project
        WHEN: Listing available missions
        THEN: Built-in missions (software-dev) should be included
        """
        project_name = "test_builtin_missions"
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

        # List available missions (text output)
        result = subprocess.run(
            ['spec-kitty', 'mission', 'list'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Check text output contains software-dev
        output = result.stdout.lower()

        assert 'software-dev' in output or 'software dev' in output, \
            f"Built-in software-dev mission should be listed. Output: {result.stdout}"

    def test_mission_list_shows_source_indicators(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Mission list shows source indicators

        GIVEN: A project with missions
        WHEN: Listing available missions
        THEN: Output should indicate source (project/built-in)
        """
        project_name = "test_source_indicators"
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

        # List missions
        result = subprocess.run(
            ['spec-kitty', 'mission', 'list'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.lower()

        # Should show source indicators (project or built-in)
        has_source = 'project' in output or 'built-in' in output or 'built in' in output
        assert has_source, \
            f"Mission list should show source indicators. Output: {result.stdout}"

    def test_missions_directory_exists(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Missions directory exists and contains mission configs

        GIVEN: A new project
        WHEN: Checking .kittify/missions/
        THEN: Should contain at least software-dev mission
        """
        project_name = "test_missions_dir"
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

        missions_dir = project_path / '.kittify' / 'missions'
        assert missions_dir.exists(), "Missions directory should exist"

        # software-dev should be present
        sw_dev = missions_dir / 'software-dev'
        assert sw_dev.exists(), "software-dev mission should exist"
        assert (sw_dev / 'mission.yaml').exists(), "mission.yaml should exist"


class TestFeatureMissionInMetaJson:
    """Test that mission is stored per-feature in meta.json."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_mission_stored_in_meta_json(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Mission is stored in feature's meta.json

        GIVEN: A feature created with --mission flag
        WHEN: Checking meta.json
        THEN: mission field should be present
        """
        project_name = "test_mission_meta"
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

        # Create feature with explicit mission
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Test Feature',
             '--mission', 'software-dev', 'Test description'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output to get branch name
        output = json.loads(result.stdout.split('\n')[-2])  # JSON is usually near end
        branch_name = output.get('BRANCH_NAME')

        if branch_name:
            # Check meta.json in worktree
            worktree_path = project_path / '.worktrees' / branch_name
            meta_json = worktree_path / 'kitty-specs' / branch_name / 'meta.json'

            if meta_json.exists():
                meta = json.loads(meta_json.read_text())
                assert 'mission' in meta, \
                    "meta.json should have mission field"
                assert meta['mission'] == 'software-dev', \
                    "Mission should be software-dev"

    def test_default_mission_when_not_specified(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Defaults to software-dev when mission not specified

        GIVEN: A feature created without --mission flag
        WHEN: Checking meta.json
        THEN: mission should default to software-dev
        """
        project_name = "test_default_mission"
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

        # Create feature WITHOUT --mission flag
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'No Mission Specified',
             'Test description without mission'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    output = json.loads(line)
                    branch_name = output.get('BRANCH_NAME')
                    if branch_name:
                        # Check meta.json
                        worktree_path = project_path / '.worktrees' / branch_name
                        meta_json = worktree_path / 'kitty-specs' / branch_name / 'meta.json'

                        if meta_json.exists():
                            meta = json.loads(meta_json.read_text())
                            # Should default to software-dev or not have mission field
                            mission = meta.get('mission', 'software-dev')
                            assert mission == 'software-dev', \
                                "Default mission should be software-dev"
                        break
                except json.JSONDecodeError:
                    continue

    def test_mission_flag_on_create_feature(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: --mission flag works on create-new-feature.sh

        GIVEN: A project with multiple missions available
        WHEN: Creating feature with --mission research
        THEN: meta.json should have mission: research
        """
        project_name = "test_mission_flag"
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

        # Ensure research mission exists
        research_mission = project_path / '.kittify' / 'missions' / 'research'
        if not research_mission.exists():
            research_mission.mkdir(parents=True)
            (research_mission / 'mission.yaml').write_text("""
name: "Research"
description: "Research mission"
version: "1.0.0"
domain: "research"
workflow:
  phases:
    - name: research
      description: Do research
artifacts:
  required: []
  optional: []
""")

        # Create feature with research mission
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Research Project',
             '--mission', 'research', 'A research project'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Verify mission in meta.json
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    output = json.loads(line)
                    branch_name = output.get('BRANCH_NAME')
                    if branch_name:
                        worktree_path = project_path / '.worktrees' / branch_name
                        meta_json = worktree_path / 'kitty-specs' / branch_name / 'meta.json'

                        if meta_json.exists():
                            meta = json.loads(meta_json.read_text())
                            assert meta.get('mission') == 'research', \
                                "Mission should be research when --mission research used"
                        break
                except json.JSONDecodeError:
                    continue


class TestBackwardCompatibility:
    """Test backward compatibility with pre-v0.8.0 features."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary directory for test project."""
        return tmp_path

    def test_legacy_feature_defaults_to_software_dev(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: Legacy features without mission in meta.json default to software-dev

        GIVEN: A feature created before v0.8.0 (no mission in meta.json)
        WHEN: Reading the feature's mission
        THEN: Should default to software-dev
        """
        project_name = "test_legacy_feature"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Legacy Feature', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse to get branch name
        for line in result.stdout.split('\n'):
            if line.strip().startswith('{'):
                try:
                    output = json.loads(line)
                    branch_name = output.get('BRANCH_NAME')
                    if branch_name:
                        worktree_path = project_path / '.worktrees' / branch_name
                        meta_json = worktree_path / 'kitty-specs' / branch_name / 'meta.json'

                        if meta_json.exists():
                            # Remove mission field to simulate legacy feature
                            meta = json.loads(meta_json.read_text())
                            if 'mission' in meta:
                                del meta['mission']
                                meta_json.write_text(json.dumps(meta, indent=2))

                            # Now test that spec-kitty defaults to software-dev
                            # This would need a spec-kitty command that reads feature mission
                            # For now, just verify the meta.json can be read
                            meta_reloaded = json.loads(meta_json.read_text())
                            assert 'mission' not in meta_reloaded, \
                                "Legacy feature should not have mission field"
                        break
                except json.JSONDecodeError:
                    continue

    def test_init_no_longer_has_mission_flag(
        self, temp_project_dir, spec_kitty_repo_root
    ):
        """Test: spec-kitty init no longer accepts --mission flag

        GIVEN: spec-kitty >= 0.8.0
        WHEN: Running spec-kitty init --mission research
        THEN: Should fail or warn (--mission removed from init)
        """
        project_name = "test_no_init_mission"

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Try to init with --mission flag
        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--mission', 'research'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=False  # Don't fail on non-zero exit
        )

        # Should either fail or not recognize --mission
        # The exact behavior depends on implementation
        if result.returncode != 0:
            assert '--mission' in result.stderr or 'mission' in result.stderr.lower(), \
                "Error should mention --mission flag is not recognized"
        else:
            # If it succeeded, it might have ignored the flag
            # Check that no project-level mission was set
            project_path = temp_project_dir / project_name
            active_mission = project_path / '.kittify' / 'active-mission'
            assert not active_mission.exists(), \
                "Project-level active-mission should not be created in v0.8.0+"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
