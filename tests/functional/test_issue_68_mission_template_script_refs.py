"""
Test: Issue #68 - Mission Templates Still Reference Deprecated Scripts

Purpose: Detect and prevent mission templates and global templates from containing
references to deprecated Python scripts that were removed in v0.10.0.

The Bug:
Even after v0.10.9 fix, mission templates still contain:
  python3 .kittify/scripts/tasks/tasks_cli.py move ...

Should be:
  spec-kitty agent tasks move-task ...

Root Cause:
- Migration m_0_10_9_repair_templates.py only regenerates agent command templates
- Does NOT update mission templates in .kittify/missions/
- Does NOT update global templates in .kittify/templates/
- These templates get bundled and copied to user projects
- Users see deprecated script references in generated files

Affected Files:
1. .kittify/missions/software-dev/templates/task-prompt-template.md (line 109)
2. .kittify/templates/task-prompt-template.md (line 104)

Test Coverage:
1. Scan mission templates for script references (5 tests)
2. Scan global templates for script references (5 tests)
3. Validate template content correctness (4 tests)
4. Prevent future divergence (3 tests)

Related Issue: #68
Related: #62, #63, #64 (template bundling), #66 (Windows encoding)
"""

import re
from pathlib import Path

import pytest


class TestMissionTemplatesNoScriptReferences:
    """Validate mission templates don't reference deprecated scripts."""

    def test_software_dev_mission_templates_exist(self, spec_kitty_repo_root):
        """Basic: Software-dev mission templates should exist."""
        mission_templates = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'templates'

        assert mission_templates.exists(), (
            f"Software-dev mission templates should exist\n"
            f"Expected: {mission_templates}"
        )

        assert mission_templates.is_dir(), (
            f"Mission templates should be a directory\n"
            f"Path: {mission_templates}"
        )

    def test_task_prompt_template_no_tasks_cli_py_reference(self, spec_kitty_repo_root):
        """
        CRITICAL (Issue #68): Mission task-prompt-template must NOT reference tasks_cli.py

        Bug: Line 109 contains:
          python3 .kittify/scripts/tasks/tasks_cli.py move ...

        Should be:
          spec-kitty agent tasks move-task ...
        """
        template_file = (
            spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' /
            'templates' / 'task-prompt-template.md'
        )

        if not template_file.exists():
            pytest.skip("Mission task-prompt-template.md not found")

        content = template_file.read_text(encoding='utf-8')

        # Check for deprecated tasks_cli.py reference
        if 'tasks_cli.py' in content:
            # Find line number for better error message
            lines = content.split('\n')
            problem_lines = []

            for i, line in enumerate(lines, 1):
                if 'tasks_cli.py' in line:
                    problem_lines.append((i, line.strip()))

            pytest.fail(
                f"🐛 ISSUE #68 CONFIRMED: Mission task-prompt-template.md references tasks_cli.py\n\n"
                f"File: {template_file}\n"
                f"Problematic line(s):\n" +
                "\n".join([f"  Line {num}: {line}" for num, line in problem_lines]) +
                "\n\nShould use: spec-kitty agent tasks move-task\n"
                "This is the exact bug from Issue #68!"
            )

    def test_mission_templates_use_python_cli_not_scripts(self, spec_kitty_repo_root):
        """
        VALIDATION: All mission templates should use Python CLI commands

        Not deprecated script paths.
        """
        mission_dir = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'templates'

        if not mission_dir.exists():
            pytest.skip("Mission templates not found")

        templates_with_scripts = []

        for template_file in mission_dir.glob('*.md'):
            content = template_file.read_text(encoding='utf-8')

            # Check for deprecated script patterns
            deprecated_patterns = [
                r'\.kittify/scripts/tasks/tasks_cli\.py',
                r'\.kittify/scripts/bash/',
                r'\.kittify/scripts/powershell/',
                r'python3?\s+\.kittify/scripts/',
            ]

            found_patterns = []
            for pattern in deprecated_patterns:
                if re.search(pattern, content):
                    matches = re.findall(f'.*{pattern}.*', content)
                    found_patterns.extend(matches)

            if found_patterns:
                templates_with_scripts.append({
                    'file': template_file.name,
                    'patterns': found_patterns
                })

        if templates_with_scripts:
            error_msg = (
                f"🐛 BUG: {len(templates_with_scripts)} mission template(s) reference deprecated scripts:\n\n"
            )
            for template in templates_with_scripts:
                error_msg += f"  {template['file']}:\n"
                for pattern in template['patterns'][:3]:  # Show first 3
                    error_msg += f"    - {pattern.strip()}\n"

            error_msg += "\nMission templates should use spec-kitty CLI commands!"
            pytest.fail(error_msg)

    def test_all_mission_templates_scanned(self, spec_kitty_repo_root):
        """
        COMPREHENSIVE: Scan ALL missions for deprecated script references

        Not just software-dev, but all mission types.
        """
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'

        if not missions_dir.exists():
            pytest.skip("Missions directory not found")

        all_templates_with_scripts = []

        # Scan all missions
        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            templates_dir = mission_dir / 'templates'
            if not templates_dir.exists():
                continue

            # Scan each template
            for template_file in templates_dir.glob('*.md'):
                content = template_file.read_text(encoding='utf-8')

                # Look for script references
                if re.search(r'\.kittify/scripts/.+\.py', content):
                    relative_path = template_file.relative_to(missions_dir)
                    matches = re.findall(r'.*\.kittify/scripts/.+\.py.*', content)

                    all_templates_with_scripts.append({
                        'mission': mission_dir.name,
                        'file': template_file.name,
                        'path': str(relative_path),
                        'references': matches
                    })

        if all_templates_with_scripts:
            error_msg = (
                f"🐛 BUG: Found deprecated script references in {len(all_templates_with_scripts)} mission template(s):\n\n"
            )
            for template in all_templates_with_scripts:
                error_msg += f"  Mission: {template['mission']}\n"
                error_msg += f"  File: {template['file']}\n"
                error_msg += f"  Path: {template['path']}\n"
                for ref in template['references'][:2]:
                    error_msg += f"    → {ref.strip()}\n"
                error_msg += "\n"

            error_msg += "All missions should use spec-kitty CLI commands!"
            pytest.fail(error_msg)

    def test_research_mission_templates_if_exist(self, spec_kitty_repo_root):
        """
        VALIDATION: Research mission templates (if they exist) should also be clean
        """
        research_templates = (
            spec_kitty_repo_root / '.kittify' / 'missions' / 'research' / 'templates'
        )

        if not research_templates.exists():
            pytest.skip("Research mission templates don't exist")

        templates_with_scripts = []

        for template_file in research_templates.glob('*.md'):
            content = template_file.read_text(encoding='utf-8')

            if re.search(r'\.kittify/scripts/', content):
                matches = re.findall(r'.*\.kittify/scripts/.*', content)
                templates_with_scripts.append({
                    'file': template_file.name,
                    'matches': matches
                })

        if templates_with_scripts:
            pytest.fail(
                f"Research mission templates have script references:\n" +
                "\n".join([
                    f"  {t['file']}: {t['matches'][:2]}"
                    for t in templates_with_scripts
                ])
            )


