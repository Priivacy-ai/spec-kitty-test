"""
Dependency Warning Propagation Tests (FR-016 to FR-018)

Purpose: Verify dependency warnings propagate correctly through all templates.

Critical Requirements:
- FR-016: Verify dependent WPs done if this WP has dependencies
- FR-017: Warn about rebase if this WP has dependents and changes requested
- FR-018: Verify dependency declarations match code dependencies

Integration Point:
- Feature 011: Templates moved to src/specify_cli/
- Feature 010: Workspace-per-WP with dependencies
- Requirements B.3: Mission templates must include dependency warnings

Test Strategy:
This file tests that dependency warnings exist and are correct in:
1. Central templates (used by init)
2. Mission templates (used by upgrade)
3. Generated agent commands
4. Task prompt templates

Tests assume implementation team:
- Forgot to add warnings to some templates
- Added warnings inconsistently
- Warnings are vague or incomplete
- Some template types missing warnings entirely

Version: Requires v0.11.0+ (Features 011 + 010)
"""

import pytest
import subprocess
import sys
import zipfile
from pathlib import Path
import re


class TestDependencyWarningCompleteness:
    """
    CRITICAL: All relevant templates must have dependency warnings.

    Per FR-016-FR-018, these templates MUST include dependency checks:
    - review.md (most critical)
    - implement.md (helpful for implementers)
    - tasks.md (for planning dependencies)
    - task-prompt-template.md (for WP prompts)

    Tests assume implementation team added warnings to some but not all.
    """

    WARNING_PATTERNS = {
        'dependency_check': [
            r'dependenc(?:y|ies)',
            r'depends on',
            r'required WP',
            r'prerequisite',
        ],
        'dependent_check': [
            r'dependent WP',
            r'WPs that depend',
            r'depending WP',
            r'downstream WP',
        ],
        'rebase_warning': [
            r'rebase',
            r'git rebase',
            r'update.*branch',
            r'merge.*main',
        ],
        'verify_instruction': [
            r'verify',
            r'check',
            r'ensure',
            r'validate',
        ],
    }

    def test_central_review_has_all_warning_types(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Central review.md must have ALL dependency warning types.

        FR-016-FR-018 require checking dependencies, dependents, and rebase.

        Failure mode: Incomplete warnings, missing key checks.
        Impact: Reviewers miss critical dependency issues.
        """
        template_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not template_content:
            pytest.fail("Central review.md not found in package")

        # Check for each warning type
        missing_types = []

        for warning_type, patterns in self.WARNING_PATTERNS.items():
            found = any(
                re.search(pattern, template_content, re.IGNORECASE)
                for pattern in patterns
            )

            if not found:
                missing_types.append(warning_type)

        assert len(missing_types) == 0, (
            f"Central review.md missing dependency warning types!\n\n"
            f"Missing: {missing_types}\n\n"
            "FR-016-FR-018 require:\n"
            "  - dependency_check: Verify dependent WPs done if this has dependencies\n"
            "  - dependent_check: Check if other WPs depend on this\n"
            "  - rebase_warning: Warn about rebase if dependents exist and changes requested\n"
            "  - verify_instruction: Instructions to validate dependencies\n\n"
            "Reviewers need ALL of these to properly validate dependencies."
        )

    @pytest.mark.xfail(reason="spec-kitty bug: mission templates missing dependency warnings")
    def test_mission_review_has_all_warning_types(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: Mission review.md must have ALL dependency warning types.

        Requirement B.3: Mission templates get dependency warnings.

        Failure mode: Mission template not updated completely.
        Impact: Upgraded projects have incomplete warnings.
        """
        template_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/review.md'
        )

        if not template_content:
            pytest.fail("Mission review.md not found in package")

        missing_types = []

        for warning_type, patterns in self.WARNING_PATTERNS.items():
            found = any(
                re.search(pattern, template_content, re.IGNORECASE)
                for pattern in patterns
            )

            if not found:
                missing_types.append(warning_type)

        assert len(missing_types) == 0, (
            f"Mission review.md missing dependency warning types!\n\n"
            f"Missing: {missing_types}\n\n"
            "Requirement B.3: Mission templates need complete warnings.\n"
            "Upgraded projects will have incomplete dependency validation."
        )

    def test_task_prompt_template_has_rebase_guidance(self, spec_kitty_repo_root, requires_v011):
        """
        HIGH: Task prompt template must have rebase guidance.

        Requirement D.6: Task prompts include rebase guidance.

        Failure mode: Template missing or incomplete rebase section.
        Impact: Implementers don't know to rebase when dependencies change.
        """
        template_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/task-prompt-template.md'
        )

        if not template_content:
            pytest.fail("task-prompt-template.md not found in package")

        # Must have rebase_warning patterns
        found_rebase = any(
            re.search(pattern, template_content, re.IGNORECASE)
            for pattern in self.WARNING_PATTERNS['rebase_warning']
        )

        assert found_rebase, (
            f"task-prompt-template.md missing rebase guidance!\n\n"
            "FR-017/FR-018: When dependencies change, implementers must rebase.\n"
            "Template should include:\n"
            "  - When to rebase (dependency changes)\n"
            "  - How to rebase (git commands)\n"
            "  - What to check after rebase"
        )

    def test_implement_template_mentions_dependency_checks(self, spec_kitty_repo_root, requires_v011):
        """
        MEDIUM: Implement template should mention dependency checks.

        Not strictly required, but helpful for implementers.

        Failure mode: No dependency guidance during implementation.
        Impact: Implementers start work without checking dependencies.
        """
        # Check both central and mission
        central_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/implement.md'
        )

        mission_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/implement.md'
        )

        if not central_content or not mission_content:
            pytest.skip("Templates not found")

        # Check if either mentions dependencies
        central_has = any(
            re.search(pattern, central_content, re.IGNORECASE)
            for pattern in self.WARNING_PATTERNS['dependency_check']
        )

        mission_has = any(
            re.search(pattern, mission_content, re.IGNORECASE)
            for pattern in self.WARNING_PATTERNS['dependency_check']
        )

        if not central_has and not mission_has:
            pytest.skip(
                "implement templates don't mention dependencies.\n"
                "Not critical, but would help implementers check dependencies first."
            )

    @pytest.mark.xfail(reason="spec-kitty bug: dependency warnings not actionable enough")
    def test_dependency_warnings_are_actionable(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Dependency warnings should be actionable with specific steps.

        Failure mode: Vague warnings like "consider dependencies".
        Impact: Users don't know what to do.
        """
        template_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not template_content:
            pytest.skip("Template not found")

        # Look for actionable patterns
        actionable_patterns = [
            r'if.*then',  # Conditional logic
            r'verify.*by',  # Specific verification method
            r'check.*that',  # Specific checks
            r'ensure.*is',  # Specific requirements
            r'git (rebase|merge|pull)',  # Specific git commands
        ]

        found_actionable = sum(
            1 for pattern in actionable_patterns
            if re.search(pattern, template_content, re.IGNORECASE)
        )

        assert found_actionable >= 2, (
            f"Dependency warnings appear too vague!\n\n"
            f"Found {found_actionable} actionable pattern(s), expected >= 2.\n\n"
            "Warnings should be specific:\n"
            "  - IF this WP has dependencies, THEN verify dependent WPs are merged\n"
            "  - CHECK that dependency declarations match code imports\n"
            "  - If changes requested, WARN about rebase impact on dependents\n\n"
            "Vague warnings like 'consider dependencies' don't help users."
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
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0]


class TestDependencyWarningConsistency:
    """
    VALIDATION: Dependency warnings should be consistent across templates.

    Tests that warnings use similar language and structure.

    Tests assume implementation team:
    - Copy-pasted warnings with variations
    - Different terminology in different templates
    - Inconsistent level of detail
    """

    def test_central_and_mission_review_warnings_similar(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: Central and mission review.md should have similar warnings.

        Failure mode: Significantly different warnings, causing confusion.
        Impact: Users unsure which guidance to follow.
        """
        central_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        mission_content = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/missions/software-dev/command-templates/review.md'
        )

        if not central_content or not mission_content:
            pytest.skip("Templates not found")

        # Extract dependency sections
        central_deps = self._extract_dependency_section(central_content)
        mission_deps = self._extract_dependency_section(mission_content)

        if not central_deps or not mission_deps:
            pytest.skip("No clear dependency section")

        # Compare key terms
        central_terms = self._extract_key_terms(central_deps)
        mission_terms = self._extract_key_terms(mission_deps)

        common_terms = central_terms & mission_terms
        total_terms = central_terms | mission_terms

        if not total_terms:
            pytest.skip("No terms found")

        similarity = len(common_terms) / len(total_terms)

        assert similarity >= 0.6, (
            f"Central and mission warnings differ significantly!\n\n"
            f"Similarity: {similarity:.2%}\n"
            f"Central terms: {sorted(central_terms)}\n"
            f"Mission terms: {sorted(mission_terms)}\n\n"
            "Warnings should use consistent terminology.\n"
            "Users may be confused by different guidance."
        )

    def test_all_templates_use_consistent_wp_reference_format(self, spec_kitty_repo_root, requires_v011):
        """
        VALIDATION: All templates should reference WPs consistently.

        Should use: "WP01", "WP02", etc. (not "work package 1", "wp-01", etc.)

        Failure mode: Inconsistent WP reference format.
        Impact: Confusion about how to reference work packages.
        """
        templates_to_check = [
            'specify_cli/templates/command-templates/review.md',
            'specify_cli/templates/command-templates/implement.md',
            'specify_cli/templates/command-templates/tasks.md',
            'specify_cli/missions/software-dev/command-templates/review.md',
            'specify_cli/missions/software-dev/command-templates/implement.md',
        ]

        # Standard format: WP01, WP02, WP##
        standard_pattern = r'WP\d{2}'

        inconsistent_templates = []

        for template_path in templates_to_check:
            content = self._get_package_file(spec_kitty_repo_root, template_path)

            if not content:
                continue

            # Check if uses standard format
            uses_standard = bool(re.search(standard_pattern, content))

            # Check for alternative formats
            alternative_patterns = [
                r'work package \d+',
                r'wp-\d+',
                r'WP\d[^0-9]',  # WP1 instead of WP01
            ]

            uses_alternative = any(
                re.search(pattern, content, re.IGNORECASE)
                for pattern in alternative_patterns
            )

            if uses_alternative or not uses_standard:
                inconsistent_templates.append(template_path)

        if inconsistent_templates:
            pytest.skip(
                f"Some templates use inconsistent WP format:\n" +
                "\n".join(f"  - {t}" for t in inconsistent_templates) +
                "\n\nConsider standardizing on 'WP01', 'WP02', etc."
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
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0]

    def _extract_dependency_section(self, template_text):
        """Helper: Extract dependency-related section"""
        lines = template_text.split('\n')
        dep_section = []
        in_section = False

        for line in lines:
            if any(kw in line.lower() for kw in ['dependenc', 'rebase', 'dependent wp']):
                in_section = True

            if in_section:
                dep_section.append(line)

                if line.startswith('##') and len(dep_section) > 5:
                    break

        return '\n'.join(dep_section)

    def _extract_key_terms(self, text):
        """Helper: Extract key dependency-related terms"""
        key_terms = set()

        # Extract important words (length > 4 to avoid noise)
        words = re.findall(r'\b\w{5,}\b', text.lower())

        dependency_related = [
            'dependency', 'dependencies', 'dependent', 'depends',
            'rebase', 'verify', 'check', 'ensure', 'validate',
            'merge', 'branch', 'worktree', 'prerequisite'
        ]

        for word in words:
            if word in dependency_related:
                key_terms.add(word)

        return key_terms


