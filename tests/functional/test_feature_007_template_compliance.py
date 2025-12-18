"""
Test: Feature 007 Template Compliance Audit (v0.9.0+ Flat Structure)

Purpose: CRITICAL AUDIT - Validate that all command templates and mission
templates have been updated to reflect Feature 007 (v0.9.0) flat directory
structure. Feature 007 eliminated tasks/ subdirectories but templates were
NEVER UPDATED, causing agents to create the wrong structure!

Background - Feature 007 (v0.9.0):
- ELIMINATED: tasks/planned/, tasks/doing/, tasks/for_review/, tasks/done/
- NEW: Flat tasks/ directory with frontmatter lane: field
- Migration: m_0_9_0_frontmatter_only flattened existing projects

CRITICAL ISSUE DISCOVERED:
Feature 007 was merged (commit be8430a) but command templates still
instruct agents to create the OLD subdirectory structure! This causes
new features to have the wrong structure.

Test Coverage:
1. Command Template Violations (8 tests)
   - tasks.md should NOT instruct subdirectory creation
   - implement.md should NOT reference tasks/doing/
   - review.md should NOT reference tasks/for_review/
   - merge.md should NOT reference tasks/done/
   - All templates use flat structure
   - All templates reference frontmatter lane: field
   - All missions affected (software-dev AND research)
   - Template examples show correct structure

2. Template File Violations (4 tests)
   - tasks-template.md should show flat structure
   - task-prompt-template.md should NOT show phase subdirs
   - README templates updated
   - Example paths are correct

3. Agent Instruction Validation (3 tests)
   - No "create tasks/planned/" instructions
   - No "ensure tasks/doing/ exists" instructions
   - Instructions reference frontmatter-only approach

Version: Applies to >= v0.9.0 (Feature 007 and later)
Severity: CRITICAL - Causes structural violations in all new features
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker - applies to v0.9.0+
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 9, 0),
    reason="Requires spec-kitty >= 0.9.0 (Feature 007 - flat structure)"
)


class TestCommandTemplateCompliance:
    """Test that command templates comply with Feature 007 flat structure."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create initialized project to check templates."""
        project_name = "template_audit"
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
            timeout=30,
            check=True
        )

        return project_path

    def test_tasks_template_no_subdirectory_instructions(self, initialized_project):
        """
        Test: tasks.md template does NOT instruct subdirectory creation

        VIOLATION FOUND:
        Current tasks.md template lines 81-87 explicitly say:
        - "Correct structure: FEATURE_DIR/tasks/planned/WPxx-slug.md"
        - "Ensure FEATURE_DIR/tasks/planned/ exists"
        - "create tasks/doing/, tasks/for_review/, tasks/done/"

        Expected (v0.9.0+):
        - "Correct structure: FEATURE_DIR/tasks/WPxx-slug.md"
        - "Use flat tasks/ directory"
        - "Set lane: field in frontmatter"

        Impact: Agents follow these instructions and create wrong structure
        """
        # Check tasks command template
        tasks_template = initialized_project / '.claude' / 'commands' / 'spec-kitty.tasks.md'

        if tasks_template.exists():
            content = tasks_template.read_text()

            # Should NOT instruct creating subdirectories
            violations = []

            if 'tasks/planned/' in content:
                violations.append("References tasks/planned/ subdirectory")
            if 'tasks/doing/' in content:
                violations.append("References tasks/doing/ subdirectory")
            if 'tasks/for_review/' in content:
                violations.append("References tasks/for_review/ subdirectory")
            if 'tasks/done/' in content:
                violations.append("References tasks/done/ subdirectory")
            if 'create tasks/planned' in content.lower():
                violations.append("Instructs creating tasks/planned/ subdirectory")
            if 'ensure' in content.lower() and 'planned' in content.lower() and 'exists' in content.lower():
                violations.append("Instructs ensuring planned/ exists")

            assert len(violations) == 0, (
                f"tasks.md template violates Feature 007 flat structure:\n" +
                "\n".join(f"  - {v}" for v in violations) +
                f"\n\nTemplate should use flat tasks/ with frontmatter lane: field"
            )

    @pytest.mark.xfail(reason="BUG: implement.md references old tasks/doing/ structure")
    def test_implement_template_no_doing_subdirectory(self, initialized_project):
        """
        Test: implement.md template does NOT reference tasks/doing/

        VIOLATION: implement.md has ~8 references to tasks/doing/ paths

        Expected (v0.9.0+):
        - References: tasks/WPxx-slug.md
        - Updates: frontmatter lane: field
        - No directory-based lane references

        Impact: Agents try to move files to non-existent doing/ directory
        """
        implement_template = initialized_project / '.claude' / 'commands' / 'spec-kitty.implement.md'

        if implement_template.exists():
            content = implement_template.read_text()

            # Count violations
            doing_refs = content.count('tasks/doing/')
            planned_refs = content.count('tasks/planned/')

            assert doing_refs == 0, (
                f"implement.md has {doing_refs} references to tasks/doing/ (should be 0)\n"
                f"Feature 007 eliminated directory-based lanes"
            )

            assert planned_refs == 0, (
                f"implement.md has {planned_refs} references to tasks/planned/ (should be 0)"
            )

    @pytest.mark.xfail(reason="BUG: review.md references old tasks/for_review/ structure")
    def test_review_template_no_for_review_subdirectory(self, initialized_project):
        """
        Test: review.md template does NOT reference tasks/for_review/

        VIOLATION: review.md references tasks/for_review/ paths

        Expected (v0.9.0+):
        - Check frontmatter lane: for_review
        - No directory paths

        Impact: Agents look for files in wrong location
        """
        review_template = initialized_project / '.claude' / 'commands' / 'spec-kitty.review.md'

        if review_template.exists():
            content = review_template.read_text()

            assert 'tasks/for_review/' not in content, (
                "review.md should not reference tasks/for_review/ subdirectory"
            )

    @pytest.mark.xfail(reason="BUG: merge.md references old tasks/done/ structure")
    def test_merge_template_no_done_subdirectory(self, initialized_project):
        """
        Test: merge.md template does NOT reference tasks/done/

        VIOLATION: merge.md references tasks/done/ paths

        Expected (v0.9.0+):
        - Check frontmatter lane: done
        - No directory paths

        Impact: Agents expect wrong file locations
        """
        merge_template = initialized_project / '.claude' / 'commands' / 'spec-kitty.merge.md'

        if merge_template.exists():
            content = merge_template.read_text()

            assert 'tasks/done/' not in content, (
                "merge.md should not reference tasks/done/ subdirectory"
            )

    def test_templates_reference_frontmatter_lanes(self, initialized_project):
        """
        Test: Templates instruct using frontmatter lane: field

        Expected (v0.9.0+):
        - Instructions mention "lane:" field
        - Explain frontmatter-based workflow
        - No directory-based instructions

        Impact: Agents don't know to use frontmatter approach
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        # Check key templates
        key_templates = ['spec-kitty.tasks.md', 'spec-kitty.implement.md']

        frontmatter_mentioned = False
        for template_name in key_templates:
            template = commands_dir / template_name
            if template.exists():
                content = content.lower()

                if 'lane:' in content or 'frontmatter' in content:
                    frontmatter_mentioned = True
                    break

        assert frontmatter_mentioned, (
            "Templates should explain frontmatter lane: approach (Feature 007)"
        )

    @pytest.mark.xfail(reason="BUG: Templates show old directory examples")
    def test_templates_show_flat_structure_examples(self, initialized_project):
        """
        Test: Template examples show flat tasks/ structure

        VIOLATION: Templates show examples like:
        - tasks/planned/WP01-setup.md (WRONG)
        - tasks/planned/phase-1-foundation/ (WRONG)

        Expected (v0.9.0+):
        - tasks/WP01-setup.md (CORRECT)
        - No phase subdirectories shown
        - Examples match actual structure

        Impact: Agents copy wrong examples
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        # Check all spec-kitty templates
        violations = {}
        for template in commands_dir.glob('spec-kitty.*.md'):
            content = template.read_text()

            template_violations = []
            # Look for specific wrong patterns
            if '/planned/WP' in content or '/planned/phase' in content:
                template_violations.append("Shows tasks/planned/ subdirectory in examples")
            if '/doing/WP' in content:
                template_violations.append("Shows tasks/doing/ subdirectory in examples")
            if '/for_review/WP' in content or '/for_review/phase' in content:
                template_violations.append("Shows tasks/for_review/ subdirectory in examples")
            if '/done/WP' in content:
                template_violations.append("Shows tasks/done/ subdirectory in examples")

            if template_violations:
                violations[template.name] = template_violations

        assert len(violations) == 0, (
            "Templates show wrong directory structure examples:\n" +
            "\n".join(f"  {name}:\n    " + "\n    ".join(v) for name, v in violations.items())
        )

    def test_software_dev_mission_templates_compliance(self, initialized_project):
        """
        Test: software-dev mission templates updated for Feature 007

        Validates:
        - Mission templates in .kittify/missions/software-dev/
        - Command templates use flat structure
        - No subdirectory instructions

        Impact: Base templates are wrong, propagate to all projects
        """
        mission_templates = initialized_project / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        if mission_templates.exists():
            violations = {}

            for template in mission_templates.glob('*.md'):
                content = template.read_text()

                template_violations = []
                if 'tasks/planned/' in content:
                    template_violations.append("References tasks/planned/")
                if 'tasks/doing/' in content:
                    template_violations.append("References tasks/doing/")
                if 'create tasks/planned' in content.lower():
                    template_violations.append("Instructs creating subdirectories")

                if template_violations:
                    violations[template.name] = template_violations

            assert len(violations) == 0, (
                "software-dev mission templates violate Feature 007:\n" +
                "\n".join(f"  {name}:\n    " + "\n    ".join(v) for name, v in violations.items())
            )

    @pytest.mark.xfail(reason="BUG: research mission templates not updated")
    def test_research_mission_templates_compliance(self, initialized_project):
        """
        Test: research mission templates updated for Feature 007

        Validates:
        - Research mission templates also updated
        - Both missions comply with flat structure
        - Consistency across all missions

        Impact: All mission types affected
        """
        mission_templates = initialized_project / '.kittify' / 'missions' / 'research' / 'command-templates'

        if mission_templates.exists():
            violations = {}

            for template in mission_templates.glob('*.md'):
                content = template.read_text()

                if 'tasks/planned/' in content or 'tasks/doing/' in content:
                    violations[template.name] = "References lane subdirectories"

            assert len(violations) == 0, (
                f"research mission templates violate Feature 007: {violations}"
            )


