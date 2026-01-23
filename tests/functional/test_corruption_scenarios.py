"""
File corruption and encoding issue tests (WP13: T080).

Tests handling of JSON corruption, file encoding issues, and symlink problems.
"""
import pytest
import json
from pathlib import Path
import yaml


@pytest.mark.functional
@pytest.mark.adversarial
class TestJSONCorruption:
    """Test handling of corrupted JSON files."""

    def test_corrupted_meta_json(self, tmp_path):
        """Corrupted meta.json file."""
        meta_file = tmp_path / "meta.json"
        meta_file.write_text("{ corrupted json")

        with pytest.raises(json.JSONDecodeError):
            json.loads(meta_file.read_text())

    def test_truncated_json(self, tmp_path):
        """JSON file truncated mid-write."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"key": "va')  # Truncated value

        with pytest.raises(json.JSONDecodeError):
            json.loads(state_file.read_text())

    def test_empty_json_file(self, tmp_path):
        """Empty JSON file."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("")

        with pytest.raises(json.JSONDecodeError):
            json.loads(json_file.read_text())

    def test_json_with_trailing_comma(self, tmp_path):
        """JSON with trailing comma (invalid)."""
        json_file = tmp_path / "trailing.json"
        json_file.write_text('{"key": "value",}')

        with pytest.raises(json.JSONDecodeError):
            json.loads(json_file.read_text())

    def test_json_with_single_quotes(self, tmp_path):
        """JSON with single quotes (invalid)."""
        json_file = tmp_path / "singlequote.json"
        json_file.write_text("{'key': 'value'}")

        with pytest.raises(json.JSONDecodeError):
            json.loads(json_file.read_text())

    def test_json_with_comments(self, tmp_path):
        """JSON with comments (invalid in standard JSON)."""
        json_file = tmp_path / "comments.json"
        json_file.write_text('{"key": "value" // comment}')

        with pytest.raises(json.JSONDecodeError):
            json.loads(json_file.read_text())


@pytest.mark.functional
@pytest.mark.adversarial
class TestYAMLCorruption:
    """Test handling of corrupted YAML files."""

    def test_malformed_yaml_frontmatter(self, tmp_path):
        """Malformed YAML frontmatter."""
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text("""---
title: Test
dependencies: [unclosed
---

# Content
""")

        with pytest.raises(yaml.YAMLError):
            content = wp_file.read_text()
            # Extract frontmatter
            parts = content.split("---")
            yaml.safe_load(parts[1])

    def test_yaml_with_tabs(self, tmp_path):
        """YAML with tabs (can cause issues)."""
        yaml_file = tmp_path / "tabs.yaml"
        yaml_file.write_text("key:\n\tvalue")  # Tab instead of spaces

        # YAML should handle tabs but may warn
        try:
            data = yaml.safe_load(yaml_file.read_text())
            # If it parses, check the value
            assert "key" in data or data is None
        except yaml.YAMLError:
            # Some YAML parsers reject tabs
            pass


@pytest.mark.functional
@pytest.mark.adversarial
class TestFileEncodingIssues:
    """Test handling of file encoding issues."""

    def test_non_utf8_content(self, tmp_path):
        """File with non-UTF8 content."""
        bad_file = tmp_path / "bad-encoding.txt"
        bad_file.write_bytes(b"\xff\xfe Invalid UTF-8 \x80\x81")

        with pytest.raises(UnicodeDecodeError):
            bad_file.read_text(encoding='utf-8')

    def test_utf8_with_bom(self, tmp_path):
        """UTF-8 file with BOM marker."""
        bom_file = tmp_path / "bom.txt"
        bom_file.write_bytes(b"\xef\xbb\xbfHello World")

        content = bom_file.read_text(encoding='utf-8-sig')
        assert content == "Hello World"

    def test_latin1_content(self, tmp_path):
        """File with Latin-1 encoded content."""
        latin1_file = tmp_path / "latin1.txt"
        latin1_file.write_bytes("Héllo Wörld".encode('latin-1'))

        # Reading as UTF-8 may fail or produce garbage
        try:
            content = latin1_file.read_text(encoding='utf-8')
            # May succeed but produce wrong characters
        except UnicodeDecodeError:
            pass

    def test_null_bytes_in_file(self, tmp_path):
        """File containing null bytes."""
        null_file = tmp_path / "null.txt"
        null_file.write_bytes(b"Hello\x00World")

        content = null_file.read_text()
        assert "\x00" in content


@pytest.mark.functional
@pytest.mark.adversarial
class TestSymlinkProblems:
    """Test handling of symbolic link issues."""

    def test_broken_symlink(self, tmp_path):
        """Broken symlink (target doesn't exist)."""
        broken_link = tmp_path / "broken"
        broken_link.symlink_to(tmp_path / "nonexistent")

        assert broken_link.is_symlink()
        assert not broken_link.exists()  # Target doesn't exist

    def test_circular_symlinks(self, tmp_path):
        """Circular symlinks (A -> B -> A)."""
        link_a = tmp_path / "a"
        link_b = tmp_path / "b"

        link_a.symlink_to(link_b)
        link_b.symlink_to(link_a)

        # Resolving should fail
        with pytest.raises(OSError):
            link_a.resolve(strict=True)

    def test_symlink_to_directory(self, tmp_path):
        """Symlink pointing to directory."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file.txt").write_text("content")

        link = tmp_path / "link"
        link.symlink_to(target_dir)

        # Should be able to access through symlink
        assert (link / "file.txt").read_text() == "content"

    def test_symlink_chain(self, tmp_path):
        """Long chain of symlinks."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        # Create chain: link1 -> link2 -> link3 -> target
        prev = target
        for i in range(3, 0, -1):
            link = tmp_path / f"link{i}"
            link.symlink_to(prev)
            prev = link

        # Should resolve through chain
        assert (tmp_path / "link1").read_text() == "content"


@pytest.mark.functional
@pytest.mark.adversarial
class TestStateFileCorruption:
    """Test handling of orchestration state file corruption."""

    def test_state_missing_required_fields(self, tmp_path):
        """State JSON missing required fields."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"incomplete": true}')

        data = json.loads(state_file.read_text())
        assert "feature" not in data
        assert "wps" not in data

    def test_state_wrong_types(self, tmp_path):
        """State JSON with wrong value types."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"wps": "should-be-object"}')

        data = json.loads(state_file.read_text())
        assert isinstance(data["wps"], str)  # Wrong type

    def test_state_extra_fields(self, tmp_path):
        """State JSON with unexpected extra fields."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"wps": {}, "unknown_field": "value"}')

        data = json.loads(state_file.read_text())
        # Should still parse, extra fields ignored
        assert "unknown_field" in data