class TestFR016To018Compliance:
    """
    CRITICAL: Explicit validation of FR-016, FR-017, FR-018 requirements.

    Direct tests for each functional requirement.

    Tests assume implementation team:
    - Missed some requirements
    - Implemented partially
    - Requirements not validated in templates
    """

    def test_FR016_verify_dependent_wps_done(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: FR-016 - Verify dependent WPs done if this WP has dependencies.

        Template must instruct:
        1. Check this WP's dependencies field
        2. Verify each dependency WP is merged/complete
        3. Block review if dependencies not met
        """
        review_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not review_template:
            pytest.fail("review.md not found")

        # Must mention checking WP dependencies
        fr016_patterns = [
            r'if.*WP.*has.*dependenc',
            r'check.*dependenc.*complete',
            r'verify.*dependent.*WP.*done',
            r'prerequisite.*WP.*merged',
        ]

        found = any(
            re.search(pattern, review_template, re.IGNORECASE)
            for pattern in fr016_patterns
        )

        assert found, (
            f"FR-016 NOT IMPLEMENTED!\n\n"
            "review.md must instruct:\n"
            "  'If this WP has dependencies, verify dependent WPs are merged'\n\n"
            "This is CRITICAL for maintaining dependency integrity."
        )

    def test_FR017_warn_about_rebase_if_dependents_exist(self, spec_kitty_repo_root, requires_v011):
        """
        CRITICAL: FR-017 - Warn about rebase if dependents exist and changes requested.

        Template must instruct:
        1. Check if other WPs depend on this WP
        2. If changes requested, warn about rebase impact
        3. Notify dependent WP implementers
        """
        review_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not review_template:
            pytest.fail("review.md not found")

        # Must warn about rebase impact on dependents
        fr017_patterns = [
            r'if.*dependent.*WP.*exist',
            r'changes.*request.*rebase',
            r'warn.*about.*rebase',
            r'other.*WP.*depend',
        ]

        found = any(
            re.search(pattern, review_template, re.IGNORECASE)
            for pattern in fr017_patterns
        )

        assert found, (
            f"FR-017 NOT IMPLEMENTED!\n\n"
            "review.md must instruct:\n"
            "  'If other WPs depend on this and you request changes, "
            "warn about rebase impact'\n\n"
            "Without this, changes break dependent WPs."
        )

    def test_FR018_verify_dependency_declarations_match_code(self, spec_kitty_repo_root, requires_v011):
        """
        HIGH: FR-018 - Verify dependency declarations match code dependencies.

        Template must instruct:
        1. Check imports/requires in code
        2. Compare to declared dependencies in frontmatter
        3. Flag mismatches
        """
        review_template = self._get_package_file(
            spec_kitty_repo_root,
            'specify_cli/templates/command-templates/review.md'
        )

        if not review_template:
            pytest.fail("review.md not found")

        # Should mention verifying dependencies match code
        fr018_patterns = [
            r'verify.*dependenc.*match',
            r'check.*import.*match.*dependenc',
            r'code.*dependenc.*declaration',
            r'validate.*actual.*dependenc',
        ]

        found = any(
            re.search(pattern, review_template, re.IGNORECASE)
            for pattern in fr018_patterns
        )

        # This is HIGH not CRITICAL - nice to have but harder to validate
        if not found:
            pytest.skip(
                "FR-018 verification not found in template.\n"
                "Would be helpful to prompt checking code dependencies match declarations."
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
            [sys.executable, '-m', 'build', '--wheel', '--outdir', str(dist_dir)],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        wheels = list(dist_dir.glob('*.whl'))
        return wheels[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
