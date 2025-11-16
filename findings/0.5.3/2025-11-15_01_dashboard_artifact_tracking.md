# Finding: Dashboard Doesn't Track constitution.md

**Date**: 2025-11-15
**Severity**: Medium
**Category**: Dashboard / State Detection
**Spec-Kitty Version**: Local pre-release (commit c989f9a and later)

## Summary

The dashboard scanner does not track `constitution.md` as an artifact, even though
it's a critical part of the spec-driven development workflow. This means the
dashboard cannot show constitution status or detect when constitutions are added.

## Discovery Method

Playwright test `test_updates_without_manual_refresh` revealed the issue when
creating `constitution.md` and checking if the dashboard API reflected it.

## Technical Details

### Code Location

`src/specify_cli/dashboard/scanner.py:145-157`

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    """Return which artifacts exist for a feature."""
    return {
        "spec": (feature_dir / "spec.md").exists(),
        "plan": (feature_dir / "plan.md").exists(),
        "tasks": (feature_dir / "tasks.md").exists(),
        "research": (feature_dir / "research.md").exists(),
        "quickstart": (feature_dir / "quickstart.md").exists(),
        "data_model": (feature_dir / "data-model.md").exists(),
        "contracts": (feature_dir / "contracts").exists(),
        "checklists": (feature_dir / "checklists").exists(),
        "kanban": (feature_dir / "tasks").exists(),
    }
    # ❌ constitution.md is missing!
```

### What's Missing

The scanner checks for 9 artifacts but **not** `constitution.md`:
- ✅ spec.md
- ✅ plan.md
- ✅ tasks.md
- ✅ research.md
- ✅ quickstart.md
- ✅ data-model.md
- ✅ contracts/
- ✅ checklists/
- ✅ tasks/ (kanban)
- ❌ **constitution.md** ← Missing!

## Impact

### On Users

1. **No constitution visibility**: Dashboard doesn't show if constitution exists
2. **Incomplete workflow tracking**: Can't track constitution → spec → plan progression
3. **Missing UI elements**: Constitution page/section not rendered
4. **Confusing status**: Specify phase may show incorrect state

### On Workflow

The typical workflow is:
1. Create `constitution.md` (define purpose, success criteria)
2. Create `spec.md` (detailed requirements)
3. Create `plan.md` (implementation steps)

Currently, step 1 is invisible to the dashboard.

## Evidence

### Test Output

```python
# Created constitution.md
constitution = feature_dir / 'constitution.md'
constitution.write_text("""# Feature Constitution
## Purpose
...
""", encoding="utf-8")

# Checked API response
response = urllib.request.urlopen(f"{url}/api/features")
api_data = json.loads(response.read())

# Result: No "constitution" key in artifacts dict
api_data['features'][0]['artifacts'] = {
    "spec": false,      # ✅ Tracked
    "plan": false,      # ✅ Tracked
    "tasks": false,     # ✅ Tracked
    # ❌ "constitution" is not in the dict at all!
}
```

### JavaScript Frontend

The frontend references constitution (from `dashboard.js`):
```javascript
if (pageName === 'constitution') {
    // Constitution page exists in UI
}
```

But the backend doesn't send constitution data to display!

## Recommended Fix

### Backend Change

Update `src/specify_cli/dashboard/scanner.py:145-157`:

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    """Return which artifacts exist for a feature."""
    return {
        "constitution": (feature_dir / "constitution.md").exists(),  # ← Add this
        "spec": (feature_dir / "spec.md").exists(),
        "plan": (feature_dir / "plan.md").exists(),
        "tasks": (feature_dir / "tasks.md").exists(),
        "research": (feature_dir / "research.md").exists(),
        "quickstart": (feature_dir / "quickstart.md").exists(),
        "data_model": (feature_dir / "data-model.md").exists(),
        "contracts": (feature_dir / "contracts").exists(),
        "checklists": (feature_dir / "checklists").exists(),
        "kanban": (feature_dir / "tasks").exists(),
    }
```

### Workflow Status Update

Also update `get_workflow_status()` to check for constitution:

```python
def get_workflow_status(artifacts: Dict[str, bool]) -> Dict[str, str]:
    """Determine workflow progression status."""
    has_constitution = artifacts.get("constitution", False)
    has_spec = artifacts.get("spec", False)
    has_plan = artifacts.get("plan", False)
    has_tasks = artifacts.get("tasks", False)
    has_kanban = artifacts.get("kanban", False)

    workflow: Dict[str, str] = {}

    # Add constitution phase
    if not has_constitution:
        workflow.update({
            "constitute": "pending",
            "specify": "pending",
            "plan": "pending",
            "tasks": "pending",
            "implement": "pending"
        })
        return workflow
    workflow["constitute"] = "complete"

    # Rest of workflow...
    if not has_spec:
        workflow.update(...)
    # ... etc
```

## Verification

After fix, the artifacts dict should include:

```json
{
  "artifacts": {
    "constitution": true,  // ← Now tracked!
    "spec": false,
    "plan": false,
    ...
  },
  "workflow": {
    "constitute": "complete",  // ← New phase!
    "specify": "pending",
    ...
  }
}
```

## Related Issues

This finding reveals a second question: **Does the dashboard auto-update?**

The test also showed that after waiting 10 seconds, the API state DID change
(spec became true when it shouldn't have). This suggests either:
1. The dashboard is polling and updating
2. There's a caching or file system issue

The Playwright tests in `test_dashboard_live_updates.py` are designed to
measure and verify the auto-update behavior.

## Test Coverage

**New Tests**: `tests/functional/test_dashboard_live_updates.py`

- 16 Playwright tests for live UI updates
- Tests constitution, spec, and plan detection
- Measures polling intervals
- Detects auto-update latency

## Priority

**Medium-High**: Constitution is a fundamental artifact in the workflow.
The dashboard should track it.

**Easy Fix**: One line addition to scanner.py

## Reproduction

```bash
# 1. Create feature
spec-kitty init test_project --ai=claude
cd test_project
.kittify/scripts/bash/create-new-feature.sh --feature-name "Test" "Description"

# 2. Create constitution in worktree
cd .worktrees/001-test/kitty-specs/001-test
echo "# Constitution" > constitution.md

# 3. Check dashboard API
curl http://127.0.0.1:9237/api/features | python -m json.tool

# 4. Observe: No "constitution" field in artifacts!
```

## Next Steps

1. ✅ Document this finding (done)
2. Add constitution tracking to scanner.py
3. Update workflow status to include constitution phase
4. Run Playwright tests to verify fix
5. Check if frontend needs updates for constitution UI
