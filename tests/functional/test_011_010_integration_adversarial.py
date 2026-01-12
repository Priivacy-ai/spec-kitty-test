"""
Adversarial tests for Feature 011 integration with Feature 010

Purpose: Test the integration of 011 (packaging safety) with 010 (workspace-per-WP).
These tests assume the implementation team made mistakes and try to find them.

Context:
- Feature 011 relocated templates from .kittify/ to src/specify_cli/
- Feature 010 changed workflow to planning in main, implementing in worktrees
- Integration requires central templates to match mission templates
- Dependency warnings must propagate through ALL templates

Test Philosophy:
- Adversarial: Assume bugs exist, find them
- Test what ships, not just what's written
- No SPEC_KITTY_TEMPLATE_ROOT bypass in distribution tests
- Validate real user experience

Critical Integration Points (from requirements):
A. Central templates must fully support init (all 13 files)
B. Central templates sync'd to mission versions for workspace-per-WP workflow
C. Mission templates include dependency warnings (FR-016-FR-018)
D. Migration points to correct locations
E. Task prompt template includes rebase guidance
F. Tests lock in the spec

Version: Requires v0.11.0+ (Features 011 + 010)
"""

import pytest
import subprocess
import tempfile
import zipfile
from pathlib import Path
import re


class TestCentralTemplateCompleteness:
    """
    CRITICAL: Central templates must support init with ALL 13 agent templates.

    Feature 010 spec says "init.py is unchanged" and "all 12 agent templates must be updated".
    Feature 011 moved templates to src/specify_cli/templates/command-templates/.

    Integration requirement: Central templates must have all 13 files so init works.

    Tests assume implementation team may have:
    - Forgotten to copy some templates
    - Left templates in wrong location
    - Created incomplete template set
    """

    REQUIRED_CENTRAL_TEMPLATES = [
        'accept.md',
        'analyze.md',
        'checklist.md',
        'clarify.md',
        'constitution.md',
        'dashboard.md',
        'implement.md',
        'merge.md',
        'plan.md',
        'research.md',
        'review.md',
        'specify.md',
        'tasks.md',
    ]

    def test_all_13_central_templates_exist_in_package(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Wheel must contain all 13 central templates.

        Failure mode: Implementation team restored only some templates.
        Impact: init breaks for missing agent types.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        # Find all command-template files in specify_cli/templates/command-templates/
        central_template_files = [
            name for name in namelist
            if 'specify_cli/templates/command-templates/' in name
            and name.endswith('.md')
        ]

        # Extract just the filenames
        found_templates = set()
        for full_path in central_template_files:
            filename = full_path.split('/')[-1]
            found_templates.add(filename)

        missing = set(self.REQUIRED_CENTRAL_TEMPLATES) - found_templates

        assert len(missing) == 0, (
            f"CRITICAL: Missing {len(missing)} central template(s)!\n\n"
            f"Missing: {sorted(missing)}\n"
            f"Found: {sorted(found_templates)}\n\n"
            "Feature 010 spec says 'init.py unchanged' and 'all 12 agent templates updated'.\n"
            "Init command requires all 13 central templates to generate agent commands.\n\n"
            "Without these templates, spec-kitty init will fail for certain --ai flags."
        )

    def test_central_templates_not_in_old_kittify_location(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Central templates should NOT be in .kittify/ location.

        Failure mode: Team didn't clean up old locations after move.
        Impact: Template duplication, confusion about source of truth.
        """
        wheel_file = self._build_wheel(spec_kitty_repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            namelist = zf.namelist()

        # Check for templates in old .kittify/ location
        old_location_templates = [
            name for name in namelist
            if '.kittify/templates/command-templates/' in name
            and name.endswith('.md')
        ]

        assert len(old_location_templates) == 0, (
            f"Templates found in old .kittify/ location!\n\n"
            f"Found {len(old_location_templates)} template(s):\n" +
            "\n".join([f"  - {f}" for f in old_location_templates[:10]]) +
            "\n\nFeature 011 moved templates to src/specify_cli/templates/.\n"
            "Old location should be cleaned up to avoid duplication."
        )

    def test_implement_template_matches_workspace_per_wp_workflow(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central implement.md must match workspace-per-WP mission version.

        Requirement A.2: "Sync central implement to mission version"

        Failure mode: Central template not updated for 010 workflow.
        Impact: init-generated implement commands don't follow workspace-per-WP pattern.
        """
        # Get both templates
        central_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/implement.md'
        )

        mission_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/implement.md'
        )

        if not central_template:
            pytest.fail("Central implement.md not found in package")

        if not mission_template:
            pytest.fail("Mission implement.md not found in package")

        # Check for workspace-per-WP keywords in central template
        workspace_keywords = [
            'worktree',
            'WP01',
            'WP##',
            'work package',
            'workspace-per-wp',
        ]

        found_keywords = [kw for kw in workspace_keywords if kw.lower() in central_template.lower()]

        assert len(found_keywords) >= 2, (
            f"Central implement.md appears NOT updated for workspace-per-WP!\n\n"
            f"Expected keywords: {workspace_keywords}\n"
            f"Found only: {found_keywords}\n\n"
            "Requirement A.2: Central implement must match mission version.\n"
            "Without this, init-generated commands don't follow 010 workflow."
        )

    def test_plan_template_matches_main_repo_planning(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central plan.md must support main-repo planning.

        Requirement A.2: "Sync central plan to mission version (main-repo planning)"

        Failure mode: Central template still assumes worktree planning.
        Impact: Users confused about where to run planning.
        """
        central_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/plan.md'
        )

        if not central_template:
            pytest.fail("Central plan.md not found in package")

        # Should mention main repo or NOT mention worktrees for planning
        main_repo_keywords = [
            'main repository',
            'main repo',
            'before implementing',
            'planning phase',
        ]

        # Should NOT instruct creating worktrees during planning
        bad_patterns = [
            'create worktree',
            'switch to worktree',
            'in the worktree',
        ]

        found_good = [kw for kw in main_repo_keywords if kw.lower() in central_template.lower()]
        found_bad = [pat for pat in bad_patterns if pat.lower() in central_template.lower()]

        assert len(found_bad) == 0, (
            f"Central plan.md incorrectly mentions worktrees during planning!\n\n"
            f"Found problematic patterns: {found_bad}\n\n"
            "Feature 010: Planning happens in MAIN, not worktrees.\n"
            "Template should not instruct users to create worktrees during planning."
        )

        assert len(found_good) >= 1, (
            f"Central plan.md doesn't clarify main-repo planning!\n\n"
            f"Expected keywords: {main_repo_keywords}\n"
            f"Found: {found_good}\n\n"
            "Template should clarify planning happens in main repository."
        )

    def test_tasks_template_has_flat_tasks_dir_structure(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central tasks.md must document flat tasks/ directory.

        Requirement A.2: "Sync central tasks to mission version (flat tasks dir + finalize step)"

        Failure mode: Template describes old hierarchical structure.
        Impact: Users create wrong directory structure.
        """
        central_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/tasks.md'
        )

        if not central_template:
            pytest.fail("Central tasks.md not found in package")

        # Should mention flat tasks directory
        flat_keywords = [
            'tasks/',
            'WP01.md',
            'WP02.md',
            'finalize',
        ]

        found = [kw for kw in flat_keywords if kw in central_template]

        assert len(found) >= 2, (
            f"Central tasks.md doesn't describe flat tasks/ structure!\n\n"
            f"Expected keywords: {flat_keywords}\n"
            f"Found: {found}\n\n"
            "Feature 010: Tasks use flat structure (tasks/WP01.md, tasks/WP02.md).\n"
            "Template must document this structure."
        )

    def test_specify_template_has_main_repo_workflow(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central specify.md must document main-repo workflow.

        Requirement A.2: "Sync central specify to mission version (main repo, no worktree)"

        Failure mode: Template still mentions worktree creation during specify.
        Impact: Users confused about workflow.
        """
        central_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/specify.md'
        )

        if not central_template:
            pytest.fail("Central specify.md not found in package")

        # Should NOT mention worktree creation
        bad_patterns = [
            'create worktree',
            'switch to worktree',
            'worktree for feature',
        ]

        found_bad = [pat for pat in bad_patterns if pat.lower() in central_template.lower()]

        assert len(found_bad) == 0, (
            f"Central specify.md incorrectly mentions worktrees!\n\n"
            f"Found: {found_bad}\n\n"
            "Feature 010: Specify happens in MAIN, not worktrees.\n"
            "Worktrees created later during implement phase."
        )

    def test_review_template_has_dependency_warnings(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central review.md must include dependency warnings.

        Requirement A.2: "Sync central review to mission version + dependency warnings"

        Failure mode: Central template missing dependency checks.
        Impact: Reviewers don't validate dependencies, broken deploys.
        """
        central_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not central_template:
            pytest.fail("Central review.md not found in package")

        # Must include dependency warnings per FR-016-FR-018
        dependency_keywords = [
            'dependenc',  # matches dependencies, dependency, etc
            'rebase',
            'dependent',
            'verify',
        ]

        found = [kw for kw in dependency_keywords if kw.lower() in central_template.lower()]

        assert len(found) >= 3, (
            f"Central review.md missing dependency warnings!\n\n"
            f"Expected keywords: {dependency_keywords}\n"
            f"Found only: {found}\n\n"
            "Requirement A.2 & FR-016-FR-018: Review must warn about dependencies.\n"
            "Reviewers need to:\n"
            "  1. Verify dependent WPs are done if this WP has dependencies\n"
            "  2. Warn about rebase if this WP has dependents and changes requested\n"
            "  3. Verify dependency declarations match code dependencies"
        )

    def _build_wheel(self, repo_root):
        """Helper: Build wheel and return path"""
        dist_dir = repo_root / 'dist'

        if dist_dir.exists():
            wheels = list(dist_dir.glob('*.whl'))
            if wheels:
                return wheels[0]

        result = subprocess.run(
            ['python', '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to build wheel:\n{result.stderr}")

        wheels = list(dist_dir.glob('*.whl'))
        assert len(wheels) > 0, "No wheel file found"
        return wheels[0]

    def _get_package_file(self, repo_root, file_path):
        """Helper: Extract file from wheel package"""
        wheel_file = self._build_wheel(repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            for name in zf.namelist():
                if file_path in name:
                    return zf.read(name).decode('utf-8', errors='ignore')

        return None


class TestMissionTemplateDependencyWarnings:
    """
    CRITICAL: Mission templates must include dependency warnings.

    Requirement B.3: "Add dependency warnings to mission review template"

    Upgrade migrations use mission templates to update projects.
    If mission templates lack dependency warnings, upgraded projects won't have them.

    Tests assume implementation team:
    - Added warnings to central templates but forgot mission templates
    - Inconsistent warning text between central and mission versions
    """

    def test_mission_review_has_dependency_warnings(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Mission review.md must have dependency warnings.

        Requirement B.3: Copy dependency warning block from central to mission review.

        Failure mode: Mission template not updated.
        Impact: Upgraded projects don't get dependency validation prompts.
        """
        mission_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/review.md'
        )

        if not mission_template:
            pytest.fail("Mission review.md not found in package")

        # Check for dependency warning content per FR-016-FR-018
        required_checks = [
            'dependencies',
            'dependent WPs',
            'rebase',
            'verify',
        ]

        found = [check for check in required_checks if check.lower() in mission_template.lower()]

        assert len(found) >= 3, (
            f"Mission review.md missing dependency warnings!\n\n"
            f"Required checks: {required_checks}\n"
            f"Found only: {found}\n\n"
            "Requirement B.3: Mission templates need dependency warnings.\n"
            "FR-016-FR-018 require:\n"
            "  - Verify dependent WPs done if this WP has dependencies\n"
            "  - Warn about rebase if dependents exist and changes requested\n"
            "  - Verify dependency declarations match code dependencies"
        )

    def test_mission_implement_has_dependency_checks(self, spec_kitty_repo_root, requires_v011):
        """
        HIGH: Mission implement.md should mention dependency validation.

        Failure mode: Implement template doesn't prompt dependency checks.
        Impact: Implementers forget to check dependencies before starting.
        """
        mission_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/implement.md'
        )

        if not mission_template:
            pytest.fail("Mission implement.md not found in package")

        # Should at least mention checking dependencies
        dependency_hints = [
            'dependenc',
            'prerequisite',
            'depends on',
            'required WP',
        ]

        found = [hint for hint in dependency_hints if hint.lower() in mission_template.lower()]

        # This is HIGH not CRITICAL - warnings more important in review
        if len(found) == 0:
            pytest.skip(
                "Mission implement.md doesn't mention dependencies.\n"
                "Not critical, but would be helpful to prompt implementers."
            )

    def test_dependency_warnings_consistent_between_central_and_mission(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Dependency warnings should be consistent across templates.

        Failure mode: Different warning text, causing confusion.
        Impact: Users get inconsistent guidance.
        """
        central_review = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        mission_review = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/review.md'
        )

        if not central_review or not mission_review:
            pytest.skip("Templates not found for comparison")

        # Extract dependency-related sections
        central_deps = self._extract_dependency_section(central_review)
        mission_deps = self._extract_dependency_section(mission_review)

        if not central_deps or not mission_deps:
            pytest.skip("No clear dependency section found")

        # They should be very similar (allow minor formatting differences)
        similarity = self._text_similarity(central_deps, mission_deps)

        assert similarity > 0.7, (
            f"Dependency warnings differ between central and mission templates!\n\n"
            f"Similarity: {similarity:.2%}\n\n"
            f"Central:\n{central_deps[:200]}...\n\n"
            f"Mission:\n{mission_deps[:200]}...\n\n"
            "Warnings should be consistent across templates."
        )

    def _get_package_file(self, repo_root, file_path):
        """Helper: Extract file from wheel package"""
        wheel_file = self._build_wheel(repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            for name in zf.namelist():
                if file_path in name:
                    return zf.read(name).decode('utf-8', errors='ignore')

        return None

    def _build_wheel(self, repo_root):
        """Helper: Build wheel"""
        dist_dir = repo_root / 'dist'
        if dist_dir.exists():
            wheels = list(dist_dir.glob('*.whl'))
            if wheels:
                return wheels[0]

        subprocess.run(
            ['python', '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0]

    def _extract_dependency_section(self, template_text):
        """Helper: Extract dependency-related section from template"""
        # Look for sections mentioning dependencies
        lines = template_text.split('\n')

        dep_section = []
        in_section = False

        for line in lines:
            if any(keyword in line.lower() for keyword in ['dependenc', 'rebase', 'dependent wp']):
                in_section = True

            if in_section:
                dep_section.append(line)

                # Stop at next major section
                if line.startswith('##') and len(dep_section) > 5:
                    break

        return '\n'.join(dep_section)

    def _text_similarity(self, text1, text2):
        """Helper: Simple text similarity measure"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)


class TestMigrationTemplateSourceLocations:
    """
    CRITICAL: Migrations must source templates from correct locations.

    Requirement C.4: "Keep m_0_11_0 pointing to new mission locations"
    Requirement C.5: "Verify slash-command migrations source mission templates"

    Feature 011 relocated templates to src/specify_cli/missions/.
    Migrations must pull from new location, not old .kittify/ location.

    Tests assume implementation team:
    - Hardcoded old paths in migrations
    - Forgot to update migration template sources
    - Migration points to non-existent locations
    """

    def test_workspace_per_wp_migration_sources_new_mission_location(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: m_0_11_0_workspace_per_wp.py must source from src/specify_cli/missions/.

        Requirement C.4: Keep migration pointing to new locations per commit 45d91c9.

        Failure mode: Migration points to old .kittify/missions/ location.
        Impact: Migration fails, cannot upgrade to v0.11.0.
        """
        migration_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations' / 'm_0_11_0_workspace_per_wp.py'

        if not migration_file.exists():
            pytest.fail(
                f"Migration file not found: {migration_file}\n"
                "Cannot test template sourcing without migration file."
            )

        content = migration_file.read_text()

        # Should reference new location
        new_location_patterns = [
            'specify_cli/missions/',
            'specify_cli.missions',
            'importlib.resources',
        ]

        # Should NOT reference old location
        old_location_patterns = [
            '.kittify/missions/',
            'kittify_root / "missions"',
        ]

        found_new = [pat for pat in new_location_patterns if pat in content]
        found_old = [pat for pat in old_location_patterns if pat in content]

        assert len(found_old) == 0, (
            f"Migration references OLD template location!\n\n"
            f"Found: {found_old}\n\n"
            f"File: {migration_file}\n\n"
            "Feature 011 moved templates to src/specify_cli/missions/.\n"
            "Migration must use new location or will fail."
        )

        assert len(found_new) >= 1, (
            f"Migration doesn't reference NEW template location!\n\n"
            f"Expected patterns: {new_location_patterns}\n"
            f"Found: {found_new}\n\n"
            f"File: {migration_file}\n\n"
            "Migration should use src/specify_cli/missions/ or importlib.resources."
        )

    def test_slash_command_migrations_source_mission_templates(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Slash-command migrations should source from mission templates.

        Requirement C.5: Verify migrations copy from missions (which now have dependency warnings).

        Failure mode: Migrations still copy from old locations without warnings.
        Impact: Upgraded projects don't get dependency warnings.
        """
        migration_files = [
            'm_0_10_2_update_slash_commands.py',
            'm_0_10_6_workflow_simplification.py',
        ]

        migrations_dir = spec_kitty_repo_root / 'src' / 'specify_cli' / 'upgrade' / 'migrations'

        for migration_name in migration_files:
            migration_file = migrations_dir / migration_name

            if not migration_file.exists():
                continue  # Skip if migration doesn't exist

            content = migration_file.read_text()

            # Should source from missions or use importlib.resources
            correct_patterns = [
                'missions/',
                'importlib.resources',
                'mission_type',
            ]

            found = [pat for pat in correct_patterns if pat in content]

            # Not blocking if missing, but should warn
            if len(found) == 0:
                pytest.skip(
                    f"{migration_name} doesn't clearly source from missions.\n"
                    "May be OK if it doesn't update templates, but worth checking."
                )


class TestTaskPromptTemplateRebaseGuidance:
    """
    HIGH: Task prompt template must include rebase guidance.

    Requirement D.6: "Ensure task prompt template includes rebase guidance"

    Per FR-017/FR-018, implementers need rebase guidance when dependencies change.

    Tests assume implementation team:
    - Forgot to add rebase guidance to template
    - Added guidance but it's unclear or incomplete
    """

    def test_task_prompt_template_has_rebase_guidance(self, spec_kitty_repo_root, requires_v011):
        """
        HIGH: task-prompt-template.md must include rebase guidance.

        Requirement D.6: Keep/add rebase block for FR-017/FR-018.

        Failure mode: Template missing rebase guidance.
        Impact: Implementers don't know to rebase when dependencies change.
        """
        template_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'task-prompt-template.md'

        if not template_file.exists():
            # Try in package
            template_content = self._get_package_file(
                spec_kitty_repo_root,
                'specify_cli/templates/task-prompt-template.md'
            )

            if not template_content:
                pytest.fail(
                    "task-prompt-template.md not found!\n"
                    "Cannot validate rebase guidance without template."
                )
        else:
            template_content = template_file.read_text()

        # Should mention rebase
        rebase_keywords = [
            'rebase',
            'git rebase',
            'dependency change',
            'dependent WP',
        ]

        found = [kw for kw in rebase_keywords if kw.lower() in template_content.lower()]

        assert len(found) >= 1, (
            f"task-prompt-template.md missing rebase guidance!\n\n"
            f"Expected keywords: {rebase_keywords}\n"
            f"Found: {found}\n\n"
            "Requirement D.6 & FR-017/FR-018: Template must include rebase guidance.\n"
            "When dependencies change, implementers need to know to rebase their WP."
        )

    def test_rebase_guidance_is_clear_and_actionable(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Rebase guidance should be clear with commands.

        Failure mode: Vague guidance like "consider rebasing".
        Impact: Implementers don't know how to rebase.
        """
        template_file = spec_kitty_repo_root / 'src' / 'specify_cli' / 'templates' / 'task-prompt-template.md'

        if template_file.exists():
            template_content = template_file.read_text()
        else:
            template_content = self._get_package_file(
                spec_kitty_repo_root,
                'specify_cli/templates/task-prompt-template.md'
            )

        if not template_content:
            pytest.skip("Template not found")

        # Should have git commands or clear instructions
        actionable_patterns = [
            'git rebase',
            'git pull',
            'git merge',
            'rebase your branch',
            'update your worktree',
        ]

        found = [pat for pat in actionable_patterns if pat.lower() in template_content.lower()]

        if len(found) == 0:
            pytest.skip(
                "Rebase guidance found but appears vague.\n"
                "Consider adding specific git commands for clarity."
            )

    def _get_package_file(self, repo_root, file_path):
        """Helper: Extract file from wheel"""
        wheel_file = self._build_wheel(repo_root)

        with zipfile.ZipFile(wheel_file, 'r') as zf:
            for name in zf.namelist():
                if file_path in name:
                    return zf.read(name).decode('utf-8', errors='ignore')

        return None

    def _build_wheel(self, repo_root):
        """Helper: Build wheel"""
        dist_dir = repo_root / 'dist'
        if dist_dir.exists():
            wheels = list(dist_dir.glob('*.whl'))
            if wheels:
                return wheels[0]

        subprocess.run(
            ['python', '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
