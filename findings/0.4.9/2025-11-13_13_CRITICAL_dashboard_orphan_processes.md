# CRITICAL: Dashboard Orphan Process Leak

**Date**: 2025-11-13
**Severity**: 🔴 **CRITICAL**
**Impact**: Dashboard completely unusable - all 100 ports exhausted
**Spec-Kitty Version**: ed3f4618b84ab40e4c5bd19ba4cd8423cea23ac6 (ed3f461)

---

## Executive Summary

**Dashboard has a critical process leak causing 101 orphaned Python processes** that exhaust the entire port range (9237-9337), making the dashboard completely unusable for new projects.

**Discovery**: Found during comprehensive dashboard testing when `find_free_port()` failed with "Could not find free port in range 9237-9337"

---

## Evidence

### Port Exhaustion

```bash
$ lsof -iTCP:9237-9337 -sTCP:LISTEN 2>/dev/null | wc -l
101
```

**All 100 dashboard ports (9237-9337) are occupied by orphaned Python processes.**

### Sample of Orphaned Processes

```
COMMAND   PID   USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python   6353 robert    3u  IPv4 0xc26b4c749db1ce1b      0t0  TCP localhost:9237 (LISTEN)
Python  14130 robert    3u  IPv4 0x881a0f45132e96a1      0t0  TCP localhost:9238 (LISTEN)
Python  24519 robert    3u  IPv4   0x8fb0900d095982      0t0  TCP localhost:9239 (LISTEN)
Python  29990 robert    3u  IPv4 0xbffcd6d2bbd7b6e5      0t0  TCP localhost:9244 (LISTEN)
Python  30043 robert    3u  IPv4 0x7dd7106bcbdf5f3f      0t0  TCP localhost:9240 (LISTEN)
...
```

**101 total Python processes** holding ports, preventing any new dashboard instances from starting.

### Test Failures

**13 tests failed** due to port exhaustion:
- `TestPortFinding::test_find_free_port_succeeds` - ❌ RuntimeError
- `TestServerStartup::test_server_starts_on_specific_port` - ❌ RuntimeError
- `TestDashboardLifecycle::test_ensure_dashboard_running_starts_new` - ❌ RuntimeError
- And 10 more...

**Error message**:
```
RuntimeError: Could not find free port in range 9237-9337
```

---

## Root Cause Analysis

### How Orphans Are Created

1. **Background Process Mode** (`background_process=True`):
   ```python
   # server.py:99-105
   subprocess.Popen(
       [sys.executable, '-c', script],
       stdout=subprocess.DEVNULL,
       stderr=subprocess.DEVNULL,
       stdin=subprocess.DEVNULL,
       start_new_session=True,  # <-- Detaches from parent
   )
   ```

2. **No Process Tracking**:
   - Processes are spawned with `start_new_session=True`
   - No PID is stored anywhere
   - `.dashboard` file only stores port/token, not PID