class TestTemplateFileCompliance:
    """Test that template files show correct structure."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create initialized project."""
        project_name = "template_files"
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
            timeout=30,
            check=True
        )

        return project_path

    @pytest.mark.xfail(reason="BUG: tasks-template.md shows old directory structure")
    def test_tasks_template_file_shows_flat_structure(self, initialized_project):
        """
        Test: tasks-template.md shows flat tasks/ structure

        VIOLATION: Shows "tasks/planned/WP01-setup.md"
        Expected: Shows "tasks/WP01-setup.md"

        Impact: Agents copy this example structure
        """
        # Find tasks-template.md (may be in mission templates or other location)
        template_locations = [
            initialized_project / '.kittify' / 'missions' / 'software-dev' / 'templates' / 'tasks-template.md',
            initialized_project / '.kittify' / 'templates' / 'tasks-template.md',
        ]

        for template_path in template_locations:
            if template_path.exists():
                content = template_path.read_text()

                # Should show flat structure examples
                assert '/planned/WP' not in content, (
                    f"tasks-template.md shows wrong structure: tasks/planned/WP01-...\n"
                    f"Should show: tasks/WP01-..."
                )

                assert '/planned/phase' not in content, (
                    "tasks-template.md shows phase subdirectories (eliminated in v0.9.0)"
                )

    @pytest.mark.xfail(reason="BUG: task-prompt-template.md shows phase subdirectories")
    def test_task_prompt_template_no_phase_subdirs(self, initialized_project):
        """
        Test: task-prompt-template.md does NOT show phase subdirectories

        VIOLATION: Shows "tasks/planned/phase-<n>-<label>/"
        Expected: No phase subdirectories (flat tasks/)

        Impact: Agents create phase subdirectories
        """
        template_locations = [
            initialized_project / '.kittify' / 'missions' / 'software-dev' / 'templates' / 'task-prompt-template.md',
            initialized_project / '.kittify' / 'templates' / 'task-prompt-template.md',
        ]

        for template_path in template_locations:
            if template_path.exists():
                content = template_path.read_text()

                assert '/phase-' not in content or 'tasks/phase-' not in content, (
                    "task-prompt-template.md should not show phase subdirectories"
                )

    @pytest.mark.xfail(reason="BUG: README templates show old structure")
    def test_readme_templates_show_flat_structure(self, initialized_project):
        """
        Test: README and documentation show correct structure

        Validates:
        - READMEs updated for Feature 007
        - Documentation examples correct
        - No outdated structure shown

        Impact: Users and agents see wrong examples
        """
        # Check mission READMEs
        readme_locations = [
            initialized_project / '.kittify' / 'missions' / 'software-dev' / 'README.md',
            initialized_project / '.kittify' / 'missions' / 'research' / 'README.md',
            initialized_project / 'README.md',
        ]

        violations = {}
        for readme in readme_locations:
            if readme.exists():
                content = readme.read_text()

                readme_violations = []
                if 'tasks/planned/' in content:
                    readme_violations.append("Shows tasks/planned/ in examples")
                if 'tasks/doing/' in content:
                    readme_violations.append("Shows tasks/doing/ in examples")

                if readme_violations:
                    violations[readme.name] = readme_violations

        assert len(violations) == 0, (
            f"README files show outdated structure: {violations}"
        )

    @pytest.mark.xfail(reason="BUG: Example paths use old subdirectory structure")
    def test_all_example_paths_are_correct(self, initialized_project):
        """
        Test: All template example paths use flat tasks/ structure

        Scans all templates for path examples and validates they're correct.

        Expected: tasks/WP01-slug.md
        Not: tasks/planned/WP01-slug.md

        Impact: Every example is teaching agents the wrong structure
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        all_violations = {}

        for template in commands_dir.glob('spec-kitty.*.md'):
            content = template.read_text()
            lines = content.split('\n')

            violations = []
            for i, line in enumerate(lines, 1):
                # Find file path examples
                if 'tasks/' in line and '.md' in line:
                    # Check if it's using subdirectories
                    if any(subdir in line for subdir in ['/planned/', '/doing/', '/for_review/', '/done/']):
                        violations.append(f"Line {i}: {line.strip()[:80]}")

            if violations:
                all_violations[template.name] = violations

        assert len(all_violations) == 0, (
            "Templates contain wrong path examples:\n" +
            "\n".join(
                f"\n{name}:\n" + "\n".join(f"  {v}" for v in viols)
                for name, viols in all_violations.items()
            )
        )


class TestAgentInstructionCompliance:
    """Test that agent instructions follow Feature 007 approach."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create initialized project."""
        project_name = "instruction_audit"
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
            timeout=30,
            check=True
        )

        return project_path

    @pytest.mark.xfail(reason='BUG: Templates instruct "create tasks/planned/" directory')
    def test_no_create_subdirectory_instructions(self, initialized_project):
        """
        Test: No instructions to create lane subdirectories

        CRITICAL VIOLATION:
        Current templates say "create tasks/doing/, tasks/for_review/, tasks/done/"

        This is EXPLICITLY what Feature 007 eliminated!

        Expected: "Create tasks/ directory (flat structure)"

        Impact: Agents follow instructions and create wrong structure
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        violations = {}

        for template in commands_dir.glob('spec-kitty.*.md'):
            content = template.read_text().lower()

            template_violations = []

            # Look for explicit subdirectory creation instructions
            if 'create tasks/planned' in content:
                template_violations.append("Instructs creating tasks/planned/")
            if 'create tasks/doing' in content:
                template_violations.append("Instructs creating tasks/doing/")
            if 'create tasks/for_review' in content or 'create tasks/for review' in content:
                template_violations.append("Instructs creating tasks/for_review/")
            if 'create tasks/done' in content:
                template_violations.append("Instructs creating tasks/done/")
            if 'mkdir' in content and ('planned' in content or 'doing' in content):
                template_violations.append("Instructs mkdir for lane directories")

            if template_violations:
                violations[template.name] = template_violations

        assert len(violations) == 0, (
            "Templates contain subdirectory creation instructions:\n" +
            "\n".join(f"  {name}:\n    " + "\n    ".join(v) for name, v in violations.items()) +
            "\n\nFeature 007 eliminated subdirectories - templates must not instruct creating them!"
        )

    @pytest.mark.xfail(reason='BUG: Templates instruct "ensure tasks/planned/ exists"')
    def test_no_ensure_subdirectory_exists_instructions(self, initialized_project):
        """
        Test: No instructions to ensure lane subdirectories exist

        VIOLATION:
        "Ensure FEATURE_DIR/tasks/planned/ exists"

        Expected:
        "Ensure FEATURE_DIR/tasks/ exists (flat structure)"

        Impact: Agents verify/create wrong directories
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        for template in commands_dir.glob('spec-kitty.*.md'):
            content = template.read_text().lower()

            assert not ('ensure' in content and 'tasks/planned/' in content), (
                f"{template.name} instructs ensuring tasks/planned/ exists (Feature 007 violation)"
            )

    @pytest.mark.xfail(reason="BUG: Templates reference move commands instead of update")
    def test_templates_use_update_not_move(self, initialized_project):
        """
        Test: Templates reference 'update' command (not 'move')

        Feature 007 Changes:
        - OLD: spec-kitty agent tasks move-task (moved files)
        - NEW: spec-kitty agent tasks update (updates frontmatter only)

        Templates should reference the correct command.

        Impact: Agents use wrong/outdated commands
        """
        commands_dir = initialized_project / '.claude' / 'commands'

        # Note: Based on actual implementation, may be 'move-task' with --to flag
        # This test validates the correct command is documented
        # May need to be adjusted based on actual v0.10.0 API
        pass  # Placeholder - need to verify actual command names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
