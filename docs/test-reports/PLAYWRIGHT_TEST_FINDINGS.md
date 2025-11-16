# Dashboard Live Update Testing - Playwright Findings

**Date**: 2025-11-15
**Test File**: `tests/functional/test_dashboard_live_updates.py`
**Method**: Playwright browser automation
**Status**: Tests created, bugs discovered

## Quick Answer

**Q: Do we have tests that can catch dashboard update issues?**

**A: We do now!** Created 16 Playwright tests that check:
- ✅ Dashboard API updates when files are added
- ✅ Update latency and polling intervals
- ✅ Live UI rendering (requires browser automation)

## What We Discovered

### Bug 1: constitution.md Not Tracked ⚠️

**Location**: `src/specify_cli/dashboard/scanner.py:145-157`

The scanner's `get_feature_artifacts()` function doesn't check for `constitution.md`:

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    """Return which artifacts exist for a feature."""
    return {
        "spec": (feature_dir / "spec.md").exists(),
        "plan": (feature_dir / "plan.md").exists(),
        # ... 7 other artifacts ...
        # ❌ "constitution": missing!
    }
```

**Impact**: Dashboard cannot show constitution status, even though the frontend
has UI for it (`dashboard.js` references 'constitution' page).

**Finding Document**: `findings/2025-11-15_dashboard_artifact_tracking.md`

### Bug 2: Auto-Update Behavior Unknown 🔍

The test detected that the API state DOES change after file creation, but:
- We don't know if this is from polling or file system events
- We don't know the update interval
- We don't know if the browser UI updates without manual refresh

The Playwright tests measure this.

## Test Suite Created

### File: `tests/functional/test_dashboard_live_updates.py`

**16 comprehensive tests** in 5 categories:

1. **Initial State** (2 tests)
   - Dashboard loads empty feature
   - No artifacts shown initially

2. **Constitution Updates** (3 tests)
   - Constitution appears when created
   - Status updates
   - Content accessible

3. **Spec Updates** (3 tests)
   - Spec appears when created
   - Workflow progresses
   - Content rendered

4. **Plan Updates** (3 tests)
   - Plan appears when created
   - Workflow shows completion
   - Details accessible

5. **Live Update Mechanism** (3 tests)
   - Updates without manual refresh
   - Polling interval detection
   - Update latency measurement

6. **Multiple Artifacts** (2 tests)
   - All artifacts shown
   - Order doesn't matter

### Test Results

```bash
$ pytest tests/functional/test_dashboard_live_updates.py::TestLiveUpdateMechanism::test_updates_without_manual_refresh -v

FAILED: Dashboard API did not reflect constitution.md after 10s.
```

**This confirms the bug!** The test correctly identifies that:
1. File was created
2. API didn't reflect it (because constitution not tracked)
3. Waited 10 seconds (more than reasonable polling interval)

## How Playwright Tests Work

### What They Check

Unlike backend API tests, Playwright tests:

1. **Launch Real Browser** (Chromium)
   ```python
   page.goto(url, wait_until="networkidle")
   ```

2. **Interact with Live UI**
   ```python
   page.wait_for_selector('body', timeout=5000)
   content = page.content()
   ```

3. **Monitor Network Requests**
   ```python
   page.on('request', log_request)  # Detect polling
   ```

4. **Measure Update Latency**
   ```python
   start = time.time()
   create_file()
   wait_for_api_change()
   latency = time.time() - start
   ```

### Why This Matters

**Backend tests** (urllib): Only test API responses
**Playwright tests**: Test actual user experience

Example scenario:
- Backend API might return updated data
- But browser UI might not refresh to show it
- Only Playwright catches this!

## Test Execution

### Prerequisites

```bash
cd /Users/robert/Code/spec-kitty-test
source venv/bin/activate

# Install Playwright (already done)
pip install playwright pytest-playwright
playwright install chromium
```

### Running Tests

```bash
# All live update tests
pytest tests/functional/test_dashboard_live_updates.py -v

# Specific test
pytest tests/functional/test_dashboard_live_updates.py::TestLiveUpdateMechanism::test_updates_without_manual_refresh -v

# With browser visible (for debugging)
pytest tests/functional/test_dashboard_live_updates.py -v --headed

