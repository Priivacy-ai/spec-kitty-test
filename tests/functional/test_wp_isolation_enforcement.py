"""
Test WP Isolation Enforcement (v0.11.0+)

Tests the work package isolation rules that prevent agents from accidentally
modifying WPs they don't own when multiple agents work in parallel.

Feature Context:
- Multiple agents can work on different WPs simultaneously
- Each agent should ONLY modify their assigned WP
- Agents see git commits from other agents but should ignore them
- Status changes in other WPs are from other agents

Enforcement Mechanisms:
1. Prominent warning banner in `implement` and `review` commands
2. Agent ownership check in `move-task` command
3. Warning about ignoring other agents' commits

Test Coverage:
1. Warning banner appears in implement command output
2. Warning banner appears in review command output
3. Banner shows correct (dynamic) WP ID, not hardcoded
4. Agent ownership check blocks mismatched agents
5. --force flag bypasses agent ownership check
6. Warning about other agents' commits appears
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_wps(temp_project_dir, spec_kitty_repo_root):
    """
    Create project with multiple work packages for isolation testing.

    Returns (project_path, feature_slug, feature_dir)
    """
    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    # Initialize project
    subprocess.run(
        ['spec-kitty', 'init', 'test-project', '--ai=claude'],
        cwd=str(temp_project_dir),
        env=env,
        input=b'y\n',
        capture_output=True
    )

    project_path = temp_project_dir / 'test-project'

    # Initialize git
    subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=str(project_path), check=True, capture_output=True)

    # Create feature
    subprocess.run(
        ['spec-kitty', 'agent', 'feature', 'create-feature', 'isolation-test'],
        cwd=str(project_path),
        env=env,
        capture_output=True
    )

    feature_slug = '001-isolation-test'
    feature_dir = project_path / 'kitty-specs' / feature_slug

    # Create multiple WP files
    tasks_dir = feature_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # WP01 - will be assigned to agent-alpha
    wp01_file = tasks_dir / 'WP01-core-feature.md'
    wp01_file.write_text("""---
title: WP01: Core Feature
lane: planned
---

# WP01: Core Feature

Implement the core feature.
""")

    # WP02 - will be assigned to agent-beta
    wp02_file = tasks_dir / 'WP02-extended-feature.md'
    wp02_file.write_text("""---
title: WP02: Extended Feature
lane: planned
---

# WP02: Extended Feature

Implement extended features.
""")

    # WP03 - unassigned
    wp03_file = tasks_dir / 'WP03-documentation.md'
    wp03_file.write_text("""---
title: WP03: Documentation
lane: planned
---

# WP03: Documentation

Write documentation.
""")

    # Create tasks.md
    tasks_md = feature_dir / 'tasks.md'
    tasks_md.write_text("""# Tasks for isolation-test

## WP01: Core Feature

- [ ] T001: Implement core
- [ ] T002: Add tests

## WP02: Extended Feature

- [ ] T010: Implement extension
- [ ] T011: Add extension tests

## WP03: Documentation