class TestGlobalTemplatesNoScriptReferences:
    """Validate global templates (.kittify/templates/) don't reference scripts."""

    def test_global_task_prompt_template_no_tasks_cli_py(self, spec_kitty_repo_root):
        """
        CRITICAL (Issue #68): Global task-prompt-template must NOT reference tasks_cli.py

        This is the second affected file mentioned in Issue #68.
        """
        template_file = spec_kitty_repo_root / '.kittify' / 'templates' / 'task-prompt-template.md'

        if not template_file.exists():
            pytest.skip("Global task-prompt-template.md not found")

        content = template_file.read_text(encoding='utf-8')

        # Check for deprecated tasks_cli.py reference
        if 'tasks_cli.py' in content:
            lines = content.split('\n')
            problem_lines = []

            for i, line in enumerate(lines, 1):
                if 'tasks_cli.py' in line:
                    problem_lines.append((i, line.strip()))

            pytest.fail(
                f"🐛 ISSUE #68: Global task-prompt-template.md references tasks_cli.py\n\n"
                f"File: {template_file}\n"
                f"Problematic line(s):\n" +
                "\n".join([f"  Line {num}: {line}" for num, line in problem_lines]) +
                "\n\nShould use: spec-kitty agent tasks move-task"
            )

    def test_all_global_templates_no_script_references(self, spec_kitty_repo_root):
        """
        COMPREHENSIVE: Scan ALL global templates for script references

        This catches any template that was missed in migrations.
        """
        templates_dir = spec_kitty_repo_root / '.kittify' / 'templates'

        if not templates_dir.exists():
            pytest.fail(".kittify/templates/ should exist (bundled in package)")

        templates_with_scripts = []

        for template_file in templates_dir.glob('*.md'):
            # Skip syntax documentation
            if 'SYNTAX' in template_file.name or 'POWERSHELL_SYNTAX' in template_file.name:
                continue

            content = template_file.read_text(encoding='utf-8')

            # Look for script references
            script_patterns = [
                r'\.kittify/scripts/tasks/\w+\.py',
                r'\.kittify/scripts/bash/\w+\.sh',
                r'\.kittify/scripts/powershell/\w+\.ps1',
                r'python3?\s+\.kittify/scripts/',
            ]

            found_refs = []
            for pattern in script_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    found_refs.extend(matches)

            if found_refs:
                templates_with_scripts.append({
                    'file': template_file.name,
                    'references': list(set(found_refs))
                })

        if templates_with_scripts:
            error_msg = (
                f"🐛 BUG: {len(templates_with_scripts)} global template(s) reference deprecated scripts:\n\n"
            )
            for template in templates_with_scripts:
                error_msg += f"  {template['file']}:\n"
                for ref in template['references']:
                    error_msg += f"    - {ref}\n"

            error_msg += "\nGlobal templates should use spec-kitty CLI commands!"
            pytest.fail(error_msg)

    def test_global_templates_use_cli_commands(self, spec_kitty_repo_root):
        """
        VALIDATION: Global templates should use spec-kitty CLI commands

        Positive test - verify correct patterns exist.
        """
        templates_dir = spec_kitty_repo_root / '.kittify' / 'templates'

        templates_with_cli = []

        for template_file in templates_dir.glob('*.md'):
            content = template_file.read_text(encoding='utf-8')

            # Look for Python CLI commands
            if re.search(r'spec-kitty\s+agent\s+tasks', content):
                templates_with_cli.append(template_file.name)

        # Some templates should have CLI commands
        # (Not all - some are pure content templates)
        if len(templates_with_cli) == 0:
            print(
                "\nWARNING: No global templates use 'spec-kitty agent tasks' commands.\n"
                "This might be expected if templates don't include task commands."
            )

    def test_command_templates_already_clean(self, spec_kitty_repo_root):
        """
        REGRESSION CHECK: Command templates should still be clean

        These were fixed in v0.10.9, ensure they stay fixed.
        """
        cmd_templates = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not cmd_templates.exists():
            pytest.skip("Command templates not found")

        scripts_found = []

        for template_file in cmd_templates.glob('*.md'):
            content = template_file.read_text(encoding='utf-8')

            if re.search(r'\.kittify/scripts/.+\.(py|sh|ps1)', content):
                matches = re.findall(r'\.kittify/scripts/.+\.(py|sh|ps1)', content)
                scripts_found.append({
                    'file': template_file.name,
                    'refs': matches
                })

        if scripts_found:
            pytest.fail(
                f"REGRESSION: Command templates have script references again!\n" +
                "\n".join([
                    f"  {s['file']}: {s['refs']}"
                    for s in scripts_found
                ])
            )

    def test_implement_template_no_script_references(self, spec_kitty_repo_root):
        """
        SPECIFIC: implement.md is a large template, ensure it's clean

        This was one of the files with massive divergence (14K lines).
        """
        implement_file = spec_kitty_repo_root / '.kittify' / 'templates' / 'implement.md'

        if not implement_file.exists():
            pytest.skip("implement.md not found")

        content = implement_file.read_text(encoding='utf-8')

        # Should NOT have script references
        script_refs = re.findall(r'\.kittify/scripts/.+\.(py|sh|ps1)', content)

        if script_refs:
            pytest.fail(
                f"implement.md contains {len(script_refs)} script reference(s):\n" +
                "\n".join([f"  - {ref}" for ref in set(script_refs)[:5]])
            )


