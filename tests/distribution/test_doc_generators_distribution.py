"""
Doc Generators Distribution Tests (v0.12.0)

Validates JSDoc, Sphinx, and rustdoc generators load and operate from the
installed package without SPEC_KITTY_TEMPLATE_ROOT or other dev overrides.
"""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def clean_environment(monkeypatch):
    """
    Clean environment simulating PyPI user (NO development overrides).

    CRITICAL: This fixture is the difference between catching Issues #62-64
    and shipping broken packages. ALL distribution tests must use this.
    """
    env = os.environ.copy()
    for key in list(env.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            env.pop(key, None)
    for key in list(os.environ.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            monkeypatch.delenv(key, raising=False)
    return env


class TestJSDocGenerator:
    """Validate JSDoc generator loads from package and detects projects correctly."""

    def test_jsdoc_detects_javascript_projects(self, tmp_path, clean_environment):
        """
        Test: JSDoc generator detects JavaScript/TypeScript projects from package.

        Why: This test would catch Issues #62-64 pattern. If JSDoc generator
        tries to load templates from local repo (via SPEC_KITTY_TEMPLATE_ROOT),
        it fails for PyPI users who don't have that env var or local repo.
        """
        project_dir = tmp_path / "js-project"
        project_dir.mkdir()
        package_json = project_dir / "package.json"
        package_json.write_text('{"name": "test-project", "version": "1.0.0"}')
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.js").write_text("console.log('test');")

        try:
            from specify_cli.doc_generators import JSDocGenerator
        except ImportError as exc:
            pytest.fail(
                "CRITICAL: Cannot import JSDocGenerator from installed package\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken\n"
                "This is the EXACT failure pattern from Issues #62-64"
            )

        generator = JSDocGenerator()
        detected = generator.detect(project_dir)

        assert detected is True, (
            "JSDoc generator should detect JavaScript project\n"
            f"Project: {project_dir}\n"
            "DO NOT SHIP v0.12.0 - detection failure breaks PyPI users"
        )
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ, (
            "Test setup error: SPEC_KITTY_TEMPLATE_ROOT should not be set\n"
            "DO NOT SHIP v0.12.0 - distribution test invalid"
        )

    def test_jsdoc_template_accessible_from_package(self, tmp_path, clean_environment):
        """
        Test: JSDoc configuration creation works from pip package.

        Why: If generator logic depends on local repo resources, config creation
        fails for PyPI users. This must fail loudly if packaging is broken.
        """
        from specify_cli.doc_generators import JSDocGenerator

        output_dir = tmp_path / "jsdoc-output"
        generator = JSDocGenerator()

        try:
            config_path = generator.configure(output_dir, {})
        except Exception as exc:
            pytest.fail(
                "CRITICAL: JSDoc config creation failed without SPEC_KITTY_TEMPLATE_ROOT\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )

        assert config_path.exists(), (
            f"Config file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config not created"
        )
        config_data = json.loads(config_path.read_text())
        assert "source" in config_data, (
            "JSDoc config missing 'source' section\n"
            "DO NOT SHIP v0.12.0 - broken config"
        )
        assert "plugins" in config_data, (
            "JSDoc config missing 'plugins' section\n"
            "DO NOT SHIP v0.12.0 - broken config"
        )

    def test_jsdoc_creates_valid_config(self, tmp_path, clean_environment):
        """
        Test: JSDoc creates valid jsdoc.json configuration from package.

        Why: End-to-end config generation must work without dev overrides.
        """
        from specify_cli.doc_generators import JSDocGenerator

        output_dir = tmp_path / "jsdoc-config"
        generator = JSDocGenerator()
        config_path = generator.configure(output_dir, {"project_name": "Test"})

        assert config_path.exists(), (
            f"Config file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config missing"
        )
        try:
            config_data = json.loads(config_path.read_text())
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Generated config is not valid JSON: {exc}\n"
                "DO NOT SHIP v0.12.0 - invalid config"
            )
        assert isinstance(config_data, dict), (
            "Config should be JSON object\n"
            "DO NOT SHIP v0.12.0 - invalid config"
        )
        assert config_data.get("opts", {}).get("destination"), (
            "Config should include opts.destination\n"
            "DO NOT SHIP v0.12.0 - invalid config"
        )


class TestSphinxGenerator:
    """Validate Sphinx generator loads from package and detects projects correctly."""

    def test_sphinx_detects_python_projects(self, tmp_path, clean_environment):
        """
        Test: Sphinx generator detects Python projects from package.
        """
        project_dir = tmp_path / "py-project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        (project_dir / "module.py").write_text("def hello():\n    return 'hi'\n")

        try:
            from specify_cli.doc_generators import SphinxGenerator
        except ImportError as exc:
            pytest.fail(
                "CRITICAL: Cannot import SphinxGenerator from installed package\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )

        generator = SphinxGenerator()
        detected = generator.detect(project_dir)
        assert detected is True, (
            "Sphinx generator should detect Python project\n"
            f"Project: {project_dir}\n"
            "DO NOT SHIP v0.12.0 - detection failure breaks PyPI users"
        )

    def test_sphinx_template_accessible_from_package(self, tmp_path, clean_environment):
        """
        Test: Sphinx configuration creation works from pip package.
        """
        from specify_cli.doc_generators import SphinxGenerator

        output_dir = tmp_path / "sphinx-output"
        generator = SphinxGenerator()

        try:
            config_path = generator.configure(output_dir, {"project_name": "Test"})
        except Exception as exc:
            pytest.fail(
                "CRITICAL: Sphinx config creation failed without SPEC_KITTY_TEMPLATE_ROOT\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )

        assert config_path.exists(), (
            f"Conf file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config not created"
        )
        conf_content = config_path.read_text()
        assert "sphinx.ext.autodoc" in conf_content, (
            "Conf.py missing expected Sphinx extensions\n"
            "DO NOT SHIP v0.12.0 - broken config"
        )

    def test_sphinx_creates_valid_conf_py(self, tmp_path, clean_environment):
        """
        Test: Sphinx creates valid conf.py configuration from package.
        """
        from specify_cli.doc_generators import SphinxGenerator

        output_dir = tmp_path / "sphinx-config"
        generator = SphinxGenerator()
        config_path = generator.configure(output_dir, {"project_name": "Test"})

        assert config_path.exists(), (
            f"Conf file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config missing"
        )
        conf_content = config_path.read_text()
        try:
            compile(conf_content, str(config_path), "exec")
        except SyntaxError as exc:
            pytest.fail(
                f"Generated conf.py is not valid Python: {exc}\n"
                "DO NOT SHIP v0.12.0 - invalid config"
            )


class TestRustdocGenerator:
    """Validate rustdoc generator loads from package and detects projects correctly."""

    def test_rustdoc_detects_rust_projects(self, tmp_path, clean_environment):
        """
        Test: rustdoc generator detects Rust projects from package.
        """
        project_dir = tmp_path / "rust-project"
        project_dir.mkdir()
        (project_dir / "Cargo.toml").write_text("[package]\nname = \"test\"\nversion = \"0.1.0\"\n")
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "lib.rs").write_text("pub fn hello() {}\n")

        try:
            from specify_cli.doc_generators import RustdocGenerator
        except ImportError as exc:
            pytest.fail(
                "CRITICAL: Cannot import RustdocGenerator from installed package\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )

        generator = RustdocGenerator()
        detected = generator.detect(project_dir)
        assert detected is True, (
            "Rustdoc generator should detect Rust project\n"
            f"Project: {project_dir}\n"
            "DO NOT SHIP v0.12.0 - detection failure breaks PyPI users"
        )

    def test_rustdoc_template_accessible_from_package(self, tmp_path, clean_environment):
        """
        Test: rustdoc configuration instructions creation works from pip package.
        """
        from specify_cli.doc_generators import RustdocGenerator

        output_dir = tmp_path / "rustdoc-output"
        generator = RustdocGenerator()

        try:
            config_path = generator.configure(output_dir, {})
        except Exception as exc:
            pytest.fail(
                "CRITICAL: rustdoc instructions creation failed without SPEC_KITTY_TEMPLATE_ROOT\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0 - packaging broken"
            )

        assert config_path.exists(), (
            f"Rustdoc config file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config not created"
        )
        content = config_path.read_text()
        assert "[package.metadata.docs.rs]" in content, (
            "Rustdoc instructions missing docs.rs metadata block\n"
            "DO NOT SHIP v0.12.0 - broken instructions"
        )

    def test_rustdoc_creates_config_instructions(self, tmp_path, clean_environment):
        """
        Test: rustdoc creates valid configuration instructions from package.
        """
        from specify_cli.doc_generators import RustdocGenerator

        output_dir = tmp_path / "rustdoc-config"
        generator = RustdocGenerator()
        config_path = generator.configure(output_dir, {"document_private": True})

        assert config_path.exists(), (
            f"Rustdoc config file should be created: {config_path}\n"
            "DO NOT SHIP v0.12.0 - config missing"
        )
        content = config_path.read_text()
        assert "--document-private-items" in content, (
            "Rustdoc instructions should mention private item flag\n"
            "DO NOT SHIP v0.12.0 - invalid instructions"
        )


class TestGeneratorIntegration:
    """Validate generator integration and package accessibility."""

    def test_all_generators_importable_from_package(self, clean_environment):
        """
        Test: All generators accessible via importlib (no SPEC_KITTY_TEMPLATE_ROOT).
        """
        try:
            from specify_cli.doc_generators import (
                JSDocGenerator,
                SphinxGenerator,
                RustdocGenerator,
            )
        except ImportError as exc:
            pytest.fail(
                "CRITICAL: Cannot import generators from package\n"
                f"Error: {exc}\n"
                "DO NOT SHIP v0.12.0"
            )

        assert inspect.isclass(JSDocGenerator), (
            "JSDocGenerator should be a class\n"
            "DO NOT SHIP v0.12.0 - import broken"
        )
        assert inspect.isclass(SphinxGenerator), (
            "SphinxGenerator should be a class\n"
            "DO NOT SHIP v0.12.0 - import broken"
        )
        assert inspect.isclass(RustdocGenerator), (
            "RustdocGenerator should be a class\n"
            "DO NOT SHIP v0.12.0 - import broken"
        )

    def test_generator_detection_works_without_dev_env_vars(self, tmp_path, clean_environment):
        """
        Test: Detection logic does not rely on SPEC_KITTY_* environment variables.
        """
        from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator

        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "package.json").write_text('{"name": "js"}')

        py_dir = tmp_path / "py"
        py_dir.mkdir()
        (py_dir / "setup.py").write_text("from setuptools import setup\nsetup(name='py')\n")

        rust_dir = tmp_path / "rust"
        rust_dir.mkdir()
        (rust_dir / "Cargo.toml").write_text("[package]\nname = \"rust\"\nversion = \"0.1.0\"\n")

        assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ, (
            "Test setup error: SPEC_KITTY_TEMPLATE_ROOT should not be set\n"
            "DO NOT SHIP v0.12.0 - distribution test invalid"
        )

        assert JSDocGenerator().detect(js_dir) is True, (
            "JSDoc detection should work without dev env vars\n"
            "DO NOT SHIP v0.12.0 - env var dependency"
        )
        assert SphinxGenerator().detect(py_dir) is True, (
            "Sphinx detection should work without dev env vars\n"
            "DO NOT SHIP v0.12.0 - env var dependency"
        )
        assert RustdocGenerator().detect(rust_dir) is True, (
            "Rustdoc detection should work without dev env vars\n"
            "DO NOT SHIP v0.12.0 - env var dependency"
        )

    def test_generator_configs_use_relative_source_paths(self, tmp_path, clean_environment):
        """
        Test: Generator configs use relative source paths (no repo leakage).
        """
        from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator

        js_output = tmp_path / "js-output"
        js_config = JSDocGenerator().configure(js_output, {})
        js_data = json.loads(js_config.read_text())

        for include_path in js_data.get("source", {}).get("include", []):
            assert not Path(include_path).is_absolute(), (
                f"JSDoc source path should be relative: {include_path}\n"
                "DO NOT SHIP v0.12.0 - absolute path leakage"
            )

        sphinx_output = tmp_path / "sphinx-output"
        sphinx_config = SphinxGenerator().configure(sphinx_output, {"project_name": "Test"})
        sphinx_content = sphinx_config.read_text()
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in sphinx_content, (
            "Sphinx config should not include template root\n"
            "DO NOT SHIP v0.12.0 - template leakage"
        )

        rust_output = tmp_path / "rust-output"
        rust_config = RustdocGenerator().configure(rust_output, {})
        rust_content = rust_config.read_text()
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in rust_content, (
            "Rustdoc instructions should not include template root\n"
            "DO NOT SHIP v0.12.0 - template leakage"
        )

    def test_multilanguage_project_detection(self, tmp_path, clean_environment):
        """
        Test: Multi-language project detected correctly by all generators.
        """
        from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator

        project_dir = tmp_path / "multi-project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "multi"}')
        (project_dir / "pyproject.toml").write_text("[project]\nname = 'multi'\n")
        (project_dir / "Cargo.toml").write_text("[package]\nname = \"multi\"\nversion = \"0.1.0\"\n")

        assert JSDocGenerator().detect(project_dir) is True, (
            "JSDoc should detect JS/TS indicators in multi-language project\n"
            "DO NOT SHIP v0.12.0 - detection broken"
        )
        assert SphinxGenerator().detect(project_dir) is True, (
            "Sphinx should detect Python indicators in multi-language project\n"
            "DO NOT SHIP v0.12.0 - detection broken"
        )
        assert RustdocGenerator().detect(project_dir) is True, (
            "Rustdoc should detect Rust indicators in multi-language project\n"
            "DO NOT SHIP v0.12.0 - detection broken"
        )

    def test_generator_error_handling(self, tmp_path, clean_environment):
        """
        Test: Generator error handling when configuration cannot be written.
        """
        from specify_cli.doc_generators import JSDocGenerator

        output_path = tmp_path / "blocked-output"
        output_path.write_text("not a directory")

        with pytest.raises((FileExistsError, OSError)) as exc_info:
            JSDocGenerator().configure(output_path, {})

        assert "File exists" in str(exc_info.value), (
            "Expected error when config output path is not a directory\n"
            "DO NOT SHIP v0.12.0 - error handling broken"
        )

        assert output_path.is_file(), (
            "Setup should create a file to block config creation\n"
            "DO NOT SHIP v0.12.0 - invalid test setup"
        )

    def test_no_template_path_leakage(self, tmp_path, clean_environment, spec_kitty_repo_root):
        """
        Test: Generated configs do not include local repo or template paths.
        """
        from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator

        js_config = JSDocGenerator().configure(tmp_path / "js", {})
        sphinx_config = SphinxGenerator().configure(tmp_path / "sphinx", {"project_name": "LeakTest"})
        rust_config = RustdocGenerator().configure(tmp_path / "rust", {})

        forbidden = [
            str(spec_kitty_repo_root),
            "SPEC_KITTY_TEMPLATE_ROOT",
        ]

        for config_path in [js_config, sphinx_config, rust_config]:
            content = config_path.read_text()
            for pattern in forbidden:
                assert pattern not in content, (
                    f"Config should not include local repo/template path: {pattern}\n"
                    f"Config: {config_path}\n"
                    "DO NOT SHIP v0.12.0 - path leakage"
                )