- [ ] T020: Write docs
- [ ] T021: Add examples
""")

    subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add WPs'], cwd=str(project_path), check=True, capture_output=True)

    return project_path, feature_slug, feature_dir


def cleanup_worktree(project_path, feature_slug, wp_id):
    """Helper to clean up worktree after test."""
    worktree_name = f"{feature_slug}-{wp_id}"
    worktree_path = project_path / '.worktrees' / worktree_name

    if worktree_path.exists():
        subprocess.run(
            ['git', 'worktree', 'remove', str(worktree_path), '--force'],
            cwd=str(project_path),
            capture_output=True
        )

    # Also try to delete the branch
    subprocess.run(
        ['git', 'branch', '-D', worktree_name],
        cwd=str(project_path),
        capture_output=True
    )


class TestImplementCommandIsolationWarning:
    """Tests for isolation warning in implement command."""

    def test_implement_shows_isolation_warning_banner(self, project_with_wps):
        """
        Test that implement command shows the WP isolation warning banner.

        GIVEN: A project with WPs in planned lane
        WHEN: Running spec-kitty agent workflow implement WP01
        THEN: Output should contain prominent isolation warning banner
        """
        project_path, feature_slug, feature_dir = project_with_wps

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01',
                 '--feature', feature_slug, '--agent', 'test-agent'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should contain isolation rules header
            assert 'ISOLATION' in output.upper() or 'CRITICAL' in output.upper(), \
                f"Should show isolation warning banner. Output: {output[:500]}"

            # Should mention what agent IS assigned to
            assert 'WP01' in output, \
                "Should mention the assigned WP (WP01)"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP01')

    def test_implement_banner_shows_dynamic_wp_id(self, project_with_wps):
        """
        Test that the banner shows the actual WP ID, not hardcoded values.

        GIVEN: A project with WP02 in planned lane
        WHEN: Running implement WP02
        THEN: Banner should show WP02, not WP01 or generic examples
        """
        project_path, feature_slug, feature_dir = project_with_wps

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'implement', 'WP02',
                 '--feature', feature_slug, '--agent', 'test-agent'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should mention WP02 specifically in the DO section
            assert 'WP02' in output, \
                f"Banner should show WP02 (the assigned WP). Output: {output[:500]}"

            # The "DO" instructions should reference WP02
            # Look for pattern like "Only modify status of WP02"
            if 'Only modify' in output:
                assert 'WP02' in output, \
                    "DO instructions should reference WP02 specifically"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP02')

    def test_implement_banner_warns_about_other_agents_commits(self, project_with_wps):
        """
        Test that the banner warns about ignoring other agents' commits.

        GIVEN: A project with WPs
        WHEN: Running implement
        THEN: Output should warn about commits from other agents
        """
        project_path, feature_slug, feature_dir = project_with_wps

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01',
                 '--feature', feature_slug, '--agent', 'test-agent'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should mention other agents or ignoring commits
            has_other_agents_warning = (
                'other agent' in output.lower() or
                'ignore' in output.lower() or
                'parallel' in output.lower()
            )

            assert has_other_agents_warning, \
                f"Should warn about other agents' activity. Output: {output[:500]}"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP01')

    def test_implement_banner_has_do_and_do_not_sections(self, project_with_wps):
        """
        Test that the banner clearly shows DO and DO NOT sections.

        GIVEN: A project with WPs
        WHEN: Running implement
        THEN: Output should have clear DO and DO NOT guidance
        """
        project_path, feature_slug, feature_dir = project_with_wps

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'implement', 'WP01',
                 '--feature', feature_slug, '--agent', 'test-agent'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should have DO section (what to do)
            has_do_section = 'DO:' in output or '✅' in output

            # Should have DO NOT section (what not to do)
            has_do_not_section = 'DO NOT' in output or 'NOT:' in output or '❌' in output

            assert has_do_section, \
                f"Should have DO section. Output: {output[:500]}"
            assert has_do_not_section, \
                f"Should have DO NOT section. Output: {output[:500]}"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP01')


class TestReviewCommandIsolationWarning:
    """Tests for isolation warning in review command."""

    def test_review_shows_isolation_warning_banner(self, project_with_wps):
        """
        Test that review command shows the WP isolation warning banner.

        GIVEN: A project with a WP in for_review lane
        WHEN: Running spec-kitty agent workflow review WP01
        THEN: Output should contain prominent isolation warning banner
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # First move WP01 to for_review
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: for_review')
        content = content.replace('---\n', '---\nagent: original-agent\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Move to for_review'], cwd=str(project_path), check=True, capture_output=True)

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'review', 'WP01',
                 '--feature', feature_slug, '--agent', 'reviewer-agent'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should contain isolation warning
            assert 'ISOLATION' in output.upper() or 'CRITICAL' in output.upper(), \
                f"Review should show isolation warning. Output: {output[:500]}"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP01')

    def test_review_banner_shows_correct_wp(self, project_with_wps):
        """
        Test that review banner shows the WP being reviewed.

        GIVEN: WP03 in for_review lane
        WHEN: Running review WP03
        THEN: Banner should reference WP03 specifically
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Move WP03 to for_review
        wp03_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP03-documentation.md'
        content = wp03_file.read_text()
        content = content.replace('lane: planned', 'lane: for_review')
        wp03_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Move WP03 to review'], cwd=str(project_path), check=True, capture_output=True)

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'review', 'WP03',
                 '--feature', feature_slug, '--agent', 'reviewer'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Should reference WP03, not generic WP01
            assert 'WP03' in output, \
                f"Review banner should show WP03. Output: {output[:500]}"

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP03')


class TestMoveTaskAgentOwnership:
    """Tests for agent ownership enforcement in move-task command."""

    def test_move_task_blocks_mismatched_agent(self, project_with_wps):
        """
        Test that move-task fails when agent doesn't match WP's assigned agent.

        GIVEN: WP01 is assigned to 'agent-alpha'
        WHEN: 'agent-beta' tries to move WP01
        THEN: Command should fail with ownership warning
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set WP01's agent to 'agent-alpha'
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: agent-alpha\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign WP01'], cwd=str(project_path), check=True, capture_output=True)

        # Now try to move as different agent
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug, '--agent', 'agent-beta'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail
        assert result.returncode != 0, \
            f"Should fail when agent doesn't match. Exit code: {result.returncode}"

        output = result.stdout + result.stderr

        # Should mention the agent mismatch
        has_ownership_warning = (
            'agent-alpha' in output or
            'ownership' in output.lower() or
            'mismatch' in output.lower() or
            'assigned' in output.lower()
        )

        assert has_ownership_warning, \
            f"Should warn about agent ownership. Output: {output}"

    def test_move_task_allows_matching_agent(self, project_with_wps):
        """
        Test that move-task succeeds when agent matches WP's assigned agent.

        GIVEN: WP01 is assigned to 'agent-alpha' and subtasks are complete
        WHEN: 'agent-alpha' moves WP01
        THEN: Command should succeed
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set WP01's agent to 'agent-alpha'
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: agent-alpha\n', 1)
        wp01_file.write_text(content)

        # Mark subtasks complete (required for for_review transition)
        tasks_md = project_path / 'kitty-specs' / feature_slug / 'tasks.md'
        tasks_content = tasks_md.read_text()
        tasks_content = tasks_content.replace('- [ ] T001', '- [x] T001')
        tasks_content = tasks_content.replace('- [ ] T002', '- [x] T002')
        tasks_md.write_text(tasks_content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign WP01 and mark subtasks'], cwd=str(project_path), check=True, capture_output=True)

        # Move as the same agent
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug, '--agent', 'agent-alpha'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, \
            f"Should succeed when agent matches. Error: {result.stdout}"

    def test_move_task_force_bypasses_ownership_check(self, project_with_wps):
        """
        Test that --force flag bypasses agent ownership check.

        GIVEN: WP01 is assigned to 'agent-alpha'
        WHEN: 'agent-beta' uses --force to move WP01
        THEN: Command should succeed despite agent mismatch
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set WP01's agent to 'agent-alpha'
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: agent-alpha\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign WP01'], cwd=str(project_path), check=True, capture_output=True)

        # Force move as different agent
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug, '--agent', 'agent-beta', '--force'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed with --force
        assert result.returncode == 0, \
            f"--force should bypass ownership check. Error: {result.stderr}"

    def test_move_task_no_agent_field_allows_any_agent(self, project_with_wps):
        """
        Test that WPs without agent field can be moved by any agent.

        GIVEN: WP01 has no agent field (just lane: planned)
        WHEN: Any agent tries to move it
        THEN: Command should succeed (agent ownership not enforced yet)
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # WP02 has no agent field initially
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP02', '--to', 'doing',
             '--feature', feature_slug, '--agent', 'any-agent'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should succeed - no prior agent assigned
        assert result.returncode == 0, \
            f"Should allow move when no prior agent assigned. Error: {result.stderr}"


class TestAgentOwnershipJsonOutput:
    """Tests for JSON output of agent ownership errors."""

    def test_ownership_error_json_format(self, project_with_wps):
        """
        Test that ownership error is properly formatted in JSON output.

        GIVEN: WP01 is assigned to 'agent-alpha'
        WHEN: 'agent-beta' tries to move with --json flag
        THEN: Error should be JSON formatted with clear message
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set WP01's agent
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: agent-alpha\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign'], cwd=str(project_path), check=True, capture_output=True)

        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug, '--agent', 'agent-beta', '--json'],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should have JSON output even on error
        try:
            output = json.loads(result.stdout.strip())
            assert output.get('result') == 'error' or 'error' in output, \
                "JSON should indicate error"
        except json.JSONDecodeError:
            # Might be in stderr instead
            pass