class TestDeprecatedScriptPatterns:
    """Test for specific deprecated script patterns that should not exist."""

    DEPRECATED_PATTERNS = {
        'tasks_cli.py': r'tasks_cli\.py',
        'bash scripts': r'\.kittify/scripts/bash/[\w\-]+\.sh',
        'powershell scripts': r'\.kittify/scripts/powershell/[\w\-]+\.ps1',
        'python scripts': r'python3?\s+\.kittify/scripts/.+\.py',
    }

    def test_no_tasks_cli_py_references_anywhere(self, spec_kitty_repo_root):
        """
        Issue #68 SPECIFIC: tasks_cli.py should not be referenced anywhere

        This script was removed/replaced in v0.10.0.
        """
        all_templates = []

        # Scan mission templates
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        if missions_dir.exists():
            all_templates.extend(missions_dir.rglob('*.md'))

        # Scan global templates
        global_dir = spec_kitty_repo_root / '.kittify' / 'templates'
        if global_dir.exists():
            all_templates.extend(global_dir.glob('*.md'))

        files_with_tasks_cli = []

        for template in all_templates:
            # Skip syntax docs
            if 'SYNTAX' in template.name:
                continue

            content = template.read_text(encoding='utf-8')

            if 'tasks_cli.py' in content:
                relative_path = template.relative_to(spec_kitty_repo_root)
                matches = re.findall(r'.*tasks_cli\.py.*', content)

                files_with_tasks_cli.append({
                    'path': str(relative_path),
                    'file': template.name,
                    'matches': matches
                })

        if files_with_tasks_cli:
            error_msg = (
                f"🐛 ISSUE #68: Found tasks_cli.py references in {len(files_with_tasks_cli)} template(s):\n\n"
            )
            for file_info in files_with_tasks_cli:
                error_msg += f"  {file_info['path']}:\n"
                for match in file_info['matches'][:2]:
                    error_msg += f"    → {match.strip()}\n"
                error_msg += "\n"

            error_msg += (
                "tasks_cli.py was removed in v0.10.0!\n"
                "Should use: spec-kitty agent tasks move-task"
            )

            pytest.fail(error_msg)

    def test_no_python_script_invocations_in_templates(self, spec_kitty_repo_root):
        """
        COMPREHENSIVE: No templates should invoke Python scripts with python/python3

        Pattern: python3 .kittify/scripts/...
        """
        all_templates = []

        # Collect all templates
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        if missions_dir.exists():
            all_templates.extend(missions_dir.rglob('*.md'))

        global_dir = spec_kitty_repo_root / '.kittify' / 'templates'
        if global_dir.exists():
            all_templates.extend(global_dir.glob('*.md'))

        templates_with_python_scripts = []

        for template in all_templates:
            if 'SYNTAX' in template.name:
                continue

            content = template.read_text(encoding='utf-8')

            # Pattern: python3 .kittify/scripts/...
            pattern = r'python3?\s+\.kittify/scripts/.+\.py'
            if re.search(pattern, content):
                relative_path = template.relative_to(spec_kitty_repo_root)
                matches = re.findall(pattern, content)

                templates_with_python_scripts.append({
                    'path': str(relative_path),
                    'matches': matches
                })

        if templates_with_python_scripts:
            error_msg = (
                f"🐛 BUG: {len(templates_with_python_scripts)} template(s) invoke Python scripts:\n\n"
            )
            for template in templates_with_python_scripts:
                error_msg += f"  {template['path']}:\n"
                for match in template['matches']:
                    error_msg += f"    → {match}\n"

            error_msg += "\nShould use spec-kitty CLI commands instead!"
            pytest.fail(error_msg)

    def test_no_bash_script_invocations_in_templates(self, spec_kitty_repo_root):
        """
        Scan for bash script references (should be gone since v0.10.0)
        """
        all_templates = []

        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        if missions_dir.exists():
            all_templates.extend(missions_dir.rglob('*.md'))

        global_dir = spec_kitty_repo_root / '.kittify' / 'templates'
        if global_dir.exists():
            all_templates.extend(global_dir.glob('*.md'))

        templates_with_bash = []

        for template in all_templates:
            if 'SYNTAX' in template.name:
                continue

            content = template.read_text(encoding='utf-8')

            if '.kittify/scripts/bash/' in content or re.search(r'[\w\-/]+\.sh\b', content):
                relative_path = template.relative_to(spec_kitty_repo_root)
                matches = re.findall(r'.*\.kittify/scripts/bash/.*', content)
                if not matches:
                    matches = re.findall(r'.*[\w\-/]+\.sh.*', content)

                templates_with_bash.append({
                    'path': str(relative_path),
                    'matches': matches[:3]
                })

        if templates_with_bash:
            error_msg = (
                f"🐛 BUG: {len(templates_with_bash)} template(s) reference bash scripts:\n\n"
            )
            for template in templates_with_bash:
                error_msg += f"  {template['path']}:\n"
                for match in template['matches']:
                    error_msg += f"    → {match.strip()}\n"

            pytest.fail(error_msg)


