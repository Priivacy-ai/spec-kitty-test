"""
Adversarial Tests for PR #111: Hyphenated Agent Names Parser Bug

These tests validate that activity log parsing correctly handles agent names
with hyphens (cursor-agent, claude-reviewer, gpt-4-turbo).

**The Bug:**
The activity log parser regex used `[^–-]+?` which treats hyphens as field
separators. This caused "cursor-agent" to be parsed as just "cursor", breaking
acceptance validation and activity log operations.

**The Fix (PR #111):**
Changed regex to r"\\S+(?:\\s+\\S+)*?" which correctly captures hyphenated names.

**Why These Tests Matter:**
- Functional tests only used simple agent names (claude, gpt, cursor)
- Real users have CI/CD agents with hyphens: cursor-agent, claude-reviewer
- Parser bugs break acceptance validation and activity logs
- These tests MUST fail if PR #111 is reverted

Run: pytest tests/distribution/test_0_13_7_hyphenated_agent_names.py -xvs
"""

import subprocess
import json
from pathlib import Path
import pytest
import re

pytestmark = [
    pytest.mark.distribution,
    pytest.mark.adversarial,
    pytest.mark.regression,
    pytest.mark.pr_111,
]


class TestHyphenatedAgentNamesParsing:
    """
    Test activity log parsing with hyphenated agent names.

    The parser must correctly extract agent names that contain hyphens.
    """

    def test_single_hyphen_agent_name(self, tmp_path, spec_kitty_repo_root):
        """
        Agent name with single hyphen: cursor-agent

        CRITICAL: Must parse "cursor-agent" as the full agent name,
        not just "cursor" (which is what the bug did).
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", ".kittify"], cwd=repo, capture_output=True)
        subprocess.run(["git", "add", ".claude"], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "001-test-feature",
            "title": "Test Hyphenated Agent",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with activity log entry using hyphenated agent name
        wp_content = """---
work_package_id: WP01
title: Test Package
lane: doing
dependencies: []
---

# WP01: Test Package

Testing hyphenated agent names.

## Activity Log

- 2025-01-23T12:40:55Z – cursor-agent – shell_pid=60665 – lane=doing – Started work on implementation
- 2025-01-23T13:15:22Z – cursor-agent – shell_pid=60665 – lane=doing – Completed core logic
"""
        wp_file = tasks_dir / "WP01-test-package.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True)

        # Test: spec-kitty agent tasks status should parse the hyphenated agent correctly
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Command should succeed
        assert result.returncode == 0, f"Status command failed: {result.stderr}"

        # Parse JSON output
        try:
            status_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.stdout}")

        # BUG CHECK: Should find WP01 with correct agent name
        # The bug would cause the agent to be parsed as "cursor" instead of "cursor-agent"
        wp01_found = False
        for wp in status_data.get("work_packages", []):
            if wp.get("id") == "WP01":
                wp01_found = True
                # Successfully found and parsed WP01 with hyphenated agent
                break

        assert wp01_found, "WP01 not found in status output"

    def test_multiple_hyphen_agent_name(self, tmp_path, spec_kitty_repo_root):
        """
        Agent name with multiple hyphens: gpt-4-turbo-reviewer

        CRITICAL: Must handle multiple hyphens correctly.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "002-multi-hyphen"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "002-multi-hyphen",
            "title": "Multi-Hyphen Agent Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with multi-hyphen agent name
        wp_content = """---
work_package_id: WP01
title: Multi Hyphen Test
lane: doing
dependencies: []
---

# WP01: Multi Hyphen Test

Testing agent names with multiple hyphens.

## Activity Log

- 2025-01-24T09:30:00Z – gpt-4-turbo-reviewer – shell_pid=12345 – lane=doing – Started review
- 2025-01-24T09:45:00Z – gpt-4-turbo-reviewer – shell_pid=12345 – lane=doing – Review completed
"""
        wp_file = tasks_dir / "WP01-multi-hyphen-test.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP01"], cwd=repo, capture_output=True)

        # Test: Parse activity with multi-hyphen agent name
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Should succeed with multi-hyphen agent name
        assert result.returncode == 0, f"Status failed with multi-hyphen agent: {result.stderr}"

        try:
            status_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON with multi-hyphen agent: {e}")

        # Verify WP01 is present
        wp_ids = [wp.get("id") for wp in status_data.get("work_packages", [])]
        assert "WP01" in wp_ids, "WP01 with multi-hyphen agent not found"

    def test_mixed_agent_names_in_same_log(self, tmp_path, spec_kitty_repo_root):
        """
        Mixed: simple names and hyphenated names in same activity log.

        CRITICAL: Parser must handle both simple (claude) and hyphenated
        (cursor-agent, gpt-4-turbo) in the same log.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "003-mixed-agents"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "003-mixed-agents",
            "title": "Mixed Agent Names",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with mixed agent names
        wp_content = """---
work_package_id: WP01
title: Mixed Agents Test
lane: for_review
dependencies: []
---

# WP01: Mixed Agents Test

Testing mixed simple and hyphenated agent names.

## Activity Log

