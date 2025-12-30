"""
Test: PR #59 - Fix dashboard contracts & checklists handlers

Purpose: Validate that dashboard correctly displays contracts and checklists directories.

Bug History:
- Before fix: "Contracts directory not found" and "Checklists directory not found"
  even when these directories existed with files
- Root cause: Nov 11 refactoring didn't migrate these handlers from monolithic
  dashboard.py to new modular structure
- Fix: Added handle_contracts() and handle_checklists() methods (commit 36f885d)

Test Coverage:
1. Contracts Handler (3 tests)
   - /api/contracts/ endpoint works
   - Returns list of contract files
   - Can serve individual contract files

2. Checklists Handler (3 tests)
   - /api/checklists/ endpoint works
   - Returns list of checklist files
   - Can serve individual checklist files

3. Generic Helper Method (2 tests)
   - _handle_artifact_directory() works for both
   - DRY principle applied

4. Frontend Integration (2 tests)
   - Dashboard UI includes contracts section
   - Dashboard UI includes checklists section

Related Issue: #52
Commit: 36f885d6a4a82e9ca6ee41804a66f23b23e53fe7
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class TestDashboardContractsChecklists:
    """Test that dashboard contracts and checklists handlers work."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def initialized_project(self, temp_project_dir, spec_kitty_repo_root):
        """Create and return an initialized spec-kitty project."""
        project_name = 'dashboard_test'
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

        return project_path

    def test_contracts_endpoint_exists(self, initialized_project, spec_kitty_repo_root):
        """
        Test: /api/contracts/ endpoint exists and responds

        Before fix: Would return 404 or error
        After fix: Returns proper JSON response
        """
        # Create a feature with contracts
        create_script = initialized_project / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'contracts-test', 'Test feature'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            check=True
        )

        # Extract feature info
        for line in reversed(result.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                data = json.loads(line.strip())
                feature_num = data['FEATURE_NUM']
                feature_name_normalized = data['BRANCH_NAME'].replace(f"{feature_num}-", "", 1)
                break

        # Create contracts directory
        worktree_path = initialized_project / '.worktrees' / f"{feature_num}-{feature_name_normalized}"
        feature_dir = worktree_path / 'kitty-specs' / f"{feature_num}-{feature_name_normalized}"
        contracts_dir = feature_dir / 'contracts'
        contracts_dir.mkdir(parents=True, exist_ok=True)

        # Add a contract file
        (contracts_dir / 'api-contract.md').write_text('# API Contract\n\nTest contract', encoding='utf-8')

        # Test the endpoint using Python directly (simulating HTTP request)
        import sys
        sys.path.insert(0, str(spec_kitty_repo_root / 'src'))

        from specify_cli.dashboard.handlers.features import FeatureHandler

        # Create a mock handler
        class MockHandler(FeatureHandler):
            def __init__(self, project_dir):
                self.project_dir = str(project_dir)
                self.response_status = None
                self.response_headers = {}
                self.response_body = b''

            def send_response(self, code):
                self.response_status = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

            def wfile_write(self, data):
                self.response_body += data

            # Override wfile
            class WFile:
                def __init__(self, handler):
                    self.handler = handler

                def write(self, data):
                    self.handler.wfile_write(data)

            @property
            def wfile(self):
                return self.WFile(self)

        handler = MockHandler(worktree_path)
        handler.handle_contracts(f'/api/contracts/{feature_num}-{feature_name_normalized}')

        # Should succeed (not 404)
        assert handler.response_status == 200, (
            f"Contracts endpoint should return 200, got {handler.response_status}"
        )

        # Should return JSON
        assert 'application/json' in handler.response_headers.get('Content-type', ''), (
            "Should return JSON content-type"
        )

        # Parse response
        response_data = json.loads(handler.response_body.decode('utf-8'))
        assert 'files' in response_data, "Response should have 'files' key"
        assert len(response_data['files']) > 0, "Should list contract files"

    def test_checklists_endpoint_exists(self, initialized_project, spec_kitty_repo_root):
        """
        Test: /api/checklists/ endpoint exists and responds

        Before fix: Would return 404 or error
        After fix: Returns proper JSON response
        """
        # Create a feature with checklists
        create_script = initialized_project / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'checklist-test', 'Test feature'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            check=True
        )

        # Extract feature info
        for line in reversed(result.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                data = json.loads(line.strip())
                feature_num = data['FEATURE_NUM']
                feature_name_normalized = data['BRANCH_NAME'].replace(f"{feature_num}-", "", 1)
                break

        # Create checklists directory
        worktree_path = initialized_project / '.worktrees' / f"{feature_num}-{feature_name_normalized}"
        feature_dir = worktree_path / 'kitty-specs' / f"{feature_num}-{feature_name_normalized}"
        checklists_dir = feature_dir / 'checklists'
        checklists_dir.mkdir(parents=True, exist_ok=True)

        # Add a checklist file
        (checklists_dir / 'qa-checklist.md').write_text('# QA Checklist\n\n- [ ] Test 1', encoding='utf-8')

        # Test the endpoint using Python directly
        import sys
        sys.path.insert(0, str(spec_kitty_repo_root / 'src'))

        from specify_cli.dashboard.handlers.features import FeatureHandler

        class MockHandler(FeatureHandler):
            def __init__(self, project_dir):
                self.project_dir = str(project_dir)
                self.response_status = None
                self.response_headers = {}
                self.response_body = b''

            def send_response(self, code):
                self.response_status = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

            def wfile_write(self, data):
                self.response_body += data

            class WFile:
                def __init__(self, handler):
                    self.handler = handler

                def write(self, data):
                    self.handler.wfile_write(data)

            @property
            def wfile(self):
                return self.WFile(self)

        handler = MockHandler(worktree_path)
        handler.handle_checklists(f'/api/checklists/{feature_num}-{feature_name_normalized}')

        # Should succeed (not 404)
        assert handler.response_status == 200, (
            f"Checklists endpoint should return 200, got {handler.response_status}"
        )

        # Should return JSON
        assert 'application/json' in handler.response_headers.get('Content-type', ''), (
            "Should return JSON content-type"
        )

        # Parse response
        response_data = json.loads(handler.response_body.decode('utf-8'))
        assert 'files' in response_data, "Response should have 'files' key"
        assert len(response_data['files']) > 0, "Should list checklist files"

    def test_contracts_file_content(self, initialized_project, spec_kitty_repo_root):
        """
        Test: Can retrieve individual contract file content

        Validates the full path: list files → get file content
        """
        # Create a feature with contract
        create_script = initialized_project / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'contract-content', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            check=True
        )

        for line in reversed(result.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                data = json.loads(line.strip())
                feature_num = data['FEATURE_NUM']
                feature_name_normalized = data['BRANCH_NAME'].replace(f"{feature_num}-", "", 1)
                break

        worktree_path = initialized_project / '.worktrees' / f"{feature_num}-{feature_name_normalized}"
        feature_dir = worktree_path / 'kitty-specs' / f"{feature_num}-{feature_name_normalized}"
        contracts_dir = feature_dir / 'contracts'
        contracts_dir.mkdir(parents=True, exist_ok=True)

        contract_content = '# Test Contract\n\nThis is a test contract'
        (contracts_dir / 'test.md').write_text(contract_content, encoding='utf-8')

        # Get file content
        import sys
        sys.path.insert(0, str(spec_kitty_repo_root / 'src'))
        from specify_cli.dashboard.handlers.features import FeatureHandler

        class MockHandler(FeatureHandler):
            def __init__(self, project_dir):
                self.project_dir = str(project_dir)
                self.response_status = None
                self.response_headers = {}
                self.response_body = b''

            def send_response(self, code):
                self.response_status = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

            def wfile_write(self, data):
                self.response_body += data

            class WFile:
                def __init__(self, handler):
                    self.handler = handler

                def write(self, data):
                    self.handler.wfile_write(data)

            @property
            def wfile(self):
                return self.WFile(self)

        handler = MockHandler(worktree_path)
        # Request specific file (path format: /api/contracts/FEATURE/FILE_PATH)
        handler.handle_contracts(f'/api/contracts/{feature_num}-{feature_name_normalized}/contracts/test.md')

        assert handler.response_status == 200, "Should serve file content"
        content = handler.response_body.decode('utf-8')
        assert 'Test Contract' in content, "Should return file content"

    def test_checklists_file_content(self, initialized_project, spec_kitty_repo_root):
        """
        Test: Can retrieve individual checklist file content

        Validates the full path: list files → get file content
        """
        create_script = initialized_project / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'checklist-content', 'Test'],
            cwd=initialized_project,
            capture_output=True,
            text=True,
            check=True
        )

        for line in reversed(result.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                data = json.loads(line.strip())
                feature_num = data['FEATURE_NUM']
                feature_name_normalized = data['BRANCH_NAME'].replace(f"{feature_num}-", "", 1)
                break

        worktree_path = initialized_project / '.worktrees' / f"{feature_num}-{feature_name_normalized}"
        feature_dir = worktree_path / 'kitty-specs' / f"{feature_num}-{feature_name_normalized}"
        checklists_dir = feature_dir / 'checklists'
        checklists_dir.mkdir(parents=True, exist_ok=True)

        checklist_content = '# QA Checklist\n\n- [ ] Item 1\n- [ ] Item 2'
        (checklists_dir / 'qa.md').write_text(checklist_content, encoding='utf-8')

        import sys
        sys.path.insert(0, str(spec_kitty_repo_root / 'src'))
        from specify_cli.dashboard.handlers.features import FeatureHandler

        class MockHandler(FeatureHandler):
            def __init__(self, project_dir):
                self.project_dir = str(project_dir)
                self.response_status = None
                self.response_headers = {}
                self.response_body = b''

            def send_response(self, code):
                self.response_status = code

            def send_header(self, key, value):
                self.response_headers[key] = value

            def end_headers(self):
                pass

            def wfile_write(self, data):
                self.response_body += data

            class WFile:
                def __init__(self, handler):
                    self.handler = handler

                def write(self, data):
                    self.handler.wfile_write(data)

            @property
            def wfile(self):
                return self.WFile(self)

        handler = MockHandler(worktree_path)
        handler.handle_checklists(f'/api/checklists/{feature_num}-{feature_name_normalized}/checklists/qa.md')

        assert handler.response_status == 200, "Should serve file content"
        content = handler.response_body.decode('utf-8')
        assert 'QA Checklist' in content, "Should return checklist content"

    def test_router_has_contracts_route(self, spec_kitty_repo_root):
        """
        Test: DashboardRouter includes /api/contracts/ route

        Verify the route is registered in router.py
        """
        router_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/handlers/router.py'
        content = router_file.read_text(encoding='utf-8')

        assert "'/api/contracts/'" in content or '"/api/contracts/"' in content, (
            "Router should have /api/contracts/ route"
        )
        assert 'handle_contracts' in content, (
            "Router should call handle_contracts method"
        )

    def test_router_has_checklists_route(self, spec_kitty_repo_root):
        """
        Test: DashboardRouter includes /api/checklists/ route

        Verify the route is registered in router.py
        """
        router_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/handlers/router.py'
        content = router_file.read_text(encoding='utf-8')

        assert "'/api/checklists/'" in content or '"/api/checklists/"' in content, (
            "Router should have /api/checklists/ route"
        )
        assert 'handle_checklists' in content, (
            "Router should call handle_checklists method"
        )

    def test_features_handler_has_methods(self, spec_kitty_repo_root):
        """
        Test: FeatureHandler has handle_contracts() and handle_checklists()

        Verify the methods exist in features.py
        """
        features_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/handlers/features.py'
        content = features_file.read_text(encoding='utf-8')

        assert 'def handle_contracts' in content, (
            "Should have handle_contracts method"
        )
        assert 'def handle_checklists' in content, (
            "Should have handle_checklists method"
        )
        assert 'def _handle_artifact_directory' in content, (
            "Should have generic _handle_artifact_directory helper (DRY principle)"
        )

    def test_dashboard_template_has_contracts_section(self, spec_kitty_repo_root):
        """
        Test: Dashboard HTML template includes contracts section

        Verify the frontend UI includes contracts navigation
        """
        template_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/templates/index.html'
        content = template_file.read_text(encoding='utf-8')

        assert 'contracts' in content.lower(), (
            "Dashboard template should mention contracts"
        )
        assert 'page-contracts' in content or 'contracts-content' in content, (
            "Dashboard should have contracts page/section"
        )

    def test_dashboard_template_has_checklists_section(self, spec_kitty_repo_root):
        """
        Test: Dashboard HTML template includes checklists section

        Verify the frontend UI includes checklists navigation
        """
        template_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/templates/index.html'
        content = template_file.read_text(encoding='utf-8')

        assert 'checklists' in content.lower(), (
            "Dashboard template should mention checklists"
        )
        assert 'page-checklists' in content or 'checklists-content' in content, (
            "Dashboard should have checklists page/section"
        )

    def test_dashboard_javascript_has_functions(self, spec_kitty_repo_root):
        """
        Test: Dashboard JavaScript has loadContracts() and loadChecklists()

        Verify the frontend JavaScript includes handler functions
        """
        js_file = spec_kitty_repo_root / 'src/specify_cli/dashboard/static/dashboard/dashboard.js'
        content = js_file.read_text(encoding='utf-8')

        assert 'function loadContracts' in content or 'loadContracts()' in content, (
            "JavaScript should have loadContracts function"
        )
        assert 'function loadChecklists' in content or 'loadChecklists()' in content, (
            "JavaScript should have loadChecklists function"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
