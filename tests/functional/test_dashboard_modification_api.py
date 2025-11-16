"""
Dashboard File Modification API Tests (No Browser)

Simplified tests that check ONLY the backend API to isolate whether the issue
is in:
1. File system monitoring (backend not detecting changes)
2. API response caching (backend detects but doesn't update response)
3. UI polling (backend updates but UI doesn't fetch)

These tests don't use Playwright - just direct API calls.
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
    """Get spec-kitty repository root."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError("spec-kitty repository not found")


class TestAPIFileModificationDetection:
    """Test if backend API detects file modifications."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_api_detects_spec_modification(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: /api/features endpoint reflects spec.md modifications.

        This isolates the backend - no browser, no UI, just API polling.
        """
        project_name = 'api_mod_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        # Create project
        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'API Test', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        feature_id = output_data['BRANCH_NAME']
        worktree_path = Path(output_data['WORKTREE_PATH'])
        feature_dir = worktree_path / 'kitty-specs' / feature_id

        # Start dashboard (threaded, not subprocess)
        from specify_cli.dashboard.lifecycle import ensure_dashboard_running

        url, port, started = ensure_dashboard_running(project_path, background_process=False)
        time.sleep(2)

        try:
            feature_dir.mkdir(parents=True, exist_ok=True)
            spec = feature_dir / 'spec.md'

            # STEP 1: Create initial spec
            print("\n=== STEP 1: Create initial spec.md ===")
            spec.write_text("# Initial Spec\n\nPlaceholder content\n", encoding="utf-8")
            print(f"Created: {spec}")
            print(f"Size: {spec.stat().st_size} bytes")
            print(f"mtime: {spec.stat().st_mtime}")

            # Wait for initial detection
            time.sleep(3)

            # Get baseline API state
            import urllib.request
            response1 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            baseline_state = json.loads(response1.read())

            print(f"\nBaseline API state:")
            print(f"  Features: {len(baseline_state.get('features', []))}")
            if baseline_state.get('features'):
                artifacts = baseline_state['features'][0].get('artifacts', {})
                print(f"  Spec exists: {artifacts.get('spec', False)}")

            # STEP 2: Modify spec (THE CRITICAL MOMENT)
            print("\n=== STEP 2: Modify spec.md with actual content ===")
            modified_content = """# Product Specification - FINAL

## Overview
This is the ACTUAL specification written by the agent after discovery.

## Requirements

### REQ-1: Auto-Update Detection
The dashboard must detect when this file changes.

### REQ-2: API Reflection
The /api/features endpoint must reflect file modifications.

### REQ-3: Timestamp Monitoring
The server should check file modification times.

## Version
This is version 2 of the spec (completely different from placeholder).
"""
            spec.write_text(modified_content, encoding="utf-8")
            modification_time = time.time()

            print(f"Modified: {spec}")
            print(f"New size: {spec.stat().st_size} bytes (was {len('# Initial Spec\n\nPlaceholder content\n')})")
            print(f"New mtime: {spec.stat().st_mtime}")

            # STEP 3: Poll API to see if it detects the change
            print(f"\n=== STEP 3: Poll API for changes ===")
            print(f"Polling /api/features every 1s for up to 15s...")

            max_wait = 15
            api_updated = False
            update_latency = None

            for elapsed in range(max_wait):
                time.sleep(1)

                response2 = urllib.request.urlopen(f"{url}/api/features", timeout=2)
                current_state = json.loads(response2.read())

                # Compare states
                baseline_json = json.dumps(baseline_state, sort_keys=True)
                current_json = json.dumps(current_state, sort_keys=True)

                if baseline_json != current_json:
                    api_updated = True
                    update_latency = time.time() - modification_time
                    print(f"\n✓ API state changed after {elapsed + 1}s (latency: {update_latency:.2f}s)")

                    # Show what changed
                    print(f"\nAPI Changes Detected:")
                    if baseline_state.get('features') and current_state.get('features'):
                        old_artifacts = baseline_state['features'][0].get('artifacts', {})
                        new_artifacts = current_state['features'][0].get('artifacts', {})

                        for key in set(old_artifacts.keys()) | set(new_artifacts.keys()):
                            old_val = old_artifacts.get(key, 'N/A')
                            new_val = new_artifacts.get(key, 'N/A')
                            if old_val != new_val:
                                print(f"  {key}: {old_val} → {new_val}")
                    break
                else:
                    if (elapsed + 1) % 3 == 0:
                        print(f"  {elapsed + 1}s: No change yet...")

            # RESULT
            print(f"\n=== RESULT ===")

            if not api_updated:
                print(f"✗ FAIL: API did not change after {max_wait}s")
                print(f"\nBaseline state:")
                print(json.dumps(baseline_state, indent=2))
                print(f"\nCurrent state:")
                print(json.dumps(current_state, indent=2))

                pytest.fail(
                    f"🐛 BUG CONFIRMED: Backend API does NOT detect file modifications!\n\n"
                    f"What happened:\n"
                    f"1. Created spec.md (size: {len('# Initial Spec\n\nPlaceholder content\n')} bytes) ✓\n"
                    f"2. API detected spec exists ✓\n"
                    f"3. Modified spec.md (size: {spec.stat().st_size} bytes) ✓\n"
                    f"4. Waited {max_wait}s ✓\n"
                    f"5. API /api/features response UNCHANGED ✗\n\n"
                    f"Root Cause: Backend is not monitoring file modifications.\n"
                    f"It only detects NEW files, not changes to EXISTING files.\n\n"
                    f"Impact: Users must restart dashboard or manually trigger refresh."
                )
            else:
                print(f"✓ PASS: API detected modification in {update_latency:.2f}s")

        finally:
            from specify_cli.dashboard.lifecycle import stop_dashboard
            stop_dashboard(project_path)

    def test_api_response_format_includes_mtime(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Check if API includes file modification times (helpful for detecting changes)"""
        project_name = 'api_mtime_test'
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            check=True
        )

        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'mtime test', 'Test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        worktree_path = Path(output_data['WORKTREE_PATH'])
        feature_id = output_data['BRANCH_NAME']
        feature_dir = worktree_path / 'kitty-specs' / feature_id

        # Create spec
        feature_dir.mkdir(parents=True, exist_ok=True)
        spec = feature_dir / 'spec.md'
        spec.write_text("# Spec\n", encoding="utf-8")
        mtime = spec.stat().st_mtime

        # Start dashboard
        from specify_cli.dashboard.lifecycle import ensure_dashboard_running
        url, port, started = ensure_dashboard_running(project_path, background_process=False)
        time.sleep(2)

        try:
            # Get API response
            import urllib.request
            response = urllib.request.urlopen(f"{url}/api/features", timeout=2)
            api_data = json.loads(response.read())

            print(f"\nAPI Response Structure:")
            print(json.dumps(api_data, indent=2))

            # Check if mtime is included
            features = api_data.get('features', [])
            if features:
                feature = features[0]
                print(f"\nFeature data keys: {list(feature.keys())}")

                # Does it include mtime or last_modified?
                has_mtime_tracking = (
                    'mtime' in str(feature).lower() or
                    'modified' in str(feature).lower() or
                    'timestamp' in str(feature).lower()
                )

                if not has_mtime_tracking:
                    print(f"\n⚠ API does not include modification timestamps!")
                    print(f"  Without mtimes, backend can't efficiently detect file changes")
                else:
                    print(f"\n✓ API includes modification time tracking")

        finally:
            from specify_cli.dashboard.lifecycle import stop_dashboard
            stop_dashboard(project_path)