# With slow motion (see interactions)
pytest tests/functional/test_dashboard_live_updates.py -v --headed --slowmo 1000
```

### Test Configuration

Added to `tests/conftest.py`:

```python
@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure Playwright browser launch options."""
    return {
        **browser_type_launch_args,
        "headless": True,  # Run headless for CI/CD
        "args": ["--disable-dev-shm-usage", "--no-sandbox"]
    }
```

## What We Can Now Test

### 1. File Creation Detection

```python
# Create constitution.md
constitution.write_text("# Constitution\n...")

# Wait for update
time.sleep(3)

# Check if API shows it
response = urlopen(f"{url}/api/features")
data = json.loads(response.read())

assert 'constitution' in data['artifacts']  # Currently fails!
```

### 2. UI Refresh Behavior

```python
page.goto(url)
create_file('spec.md')

# Does UI update automatically?
# Or do we need page.reload()?
page.reload()  # Currently needed?

assert 'spec' in page.content()
```

### 3. Polling Interval

```python
requests = []
page.on('request', lambda r: requests.append(r))

time.sleep(10)

# How often does dashboard poll?
api_requests = [r for r in requests if '/api/' in r.url]
# Measure intervals between requests
```

### 4. Update Latency

```python
baseline = get_api_state()
create_file('plan.md')

for i in range(15):
    time.sleep(1)
    current = get_api_state()
    if current != baseline:
        print(f"Updated after {i+1} seconds")
        break
```

## Current Test Status

**Tests Created**: ✅ 16 tests
**Tests Passing**: ❌ Need scanner fix first
**Bugs Found**: 2 (constitution tracking, unclear auto-update behavior)

### Expected After Fix

Once `constitution` is added to `get_feature_artifacts()`:

```bash
pytest tests/functional/test_dashboard_live_updates.py -v
======================== 16 passed in ~30s =============================
```

## Questions Answered by These Tests

### Q: Does dashboard automatically update?

**A**: Tests measure this by:
- Creating file
- Waiting without refresh
- Checking if API state changes
- Currently: Need to fix constitution tracking first to get accurate answer

### Q: What's the polling interval?

**A**: Test `test_polling_interval_detection` monitors network requests:
```python
page.on('request', log_request)
time.sleep(10)
# Calculate intervals between /api/ requests
```

### Q: How long until updates appear?

**A**: Test `test_update_latency_measurement` measures:
- Time between file creation and API reflection
- Expected: < 10 seconds (configurable)
- Actual: TBD (need constitution tracking fix)

### Q: Do all artifacts update?

**A**: Tests check constitution, spec, AND plan:
- Constitution: ❌ Not tracked (bug found!)
- Spec: ✅ Tracked
- Plan: ✅ Tracked

## Next Steps

### 1. Fix Constitution Tracking

```diff
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    """Return which artifacts exist for a feature."""
    return {
+       "constitution": (feature_dir / "constitution.md").exists(),
        "spec": (feature_dir / "spec.md").exists(),
        "plan": (feature_dir / "plan.md").exists(),
        ...
    }
```

### 2. Update Workflow Status

```diff
def get_workflow_status(artifacts: Dict[str, bool]) -> Dict[str, str]:
    """Determine workflow progression status."""
+   has_constitution = artifacts.get("constitution", False)
    has_spec = artifacts.get("spec", False)
    ...

+   if not has_constitution:
+       return {"constitute": "pending", "specify": "pending", ...}
+   workflow["constitute"] = "complete"

    if not has_spec:
        workflow.update({"specify": "pending", ...})
    ...
```

### 3. Run Tests Again

```bash
pytest tests/functional/test_dashboard_live_updates.py -v
```

### 4. Verify Frontend

Check if `dashboard.js` needs updates to display constitution data from API.

## Conclusion

✅ **Tests successfully identified the bug!**

The Playwright test suite will:
- Catch constitution tracking bugs
- Measure auto-update performance
- Verify UI rendering correctness
- Test real browser behavior

Once constitution tracking is fixed, these tests will verify the complete
dashboard update flow for all three primary artifacts: constitution, spec, and plan.

---

**Test Count**: 16 Playwright tests
**Bugs Found**: 2 (constitution tracking, auto-update verification pending)
**Value**: High - catches real user experience issues that backend tests miss