3. **Shutdown Mechanism Inadequate**:
   - `stop_dashboard()` tries HTTP `/api/shutdown` endpoint
   - If endpoint fails or server unresponsive, process lives forever
   - No fallback to kill by PID (because PID isn't tracked)

4. **Common Failure Scenarios**:
   - User terminates CLI before dashboard starts
   - System crash or force quit
   - Dashboard startup timeout
   - HTTP shutdown endpoint fails
   - .dashboard file deleted while process running

### Why All 100 Ports Are Exhausted

**This user has run spec-kitty ~100+ times** over development/testing, and EVERY SINGLE TIME a dashboard process was orphaned.

---

## Impact Assessment

### Immediate Impact 🔴

- **Dashboard completely broken** - cannot start new dashboards
- **All new projects fail** - init warns "Could not find free port"
- **Existing projects can't restart** - same port exhaustion error
- **No graceful degradation** - hard failure, no fallback

### User Experience

**User sees**:
```
Warning: Could not start dashboard: Could not find free port in range 9237-9337
Continuing without dashboard...
```

**User cannot**:
- View project state
- Monitor feature progress
- Use kanban board
- Access any dashboard functionality

### Resource Impact

- **101 orphaned Python HTTP servers** running indefinitely
- Each consuming:
  - 1 port (100% of range)
  - Memory (~20-50MB each = ~2-5GB total)
  - CPU cycles (idle but present)
  - File descriptors

---

## Reproduction Steps

1. Run `spec-kitty init` with any settings
2. Dashboard starts in background
3. Ctrl+C or close terminal before checking dashboard
4. Repeat 100 times
5. Result: All ports exhausted

---

## Recommended Fixes

### Priority 1: Track PIDs (CRITICAL)

**Store PID in .dashboard file**:

```python
# lifecycle.py:_write_dashboard_file
def _write_dashboard_file(dashboard_file: Path, url: str, port: int, token: Optional[str], pid: Optional[int]) -> None:
    """Persist dashboard metadata to disk."""
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [url, str(port)]
    if token:
        lines.append(token)
    if pid:
        lines.append(str(pid))  # <-- ADD PID
    dashboard_file.write_text("\n".join(lines) + "\n", encoding='utf-8')
```

**Parse PID from .dashboard file**:

```python
# lifecycle.py:_parse_dashboard_file
def _parse_dashboard_file(dashboard_file: Path) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[int]]:
    """Read dashboard metadata from disk."""
    # ... existing parsing ...

    pid = None
    if len(lines) >= 4:  # <-- ADD PID PARSING
        try:
            pid = int(lines[3])
        except ValueError:
            pid = None

    return url, port, token, pid  # <-- RETURN PID
```

### Priority 2: Fallback Kill by PID

**Update stop_dashboard() to kill by PID if HTTP shutdown fails**:

```python
# lifecycle.py:stop_dashboard
def stop_dashboard(project_dir: Path, timeout: float = 5.0) -> Tuple[bool, str]:
    """Attempt to stop the dashboard server."""
    # ... existing HTTP shutdown attempt ...

    # If HTTP shutdown failed, try PID kill
    if not stopped and pid is not None:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)

            # Check if process died
            try:
                os.kill(pid, 0)  # Check if still alive
                # Still alive, force kill
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                # Process is dead, good
                pass

            dashboard_file.unlink(missing_ok=True)
            return True, f"Dashboard killed (PID {pid})"
        except Exception as e:
            return False, f"Failed to kill dashboard PID {pid}: {e}"

    return False, "Could not stop dashboard"
```

### Priority 3: Orphan Cleanup on Init

**Add cleanup step in `ensure_dashboard_running()`**:

```python
# lifecycle.py:ensure_dashboard_running
def ensure_dashboard_running(...):
    """Ensure dashboard is running, cleaning up orphans first."""

    # STEP 1: Clean up orphaned .dashboard files
    if dashboard_file.exists():
        url, port, token, pid = _parse_dashboard_file(dashboard_file)

        # Check if process is actually alive
        if pid and not _is_process_alive(pid):
            # PID is dead, clean up
            dashboard_file.unlink(missing_ok=True)

        # Check if port health check works
        if port and not _check_dashboard_health(port, project_dir_resolved, token):
            # Port not responding, clean up
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass
            dashboard_file.unlink(missing_ok=True)

    # STEP 2: Start new dashboard (existing logic)
    # ...
```

**Add helper**:

```python
def _is_process_alive(pid: int) -> bool:
    """Check if process is alive."""
    try:
        import signal
        os.kill(pid, 0)  # Doesn't actually kill, just checks existence
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Exists but not ours
```

### Priority 4: Cleanup Command

**Add `spec-kitty dashboard --cleanup` command**:

```bash
spec-kitty dashboard --cleanup
# Finds all orphaned dashboard processes and kills them
# Removes stale .dashboard files
```

---

## Workaround for Users (Immediate)

**Kill all orphaned dashboards**:

```bash
# Find all orphaned dashboard processes
lsof -iTCP:9237-9337 -sTCP:LISTEN | awk 'NR>1 {print $2}' | sort -u | xargs kill

# Or force kill if they don't respond
lsof -iTCP:9237-9337 -sTCP:LISTEN | awk 'NR>1 {print $2}' | sort -u | xargs kill -9

# Clean up .dashboard files
find . -name '.dashboard' -path '*/.kittify/.dashboard' -delete
```

---

## Testing Validation

### Tests That Detected This Issue

1. ✅ `test_find_free_port_succeeds` - Failed immediately (no ports available)
2. ✅ `test_server_starts_on_specific_port` - Failed (ports exhausted)
3. ✅ All 13 dashboard tests requiring ports - Failed

**Tests revealed the issue within 4 seconds of running.**

### Tests Needed After Fix

1. `test_pid_tracked_in_dashboard_file` - Verify PID is stored
2. `test_stop_dashboard_kills_by_pid_if_http_fails` - Verify fallback
3. `test_orphan_cleanup_on_init` - Verify orphans are cleaned
4. `test_cleanup_command` - Verify cleanup command works

---

## Comparison with Similar Tools

### How Others Handle This

**VSCode Extensions**:
- Store PID in state file
- Kill by PID on extension deactivation
- Periodic health checks clean up orphans

**Docker**:
- Container lifecycle tied to parent process
- `docker ps` shows orphaned containers
- `docker system prune` cleanup command

**Jupyter**:
- Stores PID in `.jupyter` directory
- `jupyter notebook list` shows running servers
- `jupyter notebook stop` kills by PID or port

**Spec-kitty should follow these patterns.**

---

## Upstream Report Checklist

- [x] Evidence collected (port list, process count)
- [x] Root cause identified (no PID tracking)
- [x] Impact assessed (critical - dashboard unusable)
- [x] Reproduction steps documented
- [x] Fixes proposed (with code examples)
- [x] Workaround provided (kill commands)
- [x] Tests created (13 tests, all reveal issue)

---

## Severity Justification

**Why CRITICAL**:

1. **Complete feature failure** - Dashboard is primary UI, now unusable
2. **No graceful degradation** - Hard failure on every init
3. **Resource exhaustion** - All ports consumed
4. **No user recovery** - User can't fix without terminal commands
5. **Silent accumulation** - Problem grows worse over time
6. **Affects all users** - Anyone who uses spec-kitty repeatedly

**This is the #1 priority fix for spec-kitty.**

---

## Timeline

- **2025-11-13 13:00**: Issue discovered during comprehensive dashboard testing
- **2025-11-13 13:15**: Root cause identified (no PID tracking)
- **2025-11-13 13:30**: Finding documented with fixes proposed

---

## Related Issues

- Could explain why users report "dashboard won't start"
- Could explain high memory usage reports
- Could explain "port already in use" errors

---

## Next Steps

1. **Report to upstream immediately** - This blocks all dashboard usage
2. **Kill orphaned processes** - Unblock development
3. **Implement PID tracking** - Prevent future orphans
4. **Add cleanup command** - Give users recovery tool
5. **Add orphan detection** - Clean up automatically on init

---

**END CRITICAL FINDING**