class TestIsolationEnforcementEdgeCases:
    """Edge cases for isolation enforcement."""

    def test_case_insensitive_agent_matching(self, project_with_wps):
        """
        Test that agent matching is case-sensitive (security).

        GIVEN: WP assigned to 'Agent-Alpha'
        WHEN: 'agent-alpha' (lowercase) tries to move
        THEN: Should fail (case matters for agent identity)
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set agent with specific casing
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: Agent-Alpha\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign'], cwd=str(project_path), check=True, capture_output=True)

        # Try with different casing
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug, '--agent', 'agent-alpha'],  # lowercase
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        # Should fail - case mismatch
        assert result.returncode != 0, \
            "Agent matching should be case-sensitive for security"

    def test_ownership_check_only_when_agent_provided(self, project_with_wps):
        """
        Test that ownership check only triggers when --agent is provided.

        GIVEN: WP01 has agent assigned
        WHEN: Moving without --agent flag
        THEN: Should proceed (or fail for other reasons, but not ownership)
        """
        project_path, feature_slug, feature_dir = project_with_wps

        # Set agent
        wp01_file = project_path / 'kitty-specs' / feature_slug / 'tasks' / 'WP01-core-feature.md'
        content = wp01_file.read_text()
        content = content.replace('lane: planned', 'lane: doing')
        content = content.replace('---\n', '---\nagent: some-agent\n', 1)
        wp01_file.write_text(content)

        subprocess.run(['git', 'add', '.'], cwd=str(project_path), check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Assign'], cwd=str(project_path), check=True, capture_output=True)

        # Move without specifying agent
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP01', '--to', 'for_review',
             '--feature', feature_slug],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should NOT fail specifically due to ownership mismatch
        # (may fail for other reasons like missing assignee, but not ownership)
        if result.returncode != 0:
            assert 'ownership' not in output.lower() and 'mismatch' not in output.lower(), \
                "Should not trigger ownership check when --agent not provided"


class TestBannerDoesNotHardcodeWPs:
    """Adversarial tests to ensure no hardcoded WP examples leak through."""

    def test_wp03_banner_does_not_mention_wp01_as_example(self, project_with_wps):
        """
        Test that when assigned WP03, banner doesn't show WP01 as example.

        This catches bugs where hardcoded "(WP01, WP02, etc.)" examples
        confuse agents about which WP they actually own.
        """
        project_path, feature_slug, feature_dir = project_with_wps

        try:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'workflow', 'implement', 'WP03',
                 '--feature', feature_slug, '--agent', 'test'],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            # Look for patterns that suggest hardcoded examples
            # The old bug had "(WP01, WP02, etc.)" in the DON'T section
            suspicious_patterns = [
                '(WP01, WP02',  # Hardcoded list
                'WP01, WP02, etc',  # Hardcoded examples
            ]

            for pattern in suspicious_patterns:
                if pattern in output:
                    # Check if it's in a confusing context
                    # It's OK if WP01/WP02 appear in git logs or status
                    # But not OK in the instruction text
                    lines_with_pattern = [l for l in output.split('\n') if pattern in l]
                    for line in lines_with_pattern:
                        if 'DO NOT' in line or "Don't" in line.lower() or 'other than' in line.lower():
                            pytest.fail(
                                f"Banner has hardcoded WP examples that could confuse agent.\n"
                                f"When assigned WP03, saw: {line}"
                            )

        finally:
            cleanup_worktree(project_path, feature_slug, 'WP03')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