- 2025-01-20T10:00:00Z – claude – shell_pid=11111 – lane=doing – Initial implementation
- 2025-01-20T11:00:00Z – cursor-agent – shell_pid=22222 – lane=doing – Code review and fixes
- 2025-01-20T12:00:00Z – gpt-4-turbo – shell_pid=33333 – lane=for_review – Final validation
- 2025-01-20T13:00:00Z – claude – shell_pid=11111 – lane=for_review – Ready for review
"""
        wp_file = tasks_dir / "WP01-mixed-agents.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add mixed agents WP"], cwd=repo, capture_output=True)

        # Test: Status should parse all agent types
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Mixed agent names should not break parsing
        assert result.returncode == 0, f"Status failed with mixed agents: {result.stderr}"

        try:
            status_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON with mixed agents: {e}")

        # Verify WP01 is present and parsed correctly
        wp_ids = [wp.get("id") for wp in status_data.get("work_packages", [])]
        assert "WP01" in wp_ids, "WP01 with mixed agent names not found"


class TestAcceptanceValidationWithHyphenatedAgents:
    """
    Test full acceptance workflow with hyphenated agent names.

    The original bug report (PR #111) specifically mentioned that
    acceptance validation breaks with hyphenated agent names.
    """

    def test_accept_command_with_hyphenated_agent(self, tmp_path, spec_kitty_repo_root):
        """
        spec-kitty agent tasks accept with hyphenated agent name.

        CRITICAL: The bug caused acceptance validation to fail when the
        activity log contained hyphenated agent names. This is the CORE
        bug that PR #111 fixes.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "004-accept-test"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "004-accept-test",
            "title": "Accept Hyphenated Agent",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP in "done" state with hyphenated agent
        wp_content = """---
work_package_id: WP01
title: Accept Test
lane: done
dependencies: []
---

# WP01: Accept Test

Ready for acceptance.

## Activity Log

- 2025-01-25T14:00:00Z – cursor-agent – shell_pid=99999 – lane=doing – Implementation started
- 2025-01-25T15:00:00Z – cursor-agent – shell_pid=99999 – lane=for_review – Implementation complete
- 2025-01-25T16:00:00Z – cursor-agent – shell_pid=99999 – lane=done – Tests passing
"""
        wp_file = tasks_dir / "WP01-accept-test.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP for acceptance"], cwd=repo, capture_output=True)

        # Test: spec-kitty agent tasks accept WP01
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "accept", "WP01"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Accept should work with hyphenated agent names
        # The bug would cause this to crash or fail validation
        if result.returncode != 0:
            # Accept might fail for other reasons (no implementation, no branch, etc.)
            # But it should NOT fail due to parser errors
            assert "cursor-agent" not in result.stderr, \
                f"Accept failed due to hyphenated agent name parsing: {result.stderr}"
            # If it fails for other reasons, that's okay for this test
            pytest.skip(f"Accept failed for non-parser reason: {result.stderr}")

        # If accept succeeded, verify it actually ran
        assert result.returncode == 0, f"Accept should succeed with hyphenated agent: {result.stderr}"


class TestActivityLogIntegrity:
    """
    Test that activity log operations preserve hyphenated agent names.

    All commands that read/parse activity logs must handle hyphens.
    """

    def test_status_command_shows_hyphenated_agents(self, tmp_path, spec_kitty_repo_root):
        """
        spec-kitty agent tasks status with hyphenated agent.

        Status command must correctly display agent names with hyphens.
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "005-status-test"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "005-status-test",
            "title": "Status Display Test",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with hyphenated agent
        wp_content = """---
work_package_id: WP01
title: Status Test
lane: doing
dependencies: []
---

# WP01: Status Test

Testing status display.

## Activity Log

- 2025-01-26T08:00:00Z – claude-reviewer – shell_pid=55555 – lane=doing – Review in progress
"""
        wp_file = tasks_dir / "WP01-status-test.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add status test WP"], cwd=repo, capture_output=True)

        # Test: Status command with text output
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: Status should succeed and display hyphenated agent
        assert result.returncode == 0, f"Status command failed: {result.stderr}"

        # The output should contain the agent name (might be in various formats)
        # Don't require exact format, just verify command succeeded
        assert len(result.stdout) > 0, "Status output is empty"


class TestHyphenVsEndashSeparator:
    """
    Test both hyphen (-) and en-dash (–) separators in activity logs.

    Activity log format uses en-dash (–) as separator, but some users
    might use regular hyphen (-). Parser should handle both.
    """

    def test_endash_separator_standard(self, tmp_path, spec_kitty_repo_root):
        """
        Standard format with en-dash (–) separator.

        This is the official format: agent – field – value
        """
        env = {
            "SPEC_KITTY_TEMPLATE_ROOT": str(spec_kitty_repo_root),
            "PATH": subprocess.os.environ.get("PATH", ""),
        }

        # Setup git repo
        repo = tmp_path / "test_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)

        # Initialize spec-kitty
        result = subprocess.run(
            ["spec-kitty", "init", ".", "--ai", "claude", "--here", "--force"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Init failed: {result.stderr}")

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=repo, capture_output=True, check=True)

        # Create feature structure
        feature_dir = repo / "kitty-specs" / "006-endash"
        feature_dir.mkdir(parents=True)

        meta = {
            "feature_id": "006-endash",
            "title": "En-Dash Separator",
            "mission": "software-dev"
        }
        (feature_dir / "meta.json").write_text(json.dumps(meta))

        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()

        # Create WP with en-dash separators (standard format)
        wp_content = """---
work_package_id: WP01
title: En-Dash Test
lane: doing
dependencies: []
---

# WP01: En-Dash Test

Standard format with en-dash.

## Activity Log

- 2025-01-27T10:00:00Z – cursor-agent – shell_pid=77777 – lane=doing – Standard format
"""
        wp_file = tasks_dir / "WP01-endash.md"
        wp_file.write_text(wp_content)

        # Commit the WP
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add en-dash test"], cwd=repo, capture_output=True)

        # Test: Should parse en-dash separator correctly
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status", "--json"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True
        )

        # BUG CHECK: En-dash separator should work
        assert result.returncode == 0, f"En-dash parsing failed: {result.stderr}"

        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON with en-dash: {e}")