class TestCorrectCommandPatterns:
    """Validate templates use correct spec-kitty CLI patterns."""

    def test_task_movement_uses_correct_command(self, spec_kitty_repo_root):
        """
        VALIDATION: Task movement should use:
          spec-kitty agent tasks move-task <WPID> --to <lane>

        NOT:
          python3 .kittify/scripts/tasks/tasks_cli.py move ...
        """
        all_templates = []

        # Scan mission templates
        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        if missions_dir.exists():
            all_templates.extend(missions_dir.rglob('task-prompt-template.md'))

        # Scan global templates
        global_dir = spec_kitty_repo_root / '.kittify' / 'templates'
        if global_dir.exists():
            task_template = global_dir / 'task-prompt-template.md'
            if task_template.exists():
                all_templates.append(task_template)

        if not all_templates:
            pytest.skip("No task-prompt-template.md files found")

        templates_with_wrong_pattern = []

        for template in all_templates:
            content = template.read_text(encoding='utf-8')

            # Check for correct pattern
            has_correct = re.search(r'spec-kitty\s+agent\s+tasks\s+move-task', content)

            # Check for wrong pattern
            has_wrong = re.search(r'tasks_cli\.py\s+move|python3?\s+.*tasks_cli\.py', content)

            if has_wrong and not has_correct:
                templates_with_wrong_pattern.append({
                    'path': str(template.relative_to(spec_kitty_repo_root)),
                    'has_correct': has_correct,
                    'has_wrong': has_wrong
                })

        if templates_with_wrong_pattern:
            error_msg = (
                f"🐛 BUG: {len(templates_with_wrong_pattern)} template(s) use wrong task movement pattern:\n\n"
            )
            for template in templates_with_wrong_pattern:
                error_msg += f"  {template['path']}\n"
                error_msg += f"    Correct pattern: {'Found' if template['has_correct'] else 'MISSING'}\n"
                error_msg += f"    Wrong pattern: {'FOUND' if template['has_wrong'] else 'Not found'}\n"

            error_msg += (
                "\nCorrect pattern:\n"
                "  spec-kitty agent tasks move-task <WPID> --to <lane> --note \"message\"\n"
            )

            pytest.fail(error_msg)

    def test_templates_mention_spec_kitty_commands(self, spec_kitty_repo_root):
        """
        POSITIVE TEST: Templates should reference spec-kitty commands

        This validates correct usage, not just absence of wrong usage.
        """
        all_templates = []

        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'
        if missions_dir.exists():
            all_templates.extend(missions_dir.rglob('*.md'))

        global_dir = spec_kitty_repo_root / '.kittify' / 'templates'
        if global_dir.exists():
            all_templates.extend(global_dir.glob('*.md'))

        templates_with_cli = []

        for template in all_templates:
            if 'SYNTAX' in template.name:
                continue

            content = template.read_text(encoding='utf-8')

            if re.search(r'spec-kitty\s+agent', content):
                templates_with_cli.append(template.name)

        # Some templates should mention spec-kitty commands
        # (Not all - some are pure content templates)
        if len(templates_with_cli) == 0:
            print(
                "\nWARNING: No templates use 'spec-kitty agent' commands.\n"
                "Verify templates are correct or this might indicate a problem."
            )


