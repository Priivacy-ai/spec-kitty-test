# Finding: Dashboard Does Not Detect File Modifications

**Date:** 2025-11-15
**Session ID:** dashboard-live-update-testing-001
**Tested by:** Claude Code (automated tests)
**Category:** Bug Report - Dashboard State Detection
**Spec-Kitty Version:** 0.5.2 (also affects 0.5.3-pre)
**Analysis Date:** 2025-11-15
**Applies To:** v0.5.2, v0.5.3-pre (all versions with current scanner implementation)

## Summary

The dashboard backend detects when NEW files are created but does NOT detect when EXISTING files are modified. This causes the dashboard UI to show stale content until the user manually refreshes the page.

## Observation

**User-Reported Scenario:**
1. Agent creates `spec.md` with placeholder text ("Generating spec...")
2. Dashboard shows spec exists ✓
3. Agent overwrites `spec.md` with actual 10KB specification
4. Dashboard continues showing "spec exists" but doesn't reflect the modification ✗
5. User must manually refresh browser to see updated content

**Test Confirmation:**
Created automated test that reproduces this exactly:
- File size changed: 36 bytes → 469 bytes (13x larger)
- File mtime changed (filesystem confirmed modification)
- API polled every 1 second for 15 seconds
- API response: **Completely unchanged**

## Impact

- **Severity:** High
- **Scope:** All users, especially when working with LLM agents that write files in multiple passes
- **Frequency:** Happens every time a file is modified (100% reproducible)

**User Impact:**
- Must manually refresh browser to see agent's work
- No real-time collaboration feedback
- Confusing UX (agent says "I updated the spec" but dashboard shows old state)
- Breaks workflow for iterative development

**Agent Impact:**
- Agents have no way to verify their file writes succeeded from dashboard perspective
- Multi-agent coordination relies on stale state
- Approval workflows may be based on outdated content

## Root Cause Analysis

### Code Location

`src/specify_cli/dashboard/scanner.py:145-157`

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, bool]:
    """Return which artifacts exist for a feature."""
    return {
        "spec": (feature_dir / "spec.md").exists(),  # ← Only checks EXISTS
        "plan": (feature_dir / "plan.md").exists(),  # ← Not MODIFIED
        # ... other artifacts ...
    }
```

**Problem**: The scanner only calls `.exists()` which returns `True` whether the file
has 10 bytes or 10KB. It doesn't check:
- File modification time (mtime)
- File size
- File content hash
- Any change detection mechanism

### How scan_all_features() Works

```python
# Called on every /api/features request
def scan_all_features(project_dir: Path):
    for feature_id, feature_dir in feature_paths.items():
        artifacts = get_feature_artifacts(feature_dir)  # ← Only checks existence
        workflow = get_workflow_status(artifacts)        # ← Based on existence

        # Returns same data structure whether file is 1 byte or 1MB
        return {
            "artifacts": artifacts,  # {"spec": true} - no mtime, no hash
            "workflow": workflow,    # Based only on existence
        }
```

## User/Agent Journey

### Typical Agent Workflow

1. Agent runs specify command
2. Agent creates `spec.md` with outline:
   ```markdown
   # Specification

   Analyzing requirements...
   ```
3. Dashboard shows: `spec: true`, `specify: complete` ✓
4. Agent researches and writes full spec (5 minutes later):
   ```markdown
   # Product Specification

   ## Requirements
   - REQ-1: ...
   - REQ-2: ...
   [50+ requirements]

   ## Architecture
   [Detailed design]
   ```
5. Dashboard STILL shows: `spec: true`, `specify: complete` (unchanged)
6. **User has no idea the spec was updated!**

### Multi-Pass Writing

Agents often write files in multiple passes:
1. Create outline
2. Fill in requirements
3. Add implementation details
4. Refine based on feedback

Dashboard only shows step 1, never steps 2-4.

## What Could Have Helped

### For Users
- **Real-time visual feedback**: Dashboard should show "spec.md updated 30s ago"
- **File size indicators**: Show "spec.md (5.2KB)" so users know there's actual content
- **Modification timestamps**: "Last modified: 2025-11-15 14:32:15"
- **Content preview**: Show first few lines or word count

### For Agents
- **Verification mechanism**: Agent could check `/api/features` to confirm modification was detected
- **Webhooks/notifications**: "File modification registered" confirmation
- **Content hash endpoint**: Allow agents to verify content matches what they wrote

### For Dashboard Implementation
- **File system watching**: Use inotify/watchdog to detect changes in real-time
- **Modification time tracking**: Include mtime in API response
- **Content hashing**: Track file hashes to detect changes
- **Polling with mtime checks**: If polling, compare mtimes not just existence

## Suggested Improvements

### 1. Add Modification Time Tracking (Quick Fix)

```python
def get_feature_artifacts(feature_dir: Path) -> Dict[str, Any]:
    """Return artifacts with modification times."""
    artifacts = {}

    for name, filename in [
        ("spec", "spec.md"),
        ("plan", "plan.md"),
        # ... etc
    ]:
        file_path = feature_dir / filename
        if file_path.exists():
            artifacts[name] = {
                "exists": True,
                "mtime": file_path.stat().st_mtime,
                "size": file_path.stat().st_size,
            }
        else:
            artifacts[name] = {"exists": False}

    return artifacts
