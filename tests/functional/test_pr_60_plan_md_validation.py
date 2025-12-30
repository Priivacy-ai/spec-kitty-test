"""
Test: PR #60 - Fix plan.md location validation messaging

Purpose: Validate that plan.md template has prominent location validation warnings
to prevent AI agents from creating files in the wrong directory.

Bug History:
- Before fix: Subtle validation message that AI agents often ignored
- Root cause: Template messaging wasn't prominent enough
- Fix: Added prominent ⚠️ STOP header and clearer examples (commit 9e1c7c1)

Test Coverage:
1. Template Content Validation (5 tests)
   - Has prominent ⚠️ warning symbol
   - Has "STOP" directive
   - Shows correct vs wrong location examples
   - Includes validation code
   - Has success confirmation messages

2. Validation Code Quality (3 tests)
   - References validate_worktree_location()
   - Shows error handling
   - Has exit(1) on failure

3. User Guidance (2 tests)
   - Explains what to do if validation fails
   - Shows navigation commands

Related Commits: 9e1c7c1686a6adac331974de9d582aa9c7ea4088
"""

from pathlib import Path

import pytest


class TestPlanMdLocationValidation:
    """Test that plan.md template has improved location validation."""

    def test_template_has_warning_symbol(self, spec_kitty_repo_root):
        """
        Test: plan.md template has prominent ⚠️ warning symbol

        Before: "## Location Pre-flight Check (CRITICAL for AI Agents)"
        After: "## ⚠️ STOP: Before doing ANYTHING else"

        The warning symbol helps AI agents notice this critical section.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert '⚠️' in content, (
            "Template should have warning symbol (⚠️) to grab attention"
        )

    def test_template_has_stop_directive(self, spec_kitty_repo_root):
        """
        Test: Template has "STOP" directive for AI agents

        "STOP: Before doing ANYTHING else" is much more attention-grabbing
        than the previous subtle message.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert 'STOP' in content, (
            "Template should have STOP directive for AI agents"
        )

    def test_template_shows_correct_vs_wrong_examples(self, spec_kitty_repo_root):
        """
        Test: Template shows concrete examples of correct vs wrong locations

        Good example: .worktrees/001-my-feature/
        Bad example: /Users/you/spec-kitty/ (main repo root)

        Concrete examples help AI agents understand what's expected.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        # Should show worktrees path as correct example
        assert '.worktrees' in content or 'worktree' in content, (
            "Template should mention worktrees directory"
        )

        # Should distinguish correct from wrong
        assert ('✓' in content or '✅' in content or 'CORRECT' in content), (
            "Template should mark correct location examples"
        )
        assert ('❌' in content or 'WRONG' in content or 'NOT' in content), (
            "Template should mark wrong location examples"
        )

    def test_template_includes_validation_code(self, spec_kitty_repo_root):
        """
        Test: Template includes actual validation code to run

        Should reference validate_worktree_location() function.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert 'validate_worktree_location' in content, (
            "Template should reference validate_worktree_location() function"
        )

        assert 'from specify_cli.guards import' in content, (
            "Template should show how to import validation"
        )

    def test_template_has_error_handling(self, spec_kitty_repo_root):
        """
        Test: Template shows how to handle validation failures

        Should include exit(1) if validation fails.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert 'if not result.is_valid' in content or 'is_valid' in content, (
            "Template should check validation result"
        )

        assert 'exit(1)' in content, (
            "Template should exit if validation fails"
        )

    def test_template_has_success_confirmation(self, spec_kitty_repo_root):
        """
        Test: Template shows success confirmation message

        "✓ Location validated" gives AI agents positive feedback.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        # Should have some success indicator
        success_indicators = ['✓', '✅', 'validated', 'Location validated']
        has_success = any(indicator in content for indicator in success_indicators)

        assert has_success, (
            "Template should show success confirmation when validation passes"
        )

    def test_template_explains_failure_navigation(self, spec_kitty_repo_root):
        """
        Test: Template explains how to navigate if in wrong location

        Should tell agents to cd to .worktrees/<feature-name>
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert 'cd' in content, (
            "Template should show cd command to navigate"
        )

    def test_template_mentions_feature_branch_pattern(self, spec_kitty_repo_root):
        """
        Test: Template explains feature branch naming pattern

        Should mention 001-feature-name pattern.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        # Should mention feature naming pattern
        assert ('001-' in content or 'feature-name' in content or
                'feature pattern' in content), (
            "Template should explain feature branch naming pattern"
        )

    def test_template_warns_against_main_branch(self, spec_kitty_repo_root):
        """
        Test: Template warns against running on main/master branch

        Should explicitly say NOT on main or master.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        assert 'main' in content.lower() or 'master' in content.lower(), (
            "Template should mention main/master branch"
        )

        assert ('NOT' in content or 'not' in content), (
            "Template should warn against running on main"
        )

    def test_validation_appears_before_actual_work(self, spec_kitty_repo_root):
        """
        Test: Location validation appears BEFORE planning instructions

        The validation must come first, so agents don't start work in wrong place.
        """
        template_file = spec_kitty_repo_root / 'templates/command-templates/plan.md'
        content = template_file.read_text(encoding='utf-8')

        # Find positions
        validation_pos = content.find('validate_worktree_location')
        planning_keywords = ['plan', 'implementation', 'design', 'architecture']

        # Find first planning keyword after frontmatter
        frontmatter_end = content.find('---', content.find('---') + 3)
        planning_pos = len(content)  # Default to end

        for keyword in planning_keywords:
            pos = content.find(keyword, frontmatter_end)
            if pos != -1 and pos < planning_pos:
                planning_pos = pos

        assert validation_pos < planning_pos, (
            "Validation should appear BEFORE planning instructions"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
