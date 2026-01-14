---
work_package_id: "WP06"
subtasks:
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
title: "Path Resolution & Merge Tests"
phase: "Phase 1 - Sparse-Checkout Track"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "63570"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
dependencies: ["WP01", "WP05"]
history:
  - timestamp: "2026-01-14T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Path Resolution & Merge Tests

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

**Primary Objective**: Implement Suite 2 (Path Resolution) and Suite 5 (Clean Merge Behavior) tests validating commands find files in main repo and sparse-checkout doesn't interfere with git merges.

**Success Criteria**:
- ✅ 12/12 tests implemented (6 path resolution + 6 merge behavior)
- ✅ TestPathResolution class: 6 tests validating commands find kitty-specs in main repo from worktree context
- ✅ TestCleanMergeBehavior class: 6 tests validating WP branches merge cleanly without sparse-checkout conflicts
- ✅ `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestPathResolution -xvs` shows 6/6 PASSED
- ✅ `pytest tests/functional/test_sparse_checkout_infrastructure.py::TestCleanMergeBehavior -xvs` shows 6/6 PASSED
- ✅ Each test has clear docstring referencing implementation code
- ✅ Bugs found documented in findings/test-infrastructure/v0.12.0-bugs-found.md

**Why Important**: Path resolution is critical - if commands can't find kitty-specs from worktree, agents can't work. Merge behavior is critical - if sparse-checkout causes conflicts during merge, integration workflow breaks. Both are blockers for multi-agent development.

---

## Context & Constraints

### Related Documents
- **Path Resolution Reference**: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks.py lines 39-68 (_get_main_repo_root)
- **Worktree Detection**: ~/Code/spec-kitty/src/specify_cli/paths.py lines 74-94 (is_worktree_context)
- **WP Locator**: ~/Code/spec-kitty/src/specify_cli/cli/commands/agent/tasks_support.py lines 266-288 (locate_work_package)
- **Spec**: kitty-specs/001-critical-test-coverage-v012/spec.md (FR-001 Suite 2 and Suite 5)

### Implementation Code Behavior
- **Main repo detection**: _get_main_repo_root() detects if in worktree, finds main repo path
- **Path resolution**: Commands read kitty-specs from main repo even when executed in worktree
- **Feature slug stripping**: Detects -WPxx suffix in branch/feature names, strips for lookup
- **Merge behavior**: Sparse-checkout only affects working tree, not git merge operations

---

## Subtasks & Detailed Guidance

### Suite 2: Path Resolution Tests (T040-T045)

### Subtask T040 – Test tasks command finds kitty-specs in main repo (not worktree copy)

**Purpose**: Validate `spec-kitty agent task list` executed in worktree reads from main repo.

**Steps**:

1. Create test in tests/functional/test_sparse_checkout_infrastructure.py:

