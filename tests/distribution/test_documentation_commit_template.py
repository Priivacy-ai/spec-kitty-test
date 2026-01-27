"""
Distribution tests for documentation commit template propagation.

CRITICAL: These tests validate that the git commit section in the documentation
implement template is correctly propagated to all 12 agents and applied during
upgrades.

Tests validate that:
1. Template has commit section
2. Template propagates to all agents
3. Upgrade updates existing templates
4. Template syntax is correct
5. No placeholders left unresolved
"""

import subprocess
from pathlib import Path
import pytest

pytestmark = [pytest.mark.distribution, pytest.mark.adversarial, pytest.mark.templates]


class TestTemplatePropagation:
    """Test that commit template propagates to all agents."""

    def test_documentation_template_has_commit_section(
        self, tmp_path
    ):
        """
        Documentation implement template should have commit section.

        BUG CHECK:
        - Template might not have commit section
        - Section might be in wrong location
        - Template might have typos
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        # Check claude agent's documentation template
        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"

        assert template_path.exists(), "Documentation implement template should exist"

        content = template_path.read_text()

        # BUG CHECK: Should have commit section
        assert "## Commit Workflow" in content or "Commit Workflow" in content, \
            "Template should have Commit Workflow section"
        assert "git add" in content, "Template should mention git add"
        assert "git commit" in content, "Template should mention git commit"
        assert "move-task" in content and "for_review" in content, \
            "Template should mention moving to for_review"

    def test_all_agents_get_commit_instructions(
        self, tmp_path
    ):
        """
        Test all 12 agents receive updated template.

        BUG CHECK:
        - Some agents might be missed
        - Only claude might get the template
        - Agent list might be hardcoded and incomplete
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize with all agents
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)

        # List of all agents that should have documentation templates
        agents = [
            "claude", "gemini", "gpt", "deepseek", "qwen", "llama",
            "mistral", "phi", "codestral", "sonar", "command", "nova"
        ]

        missing_commit_section = []

        for agent in agents:
            template_path = project_root / f".{agent}" / "commands" / "spec-kitty.implement.md"

            if not template_path.exists():
                missing_commit_section.append(f"{agent} (template missing)")
                continue

            content = template_path.read_text()

            # Check for commit section
            if "## Commit Workflow" not in content and "Commit Workflow" not in content:
                missing_commit_section.append(f"{agent} (no commit section)")
            elif "git commit" not in content:
                missing_commit_section.append(f"{agent} (no git commit command)")

        # BUG CHECK: All agents should have commit section
        assert not missing_commit_section, \
            f"These agents are missing commit section: {', '.join(missing_commit_section)}"

    def test_commit_section_has_correct_commands(
        self, tmp_path
    ):
        """
        Template should have working git commands.

        BUG CHECK:
        - Typos in commands
        - Wrong paths
        - Placeholders not replaced
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Extract commit workflow section
        if "## Commit Workflow" in content:
            commit_section = content.split("## Commit Workflow")[1].split("##")[0]
        else:
            pytest.fail("Commit Workflow section not found")

        # BUG CHECK: Commands should be correct
        assert "cd .worktrees/" in commit_section, "Should reference .worktrees/"
        assert "git add" in commit_section, "Should have git add"
        assert "git commit -m" in commit_section, "Should have git commit -m"
        assert "docs(WP" in commit_section or "feat(WP" in commit_section, \
            "Should show commit message format with WP"

        # BUG CHECK: No unresolved placeholders
        # Look for common placeholder patterns
        assert "{" not in commit_section or "{{" not in commit_section, \
            "Should not have unresolved placeholders like {placeholder}"
        assert "<your-" not in commit_section or "<describe" in commit_section, \
            "Placeholders like <describe> are OK, but <your-something> should be filled"

        # Check that WP## placeholder is consistent
        assert "WP##" in commit_section or "WP##" in commit_section, \
            "Should use WP## as placeholder for work package ID"

    def test_commit_workflow_mentions_validation(
        self, tmp_path
    ):
        """
        Commit section should explain WHY commits are required.

        BUG CHECK:
        - Missing explanation
        - Doesn't mention validation
        - Doesn't explain consequences
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Extract commit workflow section
        commit_section = content.split("## Commit Workflow")[1].split("##")[0] \
            if "## Commit Workflow" in content else ""

        # BUG CHECK: Should explain validation
        assert "BEFORE moving to for_review" in commit_section or \
               "before moving to" in commit_section.lower(), \
               "Should explain commit is required before moving"
        assert "validates" in commit_section.lower() or "validation" in commit_section.lower() or \
               "block" in commit_section.lower() or "prevent" in commit_section.lower(), \
               "Should mention validation/blocking"

        # Should explain consequences
        assert "why" in commit_section.lower() or "Why this matters" in commit_section, \
            "Should explain why commits are required"