class TestBundledMissionTemplates:
    """Validate mission templates that get bundled in package."""

    def test_bundled_missions_have_no_script_refs(self, spec_kitty_repo_root):
        """
        PACKAGE VALIDATION: Mission templates that ship to users must be clean

        These get bundled via pyproject.toml and copied to user projects.
        """
        # Check what gets bundled according to pyproject.toml
        # Line 75: ".kittify/missions" = "specify_cli/missions"

        missions_dir = spec_kitty_repo_root / '.kittify' / 'missions'

        if not missions_dir.exists():
            pytest.fail(".kittify/missions/ should exist (bundled in package)")

        bundled_templates_with_scripts = []

        for template_file in missions_dir.rglob('*.md'):
            if 'SYNTAX' in template_file.name:
                continue

            content = template_file.read_text(encoding='utf-8')

            # Look for any script references
            if re.search(r'\.kittify/scripts/.+\.(py|sh|ps1)', content):
                relative_path = template_file.relative_to(missions_dir)
                matches = re.findall(r'.*\.kittify/scripts/.+\.(py|sh|ps1).*', content)

                bundled_templates_with_scripts.append({
                    'path': str(relative_path),
                    'matches': matches[:3]
                })

        if bundled_templates_with_scripts:
            error_msg = (
                f"🐛 CRITICAL: {len(bundled_templates_with_scripts)} bundled mission template(s) have script references:\n\n"
            )
            for template in bundled_templates_with_scripts:
                error_msg += f"  {template['path']}:\n"
                for match in template['matches']:
                    error_msg += f"    → {match.strip()}\n"

            error_msg += (
                "\nThese templates get bundled in PyPI package!\n"
                "Users will copy these into their projects and get broken references."
            )

            pytest.fail(error_msg)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