```python
class TestPathResolution:
    """Validate commands find kitty-specs in main repo from worktree context."""

    def test_tasks_command_reads_from_main_repo(
        self,
        temp_project_dir,
        init_spec_kitty_project
    ):
        """
        Test: tasks command finds kitty-specs in main repo (not worktree)

        Why: When executed in worktree, `spec-kitty agent task list` must read
        tasks.md from main repo (where kitty-specs/ exists), not look for
        worktree's kitty-specs/ (which doesn't exist due to sparse-checkout).

        Reference: tasks.py:39-68 (_get_main_repo_root finds main repo path)
        Related: Worktree-aware path resolution
        """
        project = init_spec_kitty_project("path-resolution-test")

        # Create feature and worktree
        subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                       cwd=project, capture_output=True, text=True, timeout=30, check=True)
        subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                       cwd=project, capture_output=True, text=True, timeout=60, check=True)

        worktrees = list((project / '.worktrees').glob('*'))
        worktree = worktrees[0]

        # Verify kitty-specs/ NOT in worktree (sparse-checkout working)
        assert not (worktree / 'kitty-specs').exists(), "Setup: sparse-checkout should exclude kitty-specs/"

        # Run task list command FROM WORKTREE
        result = subprocess.run(
            ['spec-kitty', 'agent', 'task', 'list'],
            cwd=worktree,  # Execute in worktree directory
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should succeed (find tasks.md in main repo)
        assert result.returncode == 0, (
            f"task list should succeed from worktree\n"
            f"Error: {result.stderr}\n"
            f"Worktree: {worktree}\n"
            f"If failed, path resolution not finding main repo - CRITICAL BUG"
        )

        # Output should show WP01 (and other WPs if present)
        output = result.stdout
        assert 'WP01' in output or 'WP' in output, (
            f"task list output should show work packages\n"
            f"Output: {output}\n"
            f"If empty, not reading tasks.md from main repo"
        )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (add TestPathResolution class, ~40 lines)

**Parallel?**: Yes [P] with T041-T045 (different commands)

**Reference**: tasks.py:39-68 (_get_main_repo_root)

---

### Subtask T041 – Test move-task finds WP file in main repo

**Purpose**: Validate move-task finds WP prompt file in main repo from worktree.

**Steps**:

1. Create test:

```python
def test_move_task_finds_wp_file_in_main(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: move-task finds WP file in main repo from worktree

    Why: move-task needs to update WP prompt file. Must find it in main repo's
    kitty-specs/, not look in worktree (where it doesn't exist).

    Reference: tasks_support.py:266-288 (locate_work_package finds in main)
    Related: WP file path resolution
    """
    project = init_spec_kitty_project("move-task-path-test")

    # Setup
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Run move-task FROM WORKTREE
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'move-task', 'WP01', '--to', 'for_review'],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Should succeed
    assert result.returncode == 0, (
        f"move-task should find WP01 file in main repo\n"
        f"Error: {result.stderr}\n"
        f"If 'file not found', path resolution broken"
    )

    # Verify WP01 file updated in main repo
    import glob
    wp_files = glob.glob(str(project / 'kitty-specs' / 'test' / 'tasks' / 'WP01-*.md'))
    assert len(wp_files) == 1, f"Expected 1 WP01 file, got {len(wp_files)}"

    wp_content = Path(wp_files[0]).read_text()
    assert 'for_review' in wp_content, "WP01 file should be updated to for_review lane"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~35 lines)

**Parallel?**: Yes [P]

**Reference**: tasks_support.py:266-288

---

### Subtask T042 – Test workflow finds WP file in main repo

**Purpose**: Validate workflow commands (implement, review) find WP files in main.

**Steps**:

1. Create test:

```python
def test_workflow_finds_wp_file_in_main(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: workflow commands find WP file in main repo

    Why: `spec-kitty implement WP02` executed from project root (or worktree)
    must find WP02 prompt file in main repo's kitty-specs/.

    Reference: workflow.py (uses locate_work_package helper)
    Related: Workflow command path resolution
    """
    project = init_spec_kitty_project("workflow-path-test")

    # Create feature with multiple WPs
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Claim WP01 first
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Agent1'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # From WP01's worktree, claim WP02 (cross-worktree path resolution)
    worktrees = list((project / '.worktrees').glob('*'))
    wp01_worktree = worktrees[0]

    result = subprocess.run(
        ['spec-kitty', 'implement', 'WP02', '--agent=Agent2'],
        cwd=wp01_worktree,  # Execute from different worktree
        capture_output=True,
        text=True,
        timeout=60
    )

    # Should succeed (find WP02 in main repo)
    assert result.returncode == 0, (
        f"implement WP02 should succeed from WP01 worktree\n"
        f"Error: {result.stderr}\n"
        f"Path resolution should find WP02 in main repo"
    )

    # Verify WP02 worktree created
    worktrees_after = list((project / '.worktrees').glob('*'))
    assert len(worktrees_after) == 2, f"Expected 2 worktrees, got {len(worktrees_after)}"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~35 lines)

**Parallel?**: Yes [P]

**Reference**: workflow.py (uses locate_work_package)

---

### Subtask T043 – Test feature slug detection strips -WPxx suffix

**Purpose**: Validate feature name detection strips worktree branch suffix.

**Steps**:

1. Create test:

```python
def test_feature_slug_strips_wp_suffix(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Feature slug detection strips -WPxx suffix

    Why: Worktree branches named "012-docs-WP04" should resolve to feature
    "012-docs". Slug detection must strip -WPxx suffix to find correct
    kitty-specs subdirectory.

    Reference: tasks_support.py (feature slug detection logic)
    Related: Branch name to feature slug mapping
    """
    project = init_spec_kitty_project("slug-test")

    # Create feature
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', '012-docs', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Create worktree (branch will be named 012-docs-WP01)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Get current branch name in worktree
    result = subprocess.run(
        ['git', 'branch', '--show-current'],
        cwd=worktree,
        capture_output=True,
        text=True
    )
    branch_name = result.stdout.strip()

    # Branch should be like "012-docs-WP01" or similar with WP suffix
    assert 'WP' in branch_name, f"Expected WP suffix in branch: {branch_name}"

    # Run task list from worktree (should strip -WPxx, find 012-docs feature)
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list'],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, (
        f"task list should resolve 012-docs feature from {branch_name} branch\n"
        f"Error: {result.stderr}\n"
        f"If 'feature not found', slug stripping not working"
    )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~35 lines)

**Parallel?**: Yes [P]

**Reference**: tasks_support.py (feature slug detection)

---

### Subtask T044 – Test _get_main_repo_root() detects worktree vs main correctly

**Purpose**: Validate worktree detection function works correctly.

**Steps**:

1. Create test:

```python
def test_main_repo_detection_from_worktree(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: _get_main_repo_root() detects worktree vs main correctly

    Why: Core path resolution function must detect if current directory is
    worktree (return main repo path) or main repo (return current path).

    Reference: tasks.py:39-68 (_get_main_repo_root implementation)
    Related: Worktree detection logic
    """
    project = init_spec_kitty_project("detection-test")

    # Create worktree
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Test from MAIN REPO: should return current path
    # (We can't directly call _get_main_repo_root, but we can test via commands)

    # From main repo, task list should work
    result_main = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list'],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result_main.returncode == 0, "task list should work from main repo"

    # From WORKTREE: should detect and find main
    result_worktree = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list'],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result_worktree.returncode == 0, (
        f"task list should work from worktree (detect main repo)\n"
        f"Error: {result_worktree.stderr}"
    )

    # Both should produce same output (reading from main repo's kitty-specs)
    # (Output may differ slightly, but both should show WP01)
    assert 'WP' in result_main.stdout, "Main repo output should show WPs"
    assert 'WP' in result_worktree.stdout, "Worktree output should show WPs"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~40 lines)

**Parallel?**: Yes [P]

**Reference**: tasks.py:39-68

---

### Subtask T045 – Test absolute paths work from nested directories in worktree

**Purpose**: Validate path resolution works from subdirectories within worktree.

**Steps**:

1. Create test:

```python
def test_absolute_paths_from_nested_dirs(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Absolute paths work from nested directories in worktree

    Why: Agent might execute commands from src/components/ subdirectory within
    worktree. Path resolution must work from any nested directory.

    Reference: tasks.py:39-68 (should detect worktree from any subdirectory)
    Related: Nested directory path resolution
    """
    project = init_spec_kitty_project("nested-path-test")

    # Create worktree
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Create nested directory in worktree
    nested_dir = worktree / 'src' / 'components'
    nested_dir.mkdir(parents=True, exist_ok=True)

    # Execute command from nested directory
    result = subprocess.run(
        ['spec-kitty', 'agent', 'task', 'list'],
        cwd=nested_dir,  # Deep nested path
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, (
        f"task list should work from nested directory\n"
        f"Nested dir: {nested_dir}\n"
        f"Error: {result.stderr}\n"
        f"If failed, path resolution doesn't traverse to find worktree root"
    )

    output = result.stdout
    assert 'WP' in output, "Should show work packages from nested directory"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~35 lines)

**Parallel?**: Yes [P]

**Reference**: tasks.py:39-68 (should traverse up to find .git)

---

### Suite 5: Clean Merge Behavior Tests (T046-T051)

### Subtask T046 – Test merge WP branch to main → no kitty-specs/ conflicts

**Purpose**: Validate merging worktree branch to main doesn't create conflicts.

**Steps**:

1. Create test:

```python
class TestCleanMergeBehavior:
    """Validate sparse-checkout doesn't interfere with git merges."""

    def test_merge_wp_branch_no_conflicts(
        self,
        temp_project_dir,
        init_spec_kitty_project
    ):
        """
        Test: Merge WP branch to main → no kitty-specs/ conflicts

        Why: After completing WP, merging worktree branch to main should be
        clean. Sparse-checkout (affecting working tree only) shouldn't cause
        merge conflicts in kitty-specs/ paths.

        Reference: Git sparse-checkout documentation (working tree vs. merge)
        Related: Merge workflow integration
        """
        project = init_spec_kitty_project("merge-test")

        # Create feature and worktree
        subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                       cwd=project, capture_output=True, text=True, timeout=30, check=True)
        subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                       cwd=project, capture_output=True, text=True, timeout=60, check=True)

        worktrees = list((project / '.worktrees').glob('*'))
        worktree = worktrees[0]

        # Make some code changes in worktree
        src_file = worktree / 'src' / 'feature.py'
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("def feature(): pass")

        # Commit in worktree branch
        subprocess.run(['git', 'add', 'src/feature.py'], cwd=worktree, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add feature'], cwd=worktree, check=True)

        # Get worktree branch name
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=worktree,
            capture_output=True,
            text=True
        )
        wp_branch = result.stdout.strip()

        # Switch to main and merge
        subprocess.run(['git', 'checkout', 'main'], cwd=project, check=True)

        result = subprocess.run(
            ['git', 'merge', wp_branch, '--no-edit'],
            cwd=project,
            capture_output=True,
            text=True
        )

        # Merge should succeed without conflicts
        assert result.returncode == 0, (
            f"Merge should succeed without conflicts\n"
            f"Branch: {wp_branch}\n"
            f"Error: {result.stderr}\n"
            f"If conflicts in kitty-specs/, sparse-checkout interfering with merge - BUG"
        )

        # Verify no merge conflicts
        assert 'conflict' not in result.stdout.lower(), f"Merge output mentions conflict: {result.stdout}"
        assert 'conflict' not in result.stderr.lower(), f"Merge error mentions conflict: {result.stderr}"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (add TestCleanMergeBehavior class, ~45 lines)

**Parallel?**: Yes [P] with T047-T051 (different merge scenarios)

**Reference**: Git sparse-checkout (working tree only, doesn't affect merge)

---

### Subtask T047 – Test merge multiple WP branches sequentially → no conflicts

**Purpose**: Validate sequential merges of multiple WP branches work.

**Steps**:

1. Create test:

```python
def test_sequential_merges_no_conflicts(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Merge multiple WP branches sequentially → no conflicts between them

    Why: When merging WP01, then WP02, then WP03 into main, branches shouldn't
    conflict due to sparse-checkout (each works on different code areas).

    Reference: Git merge behavior with sparse-checkout
    Related: Multi-WP integration workflow
    """
    project = init_spec_kitty_project("sequential-merge-test")

    # Create feature with 3 WPs
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)

    # Create 3 worktrees and make changes
    branch_names = []
    for i in range(1, 4):
        subprocess.run(['spec-kitty', 'implement', f'WP0{i}', f'--agent=Agent{i}'],
                       cwd=project, capture_output=True, text=True, timeout=60, check=True)

        worktrees = sorted((project / '.worktrees').glob('*'))
        worktree = worktrees[i-1]

        # Make unique changes in each worktree
        src_file = worktree / 'src' / f'feature{i}.py'
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text(f"def feature{i}(): pass")

        subprocess.run(['git', 'add', f'src/feature{i}.py'], cwd=worktree, check=True)
        subprocess.run(['git', 'commit', '-m', f'Add feature{i}'], cwd=worktree, check=True)

        # Get branch name
        result = subprocess.run(['git', 'branch', '--show-current'],
                                cwd=worktree, capture_output=True, text=True)
        branch_names.append(result.stdout.strip())

    # Merge all 3 branches into main sequentially
    subprocess.run(['git', 'checkout', 'main'], cwd=project, check=True)

    for branch in branch_names:
        result = subprocess.run(
            ['git', 'merge', branch, '--no-edit'],
            cwd=project,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, (
            f"Merge {branch} should succeed\n"
            f"Error: {result.stderr}"
        )

    # Verify all 3 features in main
    for i in range(1, 4):
        feature_file = project / 'src' / f'feature{i}.py'
        assert feature_file.exists(), f"feature{i}.py should be merged"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~50 lines)

**Parallel?**: Yes [P]

---

### Subtask T048 – Test fast-forward merge possible when no conflicts

**Purpose**: Validate fast-forward merges work with sparse-checkout.

**Steps**:

1. Create test:

```python
def test_fast_forward_merge_works(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Fast-forward merge works when WP branch ahead of main

    Why: When main hasn't changed since WP branch creation, merge should
    fast-forward. Sparse-checkout shouldn't prevent this.

    Reference: Git merge fast-forward behavior
    Related: Clean integration workflow
    """
    project = init_spec_kitty_project("ff-merge-test")

    # Create feature and worktree
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Make commit in worktree
    src_file = worktree / 'src' / 'feature.py'
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("def feature(): pass")
    subprocess.run(['git', 'add', 'src/feature.py'], cwd=worktree, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add feature'], cwd=worktree, check=True)

    # Get branch name
    result = subprocess.run(['git', 'branch', '--show-current'],
                            cwd=worktree, capture_output=True, text=True)
    wp_branch = result.stdout.strip()

    # Merge with fast-forward
    subprocess.run(['git', 'checkout', 'main'], cwd=project, check=True)

    result = subprocess.run(
        ['git', 'merge', '--ff-only', wp_branch],
        cwd=project,
        capture_output=True,
        text=True
    )

    # Should fast-forward successfully
    assert result.returncode == 0, (
        f"Fast-forward merge should succeed\n"
        f"Error: {result.stderr}\n"
        f"If failed, sparse-checkout preventing FF merge"
    )
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~35 lines)

**Parallel?**: Yes [P]

---

### Subtask T049 – Test cherry-pick from WP branch works

**Purpose**: Validate cherry-pick operations work with sparse-checkout.

**Steps**:

1. Create test:

```python
def test_cherry_pick_from_wp_branch(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Cherry-pick src/ changes from WP branch without kitty-specs/ interference

    Why: Sometimes need to cherry-pick specific commits from WP branch.
    Sparse-checkout shouldn't interfere with cherry-pick operations.

    Reference: Git cherry-pick with sparse-checkout
    Related: Selective commit integration
    """
    project = init_spec_kitty_project("cherry-pick-test")

    # Setup
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    # Make 2 commits in worktree
    for i in range(1, 3):
        src_file = worktree / 'src' / f'feature{i}.py'
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text(f"def feature{i}(): pass")
        subprocess.run(['git', 'add', f'src/feature{i}.py'], cwd=worktree, check=True)
        subprocess.run(['git', 'commit', '-m', f'Add feature{i}'], cwd=worktree, check=True)

    # Get commit hash of second commit
    result = subprocess.run(['git', 'log', '-1', '--format=%H'],
                            cwd=worktree, capture_output=True, text=True)
    commit_hash = result.stdout.strip()

    # Cherry-pick into main
    subprocess.run(['git', 'checkout', 'main'], cwd=project, check=True)

    result = subprocess.run(
        ['git', 'cherry-pick', commit_hash],
        cwd=project,
        capture_output=True,
        text=True
    )

    # Should succeed
    assert result.returncode == 0, (
        f"Cherry-pick should succeed\n"
        f"Commit: {commit_hash}\n"
        f"Error: {result.stderr}"
    )

    # Verify cherry-picked file present
    assert (project / 'src' / 'feature2.py').exists(), "Cherry-picked file should exist"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~40 lines)

**Parallel?**: Yes [P]

---

### Subtask T050 – Test rebase WP branch onto updated main

**Purpose**: Validate rebase operations work with sparse-checkout.

**Steps**:

1. Create test:

```python
def test_rebase_wp_branch_onto_main(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Rebase WP branch onto updated main → no sparse-checkout issues

    Why: When main advances after WP branch created, rebase brings WP branch
    up to date. Sparse-checkout shouldn't interfere with rebase.

    Reference: Git rebase with sparse-checkout
    Related: Branch synchronization workflow
    """
    project = init_spec_kitty_project("rebase-test")

    # Create feature and worktree
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Make change in main (simulate main advancing)
    main_file = project / 'README.md'
    main_file.write_text("# Updated README")
    subprocess.run(['git', 'add', 'README.md'], cwd=project, check=True)
    subprocess.run(['git', 'commit', '-m', 'Update README'], cwd=project, check=True)

    # Make change in worktree
    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    src_file = worktree / 'src' / 'feature.py'
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("def feature(): pass")
    subprocess.run(['git', 'add', 'src/feature.py'], cwd=worktree, check=True)
    subprocess.run(['git', 'commit', '-m', 'Add feature'], cwd=worktree, check=True)

    # Rebase worktree branch onto main
    result = subprocess.run(
        ['git', 'rebase', 'main'],
        cwd=worktree,
        capture_output=True,
        text=True
    )

    # Should succeed
    assert result.returncode == 0, (
        f"Rebase should succeed\n"
        f"Error: {result.stderr}\n"
        f"If conflicts in kitty-specs/, sparse-checkout interfering"
    )

    # Verify both changes present
    assert (worktree / 'README.md').exists(), "Rebased file should exist"
    assert (worktree / 'src' / 'feature.py').exists(), "WP changes should remain"
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~45 lines)

**Parallel?**: Yes [P]

---

### Subtask T051 – Test merge conditions (fast-forward vs. merge commit)

**Purpose**: Validate both fast-forward and merge commit scenarios work.

**Steps**:

1. Create test:

```python
def test_merge_commit_when_main_diverged(
    self,
    temp_project_dir,
    init_spec_kitty_project
):
    """
    Test: Merge commit created when main and WP branch diverged

    Why: When both main and WP branch have commits, merge creates merge commit.
    Sparse-checkout shouldn't prevent this.

    Reference: Git merge commit creation
    Related: Non-fast-forward merge workflow
    """
    project = init_spec_kitty_project("merge-commit-test")

    # Create feature and worktree
    subprocess.run(['spec-kitty', 'agent', 'feature', 'create-feature', 'test', '--json'],
                   cwd=project, capture_output=True, text=True, timeout=30, check=True)
    subprocess.run(['spec-kitty', 'implement', 'WP01', '--agent=Test'],
                   cwd=project, capture_output=True, text=True, timeout=60, check=True)

    # Make change in main
    main_file = project / 'main_change.txt'
    main_file.write_text("Change in main")
    subprocess.run(['git', 'add', 'main_change.txt'], cwd=project, check=True)
    subprocess.run(['git', 'commit', '-m', 'Main change'], cwd=project, check=True)

    # Make change in worktree
    worktrees = list((project / '.worktrees').glob('*'))
    worktree = worktrees[0]

    wp_file = worktree / 'wp_change.txt'
    wp_file.write_text("Change in WP")
    subprocess.run(['git', 'add', 'wp_change.txt'], cwd=worktree, check=True)
    subprocess.run(['git', 'commit', '-m', 'WP change'], cwd=worktree, check=True)

    # Get branch name
    result = subprocess.run(['git', 'branch', '--show-current'],
                            cwd=worktree, capture_output=True, text=True)
    wp_branch = result.stdout.strip()

    # Merge (will create merge commit)
    subprocess.run(['git', 'checkout', 'main'], cwd=project, check=True)

    result = subprocess.run(
        ['git', 'merge', wp_branch, '--no-edit'],
        cwd=project,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Merge should succeed: {result.stderr}"

    # Verify both changes present
    assert (project / 'main_change.txt').exists()
    assert (project / 'wp_change.txt').exists()
```

**Files**:
- Update: `tests/functional/test_sparse_checkout_infrastructure.py` (~45 lines)

**Parallel?**: Yes [P]

---

## Test Strategy

**Test File**: `tests/functional/test_sparse_checkout_infrastructure.py`

**Test Classes**:
- `TestPathResolution`: 6 tests (T040-T045)
- `TestCleanMergeBehavior`: 6 tests (T046-T051)

**Execution**:
```bash
# Run all path resolution tests
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestPathResolution -xvs

# Run all merge behavior tests
pytest tests/functional/test_sparse_checkout_infrastructure.py::TestCleanMergeBehavior -xvs
```

---

## Risks & Mitigations

**Risk 1: Path resolution fails (commands can't find kitty-specs from worktree)**
- **Likelihood**: MEDIUM
- **Impact**: CRITICAL (agents can't work)
- **Mitigation**: Tests catch immediately. Fix _get_main_repo_root logic.

**Risk 2: Merges create conflicts due to sparse-checkout**
- **Likelihood**: LOW (sparse-checkout is working tree only)
- **Impact**: HIGH (integration workflow broken)
- **Mitigation**: Tests validate clean merges. If conflicts, investigate git config.

---

## Definition of Done Checklist

- [ ] TestPathResolution class created with 6 tests
- [ ] TestCleanMergeBehavior class created with 6 tests
- [ ] All 12 tests implemented (T040-T051)
- [ ] Path resolution tests validate commands find main repo from worktree
- [ ] Merge tests validate clean merges (FF, merge commit, rebase, cherry-pick)
- [ ] Tests executed successfully
- [ ] All bugs found documented and fixed

---

## Review Guidance

**For Reviewer**:

1. **Validate path resolution tests**:
   - Tests execute commands from worktree context
   - Tests verify commands succeed (find files in main repo)

2. **Validate merge tests**:
   - Tests create actual git merges
   - Tests verify no conflicts from sparse-checkout

3. **Run tests**:
   ```bash
   pytest tests/functional/test_sparse_checkout_infrastructure.py::TestPathResolution -xvs
   pytest tests/functional/test_sparse_checkout_infrastructure.py::TestCleanMergeBehavior -xvs
   ```

**Key Questions**:
- Do path resolution tests validate finding main repo from worktree?
- Do merge tests cover all common merge scenarios?

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-14T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T16:23:57Z – unknown – lane=for_review – Implemented 12 tests: 6 path resolution + 6 merge behavior. All pass.
- 2026-01-14T16:29:20Z – unknown – lane=planned – Moved to planned
- 2026-01-14T16:30:13Z – codex – shell_pid=50612 – lane=doing – Started implementation via workflow command
- 2026-01-14T16:45:00Z – codex – shell_pid=50612 – lane=doing – Addressed review feedback: added nested path resolution, slug auto-detection, and merge scenarios.
- 2026-01-14T16:32:44Z – codex – shell_pid=50612 – lane=for_review – Ready for review: addressed path resolution auto-detection, nested dir coverage, and merge scenarios
- 2026-01-14T16:34:31Z – claude-opus – shell_pid=63570 – lane=doing – Started review via workflow command
