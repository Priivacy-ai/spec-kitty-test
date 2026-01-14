---
work_package_id: WP03
title: Multi-Agent Synchronization
lane: "for_review"
dependencies:
- WP01
- WP02
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 1 - Sparse-Checkout Track (Risk-First)
assignee: ''
agent: "codex"
shell_pid: "10701"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-14T20:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Multi-Agent Synchronization

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` in the frontmatter.
- **Report progress**: Update Activity Log explaining changes made.

---

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-01-14

**Issue 1**: `test_pid_tracking_in_activity_log` does not enforce that `shell_pid` is present. The test currently treats missing `shell_pid` as informational and passes, but the success criteria explicitly require validating PID tracking in the activity log. Make this assertion hard-fail when `shell_pid` is absent.

**Issue 2**: The required test command fails in the WP review worktree because the `spec_kitty_repo_root` fixture defaults to a path that doesn't exist in `.worktrees`. Either set `SPEC_KITTY_REPO` (or equivalent) inside the test run/setup, or update the fixture to resolve the main repo root when running from a worktree so `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs` passes as required.


## Objectives & Success Criteria

**Primary Objective**: Implement Suite 4 (Multi-Agent Parallel) tests validating parallel agent synchronization via auto-commit to main repository.

**Success Criteria**:
- ✅ 8/8 multi-agent tests implemented in TestMultiAgentParallel class
- ✅ `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs` shows 8/8 PASSED
- ✅ Tests validate: parallel agents see each other's status changes, subtask completion synchronized, lane changes visible, PID tracking captured, review feedback inserted
- ✅ Each test has clear docstring referencing implementation code
- ✅ All assertions include debugging context
- ✅ Tests use sequential simulation (deterministic, not flaky)
- ✅ Bugs found documented in findings/test-infrastructure/v0.12.0-bugs-found.md

**Why Risk-First**: Multi-agent synchronization is the CORE value proposition of sparse-checkout. If agents see divergent state (Agent A's changes invisible to Agent B), the entire workspace-per-WP architecture fails. Better to discover synchronization bugs now than after users experience data loss or conflicting work.

---

## Context & Constraints

### Related Documents
- **Implementation Reference**: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/workflow.py lines 217-218 (PID capture)
- **Activity Log Reference**: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks_support.py lines 201-222 (activity log parsing)
- **Auto-Commit Reference**: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py lines 432-475 (move-task), 557-592 (mark-status)
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (FR-001 Suite 4 requirements)
- **Plan**: kitty-specs/001-critical-test-coverage-v012/plan.md (adversarial testing philosophy)

### Implementation Code Behavior (from codebase analysis)
- **Auto-commit synchronization**: Commands commit changes to main, agents read from main (not worktree copy)
- **PID tracking**: os.getppid() captures shell PID, stored in frontmatter when claiming WP
- **Activity log**: Timestamp – agent – shell_pid=PID – lane=X – note format
- **Review feedback**: --review-feedback-file auto-inserts content into WP prompt Review Feedback section

### Adversarial Testing Mindset
- **EXPECT tests to fail** - synchronization bugs are common in distributed systems
- **Fail-fast**: Stop on first failure, investigate synchronization mechanism
- **Sequential simulation**: Simulate multi-agent via deterministic sequence (Agent A action → commit → Agent B reads → sees change)
- **Fix upstream**: Synchronization bugs in ~/Code/spec-kitty fixed before continuing
- **Document**: Every bug goes in findings/test-infrastructure/v0.12.0-bugs-found.md
- **Zero tolerance**: No xfails, no workarounds, all tests must genuinely pass

---

## Subtasks & Detailed Guidance

### Subtask T014 – Test Agent A claims WP01, Agent B claims WP02 → both see each other's status

**Purpose**: Validate parallel agents working on different WPs see each other's status changes through synchronized main repository.

**Steps**:

1. Create test in tests/functional/test_sparse_checkout_infrastructure.py:

```python
class TestMultiAgentParallel:
    """Validate multi-agent synchronization via auto-commit to main."""

    def test_parallel_agents_see_each_others_status(
        self,
        temp_project_dir,
        init_spec_kitty_project
    ):
        """
        Test: Agent A claims WP01, Agent B claims WP02 → both see each other

        Why: Multi-agent development requires visibility into what other agents
        are working on. Auto-commit to main should synchronize WP status so
        Agent A sees Agent B's claimed WP and vice versa.

        Reference: workflow.py:236-264 (implement command commits status)
        Related: Auto-commit synchronization mechanism
        """
        # 1. Initialize project with multiple WPs
        project = init_spec_kitty_project("multi-agent-test")

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0

        # 2. Create spec/plan/tasks with WP01 and WP02
        # (Feature creation should create tasks.md with WPs)

        # 3. Agent A claims WP01
        result_a = subprocess.run(
            ['spec-kitty', 'implement', 'WP01', '--agent=AgentA'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60
        )
        assert result_a.returncode == 0, f"Agent A claim failed: {result_a.stderr}"

        # 4. Agent B claims WP02
        result_b = subprocess.run(
            ['spec-kitty', 'implement', 'WP02', '--agent=AgentB'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60
        )
        assert result_b.returncode == 0, f"Agent B claim failed: {result_b.stderr}"

        # 5. Read tasks.md from main repo (source of truth)
        tasks_md = project / 'kitty-specs' / 'test-feature' / 'tasks' / 'tasks.md'
        assert tasks_md.exists(), f"tasks.md not found: {tasks_md}"

        tasks_content = tasks_md.read_text()

        # 6. Validate both WPs show as claimed (lane: doing)
        # Parse tasks.md for WP01 and WP02 status
        import yaml

        # Extract frontmatter sections (simple approach - find ---...--- blocks)
        # For real implementation, use proper YAML parsing

        assert 'WP01' in tasks_content, "WP01 not found in tasks.md"
        assert 'WP02' in tasks_content, "WP02 not found in tasks.md"
        assert 'AgentA' in tasks_content, "Agent A not recorded in tasks.md"
        assert 'AgentB' in tasks_content, "Agent B not recorded in tasks.md"

        # 7. Validate git commits recorded both claims
        result = subprocess.run(
            ['git', 'log', '--oneline', '-5'],
            cwd=project,
            capture_output=True,
            text=True
        )

        log_output = result.stdout
        assert 'WP01' in log_output or 'AgentA' in log_output, (
            f"Agent A claim not in git history\n"
            f"Log: {log_output}\n"
            f"If missing, auto-commit not working - CRITICAL BUG"
        )
        assert 'WP02' in log_output or 'AgentB' in log_output, (
            f"Agent B claim not in git history\n"
            f"Log: {log_output}"
        )

        # 8. From Agent A's worktree, verify can see Agent B's status
        worktrees = sorted((project / '.worktrees').glob('*'))
        assert len(worktrees) >= 2, f"Expected 2 worktrees, got {len(worktrees)}"

        agent_a_worktree = worktrees[0]  # First worktree (Agent A)

        # Read tasks.md from Agent A's perspective (should see main's version)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'task', 'list'],
            cwd=agent_a_worktree,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Output should show BOTH WP01 and WP02 with current status
        output = result.stdout
        assert 'WP01' in output, "Agent A can't see WP01 status"
        assert 'WP02' in output, (
            f"Agent A can't see WP02 (Agent B's work)\n"
            f"Output: {output}\n"
            f"Synchronization NOT working - agents see divergent state - CRITICAL BUG"
        )
```

2. Run test:
   ```bash
   pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel::test_parallel_agents_see_each_others_status -xvs
   ```

3. **EXPECTED**: Test may fail if synchronization reads from worktree copy instead of main

4. **If test fails**: Document bug in findings/, fix path resolution to read from main

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (add TestMultiAgentParallel class, ~60 lines)

**Parallel?**: Yes [P] - Can implement in parallel with T015-T021 (different synchronization aspects)

**Reference**: workflow.py:236-264 (implement command), tasks.py:39-68 (_get_main_repo_root for reading tasks.md from main)

---

### Subtask T015 – Test Agent A marks subtask done → Agent B sees change immediately

**Purpose**: Validate subtask completion synchronization across agents via auto-commit.

**Steps**:

1. Create test validating subtask synchronization:

```python
def test_subtask_completion_synchronized(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Agent A marks subtask done → Agent B sees change immediately

    Why: When Agent A completes a subtask, other agents must see this change
    immediately to avoid duplicate work. Requires auto-commit of task status
    to main and agents reading from main (not cached worktree copy).

    Reference: tasks.py:557-592 (mark-status auto-commit)
    Related: Status synchronization between worktrees
    """
    project = init_spec_kitty_project("subtask-sync-test")

    # Create feature with tasks
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Agent A claims WP01
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=AgentA'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Agent B claims WP02
    subprocess.run(['spec-kitty', 'implement', 'WP02', '--agent=AgentB'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = sorted((project / '.worktrees').glob('*'))
    agent_a_worktree = worktrees[0]
    agent_b_worktree = worktrees[1]

    # Agent A marks subtask T001 as done
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'mark-status', 'T001', '--status=done'],
        cwd=agent_a_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0, f"mark-status failed: {result.stderr}"

    # Validate auto-commit happened
    result = subprocess.run(
        ['git', 'log', '--oneline', '-1'],
        cwd=project,
        capture_output=True,
        text=True
    )
    log_output = result.stdout
    assert 'T001' in log_output or 'mark-status' in log_output, (
        f"Subtask completion not committed\n"
        f"Log: {log_output}\n"
        f"Auto-commit not working - BUG"
    )

    # Agent B reads tasks - should see T001 as done
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list'],
        cwd=agent_b_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    output = result.stdout
    # Check if T001 shows as completed (format depends on list output)
    assert 'T001' in output, "T001 not in task list"
    # More specific check: validate status is "done" (implementation specific)

    # Read tasks.md directly to verify
    tasks_md = project / 'kitty-specs' / 'test' / 'tasks' / 'tasks.md'
    tasks_content = tasks_md.read_text()

    assert 'T001' in tasks_content, "T001 not in tasks.md"
    # Validate T001 marked as done (format: - [x] T001 or status: done)
```

2. Run test, validate synchronization works

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~45 lines)

**Parallel?**: Yes [P]

**Reference**: tasks.py:557-592 (mark-status command commits to main)

---

### Subtask T016 – Test Agent A moves WP to for_review → Agent B sees lane change

**Purpose**: Validate lane transitions (planned → doing → for_review → done) synchronized across agents.

**Steps**:

1. Create test validating lane change synchronization:

```python
def test_lane_change_synchronized(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Agent A moves WP to for_review → Agent B sees lane change

    Why: Kanban lane changes signal workflow state to all agents. When Agent A
    moves WP01 to for_review, Agent B (potential reviewer) must see this
    immediately to pick up review work.

    Reference: tasks.py:432-475 (move-task auto-commits WP file)
    Related: Kanban board synchronization
    """
    project = init_spec_kitty_project("lane-sync-test")

    # Create feature
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Agent A claims WP01
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=AgentA'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Agent B claims WP02
    subprocess.run(['spec-kitty', 'implement', 'WP02', '--agent=AgentB'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = sorted((project / '.worktrees').glob('*'))
    agent_a_worktree = worktrees[0]
    agent_b_worktree = worktrees[1]

    # Agent A moves WP01 to for_review
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'move-task', 'WP01', '--to', 'for_review'],
        cwd=agent_a_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode == 0, f"move-task failed: {result.stderr}"

    # Validate auto-commit of WP01 file
    result = subprocess.run(
        ['git', 'log', '--oneline', '-1'],
        cwd=project,
        capture_output=True,
        text=True
    )
    log_output = result.stdout
    assert 'WP01' in log_output or 'for_review' in log_output, (
        f"Lane change not committed\n"
        f"Log: {log_output}"
    )

    # Agent B queries task status - should see WP01 in for_review
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list', '--lane=for_review'],
        cwd=agent_b_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    output = result.stdout
    assert 'WP01' in output, (
        f"Agent B can't see WP01 in for_review lane\n"
        f"Output: {output}\n"
        f"Lane change not synchronized - BUG"
    )

    # Read WP01 prompt file directly from main
    wp01_file = project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'
    # Use glob to find actual filename
    import glob
    wp_files = glob.glob(str(project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'))
    assert len(wp_files) == 1, f"Expected 1 WP01 file, found {len(wp_files)}"

    wp_content = Path(wp_files[0]).read_text()
    assert 'lane: "for_review"' in wp_content or "lane: 'for_review'" in wp_content, (
        f"WP01 frontmatter not updated\n"
        f"Expected lane: for_review\n"
        f"Content preview: {wp_content[:500]}"
    )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~50 lines)

**Parallel?**: Yes [P]

**Reference**: tasks.py:432-475 (move-task commits WP prompt file to main)

---

### Subtask T017 – Test three agents on WP01/02/03 → all synchronized via main

**Purpose**: Validate synchronization scales to 3+ concurrent agents.

**Steps**:

1. Create test with 3 agents:

```python
def test_three_agents_all_synchronized(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Three agents on WP01/02/03 → all synchronized via main

    Why: Synchronization must scale beyond 2 agents. Three agents working
    simultaneously should all see consistent state from main repository.

    Reference: tasks.py:39-68 (_get_main_repo_root ensures reading from main)
    Related: Multi-agent scalability
    """
    project = init_spec_kitty_project("three-agent-test")

    # Create feature with 3 WPs
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Claim WP01, WP02, WP03 with different agents
    for i, agent_name in enumerate(['AgentAlpha', 'AgentBeta', 'AgentGamma'], start=1):
        wp_id = f'WP0{i}'
        result = subprocess.run(
            ['spec-kitty', 'implement', wp_id, f'--agent={agent_name}'],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=60
        )
        assert result.returncode == 0, f"{agent_name} claim {wp_id} failed: {result.stderr}"

    worktrees = sorted((project / '.worktrees').glob('*'))
    assert len(worktrees) == 3, f"Expected 3 worktrees, got {len(worktrees)}"

    # Each agent performs action (move to for_review)
    for i, worktree in enumerate(worktrees, start=1):
        wp_id = f'WP0{i}'
        result = subprocess.run(
            ['spec-kitty', 'agent', 'task', 'move-task', wp_id, '--to', 'for_review'],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"move-task {wp_id} failed"

    # From any worktree, verify all 3 WPs visible in for_review
    test_worktree = worktrees[0]
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list', '--lane=for_review'],
        cwd=test_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    output = result.stdout
    for wp_id in ['WP01', 'WP02', 'WP03']:
        assert wp_id in output, (
            f"{wp_id} not visible from test worktree\n"
            f"Output: {output}\n"
            f"Multi-agent synchronization broken - CRITICAL BUG"
        )

    # Validate git history has all 6 commits (3 claims + 3 lane changes)
    result = subprocess.run(
        ['git', 'log', '--oneline', '-10'],
        cwd=project,
        capture_output=True,
        text=True
    )
    log_output = result.stdout

    # Should see references to all 3 WPs in recent history
    for wp_id in ['WP01', 'WP02', 'WP03']:
        assert wp_id in log_output, f"{wp_id} not in git history"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~55 lines)

**Parallel?**: Yes [P]

**Reference**: Multiple agents → multiple auto-commits, all visible via main

---

### Subtask T018 – Test agent claims WP with dependencies → validates base workspace exists

**Purpose**: Validate dependency checking during WP claim (can't claim WP03 if depends on WP02 which isn't done).

**Steps**:

1. Create test validating dependency enforcement:

```python
def test_dependency_validation_on_claim(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Agent claims WP with dependencies → validates base workspace exists

    Why: Work package dependencies prevent agents from working on WP03 before
    WP02 completes. System must validate dependencies satisfied before allowing
    worktree creation.

    Reference: workflow.py (implement command should check dependencies)
    Related: Work package dependency enforcement
    """
    project = init_spec_kitty_project("dependency-test")

    # Create feature
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Manually set WP03 to depend on WP02
    # (Edit WP03 prompt file to add dependencies: ["WP02"])
    # For test purposes, assume WP structure already has dependencies defined

    # Try to claim WP03 without WP02 being done
    result = subprocess.run(
        ['spec-kitty', 'implement', 'WP03', '--agent=AgentEarly'],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60
    )

    # EITHER: Should fail with dependency error
    # OR: Should warn but allow (depending on implementation)

    # Discovery test - learn current behavior
    if result.returncode != 0:
        # Expected: Dependency check failed
        error = result.stderr
        assert 'depend' in error.lower() or 'WP02' in error, (
            f"Error should mention dependency\n"
            f"Error: {error}"
        )
    else:
        # Allowed but should warn
        output = result.stdout + result.stderr
        # Check if warning issued (implementation specific)
        pass

    # Claim and complete WP02 first
    subprocess.run(['spec-kitty', 'implement', 'WP02', '--agent=AgentCorrect'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Move WP02 to done
    worktrees = list((project / '.worktrees').glob('*'))
    wp02_worktree = worktrees[0]
    subprocess.run(['spec-kitty', 'agent', 'task', 'move-task', 'WP02', '--to', 'done'],
                   cwd=wp02_worktree, capture_output=True, text=True, timeout=30, check=True)

    # Now claim WP03 - should succeed
    result = subprocess.run(
        ['spec-kitty', 'implement', 'WP03', '--agent=AgentCorrect'],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0, f"WP03 claim should succeed after WP02 done: {result.stderr}"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~45 lines)

**Parallel?**: Yes [P]

**Reference**: workflow.py (implement command should validate dependencies field from WP frontmatter)

---

### Subtask T019 – Test review feedback auto-inserted via --review-feedback-file

**Purpose**: Validate review feedback insertion mechanism during review workflow.

**Steps**:

1. Create test validating feedback insertion:

```python
def test_review_feedback_auto_inserted(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Review feedback auto-inserted via --review-feedback-file

    Why: When reviewer provides feedback, it must be inserted into WP prompt
    file's Review Feedback section automatically. Ensures implementer sees
    feedback without manual copy-paste.

    Reference: workflow.py (review command with --review-feedback-file option)
    Related: Review workflow automation
    """
    project = init_spec_kitty_project("feedback-test")

    # Create feature and implement WP01
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Implementer'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Move WP01 to for_review
    worktrees = list((project / '.worktrees').glob('*'))
    impl_worktree = worktrees[0]
    subprocess.run(['spec-kitty', 'agent', 'task', 'move-task', 'WP01', '--to', 'for_review'],
                   cwd=impl_worktree, capture_output=True, text=True, timeout=30, check=True)

    # Reviewer claims WP01 for review
    result = subprocess.run(
        ['spec-kitty', 'review', 'WP01', '--agent=Reviewer'],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0, f"Review claim failed: {result.stderr}"

    review_worktrees = sorted((project / '.worktrees').glob('*'))
    review_worktree = review_worktrees[1]  # Reviewer's worktree (second one)

    # Create feedback file
    feedback_file = review_worktree / 'review-feedback.md'
    feedback_file.write_text("""
## Issues Found

1. **Missing test coverage**: Add test for edge case X
2. **Performance concern**: Function Y has O(n²) complexity
3. **Documentation**: Update docstring for Z
""")

    # Submit review with feedback
    result = subprocess.run(
        ['spec-kitty', 'agent', 'workflow', 'submit-review', 'WP01',
         '--review-feedback-file', str(feedback_file),
         '--action=request_changes'],
        cwd=review_worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check if command exists (implementation specific)
    if result.returncode != 0 and 'not found' in result.stderr:
        pytest.skip("submit-review command not implemented yet")

    # Read WP01 prompt file from main
    import glob
    wp_files = glob.glob(str(project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'))
    assert len(wp_files) == 1
    wp_content = Path(wp_files[0]).read_text()

    # Validate feedback inserted into Review Feedback section
    assert '## Issues Found' in wp_content, (
        f"Review feedback not inserted into WP01 prompt\n"
        f"Expected feedback section with '## Issues Found'\n"
        f"Content preview: {wp_content[:1000]}"
    )
    assert 'Missing test coverage' in wp_content, "Specific feedback items not inserted"
    assert 'review_status: "has_feedback"' in wp_content or "review_status: 'has_feedback'" in wp_content, (
        f"review_status not updated to has_feedback"
    )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~50 lines)

**Parallel?**: Yes [P]

**Reference**: workflow.py (review command with --review-feedback-file parameter)

---

### Subtask T020 – Test PID tracking captured in frontmatter (via os.getppid())

**Purpose**: Validate shell PID captured when agent claims WP (for audit trail and process tracking).

**Steps**:

1. Create test validating PID capture:

```python
def test_pid_tracking_in_frontmatter(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: PID tracking captured in frontmatter via os.getppid()

    Why: Shell PID tracking enables audit trail (which shell/agent did what)
    and process management (detect hung agents, track concurrent work).

    Reference: workflow.py:217-218 (os.getppid() captures shell PID)
    Related: Process tracking and audit trail
    """
    project = init_spec_kitty_project("pid-test")

    # Create feature
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Claim WP01 (should capture PID)
    result = subprocess.run(
        ['spec-kitty', 'implement', 'WP01', '--agent=TestAgent'],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0, f"Implement failed: {result.stderr}"

    # Read WP01 prompt file
    import glob
    wp_files = glob.glob(str(project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'))
    assert len(wp_files) == 1, f"Expected 1 WP01 file, found {len(wp_files)}"

    wp_content = Path(wp_files[0]).read_text()

    # Validate shell_pid field in frontmatter
    # Should be non-empty numeric value
    import re
    pid_match = re.search(r'shell_pid:\s*"?(\d+)"?', wp_content)

    assert pid_match, (
        f"shell_pid not found in frontmatter\n"
        f"Expected: shell_pid: \"12345\" or shell_pid: 12345\n"
        f"Frontmatter preview: {wp_content[:500]}"
    )

    pid_value = pid_match.group(1)
    assert pid_value.isdigit(), f"PID should be numeric: {pid_value}"
    assert int(pid_value) > 0, f"PID should be positive: {pid_value}"

    # Validate PID is reasonable (not just placeholder)
    # Typical PID range: 1-99999 (varies by OS)
    pid_int = int(pid_value)
    assert 1 <= pid_int <= 999999, f"PID {pid_int} outside reasonable range"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~40 lines)

**Parallel?**: Yes [P]

**Reference**: workflow.py:217-218 (shell_pid = os.getppid())

---

### Subtask T021 – Test PID tracking in activity log (format: timestamp – agent – shell_pid=PID – lane=X – note)

**Purpose**: Validate activity log entries include PID tracking for audit trail.

**Steps**:

1. Create test validating activity log format:

```python
def test_pid_tracking_in_activity_log(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: PID tracking in activity log (timestamp – agent – shell_pid=PID – lane – note)

    Why: Activity log provides chronological audit trail. PID in each entry
    enables correlation with shell sessions, debugging concurrent work,
    and identifying which agent performed which action.

    Reference: tasks_support.py:181-198 (append_activity_log format)
    Related: Activity log parsing and audit trail
    """
    project = init_spec_kitty_project("pid-log-test")

    # Create feature and claim WP
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=AgentPID'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Perform lane change to add activity log entry
    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]
    subprocess.run(['spec-kitty', 'agent', 'task', 'move-task', 'WP01', '--to', 'for_review'],
                   cwd=worktree, capture_output=True, text=True, timeout=30, check=True)

    # Read WP01 prompt file
    import glob
    wp_files = glob.glob(str(project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'))
    assert len(wp_files) == 1
    wp_content = Path(wp_files[0]).read_text()

    # Find Activity Log section
    assert 'Activity Log' in wp_content or '## Activity Log' in wp_content, (
        f"Activity Log section not found in WP01"
    )

    # Extract activity log entries (lines starting with -)
    import re
    log_entries = re.findall(r'^- \d{4}-\d{2}-\d{2}T.*$', wp_content, re.MULTILINE)

    assert len(log_entries) >= 2, (
        f"Expected at least 2 activity log entries (creation + lane change)\n"
        f"Found: {len(log_entries)}\n"
        f"Entries: {log_entries}"
    )

    # Validate latest entry has shell_pid
    latest_entry = log_entries[-1]

    # Format: - YYYY-MM-DDTHH:MM:SSZ – agent_id – shell_pid=12345 – lane=for_review – note
    assert 'shell_pid=' in latest_entry or 'shell_pid =' in latest_entry, (
        f"Activity log entry missing shell_pid\n"
        f"Entry: {latest_entry}\n"
        f"Expected format: timestamp – agent – shell_pid=PID – lane=X – note"
    )

    # Extract and validate PID
    pid_match = re.search(r'shell_pid[= ]+(\d+)', latest_entry)
    assert pid_match, f"Could not parse PID from entry: {latest_entry}"

    pid_value = pid_match.group(1)
    assert pid_value.isdigit() and int(pid_value) > 0, f"Invalid PID: {pid_value}"

    # Validate lane included
    assert 'lane=' in latest_entry or 'lane =' in latest_entry, (
        f"Activity log entry missing lane\n"
        f"Entry: {latest_entry}"
    )

    # Validate agent included
    assert 'AgentPID' in latest_entry or 'agent' in latest_entry.lower(), (
        f"Activity log entry missing agent identifier\n"
        f"Entry: {latest_entry}"
    )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~55 lines)

**Parallel?**: Yes [P]

**Reference**: tasks_support.py:181-198 (append_activity_log), tasks_support.py:201-222 (activity_entries for parsing)

---
- 2026-01-14T12:28:43Z – claude-code – shell_pid=70908 – lane=doing – Started implementation via workflow command
- 2026-01-14T12:34:39Z – claude-code – shell_pid=70908 – lane=for_review – Multi-agent synchronization tests complete - FOUND BUG #5 (CRITICAL): Auto-commit not working for implement command. Worktrees created but lane changes not synchronized to main → agents don't see each other's work. Test suite (8 tests) implemented with comprehensive docstrings and adversarial validation. Bug documented in findings/. Remaining tests blocked pending Bug #5 fix.
- 2026-01-14T12:43:26Z – codex – shell_pid=54244 – lane=doing – Started review via workflow command
- 2026-01-14T12:44:37Z – codex – shell_pid=54244 – lane=planned – Moved to planned
- 2026-01-14T12:46:28Z – codex – shell_pid=54244 – lane=doing – Started implementation via workflow command
- 2026-01-14T12:46:45Z – codex – shell_pid=54244 – lane=doing – Acknowledged review feedback; updating multi-agent tests
- 2026-01-14T13:29:43Z – codex – shell_pid=54244 – lane=for_review – Review feedback addressed: (1) Fixed invalid CLI syntax, (2) Skipped tests have justification, (3) Bug #5 fixed. Test results: 5 passed, 3 skipped. Bug #6 (LOW) documented for shell_pid.
- 2026-01-14T13:31:00Z – codex – shell_pid=10701 – lane=doing – Started review via workflow command
- 2026-01-14T13:31:54Z – codex – shell_pid=10701 – lane=planned – Moved to planned
- 2026-01-14T13:33:15Z – codex – shell_pid=10701 – lane=doing – Started implementation via workflow command
- 2026-01-14T13:41:57Z – codex – shell_pid=10701 – lane=for_review – Ready for review: addressed feedback, updated repo root detection + activity log PID assertion, adjusted test scaffolding, and 8/8 TestMultiAgentParallel passing

## Test Strategy

**Test File**: `tests/functional/test_sparse_checkout_infrastructure.py`

**Test Class**: Create `TestMultiAgentParallel` class for all 8 multi-agent synchronization tests

**Execution**:
```bash
# Run all multi-agent tests
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs

# Run individual test
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel::test_parallel_agents_see_each_others_status -xvs
```

**Testing Approach**:
- **Sequential simulation**: Simulate multi-agent via deterministic sequence (not true parallelism)
- **Agent A → commit → Agent B reads**: Validate synchronization by explicit sequencing
- **Read from main**: All tests verify agents read from main repo, not worktree copy
- **Git history validation**: Check commits appear in main's git log

**Expected Outcomes**:
- Tests T014-T017: Core synchronization tests (likely pass if auto-commit working)
- Test T018: Dependency validation (may fail if not implemented)
- Test T019: Review feedback (may fail/skip if feature not complete)
- Tests T020-T021: PID tracking (should pass, validates audit trail)

**Adversarial Approach**:
- EXPECT synchronization bugs (reading from worktree instead of main)
- EXPECT PID tracking gaps (empty shell_pid fields)
- Document failures in findings/
- Fix synchronization logic in ~/Code/spec-kitty
- Re-run until all pass

---

## Risks & Mitigations

**Risk 1: Synchronization tests reveal agents read from worktree copy (not main)**
- **Likelihood**: MEDIUM (common bug in distributed systems)
- **Impact**: CRITICAL (agents see divergent state → duplicate work, conflicts)
- **Mitigation**: This is EXACTLY what tests should catch. Fix path resolution to always read from main repo. Document bug severity as CRITICAL.

**Risk 2: Auto-commit fails silently (commits not reaching main)**
- **Likelihood**: LOW (git usually fails loudly)
- **Impact**: CRITICAL (synchronization broken)
- **Mitigation**: Tests validate git log shows commits. If missing, investigate auto-commit implementation.

**Risk 3: PID tracking not implemented (shell_pid fields empty)**
- **Likelihood**: MEDIUM
- **Impact**: MEDIUM (audit trail incomplete, but not blocking)
- **Mitigation**: Tests fail clearly with "PID not found". Implement PID capture in workflow.py.

**Risk 4: Tests flaky due to timing (concurrent commits, race conditions)**
- **Likelihood**: LOW (using sequential simulation, not true parallelism)
- **Impact**: HIGH (can't trust test results)
- **Mitigation**: Zero tolerance for flaky tests. Sequential simulation ensures determinism. If flaky, add explicit synchronization points.

---

## Definition of Done Checklist

- [ ] TestMultiAgentParallel class created in tests/functional/test_sparse_checkout_infrastructure.py
- [ ] All 8 multi-agent tests implemented (T014-T021)
- [ ] Each test has clear docstring (what tested, why matters, implementation reference)
- [ ] Each test has contextual assertion messages (debugging info on failure)
- [ ] Tests use sequential simulation (deterministic, not flaky)
- [ ] Tests executed: `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs`
- [ ] Test results: 8/8 PASSED (or documented failures in findings/ with bug numbers)
- [ ] All bugs found documented in findings/test-infrastructure/v0.12.0-bugs-found.md
- [ ] All bugs fixed in ~/Code/spec-kitty (or documented as deferred with rationale)
- [ ] Tests validate synchronization via main repo (not worktree copies)
- [ ] PID tracking validated in both frontmatter and activity logs

---

## Review Guidance

**For Reviewer**:

1. **Validate test quality**:
   - Each test simulates realistic multi-agent scenario
   - Tests validate synchronization via git commits + main repo reads
   - Sequential simulation used (deterministic, not flaky)
   - Clear docstrings explain synchronization mechanism

2. **Validate synchronization approach**:
   - Tests explicitly check git log for commits
   - Tests read from main repo (not worktree copy)
   - Tests simulate Agent A action → commit → Agent B sees it

3. **Validate bug documentation** (if bugs found):
   - findings/test-infrastructure/v0.12.0-bugs-found.md updated
   - Synchronization bugs marked as CRITICAL severity
   - Fixes applied and verified

4. **Run tests**:
   ```bash
   pytest tests/functional/test_sparse_checkout_infrastructure.py::TestMultiAgentParallel -xvs
   ```
   - Should see 8/8 PASSED
   - Each test should complete in <15 seconds
   - No flaky failures (run 3 times to verify determinism)

**Key Questions**:
- Do tests genuinely validate multi-agent synchronization?
- Would these tests catch synchronization bugs (agents seeing divergent state)?
- Are tests deterministic (sequential simulation, not flaky)?
- Is PID tracking validated for audit trail?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T20:10:00Z – codex – shell_pid=10701 – lane=doing – Addressed review feedback; fixed repo root detection, enforced shell_pid activity log assertion, updated test scaffolding, and verified 8/8 multi-agent tests pass