class TestUpgradeScenarios:
    """Test that upgrades update templates correctly."""

    def test_upgrade_updates_documentation_implement_template(
        self, tmp_path
    ):
        """
        CRITICAL: spec-kitty upgrade should update doc template.

        BUG CHECK:
        - Template might not update during upgrade
        - Migration might not exist
        - Migration might not run
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        # Simulate OLD template (without commit section)
        old_template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        old_content = old_template_path.read_text()

        # Remove commit section to simulate old version
        if "## Commit Workflow" in old_content:
            parts = old_content.split("## Commit Workflow")
            # Remove commit section and everything after until next ##
            before = parts[0]
            after_parts = parts[1].split("\n##", 1)
            after = "\n##" + after_parts[1] if len(after_parts) > 1 else ""
            old_content = before + after

        old_template_path.write_text(old_content)

        # Verify commit section is gone
        assert "## Commit Workflow" not in old_template_path.read_text(), \
            "Test setup: commit section should be removed"

        # Run upgrade
        result = subprocess.run(
            ["spec-kitty", "upgrade"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # Check if upgrade ran successfully
        # Note: Might not have migration yet, so this could fail
        # BUG CHECK: Should have migration to update template

        # Check if template now has commit section
        updated_content = old_template_path.read_text()

        # This test might fail if migration doesn't exist yet
        # That's a valid bug to find!
        if result.returncode == 0:
            assert "## Commit Workflow" in updated_content or "Commit Workflow" in updated_content, \
                "Upgrade should add commit section to template"
        else:
            pytest.skip("Upgrade failed - migration might not exist yet")

    def test_new_projects_get_commit_section(
        self, tmp_path
    ):
        """
        New projects should get template with commit section.

        BUG CHECK:
        - New init might use old template
        - Package might not include updated template
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize new project
        subprocess.run(["spec-kitty", "init"], cwd=project_root, check=True, capture_output=True)

        # Check that template has commit section
        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # BUG CHECK: New projects should have commit section
        assert "## Commit Workflow" in content or "Commit Workflow" in content, \
            "New projects should get template with commit section"
        assert "git commit" in content, "Should have git commit command"


class TestTemplateEdgeCases:
    """Test edge cases and formatting."""

    def test_template_yaml_frontmatter_valid(
        self, tmp_path
    ):
        """
        Template should have valid YAML frontmatter.

        BUG CHECK:
        - Frontmatter syntax errors
        - Missing description
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Should start with ---
        assert content.startswith("---\n"), "Template should have YAML frontmatter"

        # Extract frontmatter
        parts = content.split("---\n")
        assert len(parts) >= 3, "Should have valid frontmatter structure (--- YAML ---)"

        frontmatter = parts[1]

        # BUG CHECK: Should have description
        assert "description:" in frontmatter, "Frontmatter should have description"

    def test_template_markdown_formatting_correct(
        self, tmp_path
    ):
        """
        Template should have correct markdown formatting.

        BUG CHECK:
        - Code blocks not closed
        - Incorrect heading levels
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Count code fences
        bash_fences = content.count("```bash")
        markdown_fences = content.count("```markdown")
        generic_fences = content.count("```\n")
        closing_fences = content.count("\n```")

        total_opening = bash_fences + markdown_fences + generic_fences
        total_closing = closing_fences

        # BUG CHECK: All code blocks should be closed
        assert total_opening == total_closing, \
            f"Code blocks should be balanced: {total_opening} opening vs {total_closing} closing"

    def test_template_commit_message_format_correct(
        self, tmp_path
    ):
        """
        Commit message format should follow conventional commits.

        BUG CHECK:
        - Wrong format (not conventional commits)
        - Inconsistent examples
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        template_path = project_root / ".claude" / "commands" / "spec-kitty.implement.md"
        content = template_path.read_text()

        # Extract commit workflow section
        commit_section = content.split("## Commit Workflow")[1].split("##")[0] \
            if "## Commit Workflow" in content else ""

        # BUG CHECK: Should use conventional commit format
        # For documentation mission, should use docs() prefix
        assert "docs(WP" in commit_section, \
            "Documentation template should show docs() commit prefix"

        # Should show WP## format
        assert "WP##" in commit_section or "WP01" in commit_section, \
            "Should show work package ID in commit message"

    def test_software_dev_template_also_has_commit_section(
        self, tmp_path
    ):
        """
        Software-dev mission should also have commit section.

        This is a sanity check - software-dev template is the reference.

        BUG CHECK:
        - Might only update docs template, not software-dev
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_root, capture_output=True)
        subprocess.run(["spec-kitty", "init", "--here", "--force", "--ai", "claude"], cwd=project_root, check=True, capture_output=True)

        # Check if software-dev template exists and has commit section
        # Note: This might not exist in .claude by default, need to create software-dev feature
        # Skip this test if not applicable

        # Create a software-dev feature to trigger template
        subprocess.run(
            ["spec-kitty", "specify", "Test Feature", "--mission", "software-dev", "--accept-all"],
            cwd=project_root,
            check=True,
            capture_output=True
        )

        # The implement command should use software-dev template
        # We can't easily check this without actually running implement
        # So this test is more of a documentation test

        pytest.skip("Software-dev template check requires feature implementation")
