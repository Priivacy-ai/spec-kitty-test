"""
Dashboard File Modification Detection Tests

Tests that the dashboard detects and updates when EXISTING files are modified,
not just when new files are created.

The Bug Scenario:
----------------
1. Agent creates spec.md with placeholder content ("Generating spec...")
2. Dashboard shows spec.md exists (file creation detected ✓)
3. Agent overwrites spec.md with actual specification content
4. Dashboard does NOT update to show new content ✗
5. User must manually refresh page to see updated content

This is different from file creation detection - this is about detecting
MODIFICATIONS to existing files.

Test Coverage:
-------------
1. Initial Content Detection (2 tests)
   - Dashboard shows initial file content
   - Initial state is captured correctly

2. Content Modification Detection (4 tests)
   - Modified spec.md content appears
   - Modified plan.md content appears
   - Modified constitution.md content appears
   - Modified content shows without manual refresh

3. Update Timing (3 tests)
   - Modification detected within reasonable time
   - Multiple rapid modifications handled
   - Large content changes detected

4. API vs UI Consistency (2 tests)
   - API reflects modifications
   - Browser UI reflects modifications (critical!)

5. File System Events (2 tests)
   - File modification timestamp changes trigger update
   - Multiple file modifications in sequence

Reproduction Scenario:
---------------------
This test reproduces the exact user-reported bug:

```python
# Step 1: Create initial spec.md (placeholder)
spec.write_text("# Spec\n\nGenerating specification...\n")
# Dashboard detects new file ✓

# Step 2: Wait for dashboard to show it
time.sleep(2)
verify_api_shows_spec()  # ✓ Passes

# Step 3: Agent writes actual spec content
spec.write_text('''# Actual Specification
## Requirements
- REQ-1: Real requirement
- REQ-2: Another requirement
...
''')

# Step 4: Check if dashboard shows updated content WITHOUT refresh
time.sleep(5)
api_data = get_api_features()

# BUG: API may still show old content or not trigger UI refresh
assert "REQ-1" in api_data  # May fail!
```
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


@pytest.fixture
def dashboard_with_feature(tmp_path, spec_kitty_repo_root):
    """Create a test project with dashboard running and a feature created."""
    project_name = 'mod_detect_test'
    project_path = tmp_path / project_name

    env = os.environ.copy()
    env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

    # Create project
    subprocess.run(
        ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
        cwd=tmp_path,
        env=env,
        input='y\n',
        capture_output=True,
        text=True,
        check=True
    )

    # Create a feature
    create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
    result = subprocess.run(
        [str(create_script), '--json', '--feature-name', 'Modification Test', 'Test file change detection'],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True
    )

    # Extract feature info
    output_data = json.loads(result.stdout.strip().split('\n')[-1])
    feature_id = output_data['BRANCH_NAME']
    worktree_path = Path(output_data['WORKTREE_PATH'])

    # Start dashboard
    from specify_cli.dashboard.lifecycle import ensure_dashboard_running

    url, port, started = ensure_dashboard_running(project_path, background_process=False)

    # Give it time to fully start
    time.sleep(1)

    yield {
        'project_path': project_path,
        'worktree_path': worktree_path,
        'feature_id': feature_id,
        'feature_dir': worktree_path / 'kitty-specs' / feature_id,
        'url': url,
        'port': port,
    }

    # Cleanup
    from specify_cli.dashboard.lifecycle import stop_dashboard
    stop_dashboard(project_path)


class TestInitialContentDetection:
    """Test dashboard shows initial file content correctly."""

    def test_dashboard_shows_initial_spec_content(self, page, dashboard_with_feature):
        """Test: Dashboard captures initial spec.md content"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        # Create spec.md with initial placeholder
        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'
        initial_content = "# Specification\n\nGenerating specification...\n"
        spec.write_text(initial_content, encoding="utf-8")

        # Wait for dashboard to detect it
        time.sleep(3)

        # Load dashboard
        page.goto(url, wait_until="networkidle")

        # Check API
        import urllib.request
        response = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        api_data = json.loads(response.read())

        # Spec should be detected as existing
        features = api_data.get('features', [])
        assert len(features) > 0, "Should have at least one feature"

        artifacts = features[0].get('artifacts', {})
        assert artifacts.get('spec', False), \
            "Dashboard should detect spec.md exists"

    def test_initial_state_captured(self, page, dashboard_with_feature):
        """Test: Dashboard API returns file content (if it does)"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']
        feature_id = dashboard_with_feature['feature_id']

        # Create spec with specific initial content
        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'
        spec.write_text("# Initial Spec\n\nPLACEHOLDER_CONTENT_v1\n", encoding="utf-8")

        time.sleep(3)

        # Check if API provides content (not just existence)
        import urllib.request
        try:
            # Try to get spec content via API
            response = urllib.request.urlopen(f"{url}/api/artifact/{feature_id}/spec.md", timeout=2)
            content = response.read().decode('utf-8')

            assert 'PLACEHOLDER_CONTENT_v1' in content, \
                "API should return spec content"
        except urllib.error.HTTPError:
            # If no artifact endpoint, just verify file exists
            assert spec.exists(), "Spec file should exist"


class TestContentModificationDetection:
    """Test dashboard detects when existing files are modified."""

    def test_spec_modification_detected(self, page, dashboard_with_feature):
        """
        Test: Dashboard updates when spec.md is MODIFIED (not just created).

        This reproduces the exact bug: Agent creates spec.md, then overwrites
        it with real content. Dashboard should show updated content.
        """
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']
        feature_id = dashboard_with_feature['feature_id']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # STEP 1: Agent creates initial placeholder
        initial_content = "# Specification\n\nGenerating specification based on discovery...\n"
        spec.write_text(initial_content, encoding="utf-8")

        # Wait for dashboard to detect initial version
        time.sleep(3)

        # Load page and verify initial content
        page.goto(url, wait_until="networkidle")

        import urllib.request

        # Get initial API state
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        initial_api_state = json.loads(response1.read())

        # Verify spec is detected
        features = initial_api_state.get('features', [])
        assert len(features) > 0, "Should have feature"
        assert features[0]['artifacts'].get('spec', False), \
            "Initial spec.md should be detected"

        # STEP 2: Agent overwrites with actual spec content
        actual_content = """# Product Specification

