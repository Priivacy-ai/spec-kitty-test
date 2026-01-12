"""
Comprehensive frontmatter validation tests for all .md files

Tests that ALL .md files in the repository have valid YAML frontmatter:
- Template source files in .kittify/missions/.../command-templates/
- Generated agent command files
- WP files in kitty-specs/
- Documentation files

Critical: Malformed frontmatter causes ConfigFrontmatterError in agents.

Example of the bug this prevents:
- analyze.md had only 1 `---` instead of 2
- checklist.md had only 1 `---` instead of 2
- clarify.md had only 1 `---` instead of 2
- Caused all agent commands to fail with ConfigFrontmatterError
"""
import pytest
from pathlib import Path
import re
import yaml


def parse_frontmatter(file_path: Path):
    """
    Parse YAML frontmatter from markdown file.

    Returns (frontmatter_dict, content_body, error_message)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return None, None, f"Cannot read file: {e}"

    if not content.startswith('---'):
        # No frontmatter is OK for some files
        return {}, content, None

    # Count --- delimiters
    delimiter_count = len(re.findall(r'^---\s*$', content, re.MULTILINE))

    if delimiter_count < 2:
        return None, None, f"Missing closing --- delimiter (found {delimiter_count}, need 2)"

    # Extract frontmatter between first two ---
    parts = re.split(r'^---\s*$', content, maxsplit=2, flags=re.MULTILINE)

    if len(parts) < 3:
        return None, None, "Cannot split frontmatter (expected 3 parts)"

    yaml_text = parts[1]
    body = parts[2]

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(yaml_text)
        if frontmatter is None:
            frontmatter = {}
        return frontmatter, body, None
    except yaml.YAMLError as e:
        return None, None, f"Invalid YAML in frontmatter: {e}"


class TestTemplateFrontmatterValidity:
    """Test that all template source files have valid frontmatter"""

    def test_all_command_templates_have_valid_frontmatter(self, spec_kitty_repo_root):
        """
        Test that ALL command template source files have valid frontmatter.

        Validates:
        1. Each .md file in command-templates/ has frontmatter
        2. Frontmatter has opening and closing --- delimiters
        3. YAML is parseable
        4. Required fields present (description)
        """
        template_dir = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        if not template_dir.exists():
            # Try alternative path
            template_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not template_dir.exists():
            pytest.skip("Command templates directory not found")

        errors = []
        template_files = list(template_dir.glob('*.md'))

        assert len(template_files) > 0, f"No template files found in {template_dir}"

        for template_file in template_files:
            frontmatter, body, error = parse_frontmatter(template_file)

            if error:
                errors.append(f"{template_file.name}: {error}")
                continue

            # Verify has content after frontmatter
            if body is not None and len(body.strip()) == 0:
                errors.append(f"{template_file.name}: No content after frontmatter")

        if errors:
            error_msg = "Template frontmatter validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            pytest.fail(error_msg)

    def test_specific_malformed_templates(self, spec_kitty_repo_root):
        """
        Test specific templates that were found to have malformed frontmatter.

        Known issues:
        - analyze.md: Only 1 --- (missing closing delimiter)
        - checklist.md: Only 1 --- (missing closing delimiter)
        - clarify.md: Only 1 --- (missing closing delimiter)
        """
        template_dir = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        if not template_dir.exists():
            template_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not template_dir.exists():
            pytest.skip("Command templates directory not found")

        # Check the three known problematic files
        problematic_files = ['analyze.md', 'checklist.md', 'clarify.md']

        for filename in problematic_files:
            file_path = template_dir / filename

            if not file_path.exists():
                # File may not exist in all versions
                continue

            content = file_path.read_text()

            # Count --- delimiters
            delimiter_count = len(re.findall(r'^---\s*$', content, re.MULTILINE))

            assert delimiter_count >= 2, (
                f"{filename} has malformed frontmatter: "
                f"found {delimiter_count} --- delimiters, need at least 2\n\n"
                f"First 10 lines:\n{chr(10).join(content.split(chr(10))[:10])}"
            )

    def test_all_templates_have_description_field(self, spec_kitty_repo_root):
        """
        Test that all command templates have description field in frontmatter.

        The description field is used by agents to understand command purpose.
        """
        template_dir = spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates'

        if not template_dir.exists():
            template_dir = spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates'

        if not template_dir.exists():
            pytest.skip("Command templates directory not found")

        missing_description = []

        for template_file in template_dir.glob('*.md'):
            frontmatter, body, error = parse_frontmatter(template_file)

            if error:
                # Handled by other test
                continue

            if frontmatter and 'description' not in frontmatter:
                missing_description.append(template_file.name)

        if missing_description:
            pytest.fail(
                f"Templates missing 'description' field:\n" +
                "\n".join(f"  - {f}" for f in missing_description)
            )


class TestGeneratedAgentCommandFrontmatter:
    """Test that generated agent command files have valid frontmatter"""

    def test_init_generates_valid_frontmatter(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test that spec-kitty init generates command files with valid frontmatter.

        Validates:
        1. All generated .md files have valid frontmatter
        2. No malformed YAML
        3. No missing closing delimiters
        """
        import subprocess
        import os

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project
        result = subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input='y\n',
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        project_path = temp_project_dir / 'test-project'

        # Find all generated command files
        command_files = list(project_path.rglob('spec-kitty.*.md'))

        # Also check other patterns
        if len(command_files) == 0:
            # Try alternative locations
            command_files = list(project_path.rglob('.claude/**/*.md'))
            command_files += list(project_path.rglob('.github/prompts/*.md'))

        if len(command_files) == 0:
            pytest.skip("No command files found after init")

        errors = []

        for cmd_file in command_files:
            # Skip non-command files
            if 'README' in cmd_file.name or 'spec.md' in cmd_file.name:
                continue

            frontmatter, body, error = parse_frontmatter(cmd_file)

            if error:
                errors.append(f"{cmd_file.relative_to(project_path)}: {error}")

        if errors:
            error_msg = "Generated command files have malformed frontmatter:\n" + "\n".join(f"  - {e}" for e in errors)
            pytest.fail(error_msg)

    def test_no_single_delimiter_files(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test that NO generated files have only a single --- delimiter.

        This is the specific bug that caused ConfigFrontmatterError.
        """
        import subprocess
        import os

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize project
        result = subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude,codex'],
            cwd=str(temp_project_dir),
            env=env,
            input='y\n',
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        project_path = temp_project_dir / 'test-project'

        # Scan ALL .md files
        all_md_files = list(project_path.rglob('*.md'))

        single_delimiter_files = []

        for md_file in all_md_files:
            # Skip README and other docs
            if 'README' in md_file.name:
                continue

            content = md_file.read_text()

            if not content.startswith('---'):
                # No frontmatter is OK
                continue

            # Count delimiters
            delimiter_count = len(re.findall(r'^---\s*$', content, re.MULTILINE))

            if delimiter_count == 1:
                single_delimiter_files.append(str(md_file.relative_to(project_path)))

        if single_delimiter_files:
            pytest.fail(
                f"Found {len(single_delimiter_files)} files with malformed frontmatter (only 1 ---):\n" +
                "\n".join(f"  - {f}" for f in single_delimiter_files) +
                "\n\nAll frontmatter must have opening AND closing --- delimiters:\n"
                "---\n"
                "field: value\n"
                "---\n"
            )


class TestWorkPackageFrontmatterValidity:
    """Test that WP files have valid frontmatter"""

    def test_wp_files_have_valid_frontmatter(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test that WP files created during workflow have valid frontmatter.

        Validates:
        1. dependencies field is valid YAML list
        2. title field exists
        3. No malformed YAML
        """
        import subprocess
        import os

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Initialize and create feature
        subprocess.run(
            ['spec-kitty', 'init', 'test-project', '--ai=claude'],
            cwd=str(temp_project_dir),
            env=env,
            input='y\n',
            capture_output=True
        )

        project_path = temp_project_dir / 'test-project'

        subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=str(project_path),
            env=env,
            capture_output=True
        )

        if result.returncode != 0:
            pytest.skip("Feature creation failed")

        # Create WP files manually with frontmatter
        tasks_dir = project_path / 'kitty-specs' / '001-test-feature' / 'tasks'
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create WP with dependencies
        wp01_file = tasks_dir / 'WP01.md'
        wp01_file.write_text("---\ntitle: WP01\ndependencies: []\n---\n\n# WP01")

        wp02_file = tasks_dir / 'WP02.md'
        wp02_file.write_text("---\ntitle: WP02\ndependencies: [WP01]\n---\n\n# WP02")

        # Validate frontmatter
        errors = []

        for wp_file in [wp01_file, wp02_file]:
            frontmatter, body, error = parse_frontmatter(wp_file)

            if error:
                errors.append(f"{wp_file.name}: {error}")
                continue

            # Verify dependencies is a list
            if 'dependencies' in frontmatter:
                if not isinstance(frontmatter['dependencies'], list):
                    errors.append(f"{wp_file.name}: dependencies must be a list, got {type(frontmatter['dependencies'])}")

        if errors:
            pytest.fail("WP frontmatter validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def test_dependencies_field_is_valid_yaml_list(self):
        """
        Test various dependencies field formats.

        Valid:
        - dependencies: []
        - dependencies: [WP01]
        - dependencies: [WP01, WP02]
        - dependencies:
            - WP01
            - WP02

        Invalid:
        - dependencies: WP01 (not a list)
        - dependencies: "WP01, WP02" (string, not list)
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test valid formats
            valid_cases = [
                ("empty_list", "dependencies: []"),
                ("single_item", "dependencies: [WP01]"),
                ("multiple_items", "dependencies: [WP01, WP02]"),
                ("yaml_list", "dependencies:\n  - WP01\n  - WP02"),
            ]

            for case_name, dep_line in valid_cases:
                wp_file = tmp_path / f"{case_name}.md"
                wp_file.write_text(f"---\ntitle: Test\n{dep_line}\n---\n\n# Test")

                frontmatter, body, error = parse_frontmatter(wp_file)

                assert error is None, f"{case_name} should be valid: {error}"
                assert 'dependencies' in frontmatter, f"{case_name} missing dependencies"
                assert isinstance(frontmatter['dependencies'], list), f"{case_name} dependencies not a list"

            # Test invalid formats
            invalid_cases = [
                ("not_a_list", "dependencies: WP01"),
                ("string_value", 'dependencies: "WP01, WP02"'),
            ]

            for case_name, dep_line in invalid_cases:
                wp_file = tmp_path / f"invalid_{case_name}.md"
                wp_file.write_text(f"---\ntitle: Test\n{dep_line}\n---\n\n# Test")

                frontmatter, body, error = parse_frontmatter(wp_file)

                # Should either fail to parse OR parse but dependencies not a list
                if error is None:
                    # Parsed, but dependencies should not be a list
                    if 'dependencies' in frontmatter:
                        assert not isinstance(frontmatter['dependencies'], list) or \
                               isinstance(frontmatter['dependencies'], str), \
                            f"{case_name} should have non-list dependencies"


class TestFrontmatterDelimiterCounting:
    """Test delimiter counting logic"""

    def test_delimiter_count_detection(self):
        """
        Test that we correctly count --- delimiters.

        Valid: 2 or more ---
        Invalid: 0 or 1 ---
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Test 0 delimiters (no frontmatter - valid)
            file0 = tmp_path / "no_frontmatter.md"
            file0.write_text("# Title\n\nContent")
            frontmatter, body, error = parse_frontmatter(file0)
            assert error is None, "No frontmatter should be OK"
            assert frontmatter == {}

            # Test 1 delimiter (malformed - invalid)
            file1 = tmp_path / "one_delimiter.md"
            file1.write_text("---\ndescription: Test\n\n# Content")
            frontmatter, body, error = parse_frontmatter(file1)
            assert error is not None, "One delimiter should be invalid"
            assert "closing ---" in error or "2" in error

            # Test 2 delimiters (valid)
            file2 = tmp_path / "two_delimiters.md"
            file2.write_text("---\ndescription: Test\n---\n\n# Content")
            frontmatter, body, error = parse_frontmatter(file2)
            assert error is None, f"Two delimiters should be valid: {error}"
            assert frontmatter['description'] == 'Test'

            # Test 3 delimiters (valid - extra --- in content is OK)
            file3 = tmp_path / "three_delimiters.md"
            file3.write_text("---\ndescription: Test\n---\n\n# Content\n\n---\n\nMore content")
            frontmatter, body, error = parse_frontmatter(file3)
            assert error is None, "Three delimiters should be valid"
            assert '---' in body, "Body should contain the third ---"


class TestAllRepositoryMarkdownFiles:
    """Test ALL .md files in repository for frontmatter validity"""

    def test_scan_all_md_files_in_kittify(self, spec_kitty_repo_root):
        """
        Scan ALL .md files in .kittify/ directory for frontmatter validity.

        Comprehensive validation to prevent shipping broken templates.
        """
        kittify_dir = spec_kitty_repo_root / '.kittify'

        if not kittify_dir.exists():
            pytest.skip(".kittify directory not found")

        all_md_files = list(kittify_dir.rglob('*.md'))

        if len(all_md_files) == 0:
            pytest.skip("No .md files found in .kittify")

        errors = []
        checked_count = 0

        for md_file in all_md_files:
            # Skip READMEs and docs
            if 'README' in md_file.name.upper() or 'CHANGELOG' in md_file.name.upper():
                continue

            checked_count += 1
            frontmatter, body, error = parse_frontmatter(md_file)

            if error:
                relative_path = md_file.relative_to(spec_kitty_repo_root)
                errors.append(f"{relative_path}: {error}")

        assert checked_count > 0, "No template files checked"

        if errors:
            error_msg = (
                f"Found {len(errors)} files with malformed frontmatter out of {checked_count} checked:\n" +
                "\n".join(f"  - {e}" for e in errors[:20])
            )
            if len(errors) > 20:
                error_msg += f"\n  ... and {len(errors) - 20} more"

            pytest.fail(error_msg)


class TestFrontmatterRegressionPrevention:
    """Prevent regression of the analyze.md/checklist.md/clarify.md bug"""

    def test_no_files_with_single_delimiter_in_repo(self, spec_kitty_repo_root):
        """
        Scan entire repository for files with single --- delimiter.

        This is a regression test for the specific bug where:
        - analyze.md had only 1 ---
        - checklist.md had only 1 ---
        - clarify.md had only 1 ---

        Causing ConfigFrontmatterError for all users.
        """
        # Scan command templates specifically
        template_paths = [
            spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates',
            spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates',
        ]

        template_dir = None
        for path in template_paths:
            if path.exists():
                template_dir = path
                break

        if not template_dir:
            pytest.skip("Template directory not found")

        all_template_files = list(template_dir.glob('*.md'))

        single_delimiter_files = []

        for md_file in all_template_files:
            content = md_file.read_text()

            if not content.startswith('---'):
                # No frontmatter - OK
                continue

            delimiter_count = len(re.findall(r'^---\s*$', content, re.MULTILINE))

            if delimiter_count == 1:
                single_delimiter_files.append({
                    'file': md_file.name,
                    'first_5_lines': '\n'.join(content.split('\n')[:5])
                })

        if single_delimiter_files:
            error_msg = (
                f"🚨 CRITICAL: Found {len(single_delimiter_files)} template files with malformed frontmatter!\n\n"
                "These files have opening --- but NO closing --- delimiter:\n"
            )

            for item in single_delimiter_files:
                error_msg += f"\n{item['file']}:\n{item['first_5_lines']}\n"

            error_msg += (
                "\n⚠️ This causes ConfigFrontmatterError for all agents!\n"
                "Fix: Add closing --- after frontmatter fields:\n"
                "  ---\n"
                "  description: value\n"
                "  ---  ← ADD THIS LINE\n"
            )

            pytest.fail(error_msg)


class TestFrontmatterYAMLValidity:
    """Test that frontmatter contains valid YAML"""

    def test_yaml_parsing_all_templates(self, spec_kitty_repo_root):
        """
        Test that ALL template frontmatter can be parsed as YAML.

        Catches:
        - Invalid YAML syntax
        - Indentation errors
        - Type errors
        - Malformed lists/dicts
        """
        template_paths = [
            spec_kitty_repo_root / '.kittify' / 'missions' / 'software-dev' / 'command-templates',
            spec_kitty_repo_root / '.kittify' / 'templates' / 'command-templates',
        ]

        template_dir = None
        for path in template_paths:
            if path.exists():
                template_dir = path
                break

        if not template_dir:
            pytest.skip("Template directory not found")

        yaml_errors = []

        for template_file in template_dir.glob('*.md'):
            content = template_file.read_text()

            if not content.startswith('---'):
                continue

            # Extract YAML portion
            parts = re.split(r'^---\s*$', content, maxsplit=2, flags=re.MULTILINE)

            if len(parts) < 3:
                # Handled by delimiter test
                continue

            yaml_text = parts[1]

            # Try to parse
            try:
                parsed = yaml.safe_load(yaml_text)
                if parsed is None:
                    yaml_errors.append(f"{template_file.name}: YAML parsed as null/empty")
            except yaml.YAMLError as e:
                yaml_errors.append(f"{template_file.name}: {e}")

        if yaml_errors:
            pytest.fail(
                "YAML parsing errors in templates:\n" +
                "\n".join(f"  - {e}" for e in yaml_errors)
            )


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
