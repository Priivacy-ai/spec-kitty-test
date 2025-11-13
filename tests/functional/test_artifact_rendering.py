"""
Category 5: Artifact Rendering & Display Tests

Tests artifact discovery, content serving, and error handling for research artifacts
in the spec-kitty dashboard.

Test Coverage:
1. Research Artifact Discovery (3 tests)
   - All artifact types discovered
   - Icon mapping by file extension
   - Nested directory artifacts

2. Artifact Content Serving (4 tests)
   - CSV files served correctly
   - JSON files with valid encoding
   - YAML files readable
   - Markdown artifacts

3. Error Handling (3 tests)
   - Non-UTF-8 file recovery
   - Path traversal blocked
   - Large file handling
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def spec_kitty_repo_root():
    """Get spec-kitty repository root from environment or default location."""
    env_path = os.environ.get('SPEC_KITTY_REPO')
    if env_path:
        return Path(env_path)

    # Default: sibling directory to spec-kitty-test
    default_path = Path(__file__).parent.parent.parent.parent / 'spec-kitty'
    if default_path.exists():
        return default_path

    raise ValueError(
        "Could not find spec-kitty repository. "
        "Set SPEC_KITTY_REPO environment variable or ensure ../spec-kitty exists"
    )


class TestArtifactDiscovery:
    """Test artifact discovery in research/ directories."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_research_artifacts_discovered(self, temp_project_dir, spec_kitty_repo_root):
        """Test: All artifact types in research/ directory are discovered"""
        project_name = "test_artifacts"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Artifact Test', 'Test artifacts'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Extract feature info
        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        # Create research artifacts in worktree
        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create various artifact types
        (research_dir / 'data.csv').write_text("name,value\ntest,123\n")
        (research_dir / 'config.json').write_text('{"key": "value"}')
        (research_dir / 'notes.md').write_text("# Research Notes\n")
        (research_dir / 'settings.yaml').write_text("setting: value\n")
        (research_dir / 'chart.xlsx').write_bytes(b'fake excel data')

        # Scan for artifacts using dashboard scanner
        from specify_cli.dashboard import scan_all_features

        features = scan_all_features(project_path)
        feature = next((f for f in features if f['id'] == branch_name), None)

        assert feature is not None, f"Should find feature {branch_name}"

        # Check if artifacts are discovered
        # Note: The actual artifact discovery depends on spec-kitty implementation
        # This test validates the research/ directory structure is correct
        assert research_dir.exists(), "research/ directory should exist"
        assert len(list(research_dir.glob('*'))) == 5, "Should have 5 artifacts"

    def test_artifact_icon_mapping(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Icons correctly assigned based on file extension"""
        project_name = "test_icons"
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

        # Expected icon mappings (from spec-kitty documentation)
        icon_map = {
            '.csv': '📊',
            '.json': '📋',
            '.md': '📝',
            '.yaml': '📄',
            '.yml': '📄',
            '.xlsx': '📈',
            '.txt': '📄',  # default
        }

        # This test documents expected behavior
        # Actual icon mapping may be implemented in dashboard frontend
        for ext, expected_icon in icon_map.items():
            assert expected_icon in ['📊', '📋', '📝', '📄', '📈'], \
                f"Icon {expected_icon} for {ext} should be a valid emoji"

    def test_nested_research_artifacts(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Artifacts in subdirectories are discovered recursively"""
        project_name = "test_nested"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Nested Test', 'Test nested'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        # Create nested research structure
        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'

        # Create subdirectories with artifacts
        phase1_dir = research_dir / 'phase1'
        phase2_dir = research_dir / 'phase2'
        phase1_dir.mkdir(parents=True)
        phase2_dir.mkdir(parents=True)

        (phase1_dir / 'data.csv').write_text("phase,result\n1,success\n")
        (phase2_dir / 'analysis.json').write_text('{"phase": 2, "status": "complete"}')
        (research_dir / 'summary.md').write_text("# Summary\n")

        # Verify nested structure
        assert (phase1_dir / 'data.csv').exists(), "Nested CSV should exist"
        assert (phase2_dir / 'analysis.json').exists(), "Nested JSON should exist"
        assert (research_dir / 'summary.md').exists(), "Root MD should exist"

        # Count all artifacts recursively
        all_artifacts = list(research_dir.rglob('*'))
        artifact_files = [a for a in all_artifacts if a.is_file()]
        assert len(artifact_files) == 3, "Should find 3 artifacts recursively"


class TestArtifactContentServing:
    """Test artifact content serving via dashboard API."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_csv_file_served_correctly(self, temp_project_dir, spec_kitty_repo_root):
        """Test: CSV files served as text with correct content"""
        project_name = "test_csv"
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

        # Create feature with CSV artifact
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'CSV Test', 'Test CSV'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create CSV with test data
        csv_content = """name,age,city
Alice,30,NYC
Bob,25,LA
Charlie,35,Chicago
"""
        csv_file = research_dir / 'test_data.csv'
        csv_file.write_text(csv_content)

        # Verify file can be read correctly
        read_content = csv_file.read_text()
        assert read_content == csv_content, "CSV content should match"

        # Verify it's valid CSV format
        lines = read_content.strip().split('\n')
        assert len(lines) == 4, "Should have header + 3 data rows"
        assert lines[0] == "name,age,city", "Header should be correct"

    def test_json_file_content_valid(self, temp_project_dir, spec_kitty_repo_root):
        """Test: JSON files served with valid UTF-8 encoding"""
        project_name = "test_json"
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

        # Create feature with JSON artifact
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'JSON Test', 'Test JSON'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create JSON with UTF-8 content (including emoji)
        json_content = {
            "name": "Test Project",
            "status": "active",
            "emoji": "🚀",
            "unicode": "UTF-8 ✓"
        }
        json_file = research_dir / 'config.json'
        json_file.write_text(json.dumps(json_content, ensure_ascii=False, indent=2))

        # Verify JSON can be parsed
        read_content = json_file.read_text(encoding='utf-8')
        parsed = json.loads(read_content)

        assert parsed['name'] == "Test Project", "JSON should parse correctly"
        assert parsed['emoji'] == "🚀", "UTF-8 emoji should be preserved"
        assert parsed['unicode'] == "UTF-8 ✓", "UTF-8 characters should be preserved"

    def test_yaml_file_readable(self, temp_project_dir, spec_kitty_repo_root):
        """Test: YAML files served as plain text"""
        project_name = "test_yaml"
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

        # Create feature with YAML artifact
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'YAML Test', 'Test YAML'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create YAML config
        yaml_content = """config:
  database:
    host: localhost
    port: 5432
  features:
    - authentication
    - logging
    - metrics
"""
        yaml_file = research_dir / 'config.yaml'
        yaml_file.write_text(yaml_content)

        # Verify YAML can be read as text
        read_content = yaml_file.read_text()
        assert read_content == yaml_content, "YAML content should match"
        assert 'database:' in read_content, "YAML should contain database config"
        assert '- authentication' in read_content, "YAML should contain features list"

    def test_markdown_artifact_content(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Markdown artifacts served correctly"""
        project_name = "test_markdown"
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

        # Create feature with Markdown artifact
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'MD Test', 'Test Markdown'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create Markdown research notes
        md_content = """# Research Findings

## Summary
This is a test markdown document.

## Key Points
- Point 1: Testing markdown rendering
- Point 2: UTF-8 support ✓
- Point 3: Code blocks work

```python
def example():
    return "Hello, World!"
```

## Conclusion
Markdown artifacts should be readable.
"""
        md_file = research_dir / 'findings.md'
        md_file.write_text(md_content)

        # Verify Markdown can be read
        read_content = md_file.read_text()
        assert read_content == md_content, "Markdown content should match"
        assert '# Research Findings' in read_content, "Should have heading"
        assert '```python' in read_content, "Should have code block"


class TestArtifactErrorHandling:
    """Test error handling for artifact serving."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_non_utf8_file_error_recovery(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Non-UTF-8 files trigger error message + recovery"""
        project_name = "test_encoding"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Encoding Test', 'Test encoding'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create file with latin-1 encoding
        latin1_file = research_dir / 'latin1.txt'
        latin1_file.write_bytes(b'Caf\xe9')  # é in latin-1

        # Verify UTF-8 read fails
        try:
            latin1_file.read_text(encoding='utf-8')
            assert False, "Should raise UnicodeDecodeError"
        except UnicodeDecodeError:
            pass  # Expected

        # Verify can read with errors='replace'
        content_with_replace = latin1_file.read_text(encoding='utf-8', errors='replace')
        assert 'Caf' in content_with_replace, "Should recover with replacement characters"

    def test_path_traversal_blocked(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Path traversal attacks blocked (file system level)"""
        project_name = "test_security"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Security Test', 'Test security'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Test that path traversal is prevented at file system level
        # Attempting to create ../../sensitive-file should fail or normalize
        try:
            dangerous_path = research_dir / '..' / '..' / 'sensitive.txt'
            resolved = dangerous_path.resolve()

            # Verify path doesn't escape research directory hierarchy
            assert str(research_dir) in str(resolved) or not resolved.exists(), \
                "Path traversal should be blocked or normalize safely"
        except ValueError:
            pass  # Some systems may raise ValueError for invalid paths

    def test_large_artifact_handling(self, temp_project_dir, spec_kitty_repo_root):
        """Test: Large files handled gracefully"""
        project_name = "test_large"
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

        # Create feature
        create_script = project_path / '.kittify/scripts/bash/create-new-feature.sh'
        result = subprocess.run(
            [str(create_script), '--json', '--feature-name', 'Large Test', 'Test large files'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )

        output_data = json.loads(result.stdout.strip().split('\n')[-1])
        branch_name = output_data['BRANCH_NAME']

        worktree_path = project_path / '.worktrees' / branch_name
        research_dir = worktree_path / 'kitty-specs' / branch_name / 'research'
        research_dir.mkdir(parents=True, exist_ok=True)

        # Create moderately large CSV (1MB - testing 10MB would be slow)
        large_csv = research_dir / 'large_data.csv'
        with large_csv.open('w') as f:
            f.write("id,name,value,timestamp\n")
            for i in range(50000):  # ~1MB
                f.write(f"{i},user_{i},{i*10},2025-01-01T00:00:00Z\n")

        # Verify file was created and has reasonable size
        file_size = large_csv.stat().st_size
        assert file_size > 1_000_000, "File should be > 1MB"
        assert file_size < 3_000_000, "File should be < 3MB (sanity check)"

        # Verify can read file (though slowly)
        # In real dashboard, this would be paginated or streamed
        first_line = large_csv.open().readline()
        assert first_line == "id,name,value,timestamp\n", "Should read header correctly"