```

**API Response Would Change To:**
```json
{
  "artifacts": {
    "spec": {
      "exists": true,
      "mtime": 1763294206.86,
      "size": 469
    }
  }
}
```

**Benefits:**
- Frontend can detect when mtime changes
- Can show "Updated 30s ago"
- Minimal backend change

### 2. Add File System Watching (Better Solution)

Use `watchdog` library to monitor file changes in real-time:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FeatureFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            # Trigger dashboard update
            invalidate_cache()
```

**Benefits:**
- Instant updates (no polling delay)
- Efficient (no constant file system scanning)
- Scales to large projects

### 3. Frontend Polling Enhancement

Even without backend changes, frontend could:

```javascript
// Current (assumed)
setInterval(() => {
  fetchFeatures();  // Only checks existence
}, 5000);

// Improved
let lastKnownMtimes = {};

setInterval(() => {
  const features = await fetchFeatures();

  features.forEach(feature => {
    const specMtime = feature.artifacts.spec?.mtime;
    const lastMtime = lastKnownMtimes[feature.id]?.spec;

    if (specMtime && specMtime !== lastMtime) {
      // Content changed! Reload that section
      reloadSpec(feature.id);
      lastKnownMtimes[feature.id] = { spec: specMtime };
    }
  });
}, 2000);  // Poll every 2s
```

## Related Files

- `src/specify_cli/dashboard/scanner.py:145-157` - get_feature_artifacts()
- `src/specify_cli/dashboard/scanner.py:221-276` - scan_all_features()
- `src/specify_cli/dashboard/handlers/features.py` - /api/features endpoint
- `src/specify_cli/dashboard/static/dashboard/dashboard.js` - Frontend polling (if exists)

## Example Output/Reproduction

### Reproduction Steps

```bash
# 1. Create project and feature
spec-kitty init test_project --ai=claude
cd test_project
.kittify/scripts/bash/create-new-feature.sh --feature-name "Test" "Description"

# 2. Start dashboard
spec-kitty dashboard
# Opens at http://127.0.0.1:9237

# 3. In another terminal, create initial spec
cd .worktrees/001-test/kitty-specs/001-test
echo "# Placeholder" > spec.md

# 4. Refresh dashboard - should show spec exists ✓

# 5. Modify spec with real content
cat > spec.md << 'EOF'
# Actual Specification

## Requirements
- REQ-1: Feature one
- REQ-2: Feature two
[... 100 lines ...]
EOF

# 6. Wait 15 seconds, check dashboard
# BUG: Dashboard still shows same state ✗
# API response unchanged

# 7. Manual browser refresh
# NOW shows updated (proves content is there, just not detected)
```

### Test Results

```bash
$ pytest tests/functional/test_dashboard_modification_api.py::TestAPIFileModificationDetection::test_api_detects_spec_modification -v -s

FAILED: Dashboard did not detect spec.md modification after 15s.

Timeline:
1. Created spec.md (36 bytes) ✓
2. API showed spec: true ✓
3. Modified spec.md (469 bytes) ✓
4. Polled API every 1s for 15s ✓
5. API response: UNCHANGED ✗

API state before and after: IDENTICAL
```

## Technical Details

### What the API Returns

```json
{
  "artifacts": {
    "spec": true,    // ← Just a boolean!
    "plan": false,   // ← No mtime
    "tasks": false   // ← No size
  }
}
```

**Missing Data:**
- File modification time
- File size
- Content hash
- Last modified timestamp
- Content preview

### Why This Matters

The dashboard has **no way to know** if a file changed because the API
provides the same data before and after:
- Before: `{"spec": true}` (36 bytes)
- After: `{"spec": true}` (469 bytes)
- Identical!

## Priority

**High Priority** because:
1. Affects 100% of users doing iterative development
2. Confusing UX (appears broken)
3. Breaks real-time collaboration model
4. Relatively easy fix (add mtime tracking)

## Testing

**Test Files Created:**
- `tests/functional/test_dashboard_file_modifications.py` - 13 Playwright tests
- `tests/functional/test_dashboard_modification_api.py` - 2 backend API tests

**Test Coverage:**
- ✅ File creation detection (works)
- ✅ File modification detection (FAILS - bug confirmed)
- ✅ Multiple modifications (FAILS - not detected)
- ✅ Large content changes (FAILS - not detected)
- ✅ Atomic writes (FAILS - not detected)

**All tests confirm the same bug**: Modifications are not detected.

## Recommended Fix Order

1. **Immediate** (v0.5.3 or v0.5.4):
   - Add mtime to `get_feature_artifacts()` response
   - Include mtime in API JSON
   - Frontend can detect changes by comparing mtimes

2. **Short-term** (next minor version):
   - Add file system watching with `watchdog`
   - Real-time updates without polling

3. **Long-term** (future):
   - WebSocket support for instant updates
   - Content hashing for integrity verification
   - Incremental update API (only send what changed)

---

**Notes:**
- This finding is based on Playwright and backend API tests
- Bug affects all artifacts (spec, plan, constitution, etc.)
- Constitution is also not tracked at all (separate finding: 2025-11-15_01)
- Tests are committed to spec-kitty-test repository for regression prevention