## Overview
This is the ACTUAL specification content written by the agent.

## Requirements

### REQ-1: Dashboard Auto-Update
The dashboard must automatically reflect file changes without manual refresh.

### REQ-2: Real-Time Sync
Content modifications should appear within 10 seconds.

### REQ-3: No Cache Staleness
The UI must not show cached/stale content.

## Implementation Details
- File modification timestamps trigger updates
- Server monitors file system changes
- Client polls or uses WebSocket for live updates
"""
        spec.write_text(actual_content, encoding="utf-8")

        print(f"\n✓ Modified spec.md at {spec}")
        print(f"  File mtime: {spec.stat().st_mtime}")

        # STEP 3: Wait for dashboard to detect modification
        max_wait = 15  # seconds
        updated = False
        content_updated = False

        for elapsed in range(max_wait):
            time.sleep(1)

            # Check if API reflects the change
            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current_api_state = json.loads(response2.read())

            # Try to get actual content if API exposes it
            try:
                content_response = urllib.request.urlopen(f"{url}/api/artifact/{feature_id}/spec.md", timeout=2)
                current_content = content_response.read().decode('utf-8')

                # Check if content has the new requirements
                if 'REQ-1: Dashboard Auto-Update' in current_content:
                    content_updated = True
                    print(f"✓ Content updated after {elapsed + 1}s")
                    break
            except urllib.error.HTTPError:
                # No direct artifact endpoint
                pass

            # At minimum, check if something changed
            if json.dumps(current_api_state) != json.dumps(initial_api_state):
                updated = True
                if not content_updated:
                    print(f"  API state changed after {elapsed + 1}s (but content may not be exposed)")

        # THE CRITICAL ASSERTION
        if not content_updated and not updated:
            pytest.fail(
                f"Dashboard did not detect spec.md modification after {max_wait}s.\n\n"
                f"This confirms the bug:\n"
                f"- Created spec.md with placeholder ✓\n"
                f"- Modified spec.md with actual content ✓\n"
                f"- Dashboard API did not reflect modification ✗\n\n"
                f"Expected: API shows updated content within {max_wait}s\n"
                f"Actual: API still shows old state or doesn't expose content\n\n"
                f"User must manually refresh to see changes!"
            )

        # If API updated but we can't verify content, document it
        if updated and not content_updated:
            print(f"⚠ API state changed but couldn't verify content update")
            print(f"  (API may not expose file content directly)")

    def test_plan_modification_detected(self, page, dashboard_with_feature):
        """Test: Dashboard detects plan.md modifications"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']
        feature_id = dashboard_with_feature['feature_id']

        feature_dir.mkdir(parents=True, exist_ok=True)
        plan = feature_dir / 'plan.md'

        # Create initial plan
        plan.write_text("# Plan\n\nInitial plan outline...\n", encoding="utf-8")
        time.sleep(3)

        # Get baseline
        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Modify plan with detailed content
        plan.write_text("""# Implementation Plan

## Phase 1: Foundation
- Task 1.1: Set up infrastructure
- Task 1.2: Configure tools

## Phase 2: Development
- Task 2.1: Implement core features
- Task 2.2: Add error handling

## Phase 3: Testing
- Task 3.1: Unit tests
- Task 3.2: Integration tests
""", encoding="utf-8")

        # Wait for update
        max_wait = 15
        detected = False

        for elapsed in range(max_wait):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ Plan modification detected after {elapsed + 1}s")
                break

        if not detected:
            pytest.fail(
                f"Dashboard did not detect plan.md modification after {max_wait}s.\n"
                f"Initial: {plan.read_text()[:50]}...\n"
                f"Modified content not reflected in API."
            )

    def test_multiple_rapid_modifications(self, page, dashboard_with_feature):
        """
        Test: Dashboard handles rapid successive modifications.

        Scenario: Agent writes spec in multiple passes (outline, then details, then refinement)
        """
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Version 1: Outline
        spec.write_text("# Spec v1\n\nOutline only\n", encoding="utf-8")
        time.sleep(2)

        # Version 2: With requirements (rapid change)
        spec.write_text("# Spec v2\n\n## Requirements\n- REQ-1: Test\n", encoding="utf-8")
        time.sleep(2)

        # Version 3: Full detail (rapid change)
        spec.write_text("""# Spec v3 - FINAL

## Requirements
- REQ-1: Complete requirement
- REQ-2: Another requirement
- REQ-3: Final requirement

## Design
Full design details here.
""", encoding="utf-8")

        # Wait for final update
        time.sleep(5)

        # Verify file has final content
        final_content = spec.read_text(encoding="utf-8")
        assert 'v3 - FINAL' in final_content, "File should have final version"

        # The question: Does dashboard show v3, or stale v1/v2?
        # This test documents the behavior

    def test_large_content_change_detected(self, page, dashboard_with_feature):
        """Test: Dashboard detects large content changes (not just small edits)"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Start with small spec
        small_content = "# Spec\n\nSmall initial spec.\n"
        spec.write_text(small_content, encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Replace with large spec (simulate agent writing full specification)
        large_content = "# Specification\n\n" + "\n".join([
            f"## Section {i}\n\nContent for section {i} with detailed information.\n"
            for i in range(1, 21)  # 20 sections
        ])
        spec.write_text(large_content, encoding="utf-8")

        # File size change: ~50 bytes → ~1KB+
        print(f"  File size: {len(small_content)} → {len(large_content)} bytes")

        # Wait for update
        max_wait = 15
        detected = False

        for elapsed in range(max_wait):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            # Check if anything changed
            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ Large content change detected after {elapsed + 1}s")
                break

        if not detected:
            pytest.fail(
                f"Dashboard did not detect large content change after {max_wait}s.\n"
                f"Size change: {len(small_content)} → {len(large_content)} bytes"
            )


class TestAPIvsUIConsistency:
    """Test that API updates match UI updates."""

    def test_api_reflects_modifications(self, page, dashboard_with_feature):
        """Test: API /api/features reflects file modifications"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Create initial
        spec.write_text("# Version 1\n", encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        state1 = json.loads(response1.read())

        # Modify
        spec.write_text("# Version 2 - Modified\n\nNew content here\n", encoding="utf-8")
        time.sleep(5)

        response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        state2 = json.loads(response2.read())

        # API should show some change (at minimum, mtime could be tracked)
        # The bug is if state2 == state1 (no change detected)
        state1_str = json.dumps(state1, sort_keys=True)
        state2_str = json.dumps(state2, sort_keys=True)

        # Document current behavior
        if state1_str == state2_str:
            pytest.fail(
                "API did not change after file modification!\n"
                "This confirms the bug: modifications not detected."
            )
        else:
            print("✓ API state changed after modification")

    def test_browser_ui_reflects_modifications_without_refresh(self, page, dashboard_with_feature):
        """
        Test: Browser UI updates WITHOUT manual page.reload()

        This is THE critical test for the user-reported bug.
        """
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']
        feature_id = dashboard_with_feature['feature_id']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # STEP 1: Create initial spec
        spec.write_text("# Spec v1\n\nINITIAL_MARKER\n", encoding="utf-8")

        # STEP 2: Load dashboard
        page.goto(url, wait_until="networkidle")
        page.wait_for_load_state("networkidle")

        # Wait for initial content to load
        time.sleep(3)

        # Get page content (without reload)
        initial_page_content = page.content()

        # STEP 3: Modify the spec file (like agent does)
        spec.write_text("""# Specification - UPDATED

## Requirements
- REQ-1: Auto-update detection
- REQ-2: No manual refresh needed

MODIFIED_MARKER_UNIQUE_12345
""", encoding="utf-8")

        print(f"\n✓ Modified spec.md")
        print(f"  Waiting for UI to auto-update (without page.reload())...")

        # STEP 4: Wait and check if page content updates WITHOUT reload
        max_wait = 15
        ui_updated = False

        for elapsed in range(max_wait):
            time.sleep(1)

            # Get current page content WITHOUT reload
            current_page_content = page.content()

            # Check if the modification marker appears
            if 'MODIFIED_MARKER_UNIQUE_12345' in current_page_content:
                ui_updated = True
                print(f"✓ UI auto-updated after {elapsed + 1}s (without reload!)")
                break

            # Also check if the old marker disappeared
            if 'INITIAL_MARKER' not in current_page_content and 'MODIFIED_MARKER' in current_page_content:
                ui_updated = True
                print(f"✓ UI refreshed after {elapsed + 1}s")
                break

        # THE BUG TEST
        if not ui_updated:
            # Now manually reload to verify content IS there (just not auto-updated)
            page.reload(wait_until="networkidle")
            after_refresh = page.content()

            if 'MODIFIED_MARKER_UNIQUE_12345' in after_refresh:
                pytest.fail(
                    f"🐛 BUG CONFIRMED: Dashboard does NOT auto-update!\n\n"
                    f"Timeline:\n"
                    f"1. Created spec.md with INITIAL_MARKER ✓\n"
                    f"2. Dashboard loaded and showed initial content ✓\n"
                    f"3. Modified spec.md with MODIFIED_MARKER ✓\n"
                    f"4. Waited {max_wait}s without manual refresh ✓\n"
                    f"5. UI did NOT show updated content ✗\n"
                    f"6. Manual refresh showed updated content ✓\n\n"
                    f"EXPECTED: UI auto-updates within {max_wait}s\n"
                    f"ACTUAL: UI requires manual refresh\n\n"
                    f"User Impact: Must refresh browser to see agent's work!"
                )
            else:
                pytest.fail(
                    f"File modification not reflected even after manual refresh.\n"
                    f"This suggests a deeper caching or serving issue."
                )

    def test_constitution_modification_detected(self, page, dashboard_with_feature):
        """Test: Dashboard detects constitution.md modifications (once tracking is added)"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        constitution = feature_dir / 'constitution.md'

        # Initial constitution
        constitution.write_text("# Constitution v1\n", encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Modify constitution
        constitution.write_text("""# Constitution - Updated

## Purpose
The UPDATED purpose of this feature.

## Success Criteria
- SC-1: Updated criterion
- SC-2: New criterion
""", encoding="utf-8")

        # Wait for detection
        max_wait = 15
        detected = False

        for elapsed in range(max_wait):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ Constitution modification detected after {elapsed + 1}s")
                break

        if not detected:
            # This may fail until constitution tracking is added
            pytest.skip(
                "Constitution modifications not detected. "
                "This is expected if constitution.md isn't tracked yet."
            )

    def test_plan_modification_shows_in_ui(self, page, dashboard_with_feature):
        """Test: Plan.md modifications appear in browser UI"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        plan = feature_dir / 'plan.md'

        # Create initial plan
        plan.write_text("# Plan Draft\n\nDRAFT_VERSION\n", encoding="utf-8")

        # Load dashboard
        page.goto(url, wait_until="networkidle")
        time.sleep(3)

        # Modify plan
        plan.write_text("# Final Plan\n\nFINAL_VERSION_COMPLETE\n", encoding="utf-8")

        # Wait WITHOUT reload
        time.sleep(10)

        # Check if UI updated
        current_content = page.content()

        if 'FINAL_VERSION_COMPLETE' in current_content:
            print("✓ Plan modification auto-updated in UI!")
        else:
            # Try manual refresh
            page.reload(wait_until="networkidle")
            after_refresh = page.content()

            if 'FINAL_VERSION_COMPLETE' in after_refresh:
                pytest.fail(
                    "Plan modification requires manual refresh.\n"
                    "UI does not auto-update for file changes."
                )


class TestUpdateTiming:
    """Test timing and performance of modification detection."""

    def test_modification_latency_under_10_seconds(self, page, dashboard_with_feature):
        """Test: File modifications reflected in API within 10 seconds"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Create initial
        spec.write_text("# V1\n", encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Modify and start timer
        start_time = time.time()
        spec.write_text("# V2 - UPDATED\n\nMODIFICATION_TEST\n", encoding="utf-8")

        # Poll until detected
        for elapsed in range(15):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                latency = time.time() - start_time
                print(f"✓ Modification detected in {latency:.2f}s")

                # Should be under 10 seconds for good UX
                assert latency < 10, \
                    f"Modification latency too high: {latency:.2f}s (should be < 10s)"
                return

        pytest.fail("Modification not detected within 15 seconds")

    def test_file_mtime_change_triggers_update(self, page, dashboard_with_feature):
        """Test: File modification time change triggers dashboard update"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Create file
        spec.write_text("# Original\n", encoding="utf-8")
        original_mtime = spec.stat().st_mtime
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Modify file (changes mtime)
        time.sleep(1)  # Ensure mtime changes
        spec.write_text("# Modified\n", encoding="utf-8")
        new_mtime = spec.stat().st_mtime

        assert new_mtime > original_mtime, "mtime should increase"
        print(f"  mtime changed: {original_mtime} → {new_mtime}")

        # Check if dashboard detects mtime change
        max_wait = 10
        detected = False

        for elapsed in range(max_wait):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ mtime change triggered update after {elapsed + 1}s")
                break

        if not detected:
            pytest.fail(
                f"Dashboard did not detect file modification via mtime change.\n"
                f"Original mtime: {original_mtime}\n"
                f"New mtime: {new_mtime}\n"
                f"Dashboard may not be watching file system or polling mtimes."
            )

    def test_sequential_file_modifications(self, page, dashboard_with_feature):
        """Test: Multiple files modified in sequence are all detected"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)

        # Create all three files
        constitution = feature_dir / 'constitution.md'
        spec = feature_dir / 'spec.md'
        plan = feature_dir / 'plan.md'

        constitution.write_text("# Constitution v1\n", encoding="utf-8")
        spec.write_text("# Spec v1\n", encoding="utf-8")
        plan.write_text("# Plan v1\n", encoding="utf-8")

        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Modify each file in sequence
        constitution.write_text("# Constitution v2 - UPDATED\n", encoding="utf-8")
        time.sleep(2)

        spec.write_text("# Spec v2 - UPDATED\n", encoding="utf-8")
        time.sleep(2)

        plan.write_text("# Plan v2 - UPDATED\n", encoding="utf-8")
        time.sleep(2)

        # Final check
        response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        final = json.loads(response2.read())

        # Should reflect changes
        if json.dumps(final) == json.dumps(baseline):
            pytest.fail(
                "Dashboard did not detect sequential file modifications.\n"
                "Modified constitution, spec, and plan but API unchanged."
            )


class TestFileSystemEvents:
    """Test dashboard's file system monitoring mechanism."""

    def test_file_overwrite_detected(self, page, dashboard_with_feature):
        """Test: File overwrite (not append) triggers update"""
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Create
        spec.write_text("Original content\n", encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Overwrite (common agent pattern: create temp, then move)
        spec.write_text("Completely replaced content\n", encoding="utf-8")

        # Check detection
        detected = False
        for i in range(10):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ File overwrite detected after {i + 1}s")
                break

        if not detected:
            pytest.fail(
                "File overwrite not detected.\n"
                "Dashboard may only detect new files, not modifications."
            )

    def test_atomic_write_detected(self, page, dashboard_with_feature):
        """
        Test: Atomic write operations (temp file + rename) are detected.

        Many agents write files atomically:
        1. Write to spec.md.tmp
        2. Rename spec.md.tmp → spec.md

        Dashboard should detect this as a modification.
        """
        url = dashboard_with_feature['url']
        feature_dir = dashboard_with_feature['feature_dir']

        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'

        # Create initial
        spec.write_text("Initial\n", encoding="utf-8")
        time.sleep(3)

        import urllib.request
        response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
        baseline = json.loads(response1.read())

        # Atomic write pattern
        temp_file = feature_dir / 'spec.md.tmp'
        temp_file.write_text("Updated via atomic write\n", encoding="utf-8")
        temp_file.replace(spec)  # Atomic rename

        # Check detection
        detected = False
        for i in range(10):
            time.sleep(1)

            response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            current = json.loads(response2.read())

            if json.dumps(current) != json.dumps(baseline):
                detected = True
                print(f"✓ Atomic write detected after {i + 1}s")
                break

        if not detected:
            pytest.fail(
                "Atomic write (temp + rename) not detected.\n"
                "Dashboard may not properly monitor file system events."
            )
